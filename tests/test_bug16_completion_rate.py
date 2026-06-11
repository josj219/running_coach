"""BUG-16 회귀 단위 테스트 — 수행률 정의 통일 (순수 함수, Playwright 불필요).

같은 주 수행률이 화면마다 달랐다:
  - 앱 주간 통계(기록 탭): count_sessions → 1/5 = 20% (휴식 제외 분모, ⚠️=완료)
  - AI 성장 리포트(F08): 계획 prose "총 훈련 세션 6회" + ⚠️=0.5 → 0.5/6 = 8%

통일 기준(앱이 source of truth):
  - 분모 = '요일별 계획' 표의 훈련 세션 수(휴식·회복 제외) = count_sessions 의 total
  - ✅·⚠️ = 완료(1.0), ❌ = 0.0 → 수행률 = done/total
  - 평가 프롬프트는 ⚠️=0.5 가중치를 버리고, 앱이 넘기는 [수행률(앱 집계)] 값을 사용

본 테스트는 (1) count_sessions 가 버그 시나리오에서 (1, 5)=20% 를 주는지,
(2) 평가 프롬프트가 ⚠️ 부분=0.5 규칙을 더는 담지 않고 통일 문구를 담는지 검증한다.
"""

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("WORKSPACE_PATH", tempfile.mkdtemp(prefix="qa_bug16_"))
os.environ.setdefault("COACH_MOCK", "1")
sys.path.insert(0, str(Path(__file__).parent.parent / "webapp"))

from utils import file_manager as fm  # noqa: E402
from utils import prompts  # noqa: E402


# BUG-16 재현 계획: 요일별 계획 6행 중 1행이 휴식 → total=5.
# 훈련 기록 표에 ✅ 1, ⚠️ 1 (둘 다 완료로 집계) → done=2.
_PLAN = """## 요일별 계획
| 날짜 | 요일 | 구분 | 훈련 | 소요시간 |
|---|---|---|---|---|
| 6/8 | 월 | 평일 | 쉬운 달리기 | 40분 |
| 6/9 | 화 | 평일 | 인터벌 | 50분 |
| 6/10 | 수 | 평일 | 페이스런 | 30분 |
| 6/11 | 목 | 평일 | 템포 | 45분 |
| 6/12 | 금 | 평일 | 롱런 | 70~80분 |
| 6/14 | 일 | 주말 | 휴식 | - |

## 훈련 기록 (실행 후 기입)
| 날짜 | 계획 실행 여부 | 비고 |
|---|---|---|
| 6/8 | ✅ 완료 | 5.0km |
| 6/9 | ⚠️ 부분 | 3.0km |
"""


def test_count_sessions_excludes_rest_for_denominator():
    """total 은 휴식 제외 5 (요약 prose 가 아니라 표 기준)."""
    done, total = fm.count_sessions(_PLAN)
    assert total == 5, f"휴식 제외 분모는 5여야 함, got {total}"


def test_warning_counts_as_done():
    """⚠️ 부분 수행도 완료로 집계 → done = ✅1 + ⚠️1 = 2."""
    done, total = fm.count_sessions(_PLAN)
    assert done == 2, f"✅·⚠️ 모두 완료 집계 → 2여야 함, got {done}"


def test_completion_rate_matches_app_formula():
    """앱이 표시하는 수행률 = done/total = 2/5 = 40% (화면 간 동일 기준)."""
    done, total = fm.count_sessions(_PLAN)
    rate = int(done / total * 100) if total else 0
    assert rate == 40, f"2/5 = 40%여야 함, got {rate}"


def test_eval_prompt_drops_partial_half_weight():
    """평가 프롬프트가 ⚠️ 부분=0.5 가중치를 더는 담지 않는다(통일)."""
    p = prompts.WEEKLY_EVALUATION_PROMPT
    assert "0.5점" not in p, "⚠️ 부분=0.5점 가중치가 남아 있음 (앱과 불일치)"
    assert "부분=0.5" not in p


def test_eval_prompt_has_unified_denominator_rule():
    """평가 프롬프트가 '휴식·회복 제외' 분모 + 앱 집계 우선 규칙을 담는다."""
    p = prompts.WEEKLY_EVALUATION_PROMPT
    assert "휴식" in p and "제외" in p, "휴식 제외 분모 지침 누락"
    assert "수행률(앱 집계)" in p, "[수행률(앱 집계)] 값 사용 지침 누락"
