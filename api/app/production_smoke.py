"""Exercise the running API through nginx using an isolated temporary account.

No AI/external service calls. All created rows are removed in finally. Tokens/passwords
remain in memory and are never printed. Existing accounts and records are untouched.
"""
import asyncio
import json
import os
import secrets
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4
import httpx
from sqlalchemy import delete, select
from .auth import hash_password
from .db import (Assessment, Base, ExternalActivity, Goal, PlanSession, SessionLocal,
                 User, UserProfile, WeeklyPlan, WorkoutLog, WorkoutReview, engine)


async def smoke():
    uid = None
    email = f"deployment-smoke-{uuid4()}@test.invalid"
    password = secrets.token_urlsafe(24)
    try:
        async with SessionLocal() as db:
            user = User(email=email, nickname="Deployment verification", password_hash=hash_password(password), onboarded=True)
            db.add(user); await db.flush(); uid = user.id
            db.add(UserProfile(user_id=uid, pb_10k="42:13"))
            ws = date.today() - timedelta(days=date.today().weekday())
            y, w, _ = ws.isocalendar()
            plan = WeeklyPlan(user_id=uid, iso_year=y, iso_week=w, week_start=ws, goal_km=6)
            db.add(plan); await db.flush()
            db.add(PlanSession(plan_id=plan.id, session_date=date.today(), weekday=date.today().weekday(), kind="easy", distance_km=6, status="planned", is_rest=False))
            await db.commit()
        async with httpx.AsyncClient(base_url=os.environ.get("SMOKE_BASE_URL", "http://web"), timeout=30) as c:
            async def request(method, path, **kw):
                r = await c.request(method, path, **kw)
                r.raise_for_status()
                return r.json()
            login = await request("POST", "/api/auth/login", json={"email": email, "password": password})
            c.headers["Authorization"] = "Bearer " + login["token"]
            g = await request("PUT", "/api/goal", json={"race_type": "풀마라톤", "target_time": "03:30:00", "target_date": str(date.today() + timedelta(days=60))})
            d = await request("GET", "/api/dashboard")
            assert d["current"]["data_status"]["state"] == "pb_reference"
            assert all(p["predicted_sec"] is None for p in d["series"])
            first = await request("POST", "/api/workout-logs", json={"log_date": str(date.today()), "distance_km": 1, "duration_sec": 360, "client_request_id": "smoke-first"})
            assert first["session_status"] == "partial"
            second = await request("POST", "/api/workout-logs", json={"log_date": str(date.today()), "distance_km": 8, "duration_sec": 2880})
            assert first["id"] != second["id"]
            today = await request("GET", "/api/today")
            assert len(today["logs"]) == 2 and today["day_km"] == 9
            await request("PATCH", f"/api/workout-logs/{first['id']}", json={"log_date": str(date.today()), "distance_km": 2, "duration_sec": 720, "change_reason": "배포 검증용 정정"})
            await request("PATCH", "/api/profile", json={"pb_10k": "40:00"})
            await request("PUT", "/api/goal", json={"race_type": "하프", "target_time": "01:40:00"})
            goals = await request("GET", "/api/goals")
            assert len(goals["items"]) == 2
            async with SessionLocal() as db:
                start = datetime.combine(date.today(), datetime.min.time(), timezone.utc)
                activities = [ExternalActivity(user_id=uid, provider=p, external_id="smoke", sport_type="Run", start_date=start, distance_km=12, duration_sec=4320) for p in ("garmin", "strava")]
                db.add_all(activities); await db.commit(); ids = [a.id for a in activities]
            imported = await request("POST", "/api/integrations/activities/import", json={"activity_ids": ids})
            assert imported["created_count"] == 1
            assert (await request("POST", "/api/integrations/activities/import", json={"activity_ids": ids}))["created_count"] == 0
            growth = await request("GET", f"/api/growth?start={date.today()}&end={date.today()}")
            assert growth["current"]["distance_km"] == 22
            assert not growth["comparable"]
            health = await request("GET", "/api/health")
            assert health["status"] == "ok"
            if os.environ.get("APP_REVISION"):
                assert health["revision"] == os.environ["APP_REVISION"]
            print(json.dumps({"production_smoke": "passed", "revision": health.get("revision"),
                "checks": ["nginx-to-api", "login", "PB-only", "same-day-add", "edit", "partial", "goal-history", "cross-provider-import", "import-idempotency", "growth"]}))
    finally:
        if uid is not None:
            async with SessionLocal() as db:
                # This probe creates no reviews/evaluations, but delete linked rows defensively.
                await db.execute(delete(WorkoutReview).where(WorkoutReview.log_id.in_(select(WorkoutLog.id).where(WorkoutLog.user_id == uid))))
                for table in reversed(Base.metadata.sorted_tables):
                    if "user_id" in table.c:
                        await db.execute(delete(table).where(table.c.user_id == uid))
                    elif "plan_id" in table.c:
                        await db.execute(delete(table).where(table.c.plan_id.in_(select(WeeklyPlan.id).where(WeeklyPlan.user_id == uid))))
                await db.execute(delete(User).where(User.id == uid, User.email == email))
                await db.commit()
                assert await db.get(User, uid) is None
            print("Temporary verification account and records removed")
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(smoke())
