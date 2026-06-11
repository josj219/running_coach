"""정기 훈련 가능 시간(기본 시간표) — 조회 + 전체 교체.

설정 화면에서 리스트 단위로 저장하므로 PUT 전체 교체 방식(CRUD 불필요).
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import AvailabilitySlot, get_db
from ..services.context import USER_ID

router = APIRouter(prefix="/api/availability", tags=["availability"])

PLACES = ["실내 헬스장", "야외", "트레드밀", "기타"]


class SlotIn(BaseModel):
    days: list[int] = Field(min_length=1)
    title: str = Field(min_length=1, max_length=60)
    duration_min: int | None = Field(None, ge=5, le=600)
    place: str | None = None
    note: str | None = None

    @field_validator("days")
    @classmethod
    def days_valid(cls, v: list[int]) -> list[int]:
        if any(d < 0 or d > 6 for d in v):
            raise ValueError("days는 0(월)~6(일) 범위여야 합니다")
        return sorted(set(v))


class SlotsIn(BaseModel):
    slots: list[SlotIn]


def _slot_dict(s: AvailabilitySlot) -> dict:
    return {"id": s.id, "days": s.days, "title": s.title,
            "duration_min": s.duration_min, "place": s.place, "note": s.note}


@router.get("")
async def get_availability(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(AvailabilitySlot).where(
        AvailabilitySlot.user_id == USER_ID,
    ).order_by(AvailabilitySlot.sort, AvailabilitySlot.id))
    return {"slots": [_slot_dict(s) for s in res.scalars()]}


@router.put("")
async def put_availability(body: SlotsIn, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(AvailabilitySlot).where(AvailabilitySlot.user_id == USER_ID))
    for i, s in enumerate(body.slots):
        db.add(AvailabilitySlot(user_id=USER_ID, days=s.days, title=s.title,
                                duration_min=s.duration_min, place=s.place,
                                note=s.note, sort=i))
    await db.commit()
    return await get_availability(db)
