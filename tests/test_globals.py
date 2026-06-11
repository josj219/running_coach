"""글로벌 실패 시나리오 G02~G06 단위 검증 (Playwright 불필요, 순수 함수).

G01(키 미설정 UI)은 test_g01_api_key.py(Playwright), G01b(API 오류)는
test_f04_save_flow.py::test_save_api_error_keeps_form 에서 커버.
"""

import datetime
import inspect
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "webapp"))
os.environ.setdefault("WORKSPACE_PATH", tempfile.mkdtemp(prefix="qa_glob_"))

from utils import file_manager as fm  # noqa: E402
from utils import sync  # noqa: E402


# ── G02: 저장 함수가 캐시를 무효화하는가 (코드 분석 자동 가드) ──────────────

def test_g02_save_functions_clear_cache():
    for fn in (
        fm.save_weekly_plan,
        fm.save_weekly_evaluation,
        fm.save_daily_log,
        fm.save_daily_plan,
        fm.update_profile_field,
        fm.update_goal_field,
        fm.save_settings,
    ):
        src = inspect.getsource(fn)
        assert "cache_data.clear" in src, f"{fn.__name__} 가 캐시를 비우지 않음 (G02)"


# ── G04: 주차 경계(일→월) 파일명 계산 ──────────────────────────────────────

def test_g04_week_boundary_filename():
    # 일요일과 그 다음 월요일은 서로 다른 ISO 주차로 떨어져야 함
    assert fm.current_week_filename(datetime.date(2026, 6, 7)) == "2026-W23_plan.md"  # 일
    assert fm.current_week_filename(datetime.date(2026, 6, 8)) == "2026-W24_plan.md"  # 월
    # 평가 파일도 동일 규칙
    assert fm.current_week_eval_filename(datetime.date(2026, 6, 8)) == "2026-W24_evaluation.md"


# ── G05: plan_content 없음/None 시 파싱 안전 ──────────────────────────────

def test_g05_empty_plan_parsing():
    assert fm.extract_today_session("") == ""
    assert fm.extract_today_session("", datetime.date(2026, 6, 8)) == ""
    assert fm.count_sessions("") == (0, 0)
    assert fm.count_sessions(None) == (0, 0)
    assert fm.parse_km("") == 0.0


# ── G06: AI 응답 형식 미준수(섹션 누락) 시에도 예외 없이 기본값 ─────────────

def test_g06_malformed_log_parsing():
    parsed = sync._parse_daily_log("# 제목만 있고 섹션 없음\n아무 내용", "", datetime.date(2026, 6, 8))
    assert parsed["recovery_level"] == ""
    assert parsed["distance_km"] == 0.0
    assert parsed["has_pain"] is False
    # 거리 토큰이 없으면 0.0 (잘못된 수치 형식 방어)
    assert fm.parse_km("페이스 5:00 만 있고 거리는 없음") == 0.0
    # 빈 daily log → sync_after_save 가 조용히 반환(예외 없음)
    sync.sync_after_save("2026-06-08")  # 해당 날짜 로그 없음 → early return


# ── G03: 파일 권한 오류(OSError) 시 크래시 없이 처리 ───────────────────────

@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root 는 권한 제한을 무시하므로 재현 불가",
)
def test_g03_readonly_kb_no_crash(tmp_path, monkeypatch):
    kb = tmp_path / "20-knowledge-base"
    kb.mkdir()
    monkeypatch.setenv("WORKSPACE_PATH", str(tmp_path))
    os.chmod(kb, 0o500)  # 읽기/실행만 — 파일 생성 불가
    try:
        # _write_kb 는 OSError 를 잡아 경고만 내고 예외를 전파하지 않아야 함
        sync._write_kb("current_status", "테스트 내용")
    finally:
        os.chmod(kb, 0o700)
    # 여기 도달하면(예외 없음) 통과. 읽기 전용이라 파일은 생기지 않았어야 함
    assert not (kb / "04_CURRENT_STATUS.md").exists()
