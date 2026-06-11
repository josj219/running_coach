"""Strava OAuth2 + 활동 동기화.

Garmin 사용자는 Garmin Connect → Strava 자동 업로드를 켜면 이 경로 하나로
가민 데이터까지 들어온다(Garmin Health API는 파트너 승인이 필요해 직접 연동은
어댑터만 두고 보류 — routers/integrations.py 참고).
"""

import time
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import ExternalActivity, Integration

AUTH_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"
API = "https://www.strava.com/api/v3"

RUN_TYPES = {"Run", "TrailRun", "VirtualRun", "Treadmill"}


class StravaError(Exception):
    pass


def authorize_url(redirect_uri: str) -> str:
    s = get_settings()
    if not s.strava_client_id:
        raise StravaError("STRAVA_CLIENT_ID가 설정되어 있지 않습니다 (.env 참고).")
    from urllib.parse import urlencode
    q = urlencode({
        "client_id": s.strava_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "approval_prompt": "auto",
        "scope": "read,activity:read_all",
    })
    return f"{AUTH_URL}?{q}"


async def exchange_code(code: str) -> dict:
    s = get_settings()
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(TOKEN_URL, data={
            "client_id": s.strava_client_id,
            "client_secret": s.strava_client_secret,
            "code": code,
            "grant_type": "authorization_code",
        })
    if r.status_code != 200:
        raise StravaError(f"토큰 교환 실패: {r.text[:200]}")
    return r.json()


async def _fresh_token(db: AsyncSession, integ: Integration) -> str:
    """만료 임박 시 refresh. 항상 유효한 access_token 반환."""
    if integ.expires_at and integ.expires_at > time.time() + 60:
        return integ.access_token
    s = get_settings()
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(TOKEN_URL, data={
            "client_id": s.strava_client_id,
            "client_secret": s.strava_client_secret,
            "grant_type": "refresh_token",
            "refresh_token": integ.refresh_token,
        })
    if r.status_code != 200:
        raise StravaError(f"토큰 갱신 실패: {r.text[:200]}")
    data = r.json()
    integ.access_token = data["access_token"]
    integ.refresh_token = data["refresh_token"]
    integ.expires_at = data["expires_at"]
    await db.commit()
    return integ.access_token


def _pace_str(distance_m: float, moving_sec: int) -> str | None:
    if not distance_m or not moving_sec:
        return None
    sec_per_km = moving_sec / (distance_m / 1000)
    return f"{int(sec_per_km // 60)}:{int(sec_per_km % 60):02d}"


async def sync_activities(db: AsyncSession, integ: Integration, user_id: int, limit: int = 10) -> int:
    """최근 활동을 가져와 external_activities upsert. 새로 추가된 수 반환."""
    token = await _fresh_token(db, integ)
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(f"{API}/athlete/activities",
                             params={"per_page": limit},
                             headers={"Authorization": f"Bearer {token}"})
    if r.status_code != 200:
        raise StravaError(f"활동 조회 실패({r.status_code}): {r.text[:200]}")

    added = 0
    for a in r.json():
        if a.get("type") not in RUN_TYPES and a.get("sport_type") not in RUN_TYPES:
            continue
        ext_id = str(a["id"])
        existing = (await db.execute(select(ExternalActivity).where(
            ExternalActivity.provider == "strava", ExternalActivity.external_id == ext_id,
        ))).scalar_one_or_none()
        if existing:
            continue
        start = None
        if a.get("start_date"):
            start = datetime.fromisoformat(a["start_date"].replace("Z", "+00:00")).astimezone(timezone.utc)
        db.add(ExternalActivity(
            user_id=user_id, provider="strava", external_id=ext_id,
            name=a.get("name"), sport_type=a.get("sport_type") or a.get("type"),
            start_date=start,
            distance_km=round((a.get("distance") or 0) / 1000, 2),
            duration_sec=a.get("moving_time"),
            avg_pace=_pace_str(a.get("distance") or 0, a.get("moving_time") or 0),
            avg_hr=round(a["average_heartrate"]) if a.get("average_heartrate") else None,
            max_hr=round(a["max_heartrate"]) if a.get("max_heartrate") else None,
            # Strava 러닝 케이던스는 한 발 기준 → spm은 ×2
            cadence=round(a["average_cadence"] * 2) if a.get("average_cadence") else None,
            elevation_m=round(a["total_elevation_gain"]) if a.get("total_elevation_gain") else None,
            raw={k: a.get(k) for k in ("id", "name", "type", "sport_type", "start_date",
                                       "distance", "moving_time", "average_speed")},
        ))
        added += 1
    integ.last_sync_at = datetime.now(timezone.utc)
    await db.commit()
    return added
