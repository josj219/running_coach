"""BUG-06 회귀 — count_sessions() 단위 테스트.

total_count 는 '요일별 계획'(휴식 제외) 기준, done_count 는 '## 훈련 기록'의 ✅/⚠️ 기준.
신규 계획(훈련 기록 표 비어있음)에서 첫 훈련 저장 후에도 S5 가 아니라 S3 여야 한다.
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "webapp"))
os.environ.setdefault("WORKSPACE_PATH", tempfile.mkdtemp(prefix="qa_cs_"))

from utils import file_manager as fm  # noqa: E402


def _plan(day_rows: str, record_rows: str) -> str:
    """요일별 계획 + (잘못 세기 쉬운) 세션별 요약 표 + 훈련 기록 표."""
    return f"""## 주간 훈련 계획 — 테스트

### 요일별 계획
| 날짜 | 요일 | 구분 | 훈련 | 소요시간 |
|------|------|------|------|----------|
{day_rows}

---

### 세션별 요약
| 구간 | 페이스 |
|------|--------|
| Z2 | 6:30 |

## 훈련 기록 (실행 후 기입)
| 날짜 | 완료 | 내용 |
|------|------|------|
{record_rows}

## 주간 평가 (주 종료 후 작성)
"""


THREE_TRAIN_ONE_REST = (
    "| 6/8 | 월 | 러닝 | 쉬운 달리기 6km | 40분 |\n"
    "| 6/9 | 화 | 러닝 | 인터벌 5km | 50분 |\n"
    "| 6/10 | 수 | 러닝 | 롱런 12km | 80분 |\n"
    "| 6/11 | 목 | 휴식 | 완전 휴식 | — |"
)


def _is_week_end(done, total, weekday):
    """app._is_week_end 의 조건 B/C 재현(요일 무관 A 제외)."""
    if total > 0 and done == total:
        return True  # B
    if weekday == 5 and done >= max(1, total // 2):
        return True  # C(토요일)
    return False


# 1. 훈련 기록 표가 비어 있어도 total = 요일별 실제 훈련 수
def test_total_from_weekly_plan_when_record_empty():
    done, total = fm.count_sessions(_plan(THREE_TRAIN_ONE_REST, ""))
    assert (done, total) == (0, 3), f"got {(done, total)}"


# 2. 첫 훈련 저장(done=1) + total>1 → S5(week_end) 아님 → S3
def test_first_done_is_not_week_end():
    done, total = fm.count_sessions(_plan(THREE_TRAIN_ONE_REST, "| 6/8 | ✅ | 쉬운 6km |"))
    assert (done, total) == (1, 3)
    assert _is_week_end(done, total, weekday=0) is False  # 월요일


# 3. 모든 훈련 세션 완료 → S5 진입
def test_all_done_is_week_end():
    record = "| 6/8 | ✅ | A |\n| 6/9 | ⚠️ | B |\n| 6/10 | ✅ | C |"
    done, total = fm.count_sessions(_plan(THREE_TRAIN_ONE_REST, record))
    assert (done, total) == (3, 3)
    assert _is_week_end(done, total, weekday=0) is True


# 4. 휴식/회복일은 total 에서 제외
def test_rest_excluded_from_total():
    rows = (
        "| 6/8 | 월 | 러닝 | 쉬운 6km | 40분 |\n"
        "| 6/9 | 화 | 휴식 | 완전 휴식 | — |\n"
        "| 6/10 | 수 | 회복 | 회복일 | — |\n"
        "| 6/11 | 목 | 러닝 | 인터벌 | 50분 |"
    )
    _, total = fm.count_sessions(_plan(rows, ""))
    assert total == 2, f"휴식/회복 제외 실패: total={total}"


# 5. 토요일 half-done 조건도 새 total 기준
def test_saturday_half_done():
    done, total = fm.count_sessions(_plan(THREE_TRAIN_ONE_REST, "| 6/8 | ✅ | A |\n| 6/9 | ✅ | B |"))
    assert (done, total) == (2, 3)
    assert _is_week_end(done, total, weekday=5) is True   # 토요일 + 2 >= max(1,3//2=1)
    assert _is_week_end(done, total, weekday=0) is False  # 평일은 아님


# 6. ❌(미실시)는 done 에 포함되지 않음(✅/⚠️ 만)
def test_missed_not_counted_as_done():
    done, total = fm.count_sessions(_plan(THREE_TRAIN_ONE_REST, "| 6/8 | ❌ | 미실시 |"))
    assert done == 0, f"❌가 done 으로 집계됨: {done}"
    assert total == 3
