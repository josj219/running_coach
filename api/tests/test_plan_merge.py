from app.services.plan_merge import merge_same_date


def test_run_and_strength_same_day_fold_into_run():
    # 2026-09-07 실사용 재현: 9/8에 러닝 + 근력이 따로 와서 유니크 제약으로 계획 생성이 통째로 실패했다
    out = merge_same_date([
        {"date": "2026-09-07", "kind": "easy", "title": "트레드밀 복귀 조깅 30분", "duration_min": 40, "note": "점심 헬스장 —"},
        {"date": "2026-09-08", "kind": "strength", "title": "헬스장 하체 근력 + 코어 루틴", "duration_min": 40, "note": "점심 헬스장 —"},
        {"date": "2026-09-08", "kind": "easy", "title": "저녁 이지 런 5km", "distance_km": 5, "duration_min": 35, "note": "퇴근런 —"},
    ])
    assert [s["date"] for s in out] == ["2026-09-07", "2026-09-08"]
    merged = out[1]
    assert merged["kind"] == "easy" and merged["title"] == "저녁 이지 런 5km"   # 러닝이 본 세션
    assert merged["distance_km"] == 5
    assert merged["duration_min"] == 75                                          # 35 + 40
    assert "+ 함께: 헬스장 하체 근력 + 코어 루틴 (40분)" in merged["note"]
    assert merged["note"].startswith("퇴근런 —")                                 # 본 세션 note가 앞


def test_two_supplements_same_day_keep_first_as_primary():
    out = merge_same_date([
        {"date": "2026-09-09", "kind": "core", "title": "코어 20분", "duration_min": 20},
        {"date": "2026-09-09", "kind": "mobility", "title": "가동성 15분", "duration_min": 15},
    ])
    assert len(out) == 1
    assert out[0]["kind"] == "core" and out[0]["duration_min"] == 35
    assert out[0]["note"] == "+ 함께: 가동성 15분 (15분)"


def test_rest_plus_strength_is_no_longer_rest():
    out = merge_same_date([
        {"date": "2026-09-10", "kind": "rest", "is_rest": True, "title": "휴식"},
        {"date": "2026-09-10", "kind": "strength", "title": "상체 근력", "duration_min": 30},
    ])
    assert len(out) == 1
    assert out[0]["is_rest"] is False and out[0]["kind"] == "strength"


def test_unique_dates_untouched_and_order_kept():
    src = [
        {"date": "2026-09-08", "kind": "easy", "title": "a"},
        {"date": "2026-09-07", "kind": "long", "title": "b"},
        {"kind": "other", "title": "날짜 없음"},
    ]
    out = merge_same_date(src)
    assert [s.get("date") for s in out] == ["2026-09-08", "2026-09-07", None]
    assert out[0] is not src[0]          # 원본을 변형하지 않는다
    assert "note" not in out[0]


def test_empty():
    assert merge_same_date([]) == []
