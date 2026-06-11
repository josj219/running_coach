"""당일 훈련 카드 생성 — 컨디션/날씨 반영."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import DailyPlan, PlanSession, get_db
from ..prompts import DAILY_PLAN_PROMPT
from ..services import coach
from ..services.context import (
    USER_ID, get_current_plan, render_availability_context,
    render_profile_context, render_recent_history, render_session_line,
)

router = APIRouter(prefix="/api/daily-plans", tags=["daily-plans"])


class DailyIn(BaseModel):
    condition_note: str = ""  # "수면 5시간, 약간 피곤" 등
    weather_note: str = ""    # "비 70%, 28도" 등


@router.post("", status_code=201)
async def generate_daily_plan(body: DailyIn, db: AsyncSession = Depends(get_db)):
    today = date.today()
    plan = await get_current_plan(db, today)
    if plan is None:
        raise HTTPException(404, {"code": "NOT_FOUND", "message": "이번 주 계획이 없습니다."})
    sess = (await db.execute(select(PlanSession).where(
        PlanSession.plan_id == plan.id, PlanSession.session_date == today,
    ))).scalar_one_or_none()
    if sess is None:
        raise HTTPException(404, {"code": "NOT_FOUND", "message": "오늘 계획된 세션이 없습니다."})

    profile = await render_profile_context(db)
    availability = await render_availability_context(db)
    history = await render_recent_history(db, days=14)
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

    daily = (await db.execute(select(DailyPlan).where(
        DailyPlan.user_id == USER_ID, DailyPlan.plan_date == today,
    ))).scalar_one_or_none() or DailyPlan(user_id=USER_ID, plan_date=today)
    daily.session_id = sess.id
    daily.sections = {k: data.get(k) for k in ("warmup", "main", "cooldown", "note", "detail")}
    daily.is_adjusted = bool(data.get("adjusted"))
    daily.adjust_reason = body.condition_note or None if data.get("adjusted") else None
    daily.status = "ready"
    db.add(daily)
    await db.commit()
    return {"plan_date": today.isoformat(), "sections": daily.sections,
            "is_adjusted": daily.is_adjusted}
