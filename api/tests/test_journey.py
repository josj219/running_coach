"""J01-J10 acceptance tests. Every scenario owns its user and observes persisted results."""
import copy
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4
import httpx
import pytest
from sqlalchemy import select
from app.auth import create_token
from app.db import (Assessment, ExternalActivity, Integration, JourneyEvent, PlanSession,
                    SessionLocal, User, UserProfile, WeeklyPlan, WorkoutLog)
from app.main import app
from app.services import coach
from app.services.fitness import Run, data_status, snapshot
from app.services.context import week_start_of


@pytest.fixture
async def runner(client):
    async with SessionLocal() as db:
        user = User(email=f"journey-{uuid4()}@test.invalid", nickname="테스트", onboarded=True)
        db.add(user); await db.flush()
        uid = user.id
        db.add(UserProfile(user_id=uid))
        await db.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test",
        headers={"Authorization": f"Bearer {create_token(uid)}"}) as c:
        c.uid = uid
        yield c


async def goal(c):
    r = await c.put("/api/goal", json={"race_type": "풀마라톤", "target_time": "03:30:00", "target_date": str(date.today() + timedelta(days=49))})
    assert r.status_code == 200, r.text
    return r.json()


async def log(c, km=8, days=0, **extra):
    r = await c.post("/api/workout-logs", json={"log_date": str(date.today() - timedelta(days=days)),
        "kind": "easy", "distance_km": km, "duration_sec": int(km * 360), **extra})
    assert r.status_code == 201, r.text
    return r.json()


async def plan(c, km=6, kind="easy", minutes=36):
    today = date.today(); ws = week_start_of(today); y, w, _ = ws.isocalendar()
    async with SessionLocal() as db:
        p = WeeklyPlan(user_id=c.uid, iso_year=y, iso_week=w, week_start=ws, goal_km=km)
        db.add(p); await db.flush()
        s = PlanSession(plan_id=p.id, session_date=today, weekday=today.weekday(), kind=kind,
                        distance_km=km, duration_min=minutes, title="오늘 계획", is_rest=False)
        db.add(s); await db.commit()
        return s.id


async def test_j01_empty_pb_and_recent_threshold(runner):
    await goal(runner)
    d = (await runner.get("/api/dashboard")).json()
    assert d["current"]["predicted_sec"] is None
    assert d["current"]["data_status"]["state"] == "insufficient"
    await runner.patch("/api/profile", json={"pb_10k": "00:42:13"})
    d = (await runner.get("/api/dashboard")).json()
    assert d["current"]["data_status"]["state"] == "pb_reference"
    assert "날짜 미상" in d["message"]
    assert all(p["predicted_sec"] is None for p in d["series"])
    assert d["current"]["readiness"]["endurance"] is None
    for days in [0, 3, 6, 9, 12]:
        await log(runner, days=days)
    assert not (await runner.get("/api/dashboard")).json()["current"]["data_status"]["sufficient"]
    await log(runner, days=15)
    d = (await runner.get("/api/dashboard")).json()
    assert d["current"]["data_status"]["sufficient"]
    assert d["current"]["data_status"]["record_count"] == 6
    assert "probability" not in str(d.keys())
    assert d["outlook"]["status"] == "조건부 검토 · 기록 전망 미산출"


def test_j05_nonrunning_unknown_and_inconsistent_are_excluded():
    now = date.today()
    baseline = snapshot([], [], 42.195, 12600, {}, now)
    for r in [Run(now, 40, 3600, "other"), Run(now, 40, 3600, "easy", sport="cycling"),
              Run(now, 40, 3600, "easy", sport="running"), Run(now, 10, 3600, "easy", "3:00")]:
        assert r.exclusion_reason()
        s = snapshot([r], [], 42.195, 12600, {}, now)
        assert s["predicted_sec"] == baseline["predicted_sec"] is None
        assert s["basis"]["vol_4wk_km"] == 0
    assert not Run(now, 8, 2880, "other", sport="running").exclusion_reason()


