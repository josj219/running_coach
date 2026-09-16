"""운동 기록 저장/조회 + AI 리뷰(SSE).

불변식: 기록 저장은 AI 미호출 — 항상 즉시 커밋. 리뷰 실패해도 기록은 보존.
"""

import json
from datetime import date as date_t, datetime
from typing import Literal
from zoneinfo import ZoneInfo
from ..config import get_settings

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from ..auth import get_current_user
from ..db import ExternalActivity, JourneyEvent, PlanSession, User, WorkoutLog, WorkoutReview, get_db, utcnow
from ..services.records import quality, lock_user, link_session, update_fulfillment, resolve_activity, validate_running_activity
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
    sport: Literal["running", "cycling", "strength", "other", "unknown"] | None = None
    client_request_id: str | None = Field(None, max_length=100)
    started_at: datetime | None = None
    session_id: int | None = None
    fulfillment: Literal["missed", "partial", "done", "substituted"] | None = None
    comparison_tag: str | None = Field(None, max_length=160)
    change_reason: str = Field("기록 정정", max_length=1000)
    expected_revision: int | None = None


class ImageAnalyzeIn(BaseModel):
    # data: URL 접두사 없는 순수 base64. 클라이언트가 캔버스로 축소 후 전송.
    image_b64: str = Field(..., min_length=1)
    media_type: str = "image/jpeg"


def _review_dict(r: WorkoutReview | None) -> dict | None:
    if r is None:
        return None
    return {"recovery": r.recovery, "summary": r.summary, "strengths": r.strengths,
            "improvements": r.improvements, "coach_comment": r.coach_comment, "is_stale": r.is_stale}


def _log_dict(log: WorkoutLog) -> dict:
    return {
        "id": log.id, "log_date": log.log_date.isoformat(), "kind": log.kind,
        "distance_km": log.distance_km, "duration_sec": log.duration_sec,
        "avg_pace": log.avg_pace, "avg_hr": log.avg_hr, "max_hr": log.max_hr,
        "cadence": log.cadence, "feel": log.feel, "fatigue_num": log.fatigue_num,
        "pain_part": log.pain_part, "pain_level": log.pain_level,
        "user_comment": log.user_comment, "source": log.source,
        "session_id": log.session_id, "review": _review_dict(log.review),
        "sport": quality(log)["sport"], "quality": quality(log), "fulfillment": log.fulfillment,
        "external_id": log.external_id, "started_at": log.started_at.isoformat() if log.started_at else None,
        "comparison_tag": log.comparison_tag, "revision": log.revision, "updated_at": log.updated_at.isoformat() if log.updated_at else None,
    }


@router.get("")
async def list_logs(limit: int = Query(30, ge=1, le=1000), user: User = Depends(get_current_user),
                    db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(WorkoutLog).where(WorkoutLog.user_id == user.id)
        .options(selectinload(WorkoutLog.review))
        .order_by(WorkoutLog.log_date.desc(), WorkoutLog.id.desc()).limit(limit)
    )
    return {"items": [_log_dict(l) for l in res.scalars().unique()]}


@router.post("", status_code=201)
async def create_log(body: LogIn, user: User = Depends(get_current_user),
                     db: AsyncSession = Depends(get_db)):
    await lock_user(db, user.id)
    if body.client_request_id:
        existing = (await db.execute(select(WorkoutLog).where(
            WorkoutLog.user_id == user.id, WorkoutLog.client_request_id == body.client_request_id))).scalar_one_or_none()
        if existing:
            return {"id": existing.id, "created": False, "session_id": existing.session_id}
    activity = None
    if body.external_id:
        activity = (await db.execute(select(ExternalActivity).where(
            ExternalActivity.user_id == user.id, ExternalActivity.provider == body.source,
            ExternalActivity.external_id == body.external_id))).scalar_one_or_none()
        if not activity:
            raise HTTPException(422, "소유한 외부 활동을 선택하세요.")
        existing = await resolve_activity(db, user.id, activity)
        if existing:
            await db.commit()
            return {"id": existing.id, "created": False, "session_id": existing.session_id}
    values = body.model_dump(exclude={"session_id", "change_reason", "expected_revision"})
    if activity:
        validate_running_activity(activity)
        if not activity.start_date:
            raise HTTPException(422, "외부 활동의 시작 시각을 확인하세요.")
        from ..services.records import _utc
        values["log_date"] = _utc(activity.start_date).astimezone(ZoneInfo(get_settings().tz)).date()
        values["started_at"] = activity.start_date
        values["sport"] = "running"
    log = WorkoutLog(user_id=user.id, **values)
    db.add(log)
    await link_session(db, user.id, log, body.session_id if "session_id" in body.model_fields_set else "auto")
    await db.flush()
    if activity:
        activity.imported_log_id = log.id
    status = await update_fulfillment(db, log.session_id)
    db.add(JourneyEvent(user_id=user.id, event_type="record_added", entity_id=log.id,
                       reason="새 운동 기록", after={"date": str(log.log_date), "distance_km": log.distance_km}))
    await db.commit()
    return {"id": log.id, "session_id": log.session_id, "session_status": status, "created": True,
            "quality": quality(log)}


