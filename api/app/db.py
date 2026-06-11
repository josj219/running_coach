"""DB 엔진/세션 + ORM 모델 (SQLAlchemy 2.0 async).

V2_ARCHITECTURE.md §2 스키마 기반. 차이점:
- 훈련 종류(kind)는 디자인 시안의 영문 키(easy/interval/tempo/long/rest/strength/drill/core/mobility/race/other)
  문자열로 저장한다(PG ENUM 대신 — sqlite 호환 + 종류 추가 무중단).
- Strava/Garmin 연동을 위한 integrations / external_activities 테이블 추가.
- 스키마는 시작 시 create_all로 보장한다(스키마 진화 시 Alembic 도입 예정).
"""

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text,
    UniqueConstraint,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .config import get_settings

engine = create_async_engine(get_settings().database_url, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

WORKOUT_KINDS = [
    "easy", "interval", "tempo", "long", "race",
    "rest", "strength", "drill", "core", "mobility", "other",
]
SESSION_STATUS = ["planned", "done", "partial", "missed"]  # 예정/완료/부분완료/미수행
RECOVERY_LEVELS = ["low", "medium", "high"]  # 회복 필요도 낮음/보통/높음


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    nickname: Mapped[str] = mapped_column(String, default="고고조")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UserProfile(Base):
    __tablename__ = "user_profiles"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    height_cm: Mapped[float | None] = mapped_column(Float)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    age: Mapped[int | None] = mapped_column(Integer)
    career_years: Mapped[float | None] = mapped_column(Float)
    max_hr: Mapped[int | None] = mapped_column(Integer)
    resting_hr: Mapped[int | None] = mapped_column(Integer)
    vo2_max: Mapped[float | None] = mapped_column(Float)
    pb_10k: Mapped[str | None] = mapped_column(String)    # "00:42:13"
    pb_half: Mapped[str | None] = mapped_column(String)
    pb_full: Mapped[str | None] = mapped_column(String)
    body_note: Mapped[str | None] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(String)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Goal(Base):
    __tablename__ = "goals"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    race_type: Mapped[str] = mapped_column(String)         # '풀마라톤'
    target_time: Mapped[str | None] = mapped_column(String)  # "03:30:00"
    target_date: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AppSettings(Base):
    __tablename__ = "app_settings"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    weekly_goal_km: Mapped[float] = mapped_column(Float, default=45)
    pace_unit: Mapped[str] = mapped_column(String, default="분/km")
    distance_unit: Mapped[str] = mapped_column(String, default="km")
    notify_training: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_after_workout: Mapped[bool] = mapped_column(Boolean, default=True)
    coach_tone: Mapped[str] = mapped_column(String, default="calm")  # calm|warm|strict
    accent: Mapped[str] = mapped_column(String, default="#0088ff")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class WeeklyPlan(Base):
    __tablename__ = "weekly_plans"
    __table_args__ = (UniqueConstraint("user_id", "iso_year", "iso_week"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    iso_year: Mapped[int] = mapped_column(Integer)
    iso_week: Mapped[int] = mapped_column(Integer)
    week_start: Mapped[date] = mapped_column(Date)
    direction: Mapped[str | None] = mapped_column(Text)
    goal_km: Mapped[float | None] = mapped_column(Float)
    intensity: Mapped[str | None] = mapped_column(String)
    raw_md: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    sessions: Mapped[list["PlanSession"]] = relationship(back_populates="plan", cascade="all, delete-orphan")


class PlanSession(Base):
    __tablename__ = "sessions"
    __table_args__ = (UniqueConstraint("plan_id", "session_date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("weekly_plans.id", ondelete="CASCADE"))
    session_date: Mapped[date] = mapped_column(Date, index=True)
    weekday: Mapped[int] = mapped_column(Integer)  # 0=월
    kind: Mapped[str] = mapped_column(String)      # WORKOUT_KINDS
    title: Mapped[str | None] = mapped_column(String)
    distance_km: Mapped[float | None] = mapped_column(Float)
    duration_min: Mapped[int | None] = mapped_column(Integer)
    duration_min_max: Mapped[int | None] = mapped_column(Integer)
    target_pace: Mapped[str | None] = mapped_column(String)
    focus: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="planned")  # SESSION_STATUS
    is_rest: Mapped[bool] = mapped_column(Boolean, default=False)

    plan: Mapped[WeeklyPlan] = relationship(back_populates="sessions")


class DailyPlan(Base):
    __tablename__ = "daily_plans"
    __table_args__ = (UniqueConstraint("user_id", "plan_date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    plan_date: Mapped[date] = mapped_column(Date)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("sessions.id", ondelete="SET NULL"))
    sections: Mapped[dict] = mapped_column(JSON, default=dict)  # {warmup,main,cooldown,note,detail}
    is_adjusted: Mapped[bool] = mapped_column(Boolean, default=False)
    adjust_reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="ready")  # generating|ready|error
    raw_md: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WorkoutLog(Base):
    __tablename__ = "workout_logs"
    __table_args__ = (UniqueConstraint("user_id", "log_date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    session_id: Mapped[int | None] = mapped_column(ForeignKey("sessions.id", ondelete="SET NULL"))
    log_date: Mapped[date] = mapped_column(Date, index=True)
    kind: Mapped[str] = mapped_column(String)
    distance_km: Mapped[float] = mapped_column(Float, default=0)
    duration_sec: Mapped[int | None] = mapped_column(Integer)
    avg_pace: Mapped[str | None] = mapped_column(String)   # "6:12"
    avg_hr: Mapped[int | None] = mapped_column(Integer)
    max_hr: Mapped[int | None] = mapped_column(Integer)
    cadence: Mapped[int | None] = mapped_column(Integer)
    elevation_m: Mapped[int | None] = mapped_column(Integer)
    feel: Mapped[int | None] = mapped_column(Integer)       # 1~4 (디자인 FeelPicker)
    fatigue_num: Mapped[int | None] = mapped_column(Integer)  # 0~10
    pain_part: Mapped[str | None] = mapped_column(String)
    pain_level: Mapped[int] = mapped_column(Integer, default=0)
    user_comment: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String)
    source: Mapped[str] = mapped_column(String, default="manual")  # manual|strava|garmin
    external_id: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    review: Mapped["WorkoutReview | None"] = relationship(back_populates="log", uselist=False, cascade="all, delete-orphan")


class WorkoutReview(Base):
    __tablename__ = "workout_reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    log_id: Mapped[int] = mapped_column(ForeignKey("workout_logs.id", ondelete="CASCADE"), unique=True)
    summary: Mapped[str | None] = mapped_column(Text)  # 실제 수행 훈련 요약(소감 종합)
    strengths: Mapped[str | None] = mapped_column(Text)
    improvements: Mapped[str | None] = mapped_column(Text)
    recovery: Mapped[str | None] = mapped_column(String)  # RECOVERY_LEVELS
    coach_comment: Mapped[str | None] = mapped_column(Text)
    raw_md: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    log: Mapped[WorkoutLog] = relationship(back_populates="review")


class WeeklyEvaluation(Base):
    __tablename__ = "weekly_evaluations"
    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("weekly_plans.id", ondelete="CASCADE"), unique=True)
    total_km: Mapped[float] = mapped_column(Float, default=0)
    done_sessions: Mapped[int] = mapped_column(Integer, default=0)
    total_sessions: Mapped[int] = mapped_column(Integer, default=0)
    completion_rate: Mapped[int] = mapped_column(Integer, default=0)
    coach_message: Mapped[str | None] = mapped_column(Text)
    detail_md: Mapped[str | None] = mapped_column(Text)
    is_partial: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_md: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AvailabilitySlot(Base):
    """정기 훈련 가능 시간(기본 시간표) — 요일 멀티선택 슬롯 단위.

    예: '점심 헬스장 45분' days=[0..4], '퇴근런' days=[1,3].
    주간 계획 AI 생성 시 세션 배치 기준으로 쓰인다.
    """
    __tablename__ = "availability_slots"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    days: Mapped[list] = mapped_column(JSON, default=list)  # [0..6], 0=월
    title: Mapped[str] = mapped_column(String)              # '점심 헬스장'
    duration_min: Mapped[int | None] = mapped_column(Integer)
    place: Mapped[str | None] = mapped_column(String)       # 실내 헬스장|야외|트레드밀|기타
    note: Mapped[str | None] = mapped_column(Text)
    sort: Mapped[int] = mapped_column(Integer, default=0)


class Integration(Base):
    """외부 서비스(Strava/Garmin) OAuth 연결 상태."""
    __tablename__ = "integrations"
    __table_args__ = (UniqueConstraint("user_id", "provider"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String)  # strava|garmin
    access_token: Mapped[str | None] = mapped_column(String)
    refresh_token: Mapped[str | None] = mapped_column(String)
    expires_at: Mapped[int | None] = mapped_column(Integer)  # epoch sec
    athlete_id: Mapped[str | None] = mapped_column(String)
    athlete_name: Mapped[str | None] = mapped_column(String)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ExternalActivity(Base):
    """Strava/Garmin에서 가져온 활동 캐시 — 기록 입력 자동 채움에 사용."""
    __tablename__ = "external_activities"
    __table_args__ = (UniqueConstraint("provider", "external_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String)
    external_id: Mapped[str] = mapped_column(String)
    name: Mapped[str | None] = mapped_column(String)
    sport_type: Mapped[str | None] = mapped_column(String)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    distance_km: Mapped[float | None] = mapped_column(Float)
    duration_sec: Mapped[int | None] = mapped_column(Integer)
    avg_pace: Mapped[str | None] = mapped_column(String)
    avg_hr: Mapped[int | None] = mapped_column(Integer)
    max_hr: Mapped[int | None] = mapped_column(Integer)
    cadence: Mapped[int | None] = mapped_column(Integer)
    elevation_m: Mapped[int | None] = mapped_column(Integer)
    imported_log_id: Mapped[int | None] = mapped_column(ForeignKey("workout_logs.id", ondelete="SET NULL"))
    raw: Mapped[dict] = mapped_column(JSON, default=dict)


async def get_db():
    async with SessionLocal() as session:
        yield session


# create_all은 기존 테이블에 새 컬럼을 추가하지 않는다 — Alembic 도입 전 경량 마이그레이션
_ADDED_COLUMNS = [("workout_reviews", "summary", "TEXT")]


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for table, col, typ in _ADDED_COLUMNS:
            if engine.dialect.name == "sqlite":
                rows = (await conn.exec_driver_sql(f"PRAGMA table_info({table})")).fetchall()
                if any(r[1] == col for r in rows):
                    continue
                await conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
            else:
                await conn.exec_driver_sql(
                    f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {typ}")
