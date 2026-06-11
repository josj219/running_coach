"""BUG-14 / BUG-15 회귀 단위 테스트 (순수 함수, Playwright 불필요).

- BUG-14: F06 주간 목표 진행률. `_extract_goal_km(plan)` 이 0 이면 요약 카드가
  "목표 0km" + 0% 링으로 무의미해진다. 설정 `weekly_goal_km` 로 폴백해야 한다.
- BUG-15: `_parse_weekly_rows` 의 `_clean` 이 단일 `~`(범위 구분자)까지 지워
  "70~80분" → "7080분" 으로 깨지면 안 된다. 취소선 `~~` 만 제거해야 한다.

app.py 는 import 시 streamlit 스크립트를 끝까지 실행하므로, 빈 임시 워크스페이스
(=계획 없음 → S0, AI 미호출) + COACH_MOCK 로 부작용·실 API 호출을 막는다.
"""

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("WORKSPACE_PATH", tempfile.mkdtemp(prefix="qa_bug1415_"))
os.environ.setdefault("COACH_MOCK", "1")
sys.path.insert(0, str(Path(__file__).parent.parent / "webapp"))

import app  # noqa: E402
from utils import file_manager as fm  # noqa: E402


# ── BUG-15: _parse_weekly_rows / _clean ─────────────────────────────────────

_PLAN = """## 요일별 계획
| 날짜 | 요일 | 구분 | 훈련 | 소요시간 |
|---|---|---|---|---|
| 6/13 | 토 | 주말 | 롱런 | 70~80분 |
| 6/12 | 금 | 평일 | ~~취소된 세션~~ 인터벌 | 50분 |
| 6/11 | 목 | 평일 | 템포 6:20~6:40/km | 40분 |
"""


def test_range_separator_preserved_in_duration():
    """단일 ~ 범위 구분자가 보존되어 '70~80분' 이 붙지 않는다."""
    rows = {r["날짜"]: r for r in app._parse_weekly_rows(_PLAN)}
    assert rows["6/13"]["소요시간"] == "70~80분"
    assert "7080" not in rows["6/13"]["소요시간"]


def test_range_separator_preserved_in_pace():
    rows = {r["날짜"]: r for r in app._parse_weekly_rows(_PLAN)}
    assert rows["6/11"]["훈련"] == "템포 6:20~6:40/km"


def test_strikethrough_removed():
    """취소선 ~~ 는 그대로 제거된다(범위 ~ 보존과 양립)."""
    rows = {r["날짜"]: r for r in app._parse_weekly_rows(_PLAN)}
    assert rows["6/12"]["훈련"] == "취소된 세션 인터벌"
    assert "~~" not in rows["6/12"]["훈련"]


# ── BUG-14: 목표 거리 폴백 ───────────────────────────────────────────────────

def test_extract_goal_km_with_phrase():
    assert app._extract_goal_km("달리기 거리 | 28km") == 28.0


def test_extract_goal_km_missing_returns_zero():
    """문구가 없으면 _extract_goal_km 자체는 0 — 폴백은 호출부 책임."""
    assert app._extract_goal_km("재생성 계획, 달리기 거리 문구 없음") == 0.0
    assert app._extract_goal_km("") == 0.0


def test_goal_km_falls_back_to_settings(tmp_path, monkeypatch):
    """_extract_goal_km 이 0 일 때 설정 weekly_goal_km 로 폴백하는 로직."""
    import json
    monkeypatch.setenv("WORKSPACE_PATH", str(tmp_path))
    kb = tmp_path / "20-knowledge-base"
    kb.mkdir()
    (kb / "app_settings.json").write_text(json.dumps({"weekly_goal_km": 50}), encoding="utf-8")
    goal_km = app._extract_goal_km("달리기 거리 문구 없음")
    if goal_km <= 0:
        goal_km = float(fm.read_settings().get("weekly_goal_km", 0) or 0)
    assert goal_km == 50.0


def test_goal_km_fallback_zero_when_unset(tmp_path, monkeypatch):
    """설정 weekly_goal_km 이 0/누락이면 폴백도 0 (크래시 없음)."""
    import json
    monkeypatch.setenv("WORKSPACE_PATH", str(tmp_path))
    kb = tmp_path / "20-knowledge-base"
    kb.mkdir()
    (kb / "app_settings.json").write_text(json.dumps({"weekly_goal_km": 0}), encoding="utf-8")
    goal_km = 0.0
    if goal_km <= 0:
        goal_km = float(fm.read_settings().get("weekly_goal_km", 0) or 0)
    assert goal_km == 0.0