async def test_j03_two_workouts_edit_review_and_idempotency(runner):
    a = await log(runner, 1, client_request_id="first")
    again = await log(runner, 1, client_request_id="first")
    b = await log(runner, 8)
    assert a["id"] == again["id"] != b["id"]
    assert again["created"] is False
    assert (await runner.get("/api/today")).json()["day_km"] == 9
    assert (await runner.post(f"/api/workout-logs/{a['id']}/review")).status_code == 200
    r = await runner.patch(f"/api/workout-logs/{a['id']}", json={"log_date": str(date.today()), "distance_km": 2, "duration_sec": 720, "change_reason": "거리 오입력 정정", "expected_revision": 1})
    assert r.status_code == 200, r.text
    rows = (await runner.get("/api/workout-logs")).json()["items"]
    assert len(rows) == 2 and sum(l["distance_km"] for l in rows) == 10
    assert next(l for l in rows if l["id"] == a["id"])["review"]["is_stale"] is True
    assert (await runner.patch(f"/api/workout-logs/{a['id']}", json={"log_date": str(date.today()), "expected_revision": 1})).status_code == 409
    assert (await runner.patch("/api/workout-logs/999999", json={"log_date": str(date.today())})).status_code == 404


async def test_j02_import_cross_provider_and_distinct_same_day(runner):
    await goal(runner)
    start = datetime.now(timezone.utc).replace(hour=1, minute=0)
    async with SessionLocal() as db:
        rows = [ExternalActivity(user_id=runner.uid, provider=provider, external_id=str(i), sport_type="Run",
                    start_date=start + timedelta(hours=offset), distance_km=12, duration_sec=4320)
                for i, (provider, offset) in enumerate([("garmin", 0), ("strava", 0), ("garmin", 8)])]
        db.add_all(rows); await db.commit(); ids = [a.id for a in rows]
    pending = (await runner.get("/api/integrations/activities")).json()
    assert pending["pending_count"] == 3
    r = await runner.post("/api/integrations/activities/import", json={"activity_ids": ids})
    assert r.status_code == 200, r.text
    assert r.json()["created_count"] == 2
    repeat = await runner.post("/api/integrations/activities/import", json={"activity_ids": ids})
    assert repeat.json()["created_count"] == 0
    assert (await runner.get("/api/integrations/activities")).json()["pending_count"] == 0
    d = (await runner.get("/api/dashboard")).json()
    assert d["series"][-1]["week_km"] == 24
    assert len((await runner.get("/api/workout-logs")).json()["items"]) == 2
    assert (await runner.post("/api/integrations/activities/import", json={"activity_ids": [999999]})).status_code == 404


async def test_j06_partial_participation_and_time_workout(runner):
    await plan(runner)
    a = await log(runner, 1)
    assert a["session_status"] == "partial"
    w = (await runner.get("/api/weeks/current")).json()
    assert w["progress"]["participation_rate"] == 100
    assert w["progress"]["completion_rate"] == 0
    assert w["sessions"][0]["actual_distance_km"] == 1
    b = await log(runner, 5)
    assert b["session_status"] == "done"
    w = (await runner.get("/api/weeks/current")).json()
    assert w["progress"]["completion_rate"] == 100
    assert len(w["sessions"][0]["logs"]) == 2


async def test_j06_strength_duration_and_explicit_substitution(runner):
    await plan(runner, km=0, kind="strength", minutes=30)
    a = await log(runner, 0, kind="strength", sport="strength", duration_sec=600)
    assert a["session_status"] == "partial"
    b = await log(runner, 0, kind="strength", sport="strength", duration_sec=1200)
    assert b["session_status"] == "done"
    assert (await runner.get("/api/weeks/current")).json()["progress"]["week_km"] == 0


async def test_j04_pb_goal_and_record_correction_preserve_assessments(runner):
    g = await goal(runner)
    for day in [0, 3, 6, 9, 12, 15]:
        last = await log(runner, 8, days=day)
    await runner.patch("/api/profile", json={"pb_10k": "42:13", "pb_10k_date": str(date.today() - timedelta(days=100))})
    d1 = (await runner.get("/api/dashboard")).json()
    async with SessionLocal() as db:
        frozen = copy.deepcopy((await db.get(Assessment, d1["assessment_id"])).result)
    await runner.patch("/api/profile", json={"pb_10k": "40:00"})
    d2 = (await runner.get("/api/dashboard")).json()
    assert d2["anchor"] == d1["anchor"]
    await runner.patch(f"/api/workout-logs/{last['id']}", json={"log_date": str(date.today() - timedelta(days=15)), "distance_km": 7, "duration_sec": 2520, "change_reason": "GPS 거리 정정"})
    await runner.put("/api/goal", json={"race_type": "하프", "target_time": "01:40:00"})
    history = (await runner.get("/api/goals")).json()["items"]
    assert len(history) == 2 and history[1]["id"] == g["id"] and not history[1]["is_active"]
    async with SessionLocal() as db:
        saved = await db.get(Assessment, d1["assessment_id"])
        assert saved.result == frozen and saved.goal_id == g["id"]
        events = list((await db.execute(select(JourneyEvent).where(JourneyEvent.user_id == runner.uid))).scalars())
        assert any(e.reason == "GPS 거리 정정" for e in events)


