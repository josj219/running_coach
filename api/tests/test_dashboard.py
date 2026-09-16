"""GET /api/dashboard — 홈 대시보드 조립 회귀 (시드 데모 계정, COACH_MOCK)."""

from datetime import date, timedelta


async def test_dashboard_shape_with_pb_fallback(client):
    r = await client.get("/api/dashboard")
    assert r.status_code == 200
    d = r.json()
    assert d["goal"]["race_type"] == "풀마라톤" and d["goal"]["target_sec"] == 12600
    assert d["goal"]["distance_km"] == 42.195
    assert len(d["series"]) == 12
    assert d["series"][-1]["current"] is True and d["series"][0]["current"] is False
    assert d["series"][-1]["as_of"] == date.today().isoformat()
    cur = d["current"]
    # 아직 기록이 없으므로 프로필 PB 폴백 + 안내 메시지
    assert cur["basis"]["reference"]["source"] == "pb"
    assert cur["predicted_sec"] is not None and cur["predicted_time"]
    assert cur["gap_sec"] == cur["predicted_sec"] - 12600
    assert "PB" in d["message"]
    # 요구 궤적: 목표 설정 시점 앵커 + 이번 주 요구값
    assert d["anchor"] is None
    assert cur["required_sec"] is None and cur["vs_required_sec"] is None
    assert all(p["predicted_sec"] is None for p in d["series"])
    # 시드 주간 계획이 있으므로 꾸준함 산출 가능(수행 0)
    assert cur["readiness"]["consistency"] == 0
    assert cur["readiness"]["endurance"] is None


async def test_dashboard_uses_recent_log_as_reference(client):
    """10km 템포 기록 저장 → 기준점이 PB 에서 로그로 바뀌고 예상 기록이 빨라진다."""
    before = (await client.get("/api/dashboard")).json()["current"]
    day = (date.today() - timedelta(days=10)).isoformat()  # 이번 주 밖(주간 집계 테스트와 충돌 방지)
    r = await client.post("/api/workout-logs", json={
        "log_date": day, "kind": "tempo", "distance_km": 10.0, "duration_sec": 44 * 60,
        "avg_pace": "4:24", "feel": 3, "pain_level": 0,
    })
    assert r.status_code == 201
    d = (await client.get("/api/dashboard")).json()
    ref = d["current"]["basis"]["reference"]
    assert ref["source"] == "log" and ref["date"] == day and ref["pace"] == "4:24"
    assert d["current"]["predicted_sec"] < before["predicted_sec"]
    assert d["message"] is None
    # 주간 km 집계는 시계열에 반영
    assert any(w["week_km"] >= 10.0 for w in d["series"])


async def test_fitness_context_in_prompt_renders(client):
    """프롬프트 컨텍스트 — 대시보드와 같은 숫자를 문자열로 낸다(주간 계획/평가에 삽입)."""
    from app.db import SessionLocal
    from app.services.progress import render_fitness_context
    async with SessionLocal() as db:
        txt = await render_fitness_context(db, 1)
    assert "## 목표 진척도(앱 산출" in txt
    assert "현재 기록 기준 환산값:" in txt and "준비도(0~100)" in txt and "근거:" in txt
