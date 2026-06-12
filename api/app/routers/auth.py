"""인증 라우터 — 로그인 / 내 정보 / 첫 로그인 온보딩.

회원가입(셀프)은 제공하지 않는다. 계정은 서버에서 create_user로 만든다.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import create_token, get_current_user, verify_password
from ..db import (
    AppSettings, AvailabilitySlot, Goal, User, UserProfile, get_db,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: str
    password: str


def _me(user: User) -> dict:
    return {"id": user.id, "email": user.email, "nickname": user.nickname,
            "onboarded": user.onboarded}


@router.post("/login")
async def login(body: LoginIn, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(
        select(User).where(User.email == body.email.strip().lower())
    )).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, {"code": "BAD_CREDENTIALS", "message": "이메일 또는 비밀번호가 올바르지 않습니다."})
    return {"token": create_token(user.id), "user": _me(user)}


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return _me(user)


# ---- 첫 로그인 온보딩: 프로필 + 목표 + 시간표를 한 번에 저장 ----

class OnboardSlot(BaseModel):
    days: list[int]
    title: str
    duration_min: int | None = None
    place: str | None = None
    note: str | None = None


class OnboardIn(BaseModel):
    nickname: str
    # 신체·기록
    height_cm: float | None = None
    weight_kg: float | None = None
    age: int | None = None
    career_years: float | None = None
    pb_10k: str | None = None
    pb_half: str | None = None
    pb_full: str | None = None
    body_note: str | None = None
    # 목표
    race_type: str | None = None
    target_time: str | None = None
    target_date: date | None = None
    goal_description: str | None = None
    # 주간 목표 거리 + 기본 시간표
    weekly_goal_km: float | None = None
    slots: list[OnboardSlot] = []


@router.post("/onboard")
async def onboard(body: OnboardIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    uid = user.id
    user.nickname = body.nickname.strip() or user.nickname

    # 프로필 (upsert)
    prof = (await db.execute(
        select(UserProfile).where(UserProfile.user_id == uid)
    )).scalar_one_or_none() or UserProfile(user_id=uid)
    for f in ("height_cm", "weight_kg", "age", "career_years",
              "pb_10k", "pb_half", "pb_full", "body_note"):
        setattr(prof, f, getattr(body, f))
    db.add(prof)

    # 목표 (race_type이 있을 때만)
    if body.race_type:
        goal = (await db.execute(
            select(Goal).where(Goal.user_id == uid, Goal.is_active == True)  # noqa: E712
        )).scalar_one_or_none() or Goal(user_id=uid, race_type=body.race_type)
        goal.race_type = body.race_type
        goal.target_time = body.target_time
        goal.target_date = body.target_date
        goal.description = body.goal_description
        goal.is_active = True
        db.add(goal)

    # 설정 (주간 목표 거리)
    settings = (await db.execute(
        select(AppSettings).where(AppSettings.user_id == uid)
    )).scalar_one_or_none() or AppSettings(user_id=uid)
    if body.weekly_goal_km is not None:
        settings.weekly_goal_km = body.weekly_goal_km
    db.add(settings)

    # 기본 시간표 (전체 교체)
    await db.execute(delete(AvailabilitySlot).where(AvailabilitySlot.user_id == uid))
    for i, s in enumerate(body.slots):
        db.add(AvailabilitySlot(user_id=uid, days=s.days, title=s.title,
                                duration_min=s.duration_min, place=s.place,
                                note=s.note, sort=i))

    user.onboarded = True
    db.add(user)
    await db.commit()
    return _me(user)
