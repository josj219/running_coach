"""BUG-18 회귀 단위 테스트 — 주간 계획 재생성 시 완료 기록 보존 (Playwright 불필요).

주중 계획 재생성(F07/F12 '지금 반영하기')이 `save_weekly_plan` 으로 전체를 덮어쓰며
'## 훈련 기록' 표를 빈 템플릿으로 리셋 → 이미 sync 된 완료 마킹이 소실됐다.
`save_weekly_plan` 이 기존 기록 행을 병합 보존해, count_sessions done 이 유지돼야 한다.
"""

import os
import sys
import tempfile
import datetime
from pathlib import Path

_WS = tempfile.mkdtemp(prefix="qa_bug18_")
os.environ.setdefault("WORKSPACE_PATH", _WS)
os.environ.setdefault("COACH_MOCK", "1")
sys.path.insert(0, str(Path(__file__).parent.parent / "webapp"))

from utils import file_manager as fm  # noqa: E402

# 기존 계획: 요일별 5세션 + 훈련 기록에 6/9 ⚠️ 완료 1건(이미 sync 됨)
_OLD_PLAN = """## 주간 훈련 계획 — 이번 주

## 요일별 계획
| 날짜 | 요일 | 구분 | 훈련 | 소요시간 |
|---|---|---|---|---|
| 6/8 | 월 | 평일 | 쉬운 달리기 | 40분 |
| 6/9 | 화 | 평일 | 근력 | 50분 |
| 6/10 | 수 | 평일 | 페이스런 | 30분 |
| 6/11 | 목 | 평일 | 템포 | 45분 |
| 6/12 | 금 | 평일 | 롱런 | 70~80분 |

## 훈련 기록 (실행 후 기입)
| 날짜 | 계획 실행 여부 | 비고 |
|------|--------------|------|
| 6/9 | ⚠️ 근력 6.2km | 컨디션 보통 |

## 주간 평가 (주 종료 후 작성)

_미작성_
"""

# 재생성 계획: 같은 주, 훈련 기록은 빈 템플릿(앱 auto-append 결과)
_NEW_PLAN = """## 주간 훈련 계획 — 이번 주 (재생성)

## 요일별 계획
| 날짜 | 요일 | 구분 | 훈련 | 소요시간 |
|---|---|---|---|---|
| 6/8 | 월 | 평일 | 쉬운 달리기 | 45분 |
| 6/9 | 화 | 평일 | 근력 | 50분 |
| 6/10 | 수 | 평일 | 인터벌 | 40분 |
| 6/11 | 목 | 평일 | 템포 | 45분 |
| 6/12 | 금 | 평일 | 롱런 | 80분 |

## 훈련 기록 (실행 후 기입)
| 날짜 | 계획 실행 여부 | 비고 |
|------|--------------|------|

## 주간 평가 (주 종료 후 작성)

_미작성_
"""


def _plan_path() -> Path:
    return Path(_WS) / "40-training-log" / "weekly" / fm.current_week_filename()


def _seed_old():
    """현재 주 plan 파일로 _OLD_PLAN 을 직접 기록(병합 경로 우회)."""
    p = _plan_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(_OLD_PLAN, encoding="utf-8")


def test_regeneration_preserves_completed_record():
    """재생성 저장 후에도 6/9 ⚠️ 완료 행이 보존된다."""
    _seed_old()
    fm.save_weekly_plan(_NEW_PLAN)
    saved = _plan_path().read_text(encoding="utf-8")
    assert "⚠️ 근력 6.2km" in saved, "재생성이 완료 기록을 소실시킴(BUG-18)"


def test_count_sessions_done_survives_regeneration():
    """병합 결과로 count_sessions done 이 1 로 유지(0 으로 떨어지지 않음)."""
    _seed_old()
    fm.save_weekly_plan(_NEW_PLAN)
    saved = _plan_path().read_text(encoding="utf-8")
    done, total = fm.count_sessions(saved)
    assert done == 1, f"done 이 보존돼 1 이어야 함, got {done}"
    assert total == 5, f"요일별 계획 5세션, got {total}"


def test_merge_helper_dedup_by_date():
    """같은 날짜는 기존 행 우선, new 의 새 날짜는 추가된다."""
    new_with_row = _NEW_PLAN.replace(
        "|------|--------------|------|\n",
        "|------|--------------|------|\n| 6/9 | ✅ 덮어쓰기시도 | x |\n| 6/8 | ✅ 신규 5.0km | 좋음 |\n",
    )
    merged = fm._merge_training_records(_OLD_PLAN, new_with_row)
    rows = {d: ln for d, ln in fm._extract_record_rows(merged)}
    assert "근력 6.2km" in rows["6/9"], "6/9 는 기존(완료) 행이 우선돼야 함"
    assert "덮어쓰기시도" not in rows["6/9"]
    assert "신규 5.0km" in rows["6/8"], "new 에만 있는 6/8 새 행은 추가돼야 함"


def test_no_existing_records_returns_new_unchanged():
    """기존 기록이 없으면 new 를 그대로 반환(빈 표 신규 주)."""
    old_empty = _OLD_PLAN.replace("| 6/9 | ⚠️ 근력 6.2km | 컨디션 보통 |\n", "")
    merged = fm._merge_training_records(old_empty, _NEW_PLAN)
    assert merged == _NEW_PLAN
