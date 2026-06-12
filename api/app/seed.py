"""데모 시드 — SEED_DEMO=1 일 때만 동작(로컬 개발·테스트용).

운영(도그푸딩)은 깨끗하게 시작한다: 계정은 `python -m app.create_user`로 생성하고,
프로필은 첫 로그인 온보딩으로 입력한다. 따라서 기본값(플래그 없음)에서 seed()는 아무것도
하지 않는다. SEED_DEMO=1 이면 로그인 가능한 데모 계정(고고조)과 데모 주간 계획을 만든다.
"""

import json
import os
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import hash_password
from .db import (
    AppSettings, AvailabilitySlot, Goal, PlanSession, User, UserProfile, WeeklyPlan,
)
from .services.context import iso_week_of, week_start_of

USER_ID = 1
DEMO_EMAIL = "demo@coach.local"
DEMO_PASSWORD = "demo-pass-1234"  # 로컬/테스트 전용


def _load_v1_settings() -> dict:
    base = os.environ.get("KNOWLEDGE_BASE_DIR", "")
    path = os.path.join(base, "app_settings.json") if base else ""
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


async def seed(db: AsyncSession) -> None:
    # 운영은 데모 시드를 돌리지 않는다 — 계정은 create_user, 프로필은 온보딩.
    if os.environ.get("SEED_DEMO") != "1":
        return

    user = (await db.execute(select(User).where(User.id == USER_ID))).scalar_one_or_none()
    if user is None:
        v1 = _load_v1_settings()
        nickname = v1.get("nickname", "고고조")
        db.add(User(id=USER_ID, email=DEMO_EMAIL, nickname=nickname,
                    password_hash=hash_password(DEMO_PASSWORD), onboarded=True))
        await db.flush()
        # 훈련 가능 시간은 availability_slots로 분리 — body_note에는 체형·부상 정보만
        db.add(UserProfile(
            user_id=USER_ID, height_cm=178, weight_kg=80, age=35, career_years=2,
            pb_10k="00:42:13", pb_half="01:38:00", pb_full="03:51:00",
            body_note=("어깨 넓고 하체 근육형. 왼쪽 발목 고질 통증 → 장거리 시 왼쪽 무릎 통증 경향. "
                       "2026-05-15 안와골절 후 회복기, 6월부터 기초 복귀."),
        ))
        db.add(Goal(
            user_id=USER_ID, race_type="풀마라톤", target_time="03:30:00",
            target_date=date.fromisoformat(v1.get("goal_date", "2026-11-01")),
            description="안정적인 호흡과 상태로 sub 3:30", is_active=True,
        ))
        db.add(AppSettings(
            user_id=USER_ID,
            weekly_goal_km=v1.get("weekly_goal_km", 45),
            pace_unit=v1.get("pace_unit", "분/km"),
            distance_unit=v1.get("distance_unit", "km"),
            notify_training=v1.get("notify_training", True),
            notify_after_workout=v1.get("notify_after_workout", True),
        ))
        await db.commit()

    # 정기 훈련 가능 시간 시드 (슬롯이 하나도 없을 때만 — 기존 DB에도 적용)
    has_slots = (await db.execute(select(AvailabilitySlot).where(
        AvailabilitySlot.user_id == USER_ID,
    ).limit(1))).scalar_one_or_none()
    if has_slots is None:
        db.add(AvailabilitySlot(
            user_id=USER_ID, days=[0, 1, 2, 3, 4], title="점심 헬스장", duration_min=45,
            place="실내 헬스장", note="러닝머신·무동력 트레드밀·로잉·근력 머신 사용 가능", sort=0,
        ))
        db.add(AvailabilitySlot(
            user_id=USER_ID, days=[1, 3], title="퇴근런 한강 코스", duration_min=60,
            place="야외", note="17시경 회사→집 2km+6km 총 8km 한강변", sort=1,
        ))
        db.add(AvailabilitySlot(
            user_id=USER_ID, days=[5, 6], title="주말 야외 러닝", duration_min=120,
            place="야외", note="오전 위주, 60~120분 가능", sort=2,
        ))
        await db.commit()

    # 이번 주 데모 계획 (없을 때만 · SEED_DEMO_WEEK=0 이면 생략 — E2E의 NO_PLAN 시나리오용)
    if os.environ.get("SEED_DEMO_WEEK") == "0":
        return
    today = date.today()
    y, w = iso_week_of(today)
    plan = (await db.execute(select(WeeklyPlan).where(
        WeeklyPlan.user_id == USER_ID, WeeklyPlan.iso_year == y, WeeklyPlan.iso_week == w,
    ))).scalar_one_or_none()
    if plan is None:
        ws = week_start_of(today)
        plan = WeeklyPlan(
            user_id=USER_ID, iso_year=y, iso_week=w, week_start=ws,
            direction="🟡 기초 복귀 단계 — 조깅 재개 + 하체 근력·폼 교정 병행",
            goal_km=18, intensity="낮음",
        )
        db.add(plan)
        await db.flush()
        # (요일, kind, title, km, 분, 페이스, focus=목적, note=수행 메모)
        demo = [
            (0, "easy", "트레드밀 복귀 조깅", 4, 35, "6:40~7:00 /km",
             "복귀 1주차 유산소 베이스 재가동", "심박 130~145 유지, 발목 감각 확인"),
            (1, "strength", "점심 헬스장 — 하체·코어 40분", 0, 40, None,
             "착지 안정성을 받칠 하체 근력 보강", "스쿼트·런지·코어, 가벼운 무게"),
            (2, "easy", "이지 런 5km", 5, 35, "6:30~7:00 /km",
             "Zone 2 지속주로 유산소 효율 회복", "대화 가능한 페이스"),
            (3, "rest", "휴식일", 0, 0, None,
             "초과회복 — 다음 세션 품질 확보", "수면 7시간+ · 가벼운 스트레칭"),
            (4, "drill", "폼 드릴 15분 + 빠른 걷기 15분", 0, 30, None,
             "신경근 활성화로 러닝 폼 효율 회복", "High Knees·Ankling·A-skip"),
            (5, "easy", "이지 런 5km", 5, 35, "6:30~6:50 /km",
             "케이던스 감각 회복", "케이던스 170+ 의식"),
            (6, "long", "주말 롱 조깅 6km", 6, 45, "6:50~7:10 /km",
             "시간 기반 지구력 — 부상 없이 볼륨 회복", "거리보다 시간 — 통증 시 즉시 중단"),
        ]
        # 첫 실행 UX: 설치 당일이 휴식일이면 빈 체험이 됨 → 오늘과 겹치면 다음 날과 교환
        tw = today.weekday()
        rest_idx = next(i for i, d in enumerate(demo) if d[1] == "rest")
        if rest_idx == tw and tw < 6:
            demo[tw], demo[tw + 1] = (
                (tw,) + demo[tw + 1][1:], (tw + 1,) + demo[tw][1:],
            )
        for wd, kind, title, dist, mins, pace, focus, note in demo:
            db.add(PlanSession(
                plan_id=plan.id, session_date=ws + timedelta(days=wd), weekday=wd,
                kind=kind, title=title, distance_km=dist or None,
                duration_min=mins or None, target_pace=pace, focus=focus, note=note,
                is_rest=(kind == "rest"),
            ))
        await db.commit()
