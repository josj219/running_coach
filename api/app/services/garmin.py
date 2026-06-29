"""Garmin Connect 직접 동기화 (비공식 python-garminconnect 기반).

Garmin은 개인에게 공식 OAuth를 제공하지 않아, 사용자 대신 로그인한다.
모든 라이브러리 호출은 이 모듈의 헬퍼에 격리한다.
"""

from datetime import datetime, timezone

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
