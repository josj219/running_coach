"""목표 대비 현재 실력 산출 — 앱이 결정적으로 계산하고 AI는 해석만 한다.

핵심 성질: 게으르면(주간 볼륨·롱런이 줄면) 다음 주 예상 기록이 나빠져야 한다.
순수 스피드 기반 예측(Riegel)은 2주를 쉬어도 숫자가 안 변하므로, 지구력 준비도가
낮을수록 거리 환산 지수를 키워(더 많이 처지는 것으로) 예상 기록을 늦춘다.

    예상 기록 = min over 후보 c 의  t_c × (D_goal / d_c) ^ exp
    후보      = 최근 8주 5km+ 기록  ∪  프로필 PB(×1.05 페널티, 10K 환산 후 스피드 증거로만)
    exp       = 1.06 + (1 - 지구력) × 0.25          (d_c < D_goal 일 때만 상향)
    지구력    = 0.6 × min(1, 4주 평균 주간 km / 요구 km)
              + 0.4 × min(1, 4주 최장 롱런 km / 요구 롱런 km)

PB 를 항상 후보에 두는 이유: 최근 8주가 이지 런뿐이면 "8km 5:40/km" 가 스피드 증거가 돼
예상 기록이 터무니없이 늦어진다. 스피드는 빨리 사라지지 않으므로 PB(페널티)가 스피드 하한이
되고, 지구력 지수는 여전히 볼륨을 따라 움직여 게으르면 멀어지는 성질은 유지된다.

이 모듈은 DB 를 모른다 — 라우터가 로그/목표/프로필을 넘기고 결과 dict 를 받는다.
모든 상수는 이 파일 상단에 있고 대시보드 '근거 보기'에 그대로 노출된다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import math

CALCULATION_VERSION = "journey-1"
RUN_KINDS = {"easy", "interval", "tempo", "long", "race"}
MIN_RECENT_RUNS = 6
MIN_OBSERVATION_DAYS = 14

RIEGEL_EXP = 1.06            # 완전 준비 상태의 거리 환산 지수(Riegel)
ENDURANCE_EXP_SPAN = 0.25    # 지구력 0% 일 때 지수 가산(→ 1.31). 미준비 마라토너의 후반 붕괴 반영
SPEED_WINDOW_DAYS = 56       # 스피드 기준점 탐색 창(8주)
MIN_REF_KM = 5.0             # 기준점 최소 거리 — 3km 전력 질주로 풀 기록을 외삽하지 않는다
PB_PENALTY = 1.05            # 프로필 PB(날짜 미상·오래됨)를 후보로 쓸 때 5% 페널티
CANON_KM = 10.0              # 오래된 PB 는 10K 환산 스피드 증거로만 쓴다(당시 지구력을 현재로 끌어오지 않음)
VOLUME_WINDOW_DAYS = 28      # 지구력 산출 창(4주)
VOL_WEIGHT, LONG_WEIGHT = 0.6, 0.4
SPEED_SCORE_SLOPE = 4.0      # 스피드 점수: 목표보다 5% 느리면 80, 25% 느리면 0

# 목표 거리별 요구 볼륨 — (주간 평균 km, 최장 롱런 km). 지구력 100% 기준.
REQUIREMENTS = {
    42.195: (60.0, 30.0),
    21.0975: (45.0, 18.0),
    10.0: (35.0, 12.0),
    5.0: (30.0, 10.0),
}
FULL_KM, HALF_KM = 42.195, 21.0975


# ── 시간·거리 유틸 ──────────────────────────────────────────────────────────

def parse_hms(s: str | None) -> int | None:
    """'03:30:00' / '3:30:00' / '42:13' → 초. 비어 있거나 형식이 틀리면 None."""
    if not s:
        return None
    try:
        parts = [int(p) for p in s.strip().split(":")]
    except ValueError:
        return None
    if len(parts) == 3:
        h, m, sec = parts
    elif len(parts) == 2:
        h, (m, sec) = 0, parts
    else:
        return None
    if h < 0 or m < 0 or sec < 0 or sec >= 60 or (len(parts) == 3 and m >= 60):
        return None
    total = h * 3600 + m * 60 + sec
    return total if total > 0 else None


def fmt_hms(sec: int | float | None) -> str | None:
    """초 → 'H:MM:SS' (1시간 미만은 'M:SS')."""
    if sec is None:
        return None
    sec = int(round(sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def fmt_signed(sec: int | float | None) -> str | None:
    """초 차이 → '+13:20' / '-2:10' / '0:00' / '+1:01:12'(1시간 이상)."""
    if sec is None:
        return None
    sign = "+" if sec > 0 else ("-" if sec < 0 else "")
    return f"{sign}{fmt_hms(abs(sec))}"


def pace_str(duration_sec: float, distance_km: float) -> str | None:
    if not duration_sec or not distance_km:
        return None
    spk = duration_sec / distance_km
    return f"{int(spk // 60)}:{int(round(spk % 60)):02d}"


def goal_distance_km(race_type: str | None) -> float:
    """목표 종목 문자열 → 거리(km). 모르면 풀마라톤으로 본다."""
    t = (race_type or "").lower().replace(" ", "")
    if "하프" in t or "half" in t or "21" in t:
        return HALF_KM
    if "풀" in t or "full" in t or "마라톤" in t or "42" in t:
        return FULL_KM
    if "10" in t:
        return 10.0
    if "5" in t:
        return 5.0
    return FULL_KM


def requirements_for(goal_km: float) -> tuple[float, float]:
    """목표 거리에 가장 가까운 요구 볼륨(주간 km, 롱런 km)."""
    key = min(REQUIREMENTS, key=lambda k: abs(k - goal_km))
    return REQUIREMENTS[key]


def riegel(t_sec: float, d_from: float, d_to: float, exp: float = RIEGEL_EXP) -> float:
    return t_sec * (d_to / d_from) ** exp


# ── 입력 모델 (DB 독립) ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class Run:
    """예상 기록 산출에 필요한 최소 기록. duration_sec 이 없으면 avg_pace 로 복원한다."""
    date: date
    distance_km: float
    duration_sec: int | None
    kind: str = "easy"
    avg_pace: str | None = None
    sport: str | None = None
    log_id: int | None = None

    def effective_duration(self) -> int | None:
        if self.duration_sec:
            return int(self.duration_sec)
        p = parse_hms(self.avg_pace)
        if p and self.distance_km:
            return int(round(p * self.distance_km))
        return None

    def exclusion_reason(self) -> str | None:
        sport = self.sport or ("running" if self.kind in RUN_KINDS else "unknown")
        if sport != "running":
            return "종목 확인 필요" if sport == "unknown" else "러닝 이외 종목"
        if not math.isfinite(self.distance_km) or self.distance_km <= 0:
            return "거리 확인 필요"
        duration = self.effective_duration()
        if not duration or not 120 <= duration / self.distance_km <= 1200:
            return "거리·시간 확인 필요 (페이스 적합성 범위 밖)"
        if self.avg_pace:
            pace = parse_hms(self.avg_pace)
            if not pace or abs(pace - duration / self.distance_km) > max(15, pace * .1):
                return "거리·시간·페이스 불일치"
        return None


def data_status(runs: list[Run], pbs: dict, as_of: date) -> dict:
    recent = [r for r in runs if as_of - timedelta(days=28) < r.date <= as_of
              and r.exclusion_reason() is None]
    dates = sorted(r.date for r in recent)
    span = (dates[-1] - dates[0]).days + 1 if dates else 0
    sufficient = len(recent) >= MIN_RECENT_RUNS and span >= MIN_OBSERVATION_DAYS and (as_of - dates[-1]).days <= 14
    return {
        "state": "recent" if sufficient else ("pb_reference" if any(parse_hms(pbs.get(k)) for k in ("pb_10k", "pb_half", "pb_full")) else "insufficient"),
        "sufficient": sufficient, "record_count": len(recent), "observation_days": span,
        "first_date": dates[0].isoformat() if dates else None,
        "last_date": dates[-1].isoformat() if dates else None,
        "criteria": "최근 28일 적합한 러닝 6건 이상 · 관측 14일 이상 · 마지막 기록 14일 이내. 예측 정확도 검증 기준은 아닙니다.",
    }


@dataclass(frozen=True)
class PlannedSession:
    date: date
    is_rest: bool
    status: str  # planned|done|partial|missed


# ── 구성 요소 ───────────────────────────────────────────────────────────────

def endurance(runs: list[Run], goal_km: float, as_of: date) -> dict:
    """최근 4주 볼륨·롱런 → 지구력 준비도(0~1)와 근거."""
    since = as_of - timedelta(days=VOLUME_WINDOW_DAYS)
    window = [r for r in runs if since < r.date <= as_of and r.exclusion_reason() is None]
    weeks = VOLUME_WINDOW_DAYS / 7
    vol = sum(r.distance_km for r in window) / weeks
    long_run = max((r.distance_km for r in window), default=0.0)
    req_vol, req_long = requirements_for(goal_km)
    vol_ratio = min(1.0, vol / req_vol)
    long_ratio = min(1.0, long_run / req_long)
    score = VOL_WEIGHT * vol_ratio + LONG_WEIGHT * long_ratio
    return {
        "score": score,
        "vol_4wk_km": round(vol, 1), "long_run_km": round(long_run, 1),
        "req_vol_km": req_vol, "req_long_km": req_long,
        "vol_ratio": round(vol_ratio, 3), "long_ratio": round(long_ratio, 3),
    }


def fade_exponent(endurance_score: float, ref_km: float, goal_km: float) -> float:
    """기준 거리가 목표보다 짧을 때만 지구력 부족분만큼 지수를 올린다."""
    if ref_km >= goal_km:
        return RIEGEL_EXP
    return RIEGEL_EXP + (1.0 - max(0.0, min(1.0, endurance_score))) * ENDURANCE_EXP_SPAN


def _candidates(runs: list[Run], as_of: date, pbs: dict[str, str | None]) -> list[dict]:
    """기준점 후보 — 최근 8주 5km+ 기록 전부 + 프로필 PB(페널티). 가장 빠른 예측을 내는 쪽이 채택된다."""
    since = as_of - timedelta(days=SPEED_WINDOW_DAYS)
    out = []
    for r in runs:
        if r.exclusion_reason() or not (since < r.date <= as_of) or (r.distance_km or 0) < MIN_REF_KM:
            continue
        dur = r.effective_duration()
        if not dur:
            continue
        out.append({"date": r.date, "distance_km": float(r.distance_km), "duration_sec": dur,
                    "kind": r.kind, "source": "log", "penalty": 1.0, "log_id": r.log_id})
    for key, dist in (("pb_10k", 10.0), ("pb_half", HALF_KM), ("pb_full", FULL_KM)):
        sec = parse_hms(pbs.get(key))
        achieved = pbs.get(key + "_date")
        achieved = date.fromisoformat(achieved) if isinstance(achieved, str) else achieved
        if sec and 120 <= sec / dist <= 1200 and (not achieved or achieved <= as_of):
            out.append({"date": achieved, "distance_km": dist, "duration_sec": sec,
                        "kind": "race", "source": "pb", "penalty": PB_PENALTY})
    return out


def _predict_candidate(c: dict, goal_km: float, endurance_score: float) -> tuple[float, float]:
    """후보 하나의 (예상 기록, 사용 지수).

    최근 기록은 그 거리에서 바로 외삽한다(목표 거리 이상의 최근 기록은 그 자체가 근거 → 순수 Riegel).
    오래된 PB 는 당시 지구력을 모르므로 10K 스피드로 환산한 뒤 현재 지구력 지수로 다시 외삽한다.
    """
    t, d = c["duration_sec"] * c["penalty"], c["distance_km"]
    if c["source"] == "pb" and d > CANON_KM and goal_km > CANON_KM:
        t, d = riegel(t, d, CANON_KM), CANON_KM
    exp = fade_exponent(endurance_score, d, goal_km)
    return riegel(t, d, goal_km, exp), exp


def predict(runs: list[Run], goal_km: float, as_of: date, pbs: dict[str, str | None],
            endurance_score: float) -> tuple[float | None, dict | None, float | None]:
    """(예상 기록 초, 채택된 기준점, 사용 지수). 후보가 없으면 (None, None, None)."""
    best = None
    for c in _candidates(runs, as_of, pbs):
        pred, exp = _predict_candidate(c, goal_km, endurance_score)
        if best is None or pred < best[0]:
            best = (pred, c, exp)
    if best is None:
        return None, None, None
    pred, c, exp = best
    ref = {
        **c,
        "date": c["date"].isoformat() if c["date"] else None,
        "time": fmt_hms(c["duration_sec"]),
        "pace": pace_str(c["duration_sec"], c["distance_km"]),
        # 지구력 보정 전 순수 Riegel 환산 — 스피드 점수의 기준
        "equiv_pure_sec": int(round(riegel(c["duration_sec"] * c["penalty"], c["distance_km"], goal_km))),
    }
    return pred, ref, exp


def speed_score(equiv_pure_sec: float | None, target_sec: int | None) -> int | None:
    """순수 스피드 환산이 목표 대비 얼마나 빠른가 — 목표 이하면 100, 25% 느리면 0."""
    if not equiv_pure_sec or not target_sec:
        return None
    ratio = equiv_pure_sec / target_sec - 1.0
    return int(round(100 * max(0.0, min(1.0, 1.0 - SPEED_SCORE_SLOPE * ratio))))


def consistency(sessions: list[PlannedSession], as_of: date) -> dict | None:
    """최근 4주 계획 대비 수행률 — 휴식 제외, done/partial=완료. 계획이 없으면 None."""
    since = as_of - timedelta(days=VOLUME_WINDOW_DAYS)
    workable = [s for s in sessions if since < s.date <= as_of and not s.is_rest]
    if not workable:
        return None
    done = sum(1 for s in workable if s.status == "done")
    participated = sum(1 for s in workable if s.status in ("done", "partial", "substituted"))
    return {"done": done, "participated": participated, "total": len(workable), "score": int(round(done / len(workable) * 100))}


# ── 스냅샷 ──────────────────────────────────────────────────────────────────

def snapshot(runs: list[Run], sessions: list[PlannedSession], goal_km: float,
             target_sec: int | None, pbs: dict[str, str | None], as_of: date) -> dict:
    """as_of 시점의 예상 기록 + 준비도 + 근거. 시계열은 이 함수를 주별로 호출해 만든다."""
    end = endurance(runs, goal_km, as_of)
    pred, ref, exp = predict(runs, goal_km, as_of, pbs, end["score"])
    cons = consistency(sessions, as_of)
    status = data_status(runs, pbs, as_of)
    return {
        "as_of": as_of.isoformat(),
        "calculation_version": CALCULATION_VERSION,
        "data_status": status,
        "predicted_sec": int(round(pred)) if pred is not None else None,
        "readiness": {
            "speed": speed_score(ref["equiv_pure_sec"], target_sec) if ref and status["sufficient"] else None,
            "endurance": int(round(end["score"] * 100)) if status["sufficient"] else None,
            "consistency": cons["score"] if cons else None,
        },
        "basis": {
            "reference": ref,
            "exponent": round(exp, 3) if exp is not None else None,
            "vol_4wk_km": end["vol_4wk_km"], "long_run_km": end["long_run_km"],
            "req_vol_km": end["req_vol_km"], "req_long_km": end["req_long_km"],
            "vol_ratio": end["vol_ratio"], "long_ratio": end["long_ratio"],
            "completion_4wk": cons,
            "speed_window_days": SPEED_WINDOW_DAYS, "volume_window_days": VOLUME_WINDOW_DAYS,
        },
    }


def required_at(d: date, anchor_date: date, anchor_sec: float,
                target_date: date, target_sec: float) -> float:
    """요구 궤적 — 목표 설정 시점 예상에서 목표일 목표 기록까지 직선. 구간 밖은 양 끝값."""
    span = (target_date - anchor_date).days
    if span <= 0:
        return float(target_sec)
    frac = max(0.0, min(1.0, (d - anchor_date).days / span))
    return anchor_sec + (target_sec - anchor_sec) * frac
