"""DB → AI 컨텍스트(Markdown) 직렬화 + 주간 집계 헬퍼."""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import (
    AppSettings, AvailabilitySlot, Goal, PlanSession, User, UserProfile,
    WeeklyPlan, WorkoutLog,
)

USER_ID = 1  # v2.0 단일 사용자

KIND_LABELS = {
    "easy": "이지 런", "interval": "인터벌", "tempo": "템포 런", "long": "롱런",
    "race": "대회", "rest": "휴식", "strength": "근력·보강", "drill": "드릴",
    "core": "코어", "mobility": "가동성", "other": "기타",
}
WEEKDAYS_KO = ["월", "화", "수", "목", "금", "토", "일"]


def week_start_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def iso_week_of(d: date) -> tuple[int, int]:
    iso = d.isocalendar()
    return iso.year, iso.week


async def get_current_plan(db: AsyncSession, d: date) -> WeeklyPlan | None:
    y, w = iso_week_of(d)
    res = await db.execute(
        select(WeeklyPlan).where(
            WeeklyPlan.user_id == USER_ID,
            WeeklyPlan.iso_year == y, WeeklyPlan.iso_week == w,
        )
    )
    return res.scalar_one_or_none()


async def week_progress(db: AsyncSession, plan: WeeklyPlan | None, d: date) -> dict:
    """수행률 단일 정의: 분모 = 휴식 제외 세션 수, 분자 = done/partial."""
    if plan is None:
        return {"done": 0, "total": 0, "completion_rate": 0, "week_km": 0.0, "goal_km": None, "days_km": [0] * 7}
    res = await db.execute(select(PlanSession).where(PlanSession.plan_id == plan.id))
    sessions = list(res.scalars())
    workable = [s for s in sessions if not s.is_rest]
    done = sum(1 for s in workable if s.status in ("done", "partial"))
    total = len(workable)

    ws = plan.week_start
    res = await db.execute(
        select(WorkoutLog).where(
            WorkoutLog.user_id == USER_ID,
            WorkoutLog.log_date >= ws,
            WorkoutLog.log_date <= ws + timedelta(days=6),
        )
    )
    logs = list(res.scalars())
    days_km = [0.0] * 7
    for log in logs:
        days_km[(log.log_date - ws).days] += float(log.distance_km or 0)
    return {
        "done": done, "total": total,
        "completion_rate": round(done / total * 100) if total else 0,
        "week_km": round(sum(days_km), 1),
        "goal_km": plan.goal_km,
        "days_km": [round(k, 1) for k in days_km],
    }


async def render_profile_context(db: AsyncSession) -> str:
    user = (await db.execute(select(User).where(User.id == USER_ID))).scalar_one_or_none()
    prof = (await db.execute(select(UserProfile).where(UserProfile.user_id == USER_ID))).scalar_one_or_none()
    goal = (await db.execute(
        select(Goal).where(Goal.user_id == USER_ID, Goal.is_active == True)  # noqa: E712
    )).scalar_one_or_none()
    settings = (await db.execute(select(AppSettings).where(AppSettings.user_id == USER_ID))).scalar_one_or_none()

    lines = ["## 사용자 프로필"]
    if user:
        lines.append(f"- 닉네임: {user.nickname}")
    if prof:
        if prof.height_cm: lines.append(f"- 키/체중/나이: {prof.height_cm}cm / {prof.weight_kg}kg / {prof.age}세")
        if prof.career_years: lines.append(f"- 러닝 경력: {prof.career_years}년")
        pbs = [f"10K {prof.pb_10k}" if prof.pb_10k else None,
               f"하프 {prof.pb_half}" if prof.pb_half else None,
               f"풀 {prof.pb_full}" if prof.pb_full else None]
        pbs = [p for p in pbs if p]
        if pbs: lines.append(f"- PB: {' · '.join(pbs)}")
        if prof.body_note: lines.append(f"- 메모: {prof.body_note}")
    if goal:
        dday = (goal.target_date - date.today()).days if goal.target_date else None
        lines.append(f"## 목표\n- {goal.race_type} {goal.target_time or ''}"
                     f" · {goal.target_date or '날짜 미정'}{f' (D-{dday})' if dday is not None else ''}")
        if goal.description: lines.append(f"- {goal.description}")
    if settings:
        lines.append(f"- 주간 목표 거리: {settings.weekly_goal_km}km")
    return "\n".join(lines)


