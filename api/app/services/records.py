"""Canonical workout identity, quality and plan fulfillment shared by all clients."""
from datetime import timezone
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy import select
from ..config import get_settings
from ..db import ExternalActivity, JourneyEvent, PlanSession, User, WeeklyPlan, WorkoutLog
from .fitness import Run, RUN_KINDS


def as_run(log):
    return Run(log.log_date, float(log.distance_km or 0), log.duration_sec, log.kind,
               log.avg_pace, log.sport, log.id)


def quality(log):
    reason = as_run(log).exclusion_reason()
    return {"eligible": reason is None, "reason": reason,
            "sport": log.sport or ("running" if log.kind in RUN_KINDS else "unknown")}


def session_values(s):
    return {k: getattr(s, k) for k in ("kind", "title", "distance_km", "duration_min", "duration_min_max", "target_pace", "focus", "note", "is_rest")}


async def lock_user(db, user_id):
    # Serializes imports/record mutations on PostgreSQL, including cross-provider imports.
    await db.execute(select(User.id).where(User.id == user_id).with_for_update())


async def update_fulfillment(db, session_id):
    if not session_id:
        return None
    s = await db.get(PlanSession, session_id)
    logs = list((await db.execute(select(WorkoutLog).where(WorkoutLog.session_id == session_id))).scalars())
    return fulfillment_status(s, logs)


def fulfillment_status(s, logs):
    active = [l for l in logs if l.fulfillment != "missed"]
    matching = [l for l in active if l.fulfillment != "substituted" and
                ((s.kind in RUN_KINDS and quality(l)["sport"] == "running") or
                 (s.kind not in RUN_KINDS and l.kind == s.kind))]
    distance = sum(l.distance_km or 0 for l in matching)
    duration = sum(l.duration_sec or 0 for l in matching) / 60
    if not logs:
        s.status = "planned"
    elif not active:
        s.status = "missed"
    elif not matching:
        s.status = "substituted"
    else:
        ratios = []
        if s.distance_km:
            ratios.append(distance / s.distance_km)
        elif s.duration_min:
            ratios.append(duration / s.duration_min)
        complete = min(ratios) >= .9 if ratios else any(l.fulfillment == "done" for l in matching)
        if any(l.fulfillment == "partial" for l in matching):
            complete = False
        s.status = "done" if complete else "partial"
    return s.status


async def link_session(db, user_id, log, requested="auto"):
    if requested == "auto":
        s = (await db.execute(select(PlanSession).join(WeeklyPlan).where(
            WeeklyPlan.user_id == user_id, PlanSession.session_date == log.log_date,
            PlanSession.is_rest == False))).scalar_one_or_none()
    elif requested is None:
        s = None
    else:
        s = (await db.execute(select(PlanSession).join(WeeklyPlan).where(
            WeeklyPlan.user_id == user_id, PlanSession.id == requested,
            PlanSession.session_date == log.log_date))).scalar_one_or_none()
        if s is None:
            raise HTTPException(422, "계획 연결 날짜 또는 소유자를 확인하세요.")
    log.session_id = s.id if s else None


def _utc(dt):
    return dt.replace(tzinfo=timezone.utc) if dt and dt.tzinfo is None else dt


async def resolve_activity(db, user_id, activity):
    if activity.imported_log_id:
        return await db.get(WorkoutLog, activity.imported_log_id)
    exact = list((await db.execute(select(WorkoutLog).where(
        WorkoutLog.user_id == user_id, WorkoutLog.source == activity.provider,
        WorkoutLog.external_id == activity.external_id).order_by(WorkoutLog.id))).scalars())
    if exact:
        activity.imported_log_id = exact[0].id
        return exact[0]
    if not activity.start_date or not activity.duration_sec or not activity.distance_km:
        return None
    # Date alone is never an identity. Match different providers only, with timestamp and metrics.
    others = (await db.execute(select(ExternalActivity).where(
        ExternalActivity.user_id == user_id, ExternalActivity.provider != activity.provider,
        ExternalActivity.imported_log_id.is_not(None)))).scalars()
    for other in others:
        if (other.start_date and other.duration_sec and other.distance_km and
            abs((_utc(activity.start_date) - _utc(other.start_date)).total_seconds()) <= 60 and
            abs(activity.distance_km - other.distance_km) <= max(.1, other.distance_km * .02) and
            abs(activity.duration_sec - other.duration_sec) <= max(10, other.duration_sec * .02)):
            activity.imported_log_id = other.imported_log_id
            return await db.get(WorkoutLog, other.imported_log_id)
    return None


async def import_activity(db, user_id, activity):
    existing = await resolve_activity(db, user_id, activity)
    if existing:
        return existing, False
    if not activity.start_date:
        raise HTTPException(422, "활동 시작 시각을 확인해 주세요.")
    validate_running_activity(activity)
    log = WorkoutLog(user_id=user_id, log_date=_utc(activity.start_date).astimezone(ZoneInfo(get_settings().tz)).date(),
        kind="easy", sport="running", source=activity.provider, external_id=activity.external_id,
        started_at=activity.start_date, distance_km=activity.distance_km or 0,
        duration_sec=activity.duration_sec, avg_pace=activity.avg_pace, avg_hr=activity.avg_hr,
        max_hr=activity.max_hr, cadence=activity.cadence, elevation_m=activity.elevation_m)
    db.add(log)
    await link_session(db, user_id, log)
    await db.flush()
    activity.imported_log_id = log.id
    await update_fulfillment(db, log.session_id)
    db.add(JourneyEvent(user_id=user_id, event_type="import", entity_id=log.id,
        reason="외부 활동 확인 후 반영", after={"provider": activity.provider, "activity_id": activity.id}))
    return log, True


def validate_running_activity(activity):
    sport = (activity.sport_type or "").lower().replace("_", "")
    if sport not in {"run", "running", "trailrun", "trailrunning", "treadmillrunning", "virtualrun", "trackrunning", "treadmill"}:
        raise HTTPException(422, "러닝으로 확인된 외부 활동만 가져올 수 있습니다.")
