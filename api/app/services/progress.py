"""목표 대비 진척도(대시보드) 조립 — DB 로딩 + fitness 순수 계산의 접착층.

라우터(GET /api/dashboard)와 AI 프롬프트 컨텍스트(render_fitness_context)가 같은 함수를 쓴다.
현재 입력으로 재계산한 계열을 제공한다. 당시 평가 이력은 assessments가 별도로 보존한다.
"""

from datetime import date, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import Goal, PlanSession, UserProfile, WeeklyPlan, WorkoutLog
from . import fitness
from .context import KIND_LABELS, iso_week_of, week_start_of

SERIES_WEEKS = 12


async def load_fitness_inputs(db: AsyncSession, user_id: int) -> dict:
    """대시보드·프롬프트 컨텍스트 공용 — 로그/계획 세션/목표/PB 를 fitness 입력형으로 변환."""
    goal = (await db.execute(select(Goal).where(
        Goal.user_id == user_id, Goal.is_active == True,  # noqa: E712
    ))).scalar_one_or_none()
    prof = (await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))).scalar_one_or_none()
    logs = (await db.execute(select(WorkoutLog).where(WorkoutLog.user_id == user_id))).scalars()
    from .records import as_run
    logs = list(logs)
    runs = [as_run(l) for l in logs]
    sess_rows = (await db.execute(
        select(PlanSession).join(WeeklyPlan, PlanSession.plan_id == WeeklyPlan.id)
        .where(WeeklyPlan.user_id == user_id)
    )).scalars()
    sessions = [fitness.PlannedSession(date=s.session_date, is_rest=s.is_rest, status=s.status)
                for s in sess_rows]
    return {
        "goal": goal, "runs": runs, "sessions": sessions, "logs": logs,
        "pbs": {"pb_10k": prof.pb_10k if prof else None,
                "pb_half": prof.pb_half if prof else None,
                "pb_full": prof.pb_full if prof else None,
                **{key + "_date": getattr(prof, key + "_date", None) for key in ("pb_10k", "pb_half", "pb_full")}},
        "goal_km": fitness.goal_distance_km(goal.race_type if goal else None),
        "target_sec": fitness.parse_hms(goal.target_time) if goal else None,
    }


def build_dashboard(inp: dict, today: date) -> dict:
    goal, runs, sessions = inp["goal"], inp["runs"], inp["sessions"]
    goal_km, target_sec, pbs = inp["goal_km"], inp["target_sec"], inp["pbs"]
    snap = lambda d: fitness.snapshot(runs, sessions, goal_km, target_sec, pbs, d)  # noqa: E731

    anchor = inp.get("anchor")

    def required(d: date) -> int | None:
        if anchor is None:
            return None
        return int(round(fitness.required_at(
            d, date.fromisoformat(anchor["date"]), anchor["predicted_sec"], goal.target_date, target_sec)))

    # 주별 시계열(오래된 주 → 이번 주). 지난 주는 일요일 기준, 이번 주는 오늘 기준(진행 중).
    series = []
    this_monday = week_start_of(today)
    for k in range(SERIES_WEEKS - 1, -1, -1):
        monday = this_monday - timedelta(weeks=k)
        as_of = today if k == 0 else monday + timedelta(days=6)
        s = snap(as_of)
        y, w = iso_week_of(monday)
        week_km = sum(r.distance_km for r in runs if monday <= r.date <= min(today, monday + timedelta(days=6)) and (r.sport == "running" or (not r.sport and r.kind in fitness.RUN_KINDS)))
        series.append({
            "week_start": monday.isoformat(), "iso_week": f"{y}-W{w:02d}", "as_of": as_of.isoformat(),
            "predicted_sec": s["predicted_sec"] if s["data_status"]["sufficient"] else None, "required_sec": required(as_of),
            "provenance": "현재 데이터로 재계산한 소급 추정",
            "week_km": round(week_km, 1), "current": k == 0,
        })

    cur = series[-1]
    prev = series[-2]
    current = snap(today)
    reflected = [l.updated_at or l.created_at for l in inp.get("logs", []) if l.updated_at or l.created_at]
    reflected = [value.replace(tzinfo=timezone.utc) if value.tzinfo is None
                 else value.astimezone(timezone.utc) for value in reflected]
    current["data_status"]["last_reflected_at"] = max(reflected).isoformat() if reflected else None
    pred = current["predicted_sec"]
    current.update({
        "predicted_time": fitness.fmt_hms(pred),
        "gap_sec": (pred - target_sec) if (pred is not None and target_sec) else None,
        "delta_week_sec": (pred - prev["predicted_sec"])
        if (pred is not None and prev["predicted_sec"] is not None) else None,
        "required_sec": cur["required_sec"],
        "vs_required_sec": (pred - cur["required_sec"])
        if (pred is not None and cur["required_sec"] is not None) else None,
    })

    message = None
    if goal is None:
        message = "목표를 설정하면 현재 실력과의 격차를 보여줘요."
    elif pred is None:
        message = "판단 근거가 부족해요. 기존 기록을 가져오거나 PB와 달성일을 확인해 주세요. 새 훈련은 현재 컨디션과 계획을 먼저 확인하세요."
    elif current["basis"]["reference"]["source"] == "pb":
        message = ("PB 참고 환산값입니다. PB 달성일: " + (current["basis"]["reference"].get("date") or "날짜 미상") + ". 목표일 전망이나 달성 확률이 아닙니다.")

    return {
        "goal": None if goal is None else {
            "id": goal.id, "race_type": goal.race_type, "distance_km": goal_km,
            "target_time": goal.target_time, "target_sec": target_sec,
            "target_date": goal.target_date.isoformat() if goal.target_date else None,
            "dday": (goal.target_date - today).days if goal.target_date else None,
            "weeks_left": max(0, (goal.target_date - today).days) // 7 if goal.target_date else None,
        },
        "current": current,
        "anchor": anchor,
        "series": series,
        "message": message,
    }


