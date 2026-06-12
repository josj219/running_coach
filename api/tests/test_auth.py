"""인증 — 로그인/토큰/온보딩 + 보호된 엔드포인트 401."""

import httpx
import pytest

from app.main import app
from app.seed import DEMO_EMAIL, DEMO_PASSWORD


def _anon():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_protected_requires_token(client):
    # client 픽스처가 init/seed를 보장하므로 호출만 해 둔다
    async with _anon() as c:
        for path in ("/api/profile", "/api/today", "/api/weeks/current"):
            r = await c.get(path)
            assert r.status_code == 401, path


async def test_login_bad_password(client):
    async with _anon() as c:
        r = await c.post("/api/auth/login", json={"email": DEMO_EMAIL, "password": "wrong"})
        assert r.status_code == 401
        assert r.json()["detail"]["code"] == "BAD_CREDENTIALS"


async def test_login_unknown_email(client):
    async with _anon() as c:
        r = await c.post("/api/auth/login", json={"email": "nobody@x.com", "password": "x"})
        assert r.status_code == 401


async def test_login_success_and_me(client):
    async with _anon() as c:
        r = await c.post("/api/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
        assert r.status_code == 200
        token = r.json()["token"]
        assert r.json()["user"]["email"] == DEMO_EMAIL
        me = await c.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["onboarded"] is True  # 데모는 온보딩 완료 상태


async def test_bad_token_rejected(client):
    async with _anon() as c:
        r = await c.get("/api/profile", headers={"Authorization": "Bearer not-a-jwt"})
        assert r.status_code == 401


async def test_onboard_flow():
    """create_user → 로그인 → onboarded False → onboard 후 True + 프로필 반영."""
    from app.create_user import create_user

    await create_user("newrunner@coach.local", "pw-123456", "새러너")
    async with _anon() as c:
        tok = (await c.post("/api/auth/login",
                            json={"email": "newrunner@coach.local", "password": "pw-123456"})).json()["token"]
        h = {"Authorization": f"Bearer {tok}"}
        assert (await c.get("/api/auth/me", headers=h)).json()["onboarded"] is False
        body = {"nickname": "새러너", "height_cm": 175, "age": 30, "career_years": 1.5,
                "race_type": "10K", "weekly_goal_km": 20,
                "slots": [{"days": [0, 2, 4], "title": "아침 러닝", "duration_min": 40, "place": "야외"}]}
        r = await c.post("/api/auth/onboard", json=body, headers=h)
        assert r.status_code == 200 and r.json()["onboarded"] is True
        prof = (await c.get("/api/profile", headers=h)).json()
        assert prof["height_cm"] == 175 and prof["career_years"] == 1.5
        avail = (await c.get("/api/availability", headers=h)).json()["slots"]
        assert len(avail) == 1 and avail[0]["title"] == "아침 러닝"
