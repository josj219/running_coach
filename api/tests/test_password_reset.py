"""비밀번호 재설정 — 이메일 인증 코드 발송/검증/변경 + 보호 규칙(만료·재사용·시도 제한·쿨다운)."""

import re
from datetime import timedelta

import httpx
from sqlalchemy import select

from app import mailer
from app.db import PasswordReset, SessionLocal, User, utcnow
from app.main import app
from app.seed import DEMO_EMAIL, DEMO_PASSWORD


def _anon():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def _last_code() -> str:
    m = re.search(r"인증 코드: (\d{6})", mailer.outbox[-1]["body"])
    assert m, mailer.outbox[-1]
    return m.group(1)


async def _clear_resets(email: str):
    """테스트 간 쿨다운/이전 코드 영향 제거."""
    async with SessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one()
        for r in (await db.execute(select(PasswordReset).where(PasswordReset.user_id == user.id))).scalars():
            await db.delete(r)
        await db.commit()


async def _restore_demo_password(c):
    """데모 계정 비밀번호를 원복(다른 테스트가 DEMO_PASSWORD로 로그인함)."""
    await _clear_resets(DEMO_EMAIL)
    await c.post("/api/auth/forgot-password", json={"email": DEMO_EMAIL})
    r = await c.post("/api/auth/reset-password",
                     json={"email": DEMO_EMAIL, "code": _last_code(), "new_password": DEMO_PASSWORD})
    assert r.status_code == 200
    await _clear_resets(DEMO_EMAIL)


async def test_forgot_unknown_email_is_silent(client):
    mailer.outbox.clear()
    async with _anon() as c:
        r = await c.post("/api/auth/forgot-password", json={"email": "nobody@x.com"})
        assert r.status_code == 200 and r.json() == {"ok": True}
    assert mailer.outbox == []  # 계정 없음 → 메일도 없음, 응답도 동일


