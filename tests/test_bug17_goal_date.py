"""BUG-17 회귀 단위 테스트 — 목표 날짜 편집 피커 초기값 (순수 함수, Playwright 불필요).

설정 탭 목표 날짜 행은 표시값을 점 구분("2026. 11. 1")으로 만들어 편집 다이얼로그에
넘긴다. 다이얼로그가 이를 `date.fromisoformat` 로 파싱하면 ValueError → 매번 '오늘'로
폴백해 기존 목표 날짜를 잃었다. `_parse_goal_date` 가 ISO·점 구분 모두 파싱해
기존 날짜를 보존해야 한다.
"""

import os
import sys
import tempfile
import datetime
from pathlib import Path

os.environ.setdefault("WORKSPACE_PATH", tempfile.mkdtemp(prefix="qa_bug17_"))
os.environ.setdefault("COACH_MOCK", "1")
sys.path.insert(0, str(Path(__file__).parent.parent / "webapp"))

import app  # noqa: E402

_TODAY = datetime.date(2026, 6, 9)
_GOAL = datetime.date(2026, 11, 1)


def test_dotted_display_format_parses():
    """설정 행 표시 포맷 '2026. 11. 1' → 기존 목표 날짜로 파싱(오늘 폴백 아님)."""
    assert app._parse_goal_date("2026. 11. 1", _TODAY) == _GOAL


def test_iso_format_parses():
    """ISO '2026-11-01' 도 그대로 파싱."""
    assert app._parse_goal_date("2026-11-01", _TODAY) == _GOAL


def test_compact_dotted_parses():
    """공백 없는 점 구분 '2026.11.01' 도 파싱."""
    assert app._parse_goal_date("2026.11.01", _TODAY) == _GOAL


def test_invalid_falls_back():
    """파싱 불가/빈 값 → fallback(today)."""
    assert app._parse_goal_date("", _TODAY) == _TODAY
    assert app._parse_goal_date("미설정", _TODAY) == _TODAY


def test_out_of_range_falls_back():
    """월/일이 범위를 벗어나면(13월 등) fallback."""
    assert app._parse_goal_date("2026. 13. 40", _TODAY) == _TODAY
