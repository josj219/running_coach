"""목표 대비 현재 실력 산출(services/fitness) — 순수 함수 회귀.

핵심 성질 검증: 게으르면(볼륨↓) 예상 기록이 느려진다 / 기준점 선택 / PB 폴백 / 요구 궤적.
"""

from datetime import date, timedelta

from app.services import fitness as f

AS_OF = date(2026, 9, 6)
PBS = {"pb_10k": "00:42:13", "pb_half": "01:38:00", "pb_full": "03:51:00"}
FULL = f.FULL_KM
SUB330 = 3 * 3600 + 30 * 60


def easy_weeks(weekly_km: float, weeks: int = 4, long_km: float | None = None) -> list[f.Run]:
    """as_of 이전 N주에 걸쳐 주 3회 이지 런(6:00/km)을 깐다. long_km 이 있으면 주 1회 롱런으로 대체."""
    runs = []
    for w in range(weeks):
        base = AS_OF - timedelta(days=7 * w + 1)
        per = weekly_km / 3
        dists = [per, per, per]
        if long_km:
            dists = [long_km, (weekly_km - long_km) / 2, (weekly_km - long_km) / 2]
        for i, d in enumerate(dists):
            runs.append(f.Run(date=base - timedelta(days=i * 2), distance_km=round(d, 1),
                              duration_sec=int(d * 360), kind="easy"))
    return runs


# ── 유틸 ────────────────────────────────────────────────────────────────────

def test_parse_and_format_hms():
    assert f.parse_hms("03:30:00") == SUB330
    assert f.parse_hms("42:13") == 42 * 60 + 13
    assert f.parse_hms("") is None and f.parse_hms("abc") is None
    assert f.fmt_hms(SUB330) == "3:30:00"
    assert f.fmt_hms(42 * 60 + 13) == "42:13"
    assert f.fmt_signed(800) == "+13:20" and f.fmt_signed(-130) == "-2:10" and f.fmt_signed(0) == "0:00"
    assert f.fmt_signed(3672) == "+1:01:12"


def test_goal_distance_parsing():
    assert f.goal_distance_km("풀마라톤") == FULL
    assert f.goal_distance_km("하프마라톤") == f.HALF_KM   # '마라톤' 포함이어도 하프 우선
    assert f.goal_distance_km("Half") == f.HALF_KM
    assert f.goal_distance_km("10K") == 10.0
    assert f.goal_distance_km("5km") == 5.0
    assert f.goal_distance_km(None) == FULL


def test_riegel_pure_from_10k_pb():
    """10K 42:13 → 풀 순수 환산 ≈ 3:14 (지구력 완비 가정)."""
    sec = f.riegel(42 * 60 + 13, 10.0, FULL)
    assert abs(sec - (3 * 3600 + 14 * 60 + 12)) < 60


# ── 기준점 선택 ──────────────────────────────────────────────────────────────

def test_pb_fallback_when_no_recent_runs():
    snap = f.snapshot([], [], FULL, SUB330, PBS, AS_OF)
    ref = snap["basis"]["reference"]
    assert ref["source"] == "pb" and ref["penalty"] == f.PB_PENALTY
    assert snap["predicted_sec"] is not None
    # 볼륨 0 → 지구력 0 → 지수 최대(1.31). 10K PB 기준이면 sub 3:30 보다 훨씬 느려야 한다
    assert snap["readiness"]["endurance"] is None
    assert snap["predicted_sec"] > SUB330 + 30 * 60


def test_recent_hard_effort_beats_pb_and_easy_runs():
    runs = easy_weeks(30) + [f.Run(date=AS_OF - timedelta(days=5), distance_km=10.0,
                                   duration_sec=44 * 60, kind="tempo")]
    snap = f.snapshot(runs, [], FULL, SUB330, PBS, AS_OF)
    ref = snap["basis"]["reference"]
    assert ref["source"] == "log" and ref["kind"] == "tempo" and ref["distance_km"] == 10.0
    assert ref["pace"] == "4:24"


def test_easy_runs_only_falls_back_to_pb_speed():
    """최근 8주가 이지 런뿐이면 '8km 5:40' 이 스피드 증거가 되지 않고 PB(페널티)가 하한이 된다."""
    snap = f.snapshot(easy_weeks(30), [], FULL, SUB330, PBS, AS_OF)
    assert snap["basis"]["reference"]["source"] == "pb"
    # 이지 런만으로 외삽했다면 5시간대 — PB 하한 덕에 4시간대 초반
    assert snap["predicted_sec"] < 4 * 3600 + 30 * 60


def test_stale_full_pb_does_not_carry_old_endurance():
    """풀 PB 3:51 은 10K 환산 스피드로만 쓰이고 현재(볼륨 0) 지구력 지수로 다시 외삽된다."""
    snap = f.snapshot([], [], FULL, SUB330, {"pb_full": "03:51:00"}, AS_OF)
    assert snap["basis"]["exponent"] > f.RIEGEL_EXP
    assert snap["predicted_sec"] > f.parse_hms("03:51:00") * f.PB_PENALTY + 30 * 60


def test_logging_a_hard_effort_never_worsens_prediction():
    tempo = f.Run(date=AS_OF - timedelta(days=3), distance_km=10.0, duration_sec=44 * 60, kind="tempo")
    without = f.snapshot([], [], FULL, SUB330, PBS, AS_OF)["predicted_sec"]
    with_tempo = f.snapshot([tempo], [], FULL, SUB330, PBS, AS_OF)["predicted_sec"]
    assert with_tempo <= without


