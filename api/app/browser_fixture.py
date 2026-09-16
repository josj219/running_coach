"""Create an isolated synthetic browser user only in an explicitly temporary mock DB."""
import asyncio
import json
import os
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy.engine import make_url

url = make_url(os.environ.get("DATABASE_URL", ""))
if os.environ.get("COACH_MOCK") != "1" or url.get_backend_name() != "sqlite" or not (url.database or "").startswith(("/tmp/coach-journey", "/private/tmp/coach-journey")):
    raise RuntimeError("Browser fixtures require a temporary coach-journey SQLite DB and COACH_MOCK=1")

from .auth import hash_password
from .db import ExternalActivity, Goal, PlanSession, SessionLocal, User, UserProfile, WeeklyPlan, engine, init_db


async def create():
    await init_db()
    email = f"browser-{uuid4()}@coach.local"
    password = "browser-test-only-1234"
    async with SessionLocal() as db:
        u = User(email=email, nickname="여정 검증", password_hash=hash_password(password), onboarded=True)
        db.add(u); await db.flush()
        db.add(UserProfile(user_id=u.id, pb_10k="42:13"))
        db.add(Goal(user_id=u.id, race_type="풀마라톤", target_time="03:30:00", target_date=date.today() + timedelta(days=49)))
        ws = date.today() - timedelta(days=date.today().weekday()); y, w, _ = ws.isocalendar()
        p = WeeklyPlan(user_id=u.id, iso_year=y, iso_week=w, week_start=ws, goal_km=6, direction="가용 시간과 실제 기록 확인")
        db.add(p); await db.flush()
        for i in range(7):
            d = ws + timedelta(days=i); today = d == date.today()
            db.add(PlanSession(plan_id=p.id, session_date=d, weekday=i, kind="easy" if today else "rest", title="이지 런 6km" if today else "회복", distance_km=6 if today else 0, duration_min=36 if today else 0, status="planned", is_rest=not today))
        start = datetime.combine(date.today() - timedelta(days=1), datetime.min.time(), timezone.utc)
        for i, (provider, offset) in enumerate([("garmin", 0), ("strava", 0), ("garmin", 8)]):
            db.add(ExternalActivity(user_id=u.id, provider=provider, external_id=f"{u.id}-{i}", name="검증용 러닝", sport_type="Run", start_date=start + timedelta(hours=offset), distance_km=12, duration_sec=4320))
        await db.commit()
    print(json.dumps({"email": email, "password": password}))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create())
