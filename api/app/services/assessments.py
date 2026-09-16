"""Immutable assessments and explainable changes. No future race-time model."""
import hashlib
import json
from dataclasses import asdict
from datetime import date, timedelta
from sqlalchemy import select
from ..db import Assessment, AvailabilitySlot, GoalCheckpoint, JourneyEvent, PlanSession, WeeklyPlan
from .fitness import CALCULATION_VERSION, fmt_hms
from .progress import build_dashboard, load_fitness_inputs


def serial(value):
    return json.loads(json.dumps(value, default=str, ensure_ascii=False))


async def capture_assessment(db, user_id, reason="입력 또는 관측 기간 변경", today=None):
    today = today or date.today()
    inp = await load_fitness_inputs(db, user_id)
    goal = inp["goal"]
    inputs = serial({"runs": [asdict(r) for r in inp["runs"]],
        "revisions": {str(l.id): l.revision for l in inp["logs"]},
        "sessions": [asdict(s) for s in inp["sessions"]], "pbs": inp["pbs"],
        "goal": None if goal is None else {k: getattr(goal, k) for k in ("id", "race_type", "target_time", "target_date", "created_at")}})
    digest = hashlib.sha256(json.dumps([CALCULATION_VERSION, inputs], sort_keys=True).encode()).hexdigest()
    old = (await db.execute(select(Assessment).where(Assessment.user_id == user_id,
        Assessment.goal_id == (goal.id if goal else None), Assessment.as_of == today,
        Assessment.input_hash == digest))).scalar_one_or_none()
    if old:
        return old
    result = build_dashboard(inp, today)["current"]
    assessment = Assessment(user_id=user_id, goal_id=goal.id if goal else None, as_of=today,
        input_hash=digest, calculation_version=CALCULATION_VERSION, inputs=inputs,
        result=serial(result), reason=reason)
    db.add(assessment)
    await db.flush()
    return assessment


def assessment_dict(a):
    return {"id": a.id, "goal_id": a.goal_id, "as_of": str(a.as_of),
        "created_at": a.created_at.isoformat(), "reason": a.reason,
        "calculation_version": a.calculation_version, "inputs": a.inputs, "current": a.result,
        "provenance": "당시 평가"}


def explain(previous, current):
    if not previous:
        return [{"cause": "baseline", "text": "첫 저장 평가입니다. 이후의 평가와 같은 입력 기준으로 비교합니다."}]
    reasons = []
    old, new = previous.result["basis"], current.result["basis"]
    if previous.inputs["pbs"] != current.inputs["pbs"]:
        reasons.append({"cause": "pb_changed", "text": "PB 또는 달성일이 변경되었습니다. 과거 평가는 유지됩니다.", "before": previous.inputs["pbs"], "after": current.inputs["pbs"]})
    if old["reference"] != new["reference"]:
        reasons.append({"cause": "reference_changed", "text": "환산에 사용한 기준 기록이 변경되었습니다.", "before": old["reference"], "after": new["reference"]})
    if any(v != current.inputs["revisions"].get(k) for k, v in previous.inputs["revisions"].items()):
        reasons.append({"cause": "record_corrected", "text": "기존 기록 정정이 현재 환산값에 반영되었습니다. 변경 사유는 사건 이력에서 확인하세요."})
    if (old["vol_4wk_km"], old["long_run_km"]) != (new["vol_4wk_km"], new["long_run_km"]):
        reasons.append({"cause": "volume_changed", "text": "최근 4주 운동량·최장 거리 입력이 달라졌습니다. 실제 실력 저하 또는 훈련 실패를 뜻하지 않습니다.",
            "before": {k: old[k] for k in ("vol_4wk_km", "long_run_km")}, "after": {k: new[k] for k in ("vol_4wk_km", "long_run_km")}})
    if previous.as_of != current.as_of:
        reasons.append({"cause": "window_moved", "text": f"관측 기준일이 {previous.as_of}에서 {current.as_of}로 이동했습니다."})
    return reasons or [{"cause": "unchanged", "text": "기준 기록과 운동량의 변화가 없습니다."}]


