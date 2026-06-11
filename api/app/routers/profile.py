"""프로필/목표/설정 조회 + 수정."""

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import AppSettings, Goal, User, UserProfile, get_db
from ..services.context import USER_ID

router = APIRouter(prefix="/api", tags=["profile"])


@router.get("/profile")
async def get_profile(db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.id == USER_ID))).scalar_one_or_none()
    p = (await db.execute(select(UserProfile).where(UserProfile.user_id == USER_ID))).scalar_one_or_none()
    return {
        "nickname": user.nickname if user else "러너",
        "height_cm": p.height_cm if p else None, "weight_kg": p.weight_kg if p else None,
        "age": p.age if p else None, "career_years": p.career_years if p else None,
        "max_hr": p.max_hr if p else None, "resting_hr": p.resting_hr if p else None,
        "vo2_max": p.vo2_max if p else None,
        "pb_10k": p.pb_10k if p else None, "pb_half": p.pb_half if p else None,
        "pb_full": p.pb_full if p else None,
        "body_note": p.body_note if p else None, "avatar_url": p.avatar_url if p else None,
    }


class ProfilePatch(BaseModel):
    nickname: str | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    age: int | None = None
    career_years: float | None = None
    max_hr: int | None = None
    resting_hr: int | None = None
    vo2_max: float | None = None
    pb_10k: str | None = None
    pb_half: str | None = None
    pb_full: str | None = None
    body_note: str | None = None


@router.patch("/profile")
async def patch_profile(body: ProfilePatch, db: AsyncSession = Depends(get_db)):
    data = body.model_dump(exclude_unset=True)
    if "nickname" in data:
        user = (await db.execute(select(User).where(User.id == USER_ID))).scalar_one()
        user.nickname = data.pop("nickname")
    p = (await db.execute(select(UserProfile).where(
        UserProfile.user_id == USER_ID,
    ))).scalar_one_or_none() or UserProfile(user_id=USER_ID)
    for k, v in data.items():
        setattr(p, k, v)
    db.add(p)
    await db.commit()
    return await get_profile(db)


@router.get("/goal")
async def get_goal(db: AsyncSession = Depends(get_db)):
    g = (await db.execute(select(Goal).where(
        Goal.user_id == USER_ID, Goal.is_active == True,  # noqa: E712
    ))).scalar_one_or_none()
    if g is None:
        return {"race_type": None, "target_time": None, "target_date": None,
                "dday": None, "description": None}
    return {
        "race_type": g.race_type, "target_time": g.target_time,
        "target_date": g.target_date.isoformat() if g.target_date else None,
        "dday": (g.target_date - date.today()).days if g.target_date else None,
        "description": g.description,
    }


class GoalPatch(BaseModel):
    race_type: str
    target_time: str | None = None
    target_date: date | None = None
    description: str | None = None


@router.put("/goal")
async def put_goal(body: GoalPatch, db: AsyncSession = Depends(get_db)):
    g = (await db.execute(select(Goal).where(
        Goal.user_id == USER_ID, Goal.is_active == True,  # noqa: E712
    ))).scalar_one_or_none() or Goal(user_id=USER_ID, race_type=body.race_type)
    g.race_type = body.race_type
    g.target_time = body.target_time
    g.target_date = body.target_date
    g.description = body.description
    db.add(g)
    await db.commit()
    return await get_goal(db)


@router.get("/settings")
async def get_app_settings(db: AsyncSession = Depends(get_db)):
    s = (await db.execute(select(AppSettings).where(
        AppSettings.user_id == USER_ID,
    ))).scalar_one_or_none()
    if s is None:
        s = AppSettings(user_id=USER_ID)
        db.add(s)
        await db.commit()
    return {"weekly_goal_km": s.weekly_goal_km, "pace_unit": s.pace_unit,
            "distance_unit": s.distance_unit, "notify_training": s.notify_training,
            "notify_after_workout": s.notify_after_workout,
            "coach_tone": s.coach_tone, "accent": s.accent}


class SettingsPatch(BaseModel):
    weekly_goal_km: float | None = None
    pace_unit: str | None = None
    distance_unit: str | None = None
    notify_training: bool | None = None
    notify_after_workout: bool | None = None
    coach_tone: str | None = None
    accent: str | None = None


@router.patch("/settings")
async def patch_app_settings(body: SettingsPatch, db: AsyncSession = Depends(get_db)):
    s = (await db.execute(select(AppSettings).where(
        AppSettings.user_id == USER_ID,
    ))).scalar_one_or_none() or AppSettings(user_id=USER_ID)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    db.add(s)
    await db.commit()
    return await get_app_settings(db)
