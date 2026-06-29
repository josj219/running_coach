"""테스트 픽스처 — 임시 sqlite DB + COACH_MOCK, 실 API 미호출."""

import os
import pathlib

_DB_PATH = pathlib.Path(__file__).parent / "_test_coach.db"
if _DB_PATH.exists():
    _DB_PATH.unlink()

# app 모듈 import 전에 환경 고정 (engine은 import 시 생성됨)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB_PATH}"
os.environ["COACH_MOCK"] = "1"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["STRAVA_CLIENT_ID"] = ""
os.environ["SEED_DEMO"] = "1"          # 로그인 가능한 데모 계정(고고조) 시드
os.environ["JWT_SECRET"] = "test-secret"

import httpx  # noqa: E402
import pytest  # noqa: E402

from app.db import SessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import DEMO_EMAIL, DEMO_PASSWORD, seed  # noqa: E402

_initialized = False
_token: str | None = None


@pytest.fixture
async def client():
    """데모 계정으로 로그인해 Authorization 헤더가 기본 적용된 인증 클라이언트."""
    global _initialized, _token
    transport = httpx.ASGITransport(app=app)
    if not _initialized:
        await init_db()
        async with SessionLocal() as db:
            await seed(db)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/api/auth/login",
                             json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
            _token = r.json()["token"]
        _initialized = True
    headers = {"Authorization": f"Bearer {_token}"}
    async with httpx.AsyncClient(transport=transport, base_url="http://test", headers=headers) as c:
        yield c


@pytest.fixture
async def db_session():
    """Async session fixture for database tests."""
    await init_db()
    async with SessionLocal() as s:
        yield s
