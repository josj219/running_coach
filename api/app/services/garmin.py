"""Garmin Connect 직접 동기화 (비공식 python-garminconnect 기반).

Garmin은 개인에게 공식 OAuth를 제공하지 않아, 사용자 대신 로그인한다.
모든 라이브러리 호출은 이 모듈의 헬퍼에 격리한다.
"""

import asyncio
import secrets
import time
from datetime import datetime, timezone

from garminconnect import Garmin  # 테스트에서 monkeypatch 가능하도록 모듈 레벨 import
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import ExternalActivity, Integration

RUN_KEYS = {"running", "trail_running", "treadmill_running", "virtual_run",
            "track_running", "indoor_running", "ultra_run", "obstacle_run"}

# MFA 진행 중인 세션 캐시: mfa_token -> (client, state, expires_at)
_PENDING: dict[str, tuple] = {}
_MFA_TTL = 300  # 5분


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
    c = Garmin()
    c.client.loads(blob)   # garminconnect.client.Client.loads() — JSON 토큰 복원
    return c


def _dump_blob(c) -> str:
    """클라이언트의 (갱신될 수 있는) 토큰을 JSON 문자열로 직렬화. (라이브러리 경계)

    garminconnect 0.3.6+: client.client.dumps() 가 JSON 직렬화를 담당한다.
    """
    return c.client.dumps()   # garminconnect.client.Client.dumps()


def _athlete_name(client) -> str | None:
    """클라이언트에서 선수 이름 반환. 실패 시 None."""
    try:
        return client.get_full_name()
    except Exception:
        return None


def _prune_pending() -> None:
    """만료된 MFA 세션 제거."""
    now = time.time()
    for k in [k for k, (_, _, exp) in _PENDING.items() if exp < now]:
        _PENDING.pop(k, None)


def begin_login(email: str, password: str) -> dict:
    """1단계 로그인. MFA 필요 시 중간 클라이언트를 메모리에 보관하고 토큰 반환.

    Returns:
        {"status": "ok", "blob": str, "athlete_name": str | None} — MFA 불필요
        {"status": "mfa", "mfa_token": str} — MFA 필요

    Raises:
        GarminError: 로그인 실패 시
    """
    try:
        client = Garmin(email=email, password=password, return_on_mfa=True)
        res = client.login()
    except Exception as e:
        raise GarminError("가민 로그인 실패: 이메일/비밀번호를 확인해 주세요.") from e

    # 실제 라이브러리: login() 반환값은 (mfa_status, legacy_token)
    # MFA 필요: res[0] == "needs_mfa", res[1] == state dict
    # 성공: res[0] is None (또는 "ok" — FakeClient 호환)
    if isinstance(res, tuple) and res[0] == "needs_mfa":
        _prune_pending()
        tok = secrets.token_urlsafe(16)
        _PENDING[tok] = (client, res[1], time.time() + _MFA_TTL)
        return {"status": "mfa", "mfa_token": tok}

    return {"status": "ok", "blob": _dump_blob(client), "athlete_name": _athlete_name(client)}


def complete_mfa(mfa_token: str, code: str) -> dict:
    """2단계: 보관된 클라이언트로 MFA 코드 제출.

    Returns:
        {"status": "ok", "blob": str, "athlete_name": str | None}

    Raises:
        GarminError: 토큰 만료 또는 코드 오류 시
    """
    _prune_pending()
    entry = _PENDING.pop(mfa_token, None)
    if not entry:
        raise GarminError("MFA 세션이 만료됐어요. 다시 연결해 주세요.")
    client, state, _ = entry
    try:
        client.resume_login(state, code)
    except Exception as e:
        raise GarminError("MFA 코드가 올바르지 않아요.") from e
    return {"status": "ok", "blob": _dump_blob(client), "athlete_name": _athlete_name(client)}


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
        ext_id = str(a["activityId"])
        existing = (await db.execute(select(ExternalActivity).where(
            ExternalActivity.provider == "garmin",
            ExternalActivity.external_id == ext_id,
        ))).scalar_one_or_none()
        if existing:
            continue
        m = map_activity(a)
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
