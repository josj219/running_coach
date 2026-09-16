from collections import defaultdict
from datetime import date, timedelta
from statistics import mean
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from ..auth import get_current_user
from ..db import Assessment, CoachingTask, Goal, GoalCheckpoint, User, WeeklyEvaluation, WeeklyPlan, WorkoutLog, get_db
from ..services.assessments import assessment_dict, serial
from ..services.coaching import task_dict, tasks_for
from ..services.records import as_run, quality
from .workout_logs import _log_dict

router = APIRouter(prefix="/api", tags=["journey"])


@router.get("/coaching-tasks")
async def list_tasks(user: User = Depends(get_current_user), db=Depends(get_db)):
    return {"items": [task_dict(t) for t in await tasks_for(db, user.id)]}


class TaskIn(BaseModel):
    source_log_id: int | None = None
    source_plan_id: int | None = None
    proposal: str = Field(..., min_length=1, max_length=2000)


@router.post("/coaching-tasks", status_code=201)
async def add_task(body: TaskIn, user: User = Depends(get_current_user), db=Depends(get_db)):
    if bool(body.source_log_id) == bool(body.source_plan_id):
        raise HTTPException(422, "운동 리뷰 또는 주간 평가 중 하나를 선택하세요.")
    if body.source_log_id:
        source = (await db.execute(select(WorkoutLog).where(WorkoutLog.user_id == user.id,
            WorkoutLog.id == body.source_log_id).options(selectinload(WorkoutLog.review)))).scalar_one_or_none()
        if not source or not source.review or source.review.is_stale:
            raise HTTPException(422, "최신 리뷰가 있는 본인 기록을 선택하세요.")
        evidence = {"log": _log_dict(source), "interpretation": "AI 제안 — 원시 기록으로 재검토"}
    else:
        source = (await db.execute(select(WeeklyEvaluation).join(WeeklyPlan).where(
            WeeklyPlan.user_id == user.id, WeeklyPlan.id == body.source_plan_id))).scalar_one_or_none()
        if not source:
            raise HTTPException(422, "본인의 주간 평가를 선택하세요.")
        evidence = {"plan_id": body.source_plan_id, "message": source.coach_message, "evaluated_at": str(source.created_at)}
    task = CoachingTask(user_id=user.id, **body.model_dump(), evidence=evidence)
    db.add(task)
    await db.commit()
    return task_dict(task)


class TaskPatch(BaseModel):
    status: Literal["open", "resolved"]


@router.patch("/coaching-tasks/{task_id}")
async def patch_task(task_id: int, body: TaskPatch, user: User = Depends(get_current_user), db=Depends(get_db)):
    t = (await db.execute(select(CoachingTask).where(CoachingTask.user_id == user.id, CoachingTask.id == task_id))).scalar_one_or_none()
    if not t:
        raise HTTPException(404, "과제가 없습니다.")
    t.status = body.status
    await db.commit()
    return task_dict(t)


class CheckpointIn(BaseModel):
    goal_id: int
    review_date: date
    evidence_needed: str = Field(..., min_length=1, max_length=1000)


@router.post("/checkpoints", status_code=201)
async def checkpoint(body: CheckpointIn, user: User = Depends(get_current_user), db=Depends(get_db)):
    goal = await db.get(Goal, body.goal_id)
    if not goal or goal.user_id != user.id:
        raise HTTPException(404, "목표가 없습니다.")
    cp = GoalCheckpoint(user_id=user.id, **body.model_dump())
    db.add(cp)
    await db.commit()
    return {"id": cp.id}


class DecisionIn(BaseModel):
    decision: str = Field(..., min_length=1, max_length=1000)


@router.patch("/checkpoints/{checkpoint_id}")
async def decide_checkpoint(checkpoint_id: int, body: DecisionIn, user: User = Depends(get_current_user), db=Depends(get_db)):
    cp = await db.get(GoalCheckpoint, checkpoint_id)
    if not cp or cp.user_id != user.id:
        raise HTTPException(404, "체크포인트가 없습니다.")
    cp.decision = body.decision
    await db.commit()
    return {"id": cp.id, "decision": cp.decision}


