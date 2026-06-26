"""주간 계획 조회/생성/조정/평가."""

import json
import re
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..db import PlanSession, User, WeeklyEvaluation, WeeklyPlan, WorkoutLog, get_db
from ..prompts import PLAN_ADJUSTMENT_PROMPT, WEEKLY_EVALUATION_PROMPT, WEEKLY_PLAN_PROMPT
from ..services import coach
from ..services.context import (
    get_current_plan, iso_week_of, render_availability_context,
    render_profile_context, render_recent_history, render_session_line,
    render_week_context, week_progress, week_start_of,
)
from .today import _session_dict

router = APIRouter(prefix="/api", tags=["weeks"])

ISO_RE = re.compile(r"^(\d{4})-W(\d{1,2})$")


def _parse_iso(iso_week: str) -> tuple[int, int]:
    m = ISO_RE.match(iso_week)
    if not m:
        raise HTTPException(422, {"code": "VALIDATION_ERROR", "message": "iso_week 형식: 2026-W23"})
    return int(m.group(1)), int(m.group(2))


def _log_summary(l: WorkoutLog) -> dict:
    """주간 탭에서 일자별 기록 표시 + 기록 수정 프리필에 쓰는 컴팩트 요약."""
    return {
        "id": l.id, "distance_km": l.distance_km, "duration_sec": l.duration_sec,
        "avg_pace": l.avg_pace, "avg_hr": l.avg_hr, "max_hr": l.max_hr,
        "cadence": l.cadence, "feel": l.feel, "pain_part": l.pain_part,
        "pain_level": l.pain_level, "user_comment": l.user_comment, "source": l.source,
    }


async def _plan_payload(db: AsyncSession, plan: WeeklyPlan, user_id: int) -> dict:
    res = await db.execute(select(PlanSession).where(PlanSession.plan_id == plan.id)
                           .order_by(PlanSession.session_date))
    sessions = [_session_dict(s) for s in res.scalars()]
    # 그 주의 실제 기록을 일자별로 각 세션에 첨부 — 과거 일자 기록 표시/수정 진입점
    logs_res = await db.execute(select(WorkoutLog).where(
        WorkoutLog.user_id == user_id,
        WorkoutLog.log_date >= plan.week_start,
        WorkoutLog.log_date <= plan.week_start + timedelta(days=6),
    ))
    logs_by_date = {l.log_date.isoformat(): l for l in logs_res.scalars()}
    for s in sessions:
        log = logs_by_date.get(s["session_date"])
        s["log"] = _log_summary(log) if log else None
    progress = await week_progress(db, plan, date.today(), user_id)
    ev = (await db.execute(select(WeeklyEvaluation).where(
        WeeklyEvaluation.plan_id == plan.id,
    ))).scalar_one_or_none()
    return {
        "iso_week": f"{plan.iso_year}-W{plan.iso_week:02d}",
        "week_start": plan.week_start.isoformat(),
        "direction": plan.direction, "goal_km": plan.goal_km,
        "intensity": plan.intensity,
        "progress": progress, "sessions": sessions,
        "evaluation": None if ev is None else {
            "total_km": ev.total_km, "done_sessions": ev.done_sessions,
            "total_sessions": ev.total_sessions, "completion_rate": ev.completion_rate,
            "coach_message": ev.coach_message, "detail_md": ev.detail_md,
            "is_partial": ev.is_partial,
        },
    }


