"""Strava/Garmin 연동.

- Strava: 정식 OAuth2 — 연결하면 최근 러닝을 가져와 기록 입력을 자동 채움.
- Garmin: Garmin Health API는 파트너 승인 필요(개인 발급 불가). 권장 경로는
  Garmin Connect 앱 → 설정 → 계정·연동 → Strava 자동 업로드를 켠 뒤 Strava만
  연결하는 것. 본 라우터는 Garmin 직접 연동 자리(어댑터)와 안내를 제공한다.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import ExternalActivity, Integration, get_db
from ..services import strava
from ..services.context import USER_ID

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


async def _get_integration(db: AsyncSession, provider: str) -> Integration | None:
    return (await db.execute(select(Integration).where(
        Integration.user_id == USER_ID, Integration.provider == provider,
    ))).scalar_one_or_none()


@router.get("")
async def list_integrations(db: AsyncSession = Depends(get_db)):
    st = await _get_integration(db, "strava")
    ga = await _get_integration(db, "garmin")
    s = get_settings()
    return {
        "strava": {
            "available": bool(s.strava_client_id),
            "connected": st is not None and st.access_token is not None,
            "athlete_name": st.athlete_name if st else None,
            "last_sync_at": st.last_sync_at.isoformat() if st and st.last_sync_at else None,
        },
        "garmin": {
            "available": False,
            "connected": ga is not None,
            "note": "Garmin Health API는 파트너 승인이 필요합니다. "
                    "Garmin Connect 앱에서 Strava 자동 업로드를 켜면 "
                    "Strava 연동만으로 가민 기록이 자동으로 들어옵니다.",
        },
    }


@router.get("/strava/authorize-url")
async def strava_authorize_url():
    s = get_settings()
    redirect_uri = f"{s.api_base_url}/api/integrations/strava/callback"
    try:
        return {"url": strava.authorize_url(redirect_uri)}
    except strava.StravaError as e:
        raise HTTPException(503, {"code": "INTEGRATION_UNAVAILABLE", "message": str(e)})


@router.get("/strava/callback")
async def strava_callback(code: str = "", error: str = "", db: AsyncSession = Depends(get_db)):
    s = get_settings()
    if error or not code:
        return RedirectResponse(f"{s.web_base_url}/?strava=denied")
    try:
        data = await strava.exchange_code(code)
    except strava.StravaError as e:
        raise HTTPException(502, {"code": "INTEGRATION_ERROR", "message": str(e)})

    integ = await _get_integration(db, "strava") or Integration(user_id=USER_ID, provider="strava")
    integ.access_token = data["access_token"]
    integ.refresh_token = data["refresh_token"]
    integ.expires_at = data["expires_at"]
    athlete = data.get("athlete") or {}
    integ.athlete_id = str(athlete.get("id", ""))
    integ.athlete_name = f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip()
    db.add(integ)
    await db.commit()
    # 연결 직후 1회 동기화 (실패해도 연결은 유지)
    try:
        await strava.sync_activities(db, integ, USER_ID)
    except strava.StravaError:
        pass
    return RedirectResponse(f"{s.web_base_url}/?strava=connected")


@router.post("/strava/sync")
async def strava_sync(db: AsyncSession = Depends(get_db)):
    integ = await _get_integration(db, "strava")
    if integ is None or not integ.access_token:
        raise HTTPException(404, {"code": "NOT_CONNECTED", "message": "Strava가 연결되어 있지 않습니다."})
    try:
        added = await strava.sync_activities(db, integ, USER_ID)
    except strava.StravaError as e:
        raise HTTPException(502, {"code": "INTEGRATION_ERROR", "message": str(e)})
    return {"added": added}


def _activity_dict(a: ExternalActivity) -> dict:
    return {
        "id": a.id, "provider": a.provider, "external_id": a.external_id,
        "name": a.name, "sport_type": a.sport_type,
        "start_date": a.start_date.isoformat() if a.start_date else None,
        "distance_km": a.distance_km, "duration_sec": a.duration_sec,
        "avg_pace": a.avg_pace, "avg_hr": a.avg_hr, "max_hr": a.max_hr,
        "cadence": a.cadence, "elevation_m": a.elevation_m,
        "imported": a.imported_log_id is not None,
    }


@router.get("/strava/activities")
async def strava_activities(limit: int = 5, db: AsyncSession = Depends(get_db)):
    """최근 활동 — 기록 입력 자동 채움용. 호출 시 자동으로 한번 동기화 시도."""
    integ = await _get_integration(db, "strava")
    if integ and integ.access_token:
        try:
            await strava.sync_activities(db, integ, USER_ID)
        except strava.StravaError:
            pass  # 캐시로 응답
    res = await db.execute(select(ExternalActivity).where(
        ExternalActivity.user_id == USER_ID,
    ).order_by(ExternalActivity.start_date.desc()).limit(limit))
    return {"items": [_activity_dict(a) for a in res.scalars()]}


class DisconnectBody(BaseModel):
    provider: str = "strava"


@router.delete("/strava")
async def strava_disconnect(db: AsyncSession = Depends(get_db)):
    integ = await _get_integration(db, "strava")
    if integ:
        await db.delete(integ)
        await db.commit()
    return {"disconnected": True}