def test_short_sprint_is_not_a_reference():
    """3km 전력 질주는 풀 외삽 기준점이 되지 않는다(MIN_REF_KM)."""
    runs = [f.Run(date=AS_OF - timedelta(days=2), distance_km=3.0, duration_sec=11 * 60, kind="interval")]
    snap = f.snapshot(runs, [], FULL, SUB330, PBS, AS_OF)
    assert snap["basis"]["reference"]["source"] == "pb"


def test_reference_outside_window_ignored():
    old = f.Run(date=AS_OF - timedelta(days=f.SPEED_WINDOW_DAYS + 1), distance_km=10.0,
                duration_sec=40 * 60, kind="race")
    snap = f.snapshot([old], [], FULL, SUB330, PBS, AS_OF)
    assert snap["basis"]["reference"]["source"] == "pb"


def test_duration_recovered_from_pace_when_missing():
    runs = [f.Run(date=AS_OF - timedelta(days=3), distance_km=10.0, duration_sec=None,
                  kind="tempo", avg_pace="4:30")]
    snap = f.snapshot(runs, [], FULL, SUB330, {}, AS_OF)  # PB 없이 — 페이스 복원만 검증
    assert snap["basis"]["reference"]["duration_sec"] == 2700


# ── 핵심 성질: 게으르면 멀어진다 ───────────────────────────────────────────

def test_lower_volume_gives_slower_prediction():
    tempo = f.Run(date=AS_OF - timedelta(days=3), distance_km=10.0, duration_sec=44 * 60, kind="tempo")
    busy = f.snapshot(easy_weeks(60, long_km=30) + [tempo], [], FULL, SUB330, PBS, AS_OF)
    lazy = f.snapshot(easy_weeks(20, long_km=8) + [tempo], [], FULL, SUB330, PBS, AS_OF)
    assert busy["readiness"]["endurance"] == 100
    assert lazy["readiness"]["endurance"] < 50
    assert lazy["predicted_sec"] > busy["predicted_sec"] + 10 * 60
    # 같은 스피드 기준점이므로 스피드 점수는 동일
    assert busy["readiness"]["speed"] == lazy["readiness"]["speed"]


def test_full_endurance_equals_pure_riegel():
    tempo = f.Run(date=AS_OF - timedelta(days=3), distance_km=10.0, duration_sec=44 * 60, kind="tempo")
    snap = f.snapshot(easy_weeks(60, long_km=30) + [tempo], [], FULL, SUB330, PBS, AS_OF)
    assert snap["basis"]["exponent"] == f.RIEGEL_EXP
    assert snap["predicted_sec"] == snap["basis"]["reference"]["equiv_pure_sec"]


def test_reference_longer_than_goal_uses_plain_riegel():
    """하프 목표에 풀 기록이 기준이면 지구력 부족분을 가산하지 않는다."""
    full = f.Run(date=AS_OF - timedelta(days=10), distance_km=FULL, duration_sec=3 * 3600 + 51 * 60, kind="race")
    snap = f.snapshot([full], [], f.HALF_KM, None, {}, AS_OF)  # PB 없이 — 지수 규칙만 검증
    assert snap["basis"]["reference"]["source"] == "log"
    assert snap["basis"]["exponent"] == f.RIEGEL_EXP


def test_speed_score_bounds():
    assert f.speed_score(SUB330 - 100, SUB330) == 100
    assert f.speed_score(int(SUB330 * 1.05), SUB330) == 80
    assert f.speed_score(int(SUB330 * 1.30), SUB330) == 0
    assert f.speed_score(None, SUB330) is None and f.speed_score(1000, None) is None


def test_consistency_excludes_rest_and_counts_partial():
    sessions = [
        f.PlannedSession(AS_OF - timedelta(days=1), False, "done"),
        f.PlannedSession(AS_OF - timedelta(days=2), False, "partial"),
        f.PlannedSession(AS_OF - timedelta(days=3), True, "planned"),
        f.PlannedSession(AS_OF - timedelta(days=4), False, "missed"),
        f.PlannedSession(AS_OF - timedelta(days=5), False, "planned"),
        f.PlannedSession(AS_OF - timedelta(days=40), False, "planned"),  # 창 밖
    ]
    c = f.consistency(sessions, AS_OF)
    assert c == {"done": 1, "participated": 2, "total": 4, "score": 25}
    assert f.consistency([], AS_OF) is None


# ── 요구 궤적 ────────────────────────────────────────────────────────────────

def test_required_trajectory_is_linear_and_clamped():
    a, t = date(2026, 6, 1), date(2026, 11, 1)
    assert f.required_at(a, a, 14000, t, SUB330) == 14000
    assert f.required_at(t, a, 14000, t, SUB330) == SUB330
    mid = a + timedelta(days=(t - a).days // 2)
    assert abs(f.required_at(mid, a, 14000, t, SUB330) - (14000 + SUB330) / 2) < 30
    assert f.required_at(a - timedelta(days=30), a, 14000, t, SUB330) == 14000
    assert f.required_at(t + timedelta(days=30), a, 14000, t, SUB330) == SUB330
    assert f.required_at(a, t, 14000, t, SUB330) == SUB330  # 목표일이 앵커보다 이전이면 목표값