@router.patch("/{log_id}")
async def update_log(log_id: int, body: LogIn, user: User = Depends(get_current_user),
                     db: AsyncSession = Depends(get_db)):
    await lock_user(db, user.id)
    log = (await db.execute(select(WorkoutLog).where(WorkoutLog.id == log_id,
        WorkoutLog.user_id == user.id).options(selectinload(WorkoutLog.review)))).scalar_one_or_none()
    if not log:
        raise HTTPException(404, "기록이 없습니다.")
    if body.expected_revision is not None and body.expected_revision != log.revision:
        raise HTTPException(409, "기록이 변경됐습니다. 다시 열어 수정해 주세요.")
    from ..services.assessments import capture_assessment
    await capture_assessment(db, user.id, reason="기록 정정 전 당시 평가")
    before = _log_dict(log)
    old_session = log.session_id
    # External identity belongs to the workout and cannot be replaced by an edit.
    for key, value in body.model_dump(exclude_unset=True, exclude={"session_id", "source", "external_id", "client_request_id", "change_reason", "expected_revision"}).items():
        setattr(log, key, value)
    log.revision += 1
    log.updated_at = utcnow()
    if log.review:
        log.review.is_stale = True
    if "session_id" in body.model_fields_set or before["log_date"] != str(log.log_date):
        await link_session(db, user.id, log, body.session_id if "session_id" in body.model_fields_set else "auto")
    await db.flush()
    await update_fulfillment(db, old_session)
    status = await update_fulfillment(db, log.session_id)
    db.add(JourneyEvent(user_id=user.id, event_type="record_corrected", entity_id=log.id,
        reason=body.change_reason, before=before, after=_log_dict(log)))
    await db.flush()
    await capture_assessment(db, user.id, reason="기록 정정: " + body.change_reason)
    await db.commit()
    return {"id": log.id, "created": False, "session_id": log.session_id, "session_status": status,
            "quality": quality(log), "revision": log.revision, "review_stale": bool(log.review)}


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
    await lock_user(db, log.user_id)
    revision = (await db.execute(select(WorkoutLog.revision).where(WorkoutLog.id == log.id))).scalar_one()
    if revision != log.revision:
        raise HTTPException(409, "리뷰 생성 중 기록이 변경됐습니다. 수정한 기록으로 다시 요청해 주세요.")
    review = (await db.execute(select(WorkoutReview).where(
        WorkoutReview.log_id == log.id,
    ))).scalar_one_or_none() or WorkoutReview(log_id=log.id)
    review.coach_comment = data.get("coach_comment")
    review.summary = data.get("summary")
    review.strengths = data.get("strengths")
    review.improvements = data.get("improvements")
    review.recovery = data.get("recovery")
    review.raw_md = json.dumps(data, ensure_ascii=False)
    review.is_stale = False
    review.created_at = utcnow()
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
    # Release the read transaction while the model runs; save checks the input revision.
    await db.commit()
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
        except HTTPException as e:
            yield {"event": "error", "data": json.dumps({"code": "RECORD_CHANGED", "message": e.detail}, ensure_ascii=False)}

    return EventSourceResponse(event_gen())