async def test_j09_preview_apply_stale_proposal_and_preserve_completed(runner, monkeypatch):
    sid = await plan(runner)
    async def generate(*args):
        return {"adjusted": True, "session": {"distance_km": 3, "duration_min": 20, "kind": "easy"}, "main": "회복 3km", "warmup": "걷기"}
    monkeypatch.setattr(coach, "generate", generate)
    initial = await runner.post("/api/daily-plans", json={})
    assert initial.status_code == 201
    preview = await runner.post("/api/daily-plans", json={"condition_note": "수면 부족", "preview": True})
    assert preview.json()["requires_apply"]
    pid = preview.json()["proposal_id"]
    assert (await runner.post(f"/api/daily-plans/proposals/{pid}/apply")).status_code == 200
    today = (await runner.get("/api/today")).json()
    assert today["daily_plan"]["sections"]["main"] == "회복 3km"
    assert today["session"]["distance_km"] == 3
    p2 = (await runner.post("/api/daily-plans", json={"preview": True})).json()["proposal_id"]
    await log(runner, 3)
    assert (await runner.post(f"/api/daily-plans/proposals/{p2}/apply")).status_code == 409
    assert (await runner.post("/api/daily-plans", json={})).status_code == 409
    async with SessionLocal() as db:
        events = list((await db.execute(select(JourneyEvent).where(JourneyEvent.user_id == runner.uid,
            JourneyEvent.event_type == "condition_changed"))).scalars())
        assert events[0].before["session"]["distance_km"] == 6
        assert events[-1].reason == "수면 부족"


async def test_j08_selected_task_plan_input_assignment_and_actual_evaluation(runner, monkeypatch):
    a = await log(runner, days=1)
    assert (await runner.post(f"/api/workout-logs/{a['id']}/review")).status_code == 200
    task = (await runner.post("/api/coaching-tasks", json={"source_log_id": a["id"], "proposal": "이지 런 체감 기록하기"})).json()
    messages = []
    async def generate(kind, prompt, message):
        messages.append(message)
        if kind == "weekly":
            return {"goal_km": 8, "sessions": [{"date": str(date.today()), "kind": "easy", "distance_km": 8}],
                "coaching_actions": [{"task_id": task["id"], "session_dates": [str(date.today())], "reason": "오늘 이지 런에 체감 기록 반영"}]}
        return {"coach_message": "수행 확인", "detail_md": "체감 입력 확인"}
    monkeypatch.setattr(coach, "generate", generate)
    r = await runner.post("/api/weekly-plans", json={})
    assert r.status_code == 201, r.text
    assert "이지 런 체감 기록하기" in messages[-1]
    assert r.json()["coaching_tasks"][0]["assignments"][0]["session_ids"]
    actual = await log(runner, 8, feel=3)
    assert (await runner.post("/api/weeks/current/evaluation")).status_code == 200
    tasks = (await runner.get("/api/coaching-tasks")).json()["items"]
    assert tasks[0]["evaluations"][0]["actual"][0]["log_id"] == actual["id"]
    assert "actual" in messages[-1]


async def test_j10_period_comparison_sample_requirements_and_original_logs(runner):
    await goal(runner)
    for day in [1, 3, 8, 10]:
        await log(runner, days=day, comparison_tag="평지 같은 코스 선선함", feel=3, avg_hr=140)
    end = date.today(); start = end - timedelta(days=6)
    r = await runner.get(f"/api/growth?start={start}&end={end}")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["current"]["distance_km"] == d["previous"]["distance_km"] == 16
    assert d["comparable"][0]["heart_rate"] == {"before": 140, "after": 140}
    assert len(d["logs"]) == 2 and d["logs"][0]["id"]
    empty = (await runner.get(f"/api/growth?start={end}&end={end}")).json()
    assert empty["comparable"] == [] and "비교 불가" in empty["comparison_message"]


