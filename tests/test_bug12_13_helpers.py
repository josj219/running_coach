"""BUG-12 / BUG-13 회귀 단위 테스트 (순수 함수, Playwright 불필요).

- BUG-12: `_session_preview()` — 내일 예고 카드가 주간계획 표 행을 셀 분해해
  '훈련' 칸만 보여줘야 한다. 셀 분해 없이 자르면 마크다운 파이프 노출 + 단어 중간 잘림.
- BUG-13: `_recovery_level()` — 회복 뱃지는 '회복 필요도:' 라벨 뒤 verdict 이모지로
  판정해야 한다. 리뷰 추론에 🔴 을 '언급만' 해도 high 로 오판하면 안 된다.

app.py 는 import 시 streamlit 스크립트를 끝까지 실행하므로, 빈 임시 워크스페이스
(=계획 없음 → S0, AI 미호출) + COACH_MOCK 로 부작용·실 API 호출을 막는다.
"""

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("WORKSPACE_PATH", tempfile.mkdtemp(prefix="qa_bug1213_"))
os.environ.setdefault("COACH_MOCK", "1")
sys.path.insert(0, str(Path(__file__).parent.parent / "webapp"))

import app  # noqa: E402


# ── BUG-12: _session_preview ────────────────────────────────────────────────

def test_preview_table_row_extracts_training_cell():
    """| 날짜 | 요일 | 구분 | 훈련 | 소요 | 행에서 '훈련' 칸만 추출."""
    row = "[요일별 계획 행]\n| 6/10 | 수 | 평일·헬스장 | 트레드밀 Easy Run | 40분 |"
    out = app._session_preview(row)
    assert out == "트레드밀 Easy Run"
    assert "|" not in out  # 마크다운 파이프 노출 금지


def test_preview_skips_header_and_separator_rows():
    """헤더 행('훈련' 라벨)·구분선 행을 건너뛰고 데이터 행의 훈련 칸을 잡는다."""
    block = (
        "| 날짜 | 요일 | 구분 | 훈련 | 소요 |\n"
        "|---|---|---|---|---|\n"
        "| 6/10 | 수 | 평일 | 인터벌 400m x 8 | 50분 |"
    )
    assert app._session_preview(block) == "인터벌 400m x 8"


def test_preview_avoids_gubun_cell_keyword_collision():
    """'평일·헬스장'(구분 칸)의 '헬스' 가 아니라 index 3 훈련 칸을 우선한다."""
    row = "| 6/11 | 목 | 평일·헬스장 | 롱런 12km | 80분 |"
    assert app._session_preview(row) == "롱런 12km"


def test_preview_non_table_line():
    """표가 아닌 라인은 키워드 매칭으로 추출하고 머리기호를 제거한다."""
    assert app._session_preview("### 6/10 인터벌 세션\n- 400m x 8").startswith("6/10 인터벌")


def test_preview_truncates_to_limit():
    long_cell = "회복 조깅 아주 긴 설명 " + "가" * 40
    row = f"| 6/10 | 수 | 평일 | {long_cell} | 40분 |"
    assert len(app._session_preview(row)) <= 30


def test_preview_empty_input():
    assert app._session_preview("") == ""
    assert app._session_preview(None) == ""


# ── BUG-13: _recovery_level ──────────────────────────────────────────────────

def test_recovery_mentioned_emoji_does_not_override_verdict():
    """추론에 🔴 을 '언급만' 하고 verdict 는 🟡 이면 medium 이어야 한다."""
    review = (
        "## 훈련 리뷰\n"
        "통증 없음 → 🔴 위험은 배제된다.\n"
        "종합적으로 양호하다.\n"
        "회복 필요도: 🟡 보통"
    )
    assert app._recovery_level(review) == "medium"
    assert "rc-badge-medium" in app._recovery_badge_html(review)
    assert "rc-badge-high" not in app._recovery_badge_html(review)


def test_recovery_verdict_high():
    assert app._recovery_level("회복 필요도: 🔴 회복 필요") == "high"


def test_recovery_verdict_low():
    assert app._recovery_level("회복 필요도: 🟢 양호") == "low"


def test_recovery_label_with_spacing_variants():
    """'회복 필요도' 와 이모지 사이 공백/구두점이 있어도 verdict 를 잡는다."""
    assert app._recovery_level("회복 필요도 : 🟢 양호") == "low"
    assert app._recovery_level("회복필요도: 🟡") == "medium"


def test_recovery_fallback_first_emoji_when_no_label():
    """라벨이 없으면 첫 등장 이모지로 폴백."""
    assert app._recovery_level("오늘은 🟢 컨디션이 좋았다") == "low"


def test_recovery_empty_and_none():
    assert app._recovery_level("") == ""
    assert app._recovery_level(None) == ""
    assert app._recovery_badge_html("리뷰에 이모지 없음") == ""
