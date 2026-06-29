import pytest
from sqlalchemy import select
from app.db import ExternalActivity, Integration
from app.services import garmin


async def test_integration_has_auth_blob(db_session):
    # flush(not commit) — 컬럼/라운드트립만 검증하고 공유 테스트 DB는 오염시키지 않는다
    # (세션 종료 시 롤백 → 이후 garmin 라우터 테스트의 '미연결' 가정과 충돌 방지).
    integ = Integration(user_id=1, provider="garmin", auth_blob="abc123")
    db_session.add(integ)
    await db_session.flush()
    got = (await db_session.execute(
        select(Integration).where(Integration.provider == "garmin"))).scalar_one()
    assert got.auth_blob == "abc123"


def test_pace_str():
    assert garmin._pace_str(5000, 1500) == "5:00"   # 5km / 25min
    assert garmin._pace_str(0, 100) is None
    assert garmin._pace_str(5000, 0) is None


def test_is_running():
    assert garmin.is_running({"activityType": {"typeKey": "running"}}) is True
    assert garmin.is_running({"activityType": {"typeKey": "trail_running"}}) is True
    assert garmin.is_running({"activityType": {"typeKey": "cycling"}}) is False
    assert garmin.is_running({}) is False


def test_map_activity_cadence_not_doubled():
    a = {
        "activityId": 12345,
        "activityName": "아침 러닝",
        "activityType": {"typeKey": "running"},
        "startTimeGMT": "2026-06-28 21:00:00",
        "distance": 10000.0,
        "duration": 3000.0,
        "averageHR": 150.4,
        "maxHR": 172.0,
        "averageRunningCadenceInStepsPerMinute": 178.0,
        "elevationGain": 42.0,
    }
    m = garmin.map_activity(a)
    assert m["external_id"] == "12345"
    assert m["distance_km"] == 10.0
    assert m["duration_sec"] == 3000
    assert m["avg_pace"] == "5:00"
    assert m["avg_hr"] == 150
    assert m["max_hr"] == 172
    assert m["cadence"] == 178       # ×2 하지 않음
    assert m["elevation_m"] == 42
    assert m["start_date"].year == 2026


async def test_sync_activities_upserts_running_only(db_session, monkeypatch):
    fake = [
        {"activityId": 1, "activityName": "런", "activityType": {"typeKey": "running"},
         "startTimeGMT": "2026-06-28 21:00:00", "distance": 5000.0, "duration": 1500.0,
         "averageRunningCadenceInStepsPerMinute": 176.0},
        {"activityId": 2, "activityName": "자전거", "activityType": {"typeKey": "cycling"},
         "startTimeGMT": "2026-06-27 21:00:00", "distance": 20000.0, "duration": 3600.0},
    ]
    monkeypatch.setattr(garmin, "fetch_recent", lambda blob, limit=10: (fake, "newblob"))

    integ = Integration(user_id=1, provider="garmin", auth_blob="oldblob")
    db_session.add(integ)
    await db_session.commit()

    added = await garmin.sync_activities(db_session, integ, user_id=1)
    assert added == 1                      # 러닝만
    assert integ.auth_blob == "newblob"    # 갱신된 토큰 저장
    assert integ.last_sync_at is not None

    rows = (await db_session.execute(select(ExternalActivity).where(
        ExternalActivity.provider == "garmin"))).scalars().all()
    assert len(rows) == 1
    assert rows[0].cadence == 176

    # 재동기화 시 중복 추가 안 함
    added2 = await garmin.sync_activities(db_session, integ, user_id=1)
    assert added2 == 0
