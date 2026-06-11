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

import httpx  # noqa: E402
import pytest  # noqa: E402

from app.db import SessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402

_initialized = False


@pytest.fixture
async def client():
    global _initialized
    if not _initialized:
        await init_db()
        async with SessionLocal() as db:
            await seed(db)
        _initialized = True
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
