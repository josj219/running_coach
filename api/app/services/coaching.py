"""Selected coaching tasks carry evidence, never unquestioned AI conclusions."""
import json
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from ..db import CoachingTask, PlanSession, WeeklyEvaluation, WeeklyPlan, WorkoutLog


def task_dict(t):
    return {"id": t.id, "proposal": t.proposal, "status": t.status, "source_log_id": t.source_log_id,
        "source_plan_id": t.source_plan_id, "evidence": t.evidence,
        "assignments": t.assignments, "evaluations": t.evaluations}


async def tasks_for(db, user_id):
    return list((await db.execute(select(CoachingTask).where(CoachingTask.user_id == user_id)
        .order_by(CoachingTask.id.desc()))).scalars())


async def render_coaching_context(db, user_id):
    tasks = [task_dict(t) for t in await tasks_for(db, user_id) if t.status != "resolved"][:12]
    for task in tasks:
        if task["source_log_id"]:
            source = await db.get(WorkoutLog, task["source_log_id"])
            original_revision = task["evidence"].get("log", {}).get("revision")
            task["source_changed"] = not source or source.revision != original_revision
            if task["source_changed"]:
                task["source_warning"] = "선택 당시 기록이 정정되었습니다. 과거 AI 해석을 승계하지 말고 재검토하세요."
    logs = list((await db.execute(select(WorkoutLog).where(WorkoutLog.user_id == user_id)
        .options(selectinload(WorkoutLog.review)).order_by(WorkoutLog.log_date.desc(), WorkoutLog.id.desc()).limit(8))).scalars())
    reviews = [{"log_id": l.id, "revision": l.revision, "distance_km": l.distance_km,
                "improvements": l.review.improvements, "recovery": l.review.recovery}
               for l in logs if l.review and not l.review.is_stale][:5]
    evaluations = list((await db.execute(select(WeeklyEvaluation).join(WeeklyPlan).where(WeeklyPlan.user_id == user_id)
        .order_by(WeeklyEvaluation.created_at.desc()).limit(2))).scalars())
    return "## 선택한 코칭 과제와 최근 평가 (AI 해석은 제안이며 원시 기록으로 재검토)\n" + json.dumps({
        "tasks": tasks, "recent_reviews": reviews,
        "weekly_conclusions": [{"plan_id": e.plan_id, "message": e.coach_message} for e in evaluations]}, ensure_ascii=False)


async def assign_tasks(db, user_id, plan, data):
    sessions = list((await db.execute(select(PlanSession).where(PlanSession.plan_id == plan.id))).scalars())
    dates = {str(s.session_date): s for s in sessions}
    supplied = {str(x.get("task_id")): x for x in data.get("coaching_actions", []) if isinstance(x, dict)}
    for task in await tasks_for(db, user_id):
        if task.status == "resolved":
            continue
        action = supplied.get(str(task.id), {})
        selected = [dates[d].id for d in action.get("session_dates", []) if d in dates]
        reason = action.get("reason") or "이번 생성에서 구체적 반영 훈련이 제시되지 않아 보류했습니다. 과제와 계획을 검토하세요."
        if task.source_log_id:
            source = await db.get(WorkoutLog, task.source_log_id)
            if not source or source.revision != task.evidence.get("log", {}).get("revision"):
                selected = []
                reason = "근거 기록이 정정되어 보류했습니다. 갱신된 리뷰에서 과제를 다시 선택하세요."
        task.assignments = [x for x in task.assignments if x["plan_id"] != plan.id] + [{
            "plan_id": plan.id, "iso_week": f"{plan.iso_year}-W{plan.iso_week:02d}",
            "session_ids": selected, "session_dates": [str(s.session_date) for s in sessions if s.id in selected],
            "status": "applied" if selected else "deferred", "reason": reason}]


async def evaluate_tasks(db, user_id, plan):
    """Attach observed execution to each task; no automatic claim that a coaching problem is solved."""
    logs = list((await db.execute(select(WorkoutLog).where(WorkoutLog.user_id == user_id,
        WorkoutLog.session_id.in_(select(PlanSession.id).where(PlanSession.plan_id == plan.id))))).scalars())
    for task in await tasks_for(db, user_id):
        assignments = [a for a in task.assignments if a["plan_id"] == plan.id]
        if not assignments:
            continue
        ids = assignments[-1]["session_ids"]
        actual = [{"log_id": l.id, "revision": l.revision, "distance_km": l.distance_km,
            "duration_sec": l.duration_sec, "feel": l.feel, "pain_level": l.pain_level, "comment": l.user_comment}
            for l in logs if l.session_id in ids]
        task.evaluations = [e for e in task.evaluations if e["plan_id"] != plan.id] + [{
            "plan_id": plan.id, "actual": actual,
            "result": "실제 수행 근거를 확인하고 해결 여부를 선택하세요." if actual else "연결된 실제 수행 기록이 없어 평가 보류"}]
