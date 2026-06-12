"""GET /api/today — 오늘 상태머신(S0~S5) + 세션 + 당일 카드 + 주간 진행."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..auth import get_current_user
from ..db import DailyPlan, Goal, PlanSession, User, WorkoutLog, get_db
from ..services.context import WEEKDAYS_KO, get_current_plan, week_progress

router = APIRouter(prefix="/api", tags=["today"])


def _session_dict(s: PlanSession | None) -> dict | None:
    if s is None:
        return None
    return {
        "id": s.id, "session_date": s.session_date.isoformat(),
        "weekday": WEEKDAYS_KO[s.weekday], "kind": s.kind, "title": s.title,
        "distance_km": s.distance_km, "duration_min": s.duration_min,
        "duration_min_max": s.duration_min_max, "target_pace": s.target_pace,
        "focus": s.focus, "note": s.note, "status": s.status, "is_rest": s.is_rest,
    }


@router.get("/today")
async def get_today(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    today = date.today()
    plan = await get_current_plan(db, today, user.id)

    session = None
    tomorrow_session = None
    if plan:
        res = await db.execute(select(PlanSession).where(PlanSession.plan_id == plan.id))
        by_date = {s.session_date: s for s in res.scalars()}
        session = by_date.get(today)
        # 내일 예고 — 다음 주 계획이 없으면 None
        tomorrow_session = by_date.get(today + timedelta(days=1))

    log = (await db.execute(select(WorkoutLog).where(
        WorkoutLog.user_id == user.id, WorkoutLog.log_date == today,
    ).options(selectinload(WorkoutLog.review)))).scalar_one_or_none()

    daily = (await db.execute(select(DailyPlan).where(
        DailyPlan.user_id == user.id, DailyPlan.plan_date == today,
    ))).scalar_one_or_none()

    # 상태 판정
    if plan is None:
        state = "NO_PLAN"          # S0
    elif log is not None:
        state = "REVIEWED" if log.review else "POST_WORKOUT"  # S3 / S2
    elif session is None:
        # 계획 주이지만 오늘 세션 없음 → 주말 지난 일요일 이후면 주간 종료로 취급
        state = "REST_DAY"
    elif session.is_rest:
        state = "REST_DAY"         # S4
    else:
        state = "PRE_WORKOUT"      # S1

    # 일요일 + 모든 세션 종료 → WEEK_END
    progress = await week_progress(db, plan, today, user.id)
    if (plan and today.weekday() == 6 and progress["total"] > 0
            and state in ("REVIEWED", "REST_DAY")):
        state = "WEEK_END"         # S5

    goal = (await db.execute(select(Goal).where(
        Goal.user_id == user.id, Goal.is_active == True,  # noqa: E712
    ))).scalar_one_or_none()
    dday = (goal.target_date - today).days if goal and goal.target_date else None

    return {
        "today": today.isoformat(),
        "weekday": WEEKDAYS_KO[today.weekday()],
        "state": state,
        "dday": dday,
        "session": _session_dict(session),
        "tomorrow": _session_dict(tomorrow_session),
        "log_id": log.id if log else None,
        "log": None if log is None else {
            "distance_km": log.distance_km, "duration_sec": log.duration_sec,
            "avg_pace": log.avg_pace, "avg_hr": log.avg_hr, "cadence": log.cadence,
            "feel": log.feel,
            "review": None if not log.review else {
                "recovery": log.review.recovery, "coach_comment": log.review.coach_comment,
                "summary": log.review.summary,
                "strengths": log.review.strengths, "improvements": log.review.improvements,
            },
        },
        "daily_plan": None if daily is None else {
            "sections": daily.sections, "is_adjusted": daily.is_adjusted,
            "adjust_reason": daily.adjust_reason, "status": daily.status,
        },
        "week_progress": progress,
    }