async def render_availability_context(db: AsyncSession) -> str:
    """정기 훈련 가능 시간(기본 시간표)을 AI 컨텍스트로 직렬화."""
    res = await db.execute(select(AvailabilitySlot).where(
        AvailabilitySlot.user_id == USER_ID,
    ).order_by(AvailabilitySlot.sort, AvailabilitySlot.id))
    slots = list(res.scalars())
    if not slots:
        return "## 정기 훈련 가능 시간(기본 시간표)\n- 등록된 시간표 없음 — 일반적인 가용 시간을 가정"
    lines = ["## 정기 훈련 가능 시간(기본 시간표)"]
    for s in slots:
        days = "·".join(WEEKDAYS_KO[d] for d in s.days)
        parts = [f"{days} {s.title}",
                 f"{s.duration_min}분" if s.duration_min else None,
                 f"[{s.place}]" if s.place else None,
                 f"— {s.note}" if s.note else None]
        lines.append("- " + " ".join(p for p in parts if p))
    return "\n".join(lines)


async def render_recent_history(db: AsyncSession, days: int = 28) -> str:
    since = date.today() - timedelta(days=days)
    res = await db.execute(
        select(WorkoutLog).where(WorkoutLog.user_id == USER_ID, WorkoutLog.log_date >= since)
        .order_by(WorkoutLog.log_date.desc()).limit(30)
    )
    logs = list(res.scalars())
    if not logs:
        return "## 최근 훈련 기록\n- 최근 기록 없음"
    lines = ["## 최근 훈련 기록 (최신순)"]
    for log in logs:
        parts = [f"{log.log_date} {KIND_LABELS.get(log.kind, log.kind)}",
                 f"{log.distance_km}km" if log.distance_km else None,
                 f"페이스 {log.avg_pace}/km" if log.avg_pace else None,
                 f"심박 {log.avg_hr}" if log.avg_hr else None,
                 f"케이던스 {log.cadence}" if log.cadence else None,
                 f"통증 {log.pain_part}({log.pain_level}/10)" if log.pain_level else None,
                 f"소감: {log.user_comment}" if log.user_comment else None]
        lines.append("- " + " · ".join(p for p in parts if p))
    return "\n".join(lines)


def render_session_line(s: PlanSession) -> str:
    parts = [f"{s.session_date}({WEEKDAYS_KO[s.weekday]})",
             KIND_LABELS.get(s.kind, s.kind),
             s.title or "",
             f"{s.distance_km}km" if s.distance_km else None,
             f"{s.duration_min}{'~' + str(s.duration_min_max) if s.duration_min_max else ''}분" if s.duration_min else None,
             s.target_pace, f"[{s.status}]"]
    return " · ".join(str(p) for p in parts if p)


async def render_week_context(db: AsyncSession, plan: WeeklyPlan | None) -> str:
    if plan is None:
        return "## 이번 주 계획\n- 계획 없음"
    res = await db.execute(
        select(PlanSession).where(PlanSession.plan_id == plan.id).order_by(PlanSession.session_date)
    )
    sessions = list(res.scalars())
    lines = [f"## 이번 주 계획 ({plan.iso_year}-W{plan.iso_week}, {plan.week_start}~)"]
    if plan.direction: lines.append(f"- 방향: {plan.direction}")
    if plan.goal_km: lines.append(f"- 목표 거리: {plan.goal_km}km")
    lines += ["- " + render_session_line(s) for s in sessions]
    return "\n".join(lines)
