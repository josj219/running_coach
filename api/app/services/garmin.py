"""Garmin Connect 직접 동기화 (비공식 python-garminconnect 기반).

Garmin은 개인에게 공식 OAuth를 제공하지 않아, 사용자 대신 로그인한다.
모든 라이브러리 호출은 이 모듈의 헬퍼에 격리한다.
"""

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import ExternalActivity, Integration

RUN_KEYS = {"running", "trail_running", "treadmill_running", "virtual_run",
            "track_running", "indoor_running", "ultra_run", "obstacle_run"}


class GarminError(Exception):
    pass


def _pace_str(distance_m: float, moving_sec: int) -> str | None:
    if not distance_m or not moving_sec:
        return None
    sec_per_km = moving_sec / (distance_m / 1000)
    return f"{int(sec_per_km // 60)}:{int(sec_per_km % 60):02d}"


def is_running(a: dict) -> bool:
    key = ((a.get("activityType") or {}).get("typeKey") or "").lower()
    return key in RUN_KEYS or "running" in key


def _load_client(blob: str):
    """토큰 블롭으로 로그인된 Garmin 클라이언트 복원. (라이브러리 경계)

    garminconnect 0.3.6+: 토큰은 client.client (garminconnect.client.Client)에 저장된다.
    client.client.loads(blob) 으로 JSON 토큰 문자열을 복원한다.
    """
    from garminconnect import Garmin
    c = Garmin()
    c.client.loads(blob)   # garminconnect.client.Client.loads() — JSON 토큰 복원
    return c


def _dump_blob(c) -> str:
    """클라이언트의 (갱신될 수 있는) 토큰을 JSON 문자열로 직렬화. (라이브러리 경계)

    garminconnect 0.3.6+: client.client.dumps() 가 JSON 직렬화를 담당한다.
    """
    return c.client.dumps()   # garminconnect.client.Client.dumps()


def fetch_recent(blob: str, limit: int = 10) -> tuple[list[dict], str]:
    """최근 활동 원본 리스트 + 갱신된 토큰 블롭. (블로킹 — to_thread로 호출)"""
    c = _load_client(blob)
    activities = c.get_activities(0, limit)
    return activities, _dump_blob(c)


async def sync_activities(db: AsyncSession, integ: Integration, user_id: int, limit: int = 10) -> int:
    """최근 활동을 가져와 external_activities upsert. 러닝만 필터. 새로 추가된 수 반환."""
    if not integ.auth_blob:
        raise GarminError("가민이 연결되어 있지 않습니다.")
    try:
        acts, new_blob = await asyncio.to_thread(fetch_recent, integ.auth_blob, limit)
    except GarminError:
        raise
    except Exception as e:
        raise GarminError(f"가민 활동 조회 실패: {e}") from e

    added = 0
    for a in acts:
        if not is_running(a):
            continue
        m = map_activity(a)
        existing = (await db.execute(select(ExternalActivity).where(
            ExternalActivity.provider == "garmin",
            ExternalActivity.external_id == m["external_id"],
        ))).scalar_one_or_none()
        if existing:
            continue
        db.add(ExternalActivity(
            user_id=user_id, provider="garmin",
            raw={k: a.get(k) for k in ("activityId", "activityName", "activityType",
                                       "startTimeGMT", "distance", "duration")},
            **m,
        ))
        added += 1
    integ.auth_blob = new_blob
    integ.last_sync_at = datetime.now(timezone.utc)
    await db.commit()
    return added


def map_activity(a: dict) -> dict:
    dist_m = a.get("distance") or 0
    dur = a.get("duration") or a.get("movingDuration") or 0
    start = None
    if a.get("startTimeGMT"):
        # Garmin GMT 포맷: "2026-06-28 21:00:00"
        start = datetime.strptime(a["startTimeGMT"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    cad = a.get("averageRunningCadenceInStepsPerMinute")
    return {
        "external_id": str(a["activityId"]),
        "name": a.get("activityName"),
        "sport_type": (a.get("activityType") or {}).get("typeKey"),
        "start_date": start,
        "distance_km": round(dist_m / 1000, 2) if dist_m else None,
        "duration_sec": int(dur) if dur else None,
        "avg_pace": _pace_str(dist_m, dur),
        "avg_hr": round(a["averageHR"]) if a.get("averageHR") else None,
        "max_hr": round(a["maxHR"]) if a.get("maxHR") else None,
        "cadence": round(cad) if cad else None,   # 양발 spm — ×2 하지 않음
        "elevation_m": round(a["elevationGain"]) if a.get("elevationGain") else None,
    }
