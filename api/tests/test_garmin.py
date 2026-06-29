from sqlalchemy import select
from app.db import Integration


async def test_integration_has_auth_blob(db_session):
    # flush(not commit) — 컬럼/라운드트립만 검증하고 공유 테스트 DB는 오염시키지 않는다
    # (세션 종료 시 롤백 → 이후 garmin 라우터 테스트의 '미연결' 가정과 충돌 방지).
    integ = Integration(user_id=1, provider="garmin", auth_blob="abc123")
    db_session.add(integ)
    await db_session.flush()
    got = (await db_session.execute(
        select(Integration).where(Integration.provider == "garmin"))).scalar_one()
    assert got.auth_blob == "abc123"
