"""인증 — bcrypt 비밀번호 해시 + JWT 발급/검증 + 현재 사용자 의존성.

회원가입(셀프)은 없다. 계정은 서버에서 create_user로 생성한다(app/create_user.py).
로그인 시 JWT(Bearer)를 발급하고, 보호된 엔드포인트는 get_current_user로 사용자를 식별한다.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .db import User, get_db

_ALGO = "HS256"


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_token(user_id: int) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(days=s.jwt_expire_days),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=_ALGO)


def _decode_user_id(token: str) -> int:
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=[_ALGO])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as e:
        raise HTTPException(401, {"code": "UNAUTHORIZED", "message": "로그인이 필요합니다."}) from e


async def get_current_user(
    authorization: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
) -> User:
    """`Authorization: Bearer <jwt>` 헤더에서 사용자를 식별한다. 실패 시 401."""
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(401, {"code": "UNAUTHORIZED", "message": "로그인이 필요합니다."})
    user_id = _decode_user_id(authorization.split(" ", 1)[1].strip())
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(401, {"code": "UNAUTHORIZED", "message": "계정을 찾을 수 없습니다."})
    return user