async def test_j07_checkpoint_and_no_numeric_forecast(runner):
    g = await goal(runner)
    r = await runner.post("/api/checkpoints", json={"goal_id": g["id"], "review_date": str(date.today() + timedelta(days=14)), "evidence_needed": "계획 이행과 실제 러닝 기록"})
    assert r.status_code == 201
    assert (await runner.patch(f"/api/checkpoints/{r.json()['id']}", json={"decision": "현재 목표 유지, 다음 기록 확인"})).status_code == 200
    d = (await runner.get("/api/dashboard")).json()
    assert d["checkpoints"][0]["decision"]
    assert "probability" not in d["outlook"] and "predicted_sec" not in d["outlook"]


async def test_sync_failure_is_distinct_from_never_synced(runner, monkeypatch):
    from app.services import garmin
    timestamp = datetime.now(timezone.utc) - timedelta(days=1)
    async with SessionLocal() as db:
        db.add(Integration(user_id=runner.uid, provider="garmin", auth_blob="test", last_sync_at=timestamp))
        await db.commit()
    async def fail(*args):
        raise garmin.GarminError("mock connection failure")
    monkeypatch.setattr(garmin, "sync_activities", fail)
    assert (await runner.post("/api/integrations/garmin/sync")).status_code == 502
    state = (await runner.get("/api/integrations/activities")).json()["integrations"]["garmin"]
    assert state["last_sync_at"] and state["last_sync_error"]


async def test_cross_user_mutations_are_rejected(runner, client):
    a = await log(runner)
    r = await client.patch(f"/api/workout-logs/{a['id']}", json={"log_date": str(date.today()), "distance_km": 1})
    assert r.status_code == 404
    assert (await client.post(f"/api/workout-logs/{a['id']}/review")).status_code == 404
    assert (await client.post("/api/coaching-tasks", json={"source_log_id": a["id"], "proposal": "unauthorized"})).status_code == 422
    g = await goal(runner)
    assert (await client.post("/api/checkpoints", json={"goal_id": g["id"], "review_date": str(date.today()), "evidence_needed": "test"})).status_code == 404


async def test_explicit_unlinked_record_stays_unlinked_on_plan_generation(runner):
    a = await log(runner, session_id=None)
    await runner.post("/api/weekly-plans", json={})
    rows = (await runner.get("/api/workout-logs")).json()["items"]
    assert rows[0]["id"] == a["id"] and rows[0]["session_id"] is None


async def test_parallel_import_is_idempotent_on_postgresql(runner):
    from app.db import engine
    import asyncio
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL concurrency check runs in CI")
    async with SessionLocal() as db:
        a = ExternalActivity(user_id=runner.uid, provider="garmin", external_id="parallel",
            sport_type="Run", start_date=datetime.now(timezone.utc), distance_km=8, duration_sec=2880)
        db.add(a); await db.commit(); aid = a.id
    results = await asyncio.gather(*[runner.post("/api/integrations/activities/import", json={"activity_ids": [aid]}) for _ in range(3)])
    assert all(r.status_code == 200 for r in results)
    assert sum(r.json()["created_count"] for r in results) == 1


async def test_review_cannot_overwrite_a_record_edited_during_generation(runner, monkeypatch):
    a = await log(runner)
    async def generate(*args):
        changed = await runner.patch(f"/api/workout-logs/{a['id']}", json={
            "log_date": str(date.today()), "distance_km": 7, "duration_sec": 2520})
        assert changed.status_code == 200
        return coach.MOCK_RESPONSES["review"]
    monkeypatch.setattr(coach, "generate", generate)
    response = await runner.post(f"/api/workout-logs/{a['id']}/review")
    assert response.status_code == 409
    row = (await runner.get("/api/workout-logs")).json()["items"][0]
    assert row["distance_km"] == 7 and row["review"] is None


async def test_external_prefill_cannot_relabel_cycling_as_running(runner):
    async with SessionLocal() as db:
        db.add(ExternalActivity(user_id=runner.uid, provider="strava", external_id="cycle",
            sport_type="Ride", start_date=datetime.now(timezone.utc), distance_km=40, duration_sec=3600))
        await db.commit()
    response = await runner.post("/api/workout-logs", json={"log_date": str(date.today()),
        "source": "strava", "external_id": "cycle", "distance_km": 40, "duration_sec": 3600})
    assert response.status_code == 422
    assert (await runner.get("/api/workout-logs")).json()["items"] == []