@router.get("/weeks/current")
async def get_current_week(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    plan = await get_current_plan(db, date.today(), user.id)
    if plan is None:
        raise HTTPException(404, {"code": "NOT_FOUND", "message": "이번 주 계획이 없습니다."})
    return await _plan_payload(db, plan, user.id)


@router.get("/weeks/{iso_week}")
async def get_week(iso_week: str, user: User = Depends(get_current_user),
                   db: AsyncSession = Depends(get_db)):
    y, w = _parse_iso(iso_week)
    plan = (await db.execute(select(WeeklyPlan).where(
        WeeklyPlan.user_id == user.id, WeeklyPlan.iso_year == y, WeeklyPlan.iso_week == w,
    ))).scalar_one_or_none()
    if plan is None:
        raise HTTPException(404, {"code": "NOT_FOUND", "message": f"{iso_week} 계획이 없습니다."})
    return await _plan_payload(db, plan, user.id)


@router.get("/stats/weekly")
async def weekly_stats(weeks: int = 6, user: User = Depends(get_current_user),
                       db: AsyncSession = Depends(get_db)):
    """기록 탭 — 최근 N주 거리/세션/수행률 + 최근 러닝 목록."""
    today = date.today()
    out = []
    for i in range(weeks):
        ws = week_start_of(today) - timedelta(weeks=i)
        y, w = iso_week_of(ws)
        plan = (await db.execute(select(WeeklyPlan).where(
            WeeklyPlan.user_id == user.id, WeeklyPlan.iso_year == y, WeeklyPlan.iso_week == w,
        ))).scalar_one_or_none()
        progress = await week_progress(db, plan, ws, user.id)
        if plan is None:
            # 계획 없는 주도 실제 로그 거리는 집계
            res = await db.execute(select(WorkoutLog).where(
                WorkoutLog.user_id == user.id,
                WorkoutLog.log_date >= ws, WorkoutLog.log_date <= ws + timedelta(days=6),
            ))
            km = round(sum(float(l.distance_km or 0) for l in res.scalars()), 1)
            progress["week_km"] = km
        out.append({
            "iso_week": f"{y}-W{w:02d}", "week_start": ws.isoformat(),
            "current": i == 0, **progress,
        })
    return {"weeks": out}


class GenerateWeekIn(BaseModel):
    schedule_note: str = ""   # 이번 주 일정(회식/출장/운동 불가 시간 등)
    condition_note: str = ""  # 컨디션/통증
    week_start: date | None = None  # 기본: 이번 주 월요일


@router.post("/weekly-plans", status_code=201)
async def generate_weekly_plan(body: GenerateWeekIn, user: User = Depends(get_current_user),
                               db: AsyncSession = Depends(get_db)):
    today = date.today()
    ws = body.week_start or week_start_of(today)
    y, w = iso_week_of(ws)

    profile = await render_profile_context(db, user.id)
    availability = await render_availability_context(db, user.id)
    history = await render_recent_history(db, user.id)
    prev_plan = await get_current_plan(db, ws - timedelta(days=7), user.id)
    prev_ctx = await render_week_context(db, prev_plan)
    prev_progress = await week_progress(db, prev_plan, ws - timedelta(days=1), user.id)

    message = (
        f"{profile}\n\n{availability}\n\n{history}\n\n[지난 주]\n{prev_ctx}\n"
        f"지난 주 수행률(앱 집계): {prev_progress['completion_rate']}% "
        f"({prev_progress['done']}/{prev_progress['total']}) · {prev_progress['week_km']}km\n\n"
        f"[이번 주]\n- 주 시작(월): {ws} · 오늘: {today}\n"
        f"[이번 주 특이 일정]\n{body.schedule_note or '없음 — 기본 시간표 그대로'}\n"
        f"[컨디션 메모]\n{body.condition_note or '없음'}\n\n"
        "정기 훈련 가능 시간과 특이 일정을 검토한 뒤 이번 주 훈련 계획 JSON을 생성해 주세요."
    )
    try:
        data = await coach.generate("weekly", WEEKLY_PLAN_PROMPT, message)
    except coach.CoachError as e:
        raise HTTPException(503, {"code": "AI_UNAVAILABLE", "message": str(e)})

    # upsert plan
    plan = (await db.execute(select(WeeklyPlan).where(
        WeeklyPlan.user_id == user.id, WeeklyPlan.iso_year == y, WeeklyPlan.iso_week == w,
    ))).scalar_one_or_none()
    if plan is None:
        plan = WeeklyPlan(user_id=user.id, iso_year=y, iso_week=w, week_start=ws)
        db.add(plan)
    plan.direction = data.get("direction")
    plan.goal_km = data.get("goal_km")
    plan.intensity = data.get("intensity")
    plan.raw_md = json.dumps(data, ensure_ascii=False)
    await db.flush()

    # 세션 갈아끼우기 — 단, 이미 완료(done/partial)된 세션은 보존
    res = await db.execute(select(PlanSession).where(PlanSession.plan_id == plan.id))
    existing = {s.session_date: s for s in res.scalars()}
    for sd in data.get("sessions", []):
        try:
            d = datetime.strptime(sd["date"], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            continue
        if d in existing and existing[d].status in ("done", "partial"):
            continue
        s = existing.get(d) or PlanSession(plan_id=plan.id, session_date=d, weekday=d.weekday(), kind="other")
        s.weekday = d.weekday()
        s.kind = sd.get("kind", "other")
        s.title = sd.get("title")
        s.distance_km = sd.get("distance_km")
        s.duration_min = sd.get("duration_min")
        s.duration_min_max = sd.get("duration_min_max")
        s.target_pace = sd.get("target_pace")
        s.focus = sd.get("focus")
        s.note = sd.get("note")
        s.is_rest = bool(sd.get("is_rest"))
        if d not in existing:
            db.add(s)
    await db.commit()
    return await _plan_payload(db, plan, user.id)


class AdjustIn(BaseModel):
    reason: str  # "무릎 통증 3/10", "야근으로 수요일 불가" 등


@router.post("/weeks/current/adjust")
async def adjust_current_week(body: AdjustIn, user: User = Depends(get_current_user),
                              db: AsyncSession = Depends(get_db)):
    today = date.today()
    plan = await get_current_plan(db, today, user.id)
    if plan is None:
        raise HTTPException(404, {"code": "NOT_FOUND", "message": "이번 주 계획이 없습니다."})

    week_ctx = await render_week_context(db, plan)
    history = await render_recent_history(db, user.id, days=14)
    message = (f"{week_ctx}\n\n{history}\n\n오늘: {today}\n조정 사유: {body.reason}\n\n"
               "남은 세션 조정 JSON을 생성해 주세요.")
    try:
        data = await coach.generate("adjust", PLAN_ADJUSTMENT_PROMPT, message)
    except coach.CoachError as e:
        raise HTTPException(503, {"code": "AI_UNAVAILABLE", "message": str(e)})

    res = await db.execute(select(PlanSession).where(PlanSession.plan_id == plan.id))
    by_date = {s.session_date: s for s in res.scalars()}
    changed = []
    for ch in data.get("changes", []):
        try:
            d = datetime.strptime(ch["date"], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            continue
        if d < today:
            continue  # 지난 세션 불변
        s = by_date.get(d)
        if s is not None and s.status in ("done", "partial"):
            continue
        if s is None:
            s = PlanSession(plan_id=plan.id, session_date=d, weekday=d.weekday(), kind="other")
            db.add(s)
        s.kind = ch.get("kind", s.kind)
        s.title = ch.get("title", s.title)
        s.distance_km = ch.get("distance_km")
        s.duration_min = ch.get("duration_min")
        s.duration_min_max = ch.get("duration_min_max")
        s.target_pace = ch.get("target_pace")
        s.focus = ch.get("focus")
        s.note = ch.get("note")
        s.is_rest = bool(ch.get("is_rest"))
        changed.append(d.isoformat())
    await db.commit()
    payload = await _plan_payload(db, plan, user.id)
    payload["adjustment"] = {"reason": data.get("reason"), "changed": changed,
                             "kept": data.get("kept", [])}
    return payload


@router.post("/weeks/current/evaluation")
async def evaluate_current_week(user: User = Depends(get_current_user),
                                db: AsyncSession = Depends(get_db)):
    today = date.today()
    plan = await get_current_plan(db, today, user.id)
    if plan is None:
        raise HTTPException(404, {"code": "NOT_FOUND", "message": "이번 주 계획이 없습니다."})

    progress = await week_progress(db, plan, today, user.id)
    week_ctx = await render_week_context(db, plan)
    history = await render_recent_history(db, user.id, days=35)
    is_partial = today.weekday() < 6
    message = (
        f"{week_ctx}\n\n{history}\n\n"
        f"[수행률(앱 집계)] {progress['completion_rate']}% "
        f"({progress['done']}/{progress['total']}) · 총 {progress['week_km']}km\n"
        f"오늘: {today} ({'주중 중간 평가' if is_partial else '주간 종료 평가'})\n\n"
        "주간 성장 리포트 JSON을 생성해 주세요."
    )
    try:
        data = await coach.generate("evaluation", WEEKLY_EVALUATION_PROMPT, message)
    except coach.CoachError as e:
        raise HTTPException(503, {"code": "AI_UNAVAILABLE", "message": str(e)})

    ev = (await db.execute(select(WeeklyEvaluation).where(
        WeeklyEvaluation.plan_id == plan.id,
    ))).scalar_one_or_none() or WeeklyEvaluation(plan_id=plan.id)
    ev.total_km = progress["week_km"]
    ev.done_sessions = progress["done"]
    ev.total_sessions = progress["total"]
    ev.completion_rate = progress["completion_rate"]
    ev.coach_message = data.get("coach_message")
    ev.detail_md = data.get("detail_md")
    ev.is_partial = is_partial
    ev.raw_md = json.dumps(data, ensure_ascii=False)
    db.add(ev)
    await db.commit()
    return await _plan_payload(db, plan, user.id)
