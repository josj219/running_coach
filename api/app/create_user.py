"""계정 생성 CLI — 서버에서 직접 실행한다(셀프 회원가입 없음).

사용:
    python -m app.create_user <email> <password> [nickname]

이미 있는 이메일이면 비밀번호(및 닉네임)를 갱신한다. 첫 로그인 시 프로필이 비어 있으면
앱이 온보딩으로 입력을 받는다(onboarded=False 로 시작).
"""

import asyncio
import sys

from sqlalchemy import select

from .auth import hash_password
from .db import SessionLocal, User, init_db


async def create_user(email: str, password: str, nickname: str = "러너") -> tuple[int, bool]:
    email = email.strip().lower()
    async with SessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        created = user is None
        if user is None:
            user = User(email=email, nickname=nickname or "러너", onboarded=False)
            db.add(user)
        user.password_hash = hash_password(password)
        if nickname:
            user.nickname = nickname
        await db.commit()
        await db.refresh(user)
        return user.id, created


async def _main() -> None:
    if len(sys.argv) < 3:
        print("usage: python -m app.create_user <email> <password> [nickname]")
        raise SystemExit(1)
    email, password = sys.argv[1], sys.argv[2]
    nickname = sys.argv[3] if len(sys.argv) > 3 else "러너"
    await init_db()
    uid, created = await create_user(email, password, nickname)
    print(f"{'created' if created else 'updated'} user id={uid} email={email.strip().lower()}")


if __name__ == "__main__":
    asyncio.run(_main())