async def render_fitness_context(db: AsyncSession, user_id: int, today: date | None = None) -> str:
    """AI 프롬프트용 목표 진척도 — 대시보드와 동일한 숫자를 넘겨 코치 해석이 화면과 어긋나지 않게 한다."""
    today = today or date.today()
    d = build_dashboard(await load_fitness_inputs(db, user_id), today)
    goal, cur = d["goal"], d["current"]
    cur["delta_week_sec"] = None  # 당시 평가 없는 과거와 비교하지 않는다.
    cur["vs_required_sec"] = None
    lines = ["## 목표 진척도(앱 산출 — 재계산 금지, 해석만)",
             "현재 기록 기준 거리 환산이며 목표일까지의 예측이 아니다. 달성 확률·범위·실력 저하를 단정하지 않는다.",
             f"데이터 상태: {cur['data_status']}"]
    if goal is None:
        lines.append("- 목표 미설정")
        return "\n".join(lines)
    left = f" · {goal['weeks_left']}주 남음" if goal["weeks_left"] is not None else ""
    lines.append(f"- 목표: {goal['race_type']} {fitness.fmt_hms(goal['target_sec']) or '기록 미정'}"
                 f" · {goal['target_date'] or '날짜 미정'}{left}")
    if cur["predicted_sec"] is None:
        lines.append(f"- 현재 기록 기준 환산값: 산출 불가 — {d['message']}")
        return "\n".join(lines)
    gap = f" (목표 대비 {fitness.fmt_signed(cur['gap_sec'])})" if cur["gap_sec"] is not None else ""
    lines.append(f"- 현재 기록 기준 환산값: {cur['predicted_time']}{gap}")
    if cur["delta_week_sec"] is not None:
        trend = "환산값 증가" if cur["delta_week_sec"] > 0 else ("환산값 감소" if cur["delta_week_sec"] < 0 else "변화 없음")
        lines.append(f"- 지난주 대비: {fitness.fmt_signed(cur['delta_week_sec'])} {trend}")
    if cur["vs_required_sec"] is not None:
        pos = "뒤처짐" if cur["vs_required_sec"] > 0 else ("앞섬" if cur["vs_required_sec"] < 0 else "궤적 위")
        lines.append(f"- 요구 궤적 대비: {fitness.fmt_signed(cur['vs_required_sec'])} {pos}"
                     f" (목표일까지 매주 내려와야 하는 직선 기준)")
    r = cur["readiness"]
    lines.append(f"- 준비도(0~100): 스피드 {r['speed'] if r['speed'] is not None else '-'}"
                 f" · 지구력 {r['endurance']} · 꾸준함 {r['consistency'] if r['consistency'] is not None else '-'}")
    b = cur["basis"]
    ref = b["reference"]
    if ref["source"] == "pb":
        ref_txt = f"프로필 PB {ref['distance_km']}km {ref['time']} (최근 8주에 이보다 빠른 수행 없음 → 5% 페널티)"
    else:
        ref_txt = (f"{ref['date']} {KIND_LABELS.get(ref['kind'], ref['kind'])} {ref['distance_km']}km "
                   f"{ref['time']} ({ref['pace']}/km)")
    lines.append(f"- 근거: 기준 기록 {ref_txt} · 최근 4주 평균 {b['vol_4wk_km']}km/주(요구 {b['req_vol_km']})"
                 f" · 최장 롱런 {b['long_run_km']}km(요구 {b['req_long_km']})")
    if d["message"]:
        lines.append(f"- 참고: {d['message']}")
    return "\n".join(lines)
