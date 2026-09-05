"""인증 라우터 — 로그인 / 내 정보 / 첫 로그인 온보딩 / 비밀번호 재설정(이메일 인증).

회원가입(셀프)은 제공하지 않는다. 계정은 서버에서 create_user로 만든다.
비밀번호를 잊으면 등록된 이메일로 6자리 인증 코드를 받아 재설정한다.
"""

import hashlib
import hmac
import secrets
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import create_token, get_current_user, hash_password, verify_password
from ..config import get_settings
from ..db import (
    AppSettings, AvailabilitySlot, Goal, PasswordReset, User, UserProfile, get_db, utcnow,
)
from ..mailer import send_mail

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


# ---- 비밀번호 재설정: 이메일로 6자리 코드 발송 → 코드 + 새 비밀번호로 변경 ----

RESET_MAX_ATTEMPTS = 5      # 틀린 코드 허용 횟수. 넘으면 코드 폐기 → 다시 받아야 한다
RESET_RESEND_COOLDOWN_S = 60  # 재발송 최소 간격(초). 메일 폭주 방지
PASSWORD_MIN_LEN = 8


class ForgotIn(BaseModel):
    email: str


class ResetIn(BaseModel):
    email: str
    code: str
    new_password: str


def _code_hash(user_id: int, code: str) -> str:
    key = get_settings().jwt_secret.encode("utf-8")
    return hmac.new(key, f"{user_id}:{code}".encode("utf-8"), hashlib.sha256).hexdigest()


def _aware(dt: datetime | None) -> datetime | None:
    """sqlite는 tz 정보를 버리고 naive로 돌려준다 → UTC로 간주해 비교 가능하게 맞춘다."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def _latest_reset(db: AsyncSession, user_id: int) -> PasswordReset | None:
    return (await db.execute(
        select(PasswordReset).where(PasswordReset.user_id == user_id)
        .order_by(PasswordReset.created_at.desc(), PasswordReset.id.desc()).limit(1)
    )).scalar_one_or_none()


def _reset_mail(code: str, ttl_min: int) -> tuple[str, str]:
    subject = f"[러닝 코치] 비밀번호 재설정 인증 코드 {code}"
    body = (
        "러닝 코치 비밀번호 재설정 요청이 접수됐습니다.\n\n"
        f"인증 코드: {code}\n\n"
        f"이 코드는 {ttl_min}분 동안만 유효하며 한 번만 사용할 수 있습니다.\n"
        "본인이 요청하지 않았다면 이 메일을 무시하세요. 비밀번호는 바뀌지 않습니다.\n"
    )
    return subject, body


@router.post("/forgot-password")
async def forgot_password(body: ForgotIn, db: AsyncSession = Depends(get_db)):
    """등록된 이메일이면 인증 코드를 보낸다. 계정 존재 여부를 노출하지 않기 위해 항상 200."""
    email = body.email.strip().lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None:
        return {"ok": True}

    now = utcnow()
    last = await _latest_reset(db, user.id)
    if last is not None and last.used_at is None:
        created = _aware(last.created_at)
        if created and (now - created).total_seconds() < RESET_RESEND_COOLDOWN_S:
            return {"ok": True}  # 방금 보냈다 — 재발송 안 함(폭주 방지)

    # 이전 미사용 코드는 모두 폐기 → 항상 최신 코드 하나만 유효
    await db.execute(delete(PasswordReset).where(
        PasswordReset.user_id == user.id, PasswordReset.used_at.is_(None)))

    s = get_settings()
    code = f"{secrets.randbelow(10 ** 6):06d}"
    db.add(PasswordReset(user_id=user.id, code_hash=_code_hash(user.id, code),
                         expires_at=now + timedelta(minutes=s.reset_code_ttl_min)))
    await db.commit()

    subject, text = _reset_mail(code, s.reset_code_ttl_min)
    try:
        await send_mail(user.email, subject, text)
    except Exception as e:  # SMTP 장애 — 방금 만든 코드를 지워 쿨다운에 걸리지 않게 하고 사용자에게 알린다.
        await db.execute(delete(PasswordReset).where(
            PasswordReset.user_id == user.id, PasswordReset.used_at.is_(None)))
        await db.commit()
        raise HTTPException(503, {"code": "MAIL_FAILED",
                                  "message": "인증 메일을 보내지 못했어요. 잠시 후 다시 시도해 주세요."}) from e
    return {"ok": True}


@router.post("/reset-password")
async def reset_password(body: ResetIn, db: AsyncSession = Depends(get_db)):
    """코드 검증 후 비밀번호 변경. 성공 시 바로 로그인 토큰을 준다."""
    invalid = HTTPException(400, {"code": "RESET_CODE_INVALID",
                                  "message": "인증 코드가 올바르지 않거나 만료됐어요. 코드를 다시 받아주세요."})
    if len(body.new_password) < PASSWORD_MIN_LEN:
        raise HTTPException(400, {"code": "WEAK_PASSWORD",
                                  "message": f"비밀번호는 {PASSWORD_MIN_LEN}자 이상이어야 해요."})

    email = body.email.strip().lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None:
        raise invalid

    reset = await _latest_reset(db, user.id)
    now = utcnow()
    if (reset is None or reset.used_at is not None
            or reset.attempts >= RESET_MAX_ATTEMPTS
            or _aware(reset.expires_at) < now):
        raise invalid

    if not hmac.compare_digest(reset.code_hash, _code_hash(user.id, body.code.strip())):
        reset.attempts += 1
        db.add(reset)
        await db.commit()
        raise invalid

    reset.used_at = now
    user.password_hash = hash_password(body.new_password)
    db.add_all([reset, user])
    await db.commit()
    return {"token": create_token(user.id), "user": _me(user)}


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
