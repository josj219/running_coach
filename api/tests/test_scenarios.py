"""기능·시나리오 기반 테스트 — '하루 사이클' 전체 플로우를 순서대로 검증한다.

S1: 오늘 조회 → S2: 기록 저장(멱등) → S3: AI 리뷰(성공/실패/재생성)
→ 주간 진행 갱신 → 계획 생성/조정/평가 → 연동 상태.
COACH_MOCK=1 — 실 Claude 미호출.
"""

from datetime import date, timedelta

from app.services import coach


def today_str() -> str:
    return date.today().isoformat()


# ── 기본 조회 ──────────────────────────────────────────────────────────────

async def test_01_health(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_02_profile_seeded(client):
    r = await client.get("/api/profile")
    assert r.status_code == 200
    body = r.json()
    assert body["nickname"] == "고고조"
    assert body["pb_10k"] == "00:42:13"


async def test_03_goal_dday(client):
    r = await client.get("/api/goal")
    body = r.json()
    assert body["race_type"] == "풀마라톤"
    expected = (date.fromisoformat(body["target_date"]) - date.today()).days
    assert body["dday"] == expected


async def test_04_today_initial_state(client):
    r = await client.get("/api/today")
    body = r.json()
    assert body["today"] == today_str()
    # 시드 주간 계획 존재 → NO_PLAN은 아님
    assert body["state"] in ("PRE_WORKOUT", "REST_DAY", "WEEK_END")
    assert body["week_progress"]["total"] > 0
    assert body["log"] is None


async def test_05_week_current(client):
    r = await client.get("/api/weeks/current")
    assert r.status_code == 200
    body = r.json()
    assert len(body["sessions"]) == 7  # 시드: 월~일
    assert body["progress"]["completion_rate"] == 0


# ── 기록 저장 (핵심 쓰기) ──────────────────────────────────────────────────

async def test_06_save_log(client):
    r = await client.post("/api/workout-logs", json={
        "log_date": today_str(), "kind": "easy", "distance_km": 5.2,
        "duration_sec": 1932, "avg_pace": "6:12", "avg_hr": 143, "cadence": 172,
        "feel": 3, "pain_level": 0, "user_comment": "발목 이상 없음",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["created"] is True
    assert body["session_id"] is not None  # 오늘 세션과 매칭됨


async def test_07_save_log_idempotent_upsert(client):
    """같은 날 재저장 → 중복 행 없이 덮어쓰기 (자연키 upsert)."""
    r = await client.post("/api/workout-logs", json={
        "log_date": today_str(), "kind": "easy", "distance_km": 5.5, "feel": 4,
    })
    assert r.status_code == 201
    assert r.json()["created"] is False
    logs = (await client.get("/api/workout-logs")).json()["items"]
    same_day = [l for l in logs if l["log_date"] == today_str()]
    assert len(same_day) == 1
    assert same_day[0]["distance_km"] == 5.5


async def test_08_validation_error(client):
    r = await client.post("/api/workout-logs", json={
        "log_date": today_str(), "distance_km": -3,
    })
    assert r.status_code == 422


async def test_08b_analyze_image_returns_metrics(client):
    """이미지 분석 → 추출 수치 반환(COACH_MOCK). DB 저장은 하지 않는다."""
    # 1x1 투명 PNG (base64) — mock 분기라 내용은 무관
    px = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
          "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
    r = await client.post("/api/workout-logs/analyze-image",
                          json={"image_b64": px, "media_type": "image/png"})
    assert r.status_code == 200
    body = r.json()
    assert body["found"] is True
    assert body["distance_km"] == 5.2 and body["avg_hr"] == 145
    # 분석은 저장하지 않는다 — 이미지 호출만으로 로그가 늘지 않아야 한다
    assert "id" not in body


async def test_08c_analyze_image_requires_b64(client):
    r = await client.post("/api/workout-logs/analyze-image", json={"image_b64": ""})
    assert r.status_code == 422


async def test_09_week_progress_updated(client):
    """기록 저장 후 주간 거리·수행률 반영 (단일 정의)."""
    body = (await client.get("/api/weeks/current")).json()
    assert body["progress"]["week_km"] == 5.5
    # 오늘 세션이 휴식이 아니면 done 1
    today_sessions = [s for s in body["sessions"] if s["session_date"] == today_str()]
    if today_sessions and not today_sessions[0]["is_rest"]:
        assert body["progress"]["done"] == 1
        assert today_sessions[0]["status"] == "done"


# ── AI 리뷰 (SSE/JSON · 실패 격리) ────────────────────────────────────────

async def test_10_review_json(client):
    logs = (await client.get("/api/workout-logs")).json()["items"]
    log_id = logs[0]["id"]
    r = await client.post(f"/api/workout-logs/{log_id}/review",
                          headers={"Accept": "application/json"})
    assert r.status_code == 200
    body = r.json()
    assert body["recovery"] in ("low", "medium", "high")
    assert body["coach_comment"]


async def test_11_today_reviewed_state(client):
    body = (await client.get("/api/today")).json()
    assert body["state"] in ("REVIEWED", "WEEK_END")
    assert body["log"]["review"]["recovery"] == "low"


async def test_12_review_regenerate_overwrites(client):
    """리뷰 재생성 → UNIQUE(log_id) 덮어쓰기, 행 1개."""
    logs = (await client.get("/api/workout-logs")).json()["items"]
    log_id = logs[0]["id"]
    r1 = await client.post(f"/api/workout-logs/{log_id}/review",
                           headers={"Accept": "application/json"})
    r2 = await client.post(f"/api/workout-logs/{log_id}/review",
                           headers={"Accept": "application/json"})
    assert r1.json()["review_id"] == r2.json()["review_id"]


async def test_13_review_ai_failure_keeps_log(client):
    """AI 실패 → 503, 기록은 보존 (BUG-04 불변식)."""
    coach.get_settings().coach_mock = "__ERROR__"
    try:
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        r = await client.post("/api/workout-logs", json={
            "log_date": yesterday, "kind": "drill", "distance_km": 0, "feel": 2,
        })
        assert r.status_code == 201  # 저장은 AI와 무관하게 성공
        log_id = r.json()["id"]
        r = await client.post(f"/api/workout-logs/{log_id}/review",
                              headers={"Accept": "application/json"})
        assert r.status_code == 503
        assert r.json()["detail"]["code"] == "AI_UNAVAILABLE"
        logs = (await client.get("/api/workout-logs")).json()["items"]
        kept = [l for l in logs if l["id"] == log_id]
        assert kept and kept[0]["review"] is None  # 기록 보존, 리뷰만 없음
    finally:
        coach.get_settings().coach_mock = "1"


async def test_14_review_sse_stream(client):
    logs = (await client.get("/api/workout-logs")).json()["items"]
    log_id = logs[0]["id"]
    async with client.stream("POST", f"/api/workout-logs/{log_id}/review",
                             headers={"Accept": "text/event-stream"}) as r:
        assert r.status_code == 200
        text = ""
        async for chunk in r.aiter_text():
            text += chunk
    assert "event: token" in text
    assert "event: done" in text


# ── 통증 → 부분완료 트리거 ─────────────────────────────────────────────────

async def test_15_pain_marks_session_partial(client):
    """통증 4/10+ → 매칭 세션 '부분완료'."""
    week = (await client.get("/api/weeks/current")).json()
    future = [s for s in week["sessions"]
              if s["session_date"] > today_str() and not s["is_rest"]]
    if not future:  # 주 후반 실행 시 스킵
        return
    target = future[0]
    r = await client.post("/api/workout-logs", json={
        "log_date": target["session_date"], "kind": target["kind"],
        "distance_km": 3, "feel": 2, "pain_part": "무릎", "pain_level": 5,
    })
    assert r.json()["session_status"] == "partial"


# ── 과거 일자 백필 (어제 깜빡한 기록) ─────────────────────────────────────

async def test_15b_backfill_past_date_attaches_log(client):
    """과거 일자 기록 → 주간 payload의 해당 세션에 log가 첨부되고 상태가 갱신된다.

    주간 탭에서 지난 날을 눌러 기록하는 UX의 백엔드 계약.
    """
    week = (await client.get("/api/weeks/current")).json()
    # 모든 세션 dict에 log 키가 존재(미기록 시 None)
    assert all("log" in s for s in week["sessions"])
    target = next((s for s in week["sessions"]
                   if s["session_date"] < today_str() and s["log"] is None), None)
    if target is None:  # 주 초반 실행 등 과거 미기록 세션이 없으면 스킵
        return
    r = await client.post("/api/workout-logs", json={
        "log_date": target["session_date"], "kind": target["kind"] or "easy",
        "distance_km": 6.0, "duration_sec": 2160, "avg_pace": "6:00", "feel": 3,
    })
    assert r.status_code == 201
    assert r.json()["created"] is True

    week2 = (await client.get("/api/weeks/current")).json()
    s2 = next(s for s in week2["sessions"] if s["session_date"] == target["session_date"])
    assert s2["log"] is not None
    assert s2["log"]["distance_km"] == 6.0
    assert s2["log"]["avg_pace"] == "6:00"
    assert s2["status"] in ("done", "partial")  # 과거여도 매칭 세션 상태 갱신


# ── AI 생성 경로: 주간 계획 / 조정 / 평가 / 당일 카드 ─────────────────────

async def test_16_generate_weekly_plan_preserves_done(client):
    """계획 재생성 시 완료(done/partial) 세션은 보존된다."""
    mock_sessions = [
        {"date": (date.today() + timedelta(days=i)).isoformat(),
         "kind": "easy", "title": f"모의 세션 {i}", "distance_km": 4,
         "duration_min": 30, "target_pace": "6:30 /km", "focus": "테스트",
         "is_rest": False}
        for i in range(0, 3)
    ]
    original = coach.MOCK_RESPONSES["weekly"]["sessions"]
    coach.MOCK_RESPONSES["weekly"]["sessions"] = mock_sessions
    try:
        r = await client.post("/api/weekly-plans", json={"schedule_note": "테스트"})
        assert r.status_code == 201
        body = r.json()
        today_s = [s for s in body["sessions"] if s["session_date"] == today_str()]
        # 오늘 세션은 이미 done → 모의 제목으로 덮이지 않음
        if today_s and today_s[0]["status"] in ("done", "partial"):
            assert today_s[0]["title"] != "모의 세션 0"
    finally:
        coach.MOCK_RESPONSES["weekly"]["sessions"] = original


async def test_17_adjust_never_touches_past(client):
    """조정이 지난 날짜 변경을 시도해도 무시된다."""
    original = coach.MOCK_RESPONSES["adjust"]["changes"]
    coach.MOCK_RESPONSES["adjust"]["changes"] = [{
        "date": (date.today() - timedelta(days=2)).isoformat(),
        "kind": "rest", "title": "조작 시도", "is_rest": True,
    }]
    try:
        r = await client.post("/api/weeks/current/adjust", json={"reason": "테스트"})
        assert r.status_code == 200
        assert r.json()["adjustment"]["changed"] == []  # 과거 변경 차단
    finally:
        coach.MOCK_RESPONSES["adjust"]["changes"] = original


async def test_18_weekly_evaluation(client):
    r = await client.post("/api/weeks/current/evaluation")
    assert r.status_code == 200
    ev = r.json()["evaluation"]
    assert ev["coach_message"].startswith("📈")
    assert ev["total_km"] >= 5.5  # 앱 집계 숫자 (AI 아님)


async def test_19_daily_plan_card(client):
    r = await client.post("/api/daily-plans", json={"condition_note": "수면 6시간"})
    if r.status_code == 404:  # 오늘 세션 없는 요일이면 스킵
        return
    assert r.status_code == 201
    sections = r.json()["sections"]
    assert sections["warmup"] and sections["main"] and sections["cooldown"]
    today = (await client.get("/api/today")).json()
    assert today["daily_plan"] is not None


# ── 통계 · 설정 · 연동 ────────────────────────────────────────────────────

async def test_20_weekly_stats(client):
    r = await client.get("/api/stats/weekly?weeks=4")
    weeks = r.json()["weeks"]
    assert len(weeks) == 4
    assert weeks[0]["current"] is True
    assert weeks[0]["week_km"] >= 5.5


async def test_21_settings_patch(client):
    r = await client.patch("/api/settings", json={"weekly_goal_km": 30, "coach_tone": "warm"})
    body = r.json()
    assert body["weekly_goal_km"] == 30
    assert body["coach_tone"] == "warm"


async def test_22_profile_patch(client):
    r = await client.patch("/api/profile", json={"weight_kg": 79.5})
    assert r.json()["weight_kg"] == 79.5


async def test_23_integrations_status(client):
    body = (await client.get("/api/integrations")).json()
    assert body["strava"]["available"] is False  # 키 미설정
    assert body["strava"]["connected"] is False
    assert "Strava" in body["garmin"]["note"]


async def test_24_strava_authorize_requires_keys(client):
    r = await client.get("/api/integrations/strava/authorize-url")
    assert r.status_code == 503


async def test_25_strava_sync_requires_connection(client):
    r = await client.post("/api/integrations/strava/sync")
    assert r.status_code == 404


async def test_26_week_404_format(client):
    r = await client.get("/api/weeks/2020-W01")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "NOT_FOUND"


# ── 정기 훈련 가능 시간(기본 시간표) ──────────────────────────────────────

async def test_27_availability_seeded(client):
    """시드: 점심 헬스장(평일)·퇴근런(화목)·주말 러닝 3슬롯."""
    body = (await client.get("/api/availability")).json()
    assert len(body["slots"]) == 3
    lunch = next(s for s in body["slots"] if s["title"] == "점심 헬스장")
    assert lunch["days"] == [0, 1, 2, 3, 4]
    assert lunch["duration_min"] == 45
    assert lunch["place"] == "실내 헬스장"


async def test_28_availability_put_replace(client):
    """PUT 전체 교체 — 재PUT해도 행 수 동일(멱등)."""
    slots = [
        {"days": [0, 2, 4], "title": "점심 헬스장", "duration_min": 45, "place": "실내 헬스장"},
        {"days": [5], "title": "토요 야외 러닝", "duration_min": 90, "place": "야외", "note": "오전"},
    ]
    r = await client.put("/api/availability", json={"slots": slots})
    assert r.status_code == 200
    assert len(r.json()["slots"]) == 2
    r2 = await client.put("/api/availability", json={"slots": slots})
    assert len(r2.json()["slots"]) == 2
    got = (await client.get("/api/availability")).json()["slots"]
    assert [s["title"] for s in got] == ["점심 헬스장", "토요 야외 러닝"]
    assert got[0]["days"] == [0, 2, 4]


async def test_29_availability_validation(client):
    # 요일 범위 밖
    r = await client.put("/api/availability", json={"slots": [{"days": [9], "title": "x"}]})
    assert r.status_code == 422
    # 요일 비어 있음
    r = await client.put("/api/availability", json={"slots": [{"days": [], "title": "x"}]})
    assert r.status_code == 422
    # 제목 없음
    r = await client.put("/api/availability", json={"slots": [{"days": [0], "title": ""}]})
    assert r.status_code == 422
    # 기존 데이터는 변경되지 않음 (트랜잭션 롤백)
    got = (await client.get("/api/availability")).json()["slots"]
    assert len(got) == 2


async def test_30_weekly_plan_reviews_availability(client, monkeypatch):
    """주간 계획 생성 시 AI 메시지에 기본 시간표 + 이번 주 특이 일정이 포함된다."""
    captured = {}

    async def fake_generate(kind, system_prompt, user_message, **kw):
        captured["kind"] = kind
        captured["system"] = system_prompt
        captured["message"] = user_message
        return coach.MOCK_RESPONSES["weekly"]

    monkeypatch.setattr("app.routers.weeks.coach.generate", fake_generate)
    r = await client.post("/api/weekly-plans", json={
        "schedule_note": "수요일 회식, 금요일 부산 출장",
        "condition_note": "발목 통증 없음",
    })
    assert r.status_code == 201
    msg = captured["message"]
    # 기본 시간표가 컨텍스트로 들어감 (test_28에서 교체한 슬롯 기준)
    assert "정기 훈련 가능 시간(기본 시간표)" in msg
    assert "점심 헬스장" in msg and "토요 야외 러닝" in msg
    # 특이 일정 라벨 + 입력값
    assert "[이번 주 특이 일정]" in msg
    assert "수요일 회식, 금요일 부산 출장" in msg
    # 프롬프트에 가능 시간 준수 규칙 존재
    assert "훈련 가능 시간" in captured["system"]


async def test_31_daily_plan_includes_availability(client, monkeypatch):
    """당일 카드 생성도 기본 시간표를 인지한다."""
    captured = {}

    async def fake_generate(kind, system_prompt, user_message, **kw):
        captured["message"] = user_message
        return coach.MOCK_RESPONSES["daily"]

    monkeypatch.setattr("app.routers.daily_plans.coach.generate", fake_generate)
    r = await client.post("/api/daily-plans", json={"condition_note": "컨디션 좋음"})
    if r.status_code == 404:  # 오늘 세션 없는 요일이면 스킵
        return
    assert r.status_code == 201
    assert "정기 훈련 가능 시간(기본 시간표)" in captured["message"]


async def test_32_daily_adjustment_propagates_to_weekly_session(client, monkeypatch):
    """당일 카드가 컨디션 반영으로 조정되면(adjusted+session) 그 변경이
    이번 주 계획의 해당 PlanSession에도 반영된다 — 오늘 탭→주간 탭 동기화."""
    # 이번 주 계획 재생성 — 평일(미수행) 세션을 planned 상태로 보장
    wk = (await client.post("/api/weekly-plans", json={})).json()
    week_start = date.fromisoformat(wk["week_start"])
    target = week_start + timedelta(days=2)  # 수요일 — 미수행 세션을 타깃

    # daily 엔드포인트의 '오늘'을 수요일로 고정 (공유 DB에서 오늘=월은 done 상태)
    class FakeDate(date):
        @classmethod
        def today(cls):
            return target

    monkeypatch.setattr("app.routers.daily_plans.date", FakeDate)

    async def fake_generate(kind, system_prompt, user_message, **kw):
        return {
            "warmup": "이지 조깅 10분", "main": "템포 6km @ 5:30/km",
            "cooldown": "이지 조깅 10분", "note": "오늘 뛰고 싶다는 요청 반영",
            "adjusted": True,
            "detail": "#### 메인\n- 템포 6km",
            "session": {
                "kind": "tempo", "title": "템포런 6km", "distance_km": 6,
                "duration_min": 35, "duration_min_max": None,
                "target_pace": "5:30/km", "focus": "역치 자극", "is_rest": False,
            },
        }

    monkeypatch.setattr("app.routers.daily_plans.coach.generate", fake_generate)

    r = await client.post("/api/daily-plans", json={"condition_note": "오늘 뛰고 싶어요"})
    assert r.status_code == 201
    assert r.json()["is_adjusted"] is True

    # 이번 주 탭(주간 계획)에 반영됐는지 확인
    week = (await client.get("/api/weeks/current")).json()
    sess = next(s for s in week["sessions"] if s["session_date"] == target.isoformat())
    assert sess["kind"] == "tempo"
    assert sess["is_rest"] is False
    assert sess["distance_km"] == 6
    assert sess["title"] == "템포런 6km"


async def test_33_daily_adjustment_preserves_completed_session(client, monkeypatch):
    """이미 수행(done/partial)한 오늘 세션은 당일 카드 조정으로 덮어쓰지 않는다."""
    today_payload = (await client.get("/api/today")).json()
    sess = today_payload["session"]
    if sess is None or sess["status"] not in ("done", "partial"):
        return  # 오늘 세션이 미수행이면 이 가드 시나리오 아님 → 스킵
    original_kind = sess["kind"]

    async def fake_generate(kind, system_prompt, user_message, **kw):
        return {
            "warmup": "이지 조깅", "main": "템포 6km", "cooldown": "이지 조깅",
            "note": "조정", "adjusted": True, "detail": "...",
            "session": {"kind": "tempo", "title": "덮어쓰면 안 됨",
                        "distance_km": 6, "is_rest": False},
        }

    monkeypatch.setattr("app.routers.daily_plans.coach.generate", fake_generate)
    r = await client.post("/api/daily-plans", json={"condition_note": "뛰고 싶어요"})
    assert r.status_code == 201

    after = (await client.get("/api/today")).json()["session"]
    assert after["kind"] == original_kind  # 완료 세션은 보존
    assert after["status"] in ("done", "partial")


async def test_34_today_exposes_session_updated_flag(client, monkeypatch):
    """주간 반영이 일어난 날은 /api/today가 session_updated=True를 내려준다 — 오늘 탭 확인 문구용."""
    wk = (await client.post("/api/weekly-plans", json={})).json()
    target = date.fromisoformat(wk["week_start"]) + timedelta(days=2)  # 수요일

    class FakeDate(date):
        @classmethod
        def today(cls):
            return target

    monkeypatch.setattr("app.routers.daily_plans.date", FakeDate)
    monkeypatch.setattr("app.routers.today.date", FakeDate)

    async def fake_generate(kind, system_prompt, user_message, **kw):
        return {
            "warmup": "조깅 10분", "main": "템포 6km", "cooldown": "조깅 10분",
            "note": "오늘 뛰고 싶다는 요청 반영", "adjusted": True, "detail": "...",
            "session": {"kind": "tempo", "title": "템포런 6km", "distance_km": 6,
                        "is_rest": False},
        }

    monkeypatch.setattr("app.routers.daily_plans.coach.generate", fake_generate)

    await client.post("/api/daily-plans", json={"condition_note": "오늘 뛰고 싶어요"})
    today = (await client.get("/api/today")).json()
    assert today["daily_plan"]["session_updated"] is True