@router.get("/growth")
async def growth(start: date, end: date, goal_id: int | None = None,
                 user: User = Depends(get_current_user), db=Depends(get_db)):
    if end < start or (end - start).days > 730 or end > date.today():
        raise HTTPException(422, "오늘까지 최대 2년의 기간을 선택하세요.")
    span = end - start + timedelta(days=1)
    previous_start, previous_end = start - span, start - timedelta(days=1)
    all_logs = list((await db.execute(select(WorkoutLog).where(WorkoutLog.user_id == user.id,
        WorkoutLog.log_date >= previous_start, WorkoutLog.log_date <= end)
        .options(selectinload(WorkoutLog.review)).order_by(WorkoutLog.log_date.desc(), WorkoutLog.id.desc()))).scalars())
    now = [l for l in all_logs if start <= l.log_date <= end]
    previous = [l for l in all_logs if previous_start <= l.log_date <= previous_end]
    def observed(logs):
        runs = [l for l in logs if quality(l)["sport"] == "running"]
        return {"records": len(logs), "running_records": len(runs), "distance_km": round(sum(l.distance_km or 0 for l in runs), 2),
                "duration_sec": sum(l.duration_sec or 0 for l in runs), "timed_records": sum(bool(l.duration_sec) for l in runs),
                "eligible_records": sum(quality(l)["eligible"] for l in runs)}
    groups = defaultdict(lambda: [[], []])
    for i, logs in enumerate([previous, now]):
        for l in logs:
            if l.comparison_tag and quality(l)["eligible"]:
                groups[(l.comparison_tag, l.kind, round(l.distance_km, 1))][i].append(l)
    comparable = []
    for (tag, kind, distance), (old, new) in groups.items():
        if len(old) < 2 or len(new) < 2:
            continue
        hr_ok = all(l.avg_hr and l.feel is not None for l in old + new) and len({l.feel for l in old + new}) == 1
        comparable.append({"condition": tag, "kind": kind, "distance_km": distance,
            "before_count": len(old), "after_count": len(new), "log_ids": [l.id for l in old + new],
            "before_pace_sec": round(mean(as_run(l).effective_duration() / l.distance_km for l in old)),
            "after_pace_sec": round(mean(as_run(l).effective_duration() / l.distance_km for l in new)),
            "heart_rate": {"before": round(mean(l.avg_hr for l in old)), "after": round(mean(l.avg_hr for l in new))} if hr_ok else None})
    query = select(Assessment).where(Assessment.user_id == user.id, Assessment.as_of >= previous_start, Assessment.as_of <= end)
    if goal_id:
        goal = await db.get(Goal, goal_id)
        if not goal or goal.user_id != user.id:
            raise HTTPException(404, "목표가 없습니다.")
        query = query.where(Assessment.goal_id == goal_id)
    assessments = list((await db.execute(query.order_by(Assessment.id))).scalars())
    plans = list((await db.execute(select(WeeklyPlan).where(WeeklyPlan.user_id == user.id,
        WeeklyPlan.week_start >= previous_start - timedelta(days=6), WeeklyPlan.week_start <= end)
        .order_by(WeeklyPlan.week_start.desc()))).scalars())
    return {"start": str(start), "end": str(end), "previous_start": str(previous_start), "previous_end": str(previous_end),
        "current": observed(now), "previous": observed(previous), "comparable": comparable,
        "comparison_rule": "사용자가 같은 경로·환경으로 표시한 비교 조건, 같은 훈련 종류·거리(0.1km 단위), 양쪽 기간 각 2건 이상. 심박은 체감도 같은 경우만 보조 표시.",
        "comparison_message": "비교 조건은 사용자 입력이며 환경 차이의 영향은 남습니다." if comparable else "비교 불가 — 같은 조건의 러닝 표본이 양쪽 기간에 2건 이상 필요합니다.",
        "assessments": [assessment_dict(a) for a in assessments], "logs": [_log_dict(l) for l in now],
        "reports": [{"plan_id": p.id, "iso_week": f"{p.iso_year}-W{p.iso_week:02d}"} for p in plans],
        "next_action": "미반영 기록을 확인하고 같은 경로·종류·체감의 훈련에 비교 조건을 남기세요. 현재 컨디션과 계획을 먼저 확인하세요."}
