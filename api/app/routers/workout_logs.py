"""운동 기록 저장/조회 + AI 리뷰(SSE).

불변식: 기록 저장은 AI 미호출 — 항상 즉시 커밋. 리뷰 실패해도 기록은 보존.
"""

import json
from datetime import date as date_t

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from ..auth import get_current_user
from ..db import PlanSession, User, WorkoutLog, WorkoutReview, get_db
from ..prompts import WORKOUT_REVIEW_PROMPT
from ..services import coach
from ..services.context import (
    KIND_LABELS, get_current_plan, render_profile_context,
    render_recent_history, render_session_line,
)

router = APIRouter(prefix="/api/workout-logs", tags=["workout-logs"])


class LogIn(BaseModel):
    log_date: date_t
    kind: str = "easy"
    distance_km: float = Field(0, ge=0, le=200)
    duration_sec: int | None = Field(None, ge=0)
    avg_pace: str | None = None
    avg_hr: int | None = Field(None, ge=30, le=250)
    max_hr: int | None = Field(None, ge=30, le=250)
    cadence: int | None = Field(None, ge=0, le=300)
    elevation_m: int | None = None
    feel: int | None = Field(None, ge=1, le=4)
    fatigue_num: int | None = Field(None, ge=0, le=10)
    pain_part: str | None = None
    pain_level: int = Field(0, ge=0, le=10)
    user_comment: str | None = None
    image_url: str | None = None
    source: str = "manual"
    external_id: str | None = None


class ImageAnalyzeIn(BaseModel):
    # data: URL 접두사 없는 순수 base64. 클라이언트가 캔버스로 축소 후 전송.
    image_b64: str = Field(..., min_length=1)
    media_type: str = "image/jpeg"


def _review_dict(r: WorkoutReview | None) -> dict | None:
    if r is None:
        return None
    return {"recovery": r.recovery, "summary": r.summary, "strengths": r.strengths,
            "improvements": r.improvements, "coach_comment": r.coach_comment}


def _log_dict(log: WorkoutLog) -> dict:
    return {
        "id": log.id, "log_date": log.log_date.isoformat(), "kind": log.kind,
        "distance_km": log.distance_km, "duration_sec": log.duration_sec,
        "avg_pace": log.avg_pace, "avg_hr": log.avg_hr, "max_hr": log.max_hr,
        "cadence": log.cadence, "feel": log.feel, "fatigue_num": log.fatigue_num,
        "pain_part": log.pain_part, "pain_level": log.pain_level,
        "user_comment": log.user_comment, "source": log.source,
        "session_id": log.session_id, "review": _review_dict(log.review),
    }


@router.get("")
async def list_logs(limit: int = 30, user: User = Depends(get_current_user),
                    db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(WorkoutLog).where(WorkoutLog.user_id == user.id)
        .options(selectinload(WorkoutLog.review))
        .order_by(WorkoutLog.log_date.desc()).limit(limit)
    )
    return {"items": [_log_dict(l) for l in res.scalars().unique()]}


@router.post("", status_code=201)
async def create_log(body: LogIn, user: User = Depends(get_current_user),
                     db: AsyncSession = Depends(get_db)):
    # 자연키(user_id, log_date) upsert — 같은 날 재저장은 덮어쓰기
    existing = (await db.execute(select(WorkoutLog).where(
        WorkoutLog.user_id == user.id, WorkoutLog.log_date == body.log_date,
    ))).scalar_one_or_none()
    log = existing or WorkoutLog(user_id=user.id, log_date=body.log_date, kind=body.kind)
    for k, v in body.model_dump().items():
        setattr(log, k, v)
    if existing is None:
        db.add(log)

    # 같은 날짜의 계획 세션과 매칭 → 상태 갱신 (통증 4+ → partial)
    plan = await get_current_plan(db, body.log_date, user.id)
    session_status = None
    if plan:
        sess = (await db.execute(select(PlanSession).where(
            PlanSession.plan_id == plan.id, PlanSession.session_date == body.log_date,
        ))).scalar_one_or_none()
        if sess:
            sess.status = "partial" if body.pain_level >= 4 else "done"
            log.session_id = sess.id
            session_status = sess.status
    await db.commit()
    await db.refresh(log)
    return {"id": log.id, "session_id": log.session_id, "session_status": session_status,
            "created": existing is None}