async def test_reset_happy_path_and_code_single_use(client):
    await _clear_resets(DEMO_EMAIL)
    mailer.outbox.clear()
    async with _anon() as c:
        r = await c.post("/api/auth/forgot-password", json={"email": DEMO_EMAIL.upper()})  # 대소문자 무시
        assert r.status_code == 200
        assert len(mailer.outbox) == 1 and mailer.outbox[0]["to"] == DEMO_EMAIL
        code = _last_code()

        # 틀린 코드 → 400
        r = await c.post("/api/auth/reset-password",
                         json={"email": DEMO_EMAIL, "code": "000000" if code != "000000" else "111111",
                               "new_password": "brand-new-pw-1"})
        assert r.status_code == 400 and r.json()["detail"]["code"] == "RESET_CODE_INVALID"

        # 맞는 코드 → 200 + 토큰(바로 로그인)
        r = await c.post("/api/auth/reset-password",
                         json={"email": DEMO_EMAIL, "code": code, "new_password": "brand-new-pw-1"})
        assert r.status_code == 200
        tok = r.json()["token"]
        assert (await c.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"})).status_code == 200

        # 새 비밀번호로 로그인 OK, 옛 비밀번호는 거절
        assert (await c.post("/api/auth/login", json={"email": DEMO_EMAIL, "password": "brand-new-pw-1"})).status_code == 200
        assert (await c.post("/api/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})).status_code == 401

        # 같은 코드 재사용 → 400
        r = await c.post("/api/auth/reset-password",
                         json={"email": DEMO_EMAIL, "code": code, "new_password": "another-pw-99"})
        assert r.status_code == 400

        await _restore_demo_password(c)


async def test_weak_password_rejected(client):
    async with _anon() as c:
        r = await c.post("/api/auth/reset-password",
                         json={"email": DEMO_EMAIL, "code": "123456", "new_password": "short"})
        assert r.status_code == 400 and r.json()["detail"]["code"] == "WEAK_PASSWORD"


async def test_resend_cooldown_then_new_code_invalidates_old(client):
    await _clear_resets(DEMO_EMAIL)
    mailer.outbox.clear()
    async with _anon() as c:
        await c.post("/api/auth/forgot-password", json={"email": DEMO_EMAIL})
        await c.post("/api/auth/forgot-password", json={"email": DEMO_EMAIL})
        assert len(mailer.outbox) == 1  # 60초 안 재요청은 무시(메일 폭주 방지)
        old_code = _last_code()

        # 쿨다운을 지난 것으로 만들고 재요청 → 새 코드 발송, 옛 코드는 무효
        async with SessionLocal() as db:
            reset = (await db.execute(select(PasswordReset))).scalars().first()
            reset.created_at = utcnow() - timedelta(seconds=120)
            db.add(reset)
            await db.commit()
        await c.post("/api/auth/forgot-password", json={"email": DEMO_EMAIL})
        assert len(mailer.outbox) == 2
        new_code = _last_code()
        if old_code != new_code:
            r = await c.post("/api/auth/reset-password",
                             json={"email": DEMO_EMAIL, "code": old_code, "new_password": "whatever-pw-1"})
            assert r.status_code == 400
        r = await c.post("/api/auth/reset-password",
                         json={"email": DEMO_EMAIL, "code": new_code, "new_password": DEMO_PASSWORD})
        assert r.status_code == 200
    await _clear_resets(DEMO_EMAIL)


async def test_expired_code_rejected(client):
    await _clear_resets(DEMO_EMAIL)
    mailer.outbox.clear()
    async with _anon() as c:
        await c.post("/api/auth/forgot-password", json={"email": DEMO_EMAIL})
        code = _last_code()
        async with SessionLocal() as db:
            reset = (await db.execute(select(PasswordReset))).scalars().first()
            reset.expires_at = utcnow() - timedelta(minutes=1)
            db.add(reset)
            await db.commit()
        r = await c.post("/api/auth/reset-password",
                         json={"email": DEMO_EMAIL, "code": code, "new_password": "whatever-pw-1"})
        assert r.status_code == 400 and r.json()["detail"]["code"] == "RESET_CODE_INVALID"
        # 비밀번호는 그대로
        assert (await c.post("/api/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})).status_code == 200
    await _clear_resets(DEMO_EMAIL)


async def test_too_many_wrong_attempts_burns_code(client):
    await _clear_resets(DEMO_EMAIL)
    mailer.outbox.clear()
    async with _anon() as c:
        await c.post("/api/auth/forgot-password", json={"email": DEMO_EMAIL})
        code = _last_code()
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(5):
            r = await c.post("/api/auth/reset-password",
                             json={"email": DEMO_EMAIL, "code": wrong, "new_password": "whatever-pw-1"})
            assert r.status_code == 400
        # 5회 실패 후엔 맞는 코드도 거절 — 무차별 대입 차단
        r = await c.post("/api/auth/reset-password",
                         json={"email": DEMO_EMAIL, "code": code, "new_password": "whatever-pw-1"})
        assert r.status_code == 400
        assert (await c.post("/api/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})).status_code == 200
    await _clear_resets(DEMO_EMAIL)


async def test_mail_failure_returns_503_and_allows_retry(client, monkeypatch):
    await _clear_resets(DEMO_EMAIL)
    mailer.outbox.clear()
    from app.routers import auth as auth_router

    async def boom(*a, **k):
        raise RuntimeError("smtp down")
    monkeypatch.setattr(auth_router, "send_mail", boom)
    async with _anon() as c:
        r = await c.post("/api/auth/forgot-password", json={"email": DEMO_EMAIL})
        assert r.status_code == 503 and r.json()["detail"]["code"] == "MAIL_FAILED"
    monkeypatch.undo()
    async with _anon() as c:
        r = await c.post("/api/auth/forgot-password", json={"email": DEMO_EMAIL})  # 쿨다운에 안 걸려야 한다
        assert r.status_code == 200 and len(mailer.outbox) == 1
    await _clear_resets(DEMO_EMAIL)