async def dashboard(db, user_id, today=None):
    today = today or date.today()
    from .records import lock_user
    await lock_user(db, user_id)
    current = await capture_assessment(db, user_id, today=today)
    inp = await load_fitness_inputs(db, user_id)
    history = list((await db.execute(select(Assessment).where(Assessment.user_id == user_id,
        Assessment.goal_id == current.goal_id).order_by(Assessment.id))).scalars())
    anchors = [a for a in history if a.result["predicted_sec"] is not None and a.result["data_status"]["sufficient"]]
    if anchors:
        inp["anchor"] = {"date": str(anchors[0].as_of), "predicted_sec": anchors[0].result["predicted_sec"], "assessment_id": anchors[0].id}
    d = build_dashboard(inp, today)
    d["recalculated_series"] = d["series"]
    # The chart only connects assessments actually saved at the time.
    actual = []
    for point in d["series"]:
        within = [a for a in history if point["week_start"] <= str(a.as_of) <= point["as_of"]]
        saved = within[-1] if within else None
        actual.append({**point, "predicted_sec": saved.result["predicted_sec"] if saved and saved.result["data_status"]["sufficient"] else None,
            "assessment_id": saved.id if saved else None, "provenance": "당시 평가" if saved else "당시 평가 없음"})
    d["series"] = actual
    previous = next((a for a in reversed(history) if a.id != current.id), None)
    pred = current.result["predicted_sec"]
    prev_pred = previous.result["predicted_sec"] if previous else None
    d["current"]["delta_week_sec"] = None  # no synthetic previous week
    d["current"]["delta_assessment_sec"] = pred - prev_pred if pred is not None and prev_pred is not None else None
    d["assessment_id"] = current.id
    d["changes"] = explain(previous, current)
    events = list((await db.execute(select(JourneyEvent).where(JourneyEvent.user_id == user_id)
        .order_by(JourneyEvent.id.desc()).limit(30))).scalars())
    d["events"] = [{"id": e.id, "type": e.event_type, "date": e.created_at.isoformat(),
        "reason": e.reason, "before": e.before, "after": e.after} for e in events]
    slots = list((await db.execute(select(AvailabilitySlot).where(AvailabilitySlot.user_id == user_id))).scalars())
    available = sum((s.duration_min or 0) * len(s.days) for s in slots)
    week_start = today - timedelta(days=today.weekday())
    planned = list((await db.execute(select(PlanSession).join(WeeklyPlan).where(WeeklyPlan.user_id == user_id,
        PlanSession.session_date >= today, PlanSession.session_date <= week_start + timedelta(days=6),
        PlanSession.is_rest == False))).scalars())
    checkpoint = list((await db.execute(select(GoalCheckpoint).where(GoalCheckpoint.user_id == user_id,
        GoalCheckpoint.goal_id == current.goal_id).order_by(GoalCheckpoint.review_date))).scalars()) if current.goal_id else []
    next_date = min(today + timedelta(days=14), inp["goal"].target_date) if inp["goal"] and inp["goal"].target_date and inp["goal"].target_date >= today else today + timedelta(days=14)
    d["outlook"] = {"status": "조건부 검토 · 기록 전망 미산출", "available_min_per_week": available,
        "weeks_left": d["goal"]["weeks_left"] if d["goal"] else None,
        "remaining_plan_min_this_week": sum(s.duration_min or 0 for s in planned),
        "remaining_plan_sessions": len(planned),
        "required_change_sec": d["current"]["gap_sec"], "suggested_checkpoint": str(next_date),
        "conditions": ["미반영 기록과 PB 달성일을 확인", "가용 시간·현재 컨디션에 맞는 계획 실행", "체크포인트에서 실제 수행 기록과 당시 평가를 비교"],
        "message": "현재 환산값과 목표 격차는 확인할 수 있습니다. 훈련 효과·대회 오차를 검증한 모델이 없어 목표일 기록, 달성 확률, 예측 범위는 산출하지 않습니다."}
    d["checkpoints"] = [{"id": c.id, "review_date": str(c.review_date), "evidence_needed": c.evidence_needed, "decision": c.decision} for c in checkpoint]
    d["history_note"] = "스냅샷 도입 전에는 당시 평가가 없습니다. 현재 데이터로 재계산한 값은 소급 추정으로 별도 표시합니다."
    await db.commit()
    return d