@router.post("/analyze-image")
async def analyze_image(body: ImageAnalyzeIn, user: User = Depends(get_current_user)):
    """운동 기록 스크린샷을 Claude 비전으로 분석해 거리·시간·페이스·심박 등 수치를 추출.

    DB에 저장하지 않는다 — 추출 결과만 돌려주고, 사용자가 폼에서 확인 후 저장한다.
    """
    # base64 길이(문자) ≈ 원본 바이트 × 4/3. ~8MB 원본 상한.
    if len(body.image_b64) > 11_000_000:
        raise HTTPException(413, {"code": "IMAGE_TOO_LARGE", "message": "이미지가 너무 큽니다. 더 작게 캡처해 주세요."})
    try:
        data = await coach.extract_workout_image(body.image_b64, body.media_type)
    except coach.CoachError as e:
        raise HTTPException(503, {"code": "AI_UNAVAILABLE", "message": str(e)})
    return data


async def _build_review_message(db: AsyncSession, log: WorkoutLog, user_id: int) -> str:
    plan = await get_current_plan(db, log.log_date, user_id)
    planned = "계획 없음 (즉흥 훈련)"
    if plan:
        sess = (await db.execute(select(PlanSession).where(
            PlanSession.plan_id == plan.id, PlanSession.session_date == log.log_date,
        ))).scalar_one_or_none()
        if sess:
            planned = render_session_line(sess) + (f"\n메모: {sess.note}" if sess.note else "")
    profile = await render_profile_context(db, user_id)
    history = await render_recent_history(db, user_id)
    actual = json.dumps(_log_dict(log), ensure_ascii=False)
    return (f"{profile}\n\n{history}\n\n## 오늘 계획\n{planned}\n\n"
            f"## 실제 수행 ({log.log_date}, {KIND_LABELS.get(log.kind, log.kind)})\n{actual}\n\n"
            "위 훈련을 리뷰해 주세요.")


async def _save_review(db: AsyncSession, log: WorkoutLog, data: dict) -> WorkoutReview:
    review = (await db.execute(select(WorkoutReview).where(
        WorkoutReview.log_id == log.id,
    ))).scalar_one_or_none() or WorkoutReview(log_id=log.id)
    review.coach_comment = data.get("coach_comment")
    review.summary = data.get("summary")
    review.strengths = data.get("strengths")
    review.improvements = data.get("improvements")
    review.recovery = data.get("recovery")
    review.raw_md = json.dumps(data, ensure_ascii=False)
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review


@router.post("/{log_id}/review")
async def create_review(log_id: int, request: Request, user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    log = (await db.execute(select(WorkoutLog).where(
        WorkoutLog.id == log_id, WorkoutLog.user_id == user.id,
    ).options(selectinload(WorkoutLog.review)))).scalar_one_or_none()
    if log is None:
        raise HTTPException(404, {"code": "NOT_FOUND", "message": "기록이 없습니다."})

    message = await _build_review_message(db, log, user.id)
    accept = request.headers.get("accept", "")

    if "text/event-stream" not in accept:
        # 비스트리밍: 완성 JSON 한 번에
        try:
            data = await coach.generate("review", WORKOUT_REVIEW_PROMPT, message)
        except coach.CoachError as e:
            raise HTTPException(503, {"code": "AI_UNAVAILABLE", "message": str(e)})
        review = await _save_review(db, log, data)
        return {"review_id": review.id, **data}

    async def event_gen():
        chunks: list[str] = []
        try:
            async for token in coach.stream_text(WORKOUT_REVIEW_PROMPT, message):
                chunks.append(token)
                yield {"event": "token", "data": token}
            data = (coach.MOCK_RESPONSES["review"] if coach.get_settings().coach_mock
                    else coach.parse_json_block("".join(chunks)))
            review = await _save_review(db, log, data)
            yield {"event": "done", "data": json.dumps({"review_id": review.id, **data}, ensure_ascii=False)}
        except coach.CoachError as e:
            yield {"event": "error", "data": json.dumps({"code": "AI_UNAVAILABLE", "message": str(e)}, ensure_ascii=False)}

    return EventSourceResponse(event_gen())
