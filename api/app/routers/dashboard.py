"""GET /api/dashboard — 홈 대시보드: 희망 목표 vs 현재 추세 예상 기록 + 주별 궤적.

숫자는 전부 services/fitness 가 결정적으로 계산한다(AI 미개입). 조립은 services/progress.
"""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..db import User, get_db
from ..services.assessments import dashboard

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
async def get_dashboard(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await dashboard(db, user.id)
