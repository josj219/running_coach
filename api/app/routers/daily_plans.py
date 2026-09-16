"""당일 훈련 카드 생성 — 컨디션/날씨 반영."""

from datetime import date, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..db import DailyPlan, DailyProposal, JourneyEvent, PlanSession, User, WorkoutLog, get_db, utcnow
from ..services.records import lock_user, session_values
from ..prompts import DAILY_PLAN_PROMPT
from ..services import coach
from ..services.context import (
    get_current_plan, render_availability_context,
    render_profile_context, render_recent_history, render_session_line,
)

router = APIRouter(prefix="/api/daily-plans", tags=["daily-plans"])


class DailyIn(BaseModel):
    condition_note: str = ""  # "수면 5시간, 약간 피곤" 등
    preview: bool = False
    weather_note: str = ""    # "비 70%, 28도" 등


@router.post("", status_code=201)
async def generate_daily_plan(body: DailyIn, user: User = Depends(get_current_user),
                              db: AsyncSession = Depends(get_db)):
    today = date.today()
    plan = await get_current_plan(db, today, user.id)
    if plan is None:
        raise HTTPException(404, {"code": "NOT_FOUND", "message": "이번 주 계획이 없습니다."})
    sess = (await db.execute(select(PlanSession).where(
        PlanSession.plan_id == plan.id, PlanSession.session_date == today,
    ))).scalar_one_or_none()
    if sess is None:
        raise HTTPException(404, {"code": "NOT_FOUND", "message": "오늘 계획된 세션이 없습니다."})

    if sess.status != "planned":
        raise HTTPException(409, "기록이 있는 세션은 보존합니다. 다음 훈련을 조정하세요.")

    profile = await render_profile_context(db, user.id)
    availability = await render_availability_context(db, user.id)
    history = await render_recent_history(db, user.id, days=14)
    message = (
        f"{profile}\n\n{availability}\n\n{history}\n\n"
        f"## 오늘 세션 (주간 계획)\n{render_session_line(sess)}\n"
        f"메모: {sess.note or '없음'}\n\n"
        f"## 오늘 컨디션\n{body.condition_note or '특이사항 없음'}\n"
        f"## 날씨\n{body.weather_note or '정보 없음'}\n\n"
        "오늘 훈련 카드 JSON을 생성해 주세요."
    )
    try:
        data = await coach.generate("daily", DAILY_PLAN_PROMPT, message)
    except coach.CoachError as e:
        raise HTTPException(503, {"code": "AI_UNAVAILABLE", "message": str(e)})

    await lock_user(db, user.id)
    await db.refresh(sess)
    if sess.status != "planned":
        raise HTTPException(409, "생성 중 운동이 기록되어 변경을 적용하지 않았습니다.")
    daily = (await db.execute(select(DailyPlan).where(
        DailyPlan.user_id == user.id, DailyPlan.plan_date == today))).scalar_one_or_none()
    before = {"session": session_values(sess), "sections": daily.sections if daily else None}
    if body.preview or daily:
        proposal = DailyProposal(user_id=user.id, session_id=sess.id, plan_date=today,
            reason=body.condition_note or body.weather_note or "컨디션 재확인", before=before, data=data)
        db.add(proposal)
        await db.commit()
        return {"proposal_id": proposal.id, "created_at": proposal.created_at.isoformat(),
                "reason": proposal.reason, "before": before,
                "after": {"session": {**before["session"], **(data.get("session") or {})} if data.get("adjusted") else before["session"],
                          "sections": {k: data.get(k) for k in ("warmup", "main", "cooldown", "note", "detail")}},
                "requires_apply": True}
    return await _apply(db, user.id, sess, data, body.condition_note or body.weather_note or "첫 당일 설계", before)


async def _apply(db, user_id, sess, data, reason, before):
    daily = (await db.execute(select(DailyPlan).where(DailyPlan.user_id == user_id,
        DailyPlan.plan_date == sess.session_date))).scalar_one_or_none() or DailyPlan(user_id=user_id, plan_date=sess.session_date)
    daily.session_id = sess.id
    daily.sections = {k: data.get(k) for k in ("warmup", "main", "cooldown", "note", "detail")}
    daily.is_adjusted = bool(data.get("adjusted"))
    daily.adjust_reason = reason
    daily.status = "ready"
    sdata = data.get("session")
    updated = bool(data.get("adjusted") and isinstance(sdata, dict))
    if updated:
        for k in session_values(sess):
            if k in sdata:
                setattr(sess, k, sdata[k])
    daily.session_updated = updated
    daily.created_at = utcnow()
    db.add(daily)
    db.add(JourneyEvent(user_id=user_id, event_type="condition_changed", entity_id=sess.id,
        reason=reason, before=before, after={"session": session_values(sess), "sections": daily.sections}))
    await db.commit()
    return {"plan_date": str(sess.session_date), "sections": daily.sections,
        "is_adjusted": daily.is_adjusted, "session_updated": updated}


@router.post("/proposals/{proposal_id}/apply")
async def apply_proposal(proposal_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await lock_user(db, user.id)
    proposal = (await db.execute(select(DailyProposal).where(DailyProposal.id == proposal_id,
        DailyProposal.user_id == user.id))).scalar_one_or_none()
    if not proposal:
        raise HTTPException(404, "변경 제안이 없습니다.")
    if proposal.applied:
        return {"applied": True}
    created = proposal.created_at.replace(tzinfo=timezone.utc) if proposal.created_at.tzinfo is None else proposal.created_at
    if proposal.plan_date != date.today() or utcnow() - created > timedelta(minutes=30):
        raise HTTPException(409, "제안이 만료되었습니다. 현재 컨디션으로 다시 생성하세요.")
    sess = await db.get(PlanSession, proposal.session_id)
    recorded = (await db.execute(select(WorkoutLog.id).where(WorkoutLog.session_id == sess.id).limit(1))).scalar_one_or_none()
    daily = (await db.execute(select(DailyPlan).where(DailyPlan.user_id == user.id,
        DailyPlan.plan_date == proposal.plan_date))).scalar_one_or_none()
    now = {"session": session_values(sess), "sections": daily.sections if daily else None}
    if recorded or sess.status != "planned" or now != proposal.before:
        raise HTTPException(409, "계획 또는 기록이 변경되었습니다. 최신 상태로 다시 확인하세요.")
    proposal.applied = True
    return await _apply(db, user.id, sess, proposal.data, proposal.reason, proposal.before)
