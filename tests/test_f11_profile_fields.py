"""F11 단위 테스트 — Profile.md 필드 파싱/저장 (BUG-05 회귀 방지).

parse_profile_fields() / update_profile_field() 의 정규식이
빈 필드일 때 다음 줄(섹션 헤더·다른 필드)을 흡수/덮어쓰지 않는지 검증한다.

Playwright/브라우저 불필요 — file_manager 순수 함수 + 임시 워크스페이스 파일 I/O.
"""

import os
import sys
from pathlib import Path

import pytest

# webapp 디렉토리를 import path에 추가
WEBAPP = Path(__file__).parent.parent / "webapp"
sys.path.insert(0, str(WEBAPP))

from utils import file_manager as fm  # noqa: E402


# 빈 필드(체중)와 그 뒤에 섹션 헤더가 오는 프로필 — BUG-05 재현 형태
PROFILE_WITH_EMPTY = """# 프로필

- 닉네임: 고고조
- 나이: 38
- 키: 175cm
- 체중:

## 개인 최고 기록
- 10km · 42분 13초 2025년 3월
- 21km · 1시간 38분
- 풀 마라톤 · 미입력
"""


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """임시 워크스페이스에 01_PROFILE.md 작성 후 WORKSPACE_PATH 지정."""
    kb = tmp_path / "20-knowledge-base"
    kb.mkdir()
    profile = kb / "01_PROFILE.md"
    profile.write_text(PROFILE_WITH_EMPTY, encoding="utf-8")
    monkeypatch.setenv("WORKSPACE_PATH", str(tmp_path))
    return profile


# ─────────────────────────────────────────────────────────────
# 1. 빈 필드는 빈 문자열로 파싱
# ─────────────────────────────────────────────────────────────

def test_empty_field_parses_as_empty_string():
    fields = fm.parse_profile_fields(PROFILE_WITH_EMPTY)
    assert fields["weight"] == "", f"빈 체중 필드가 {fields['weight']!r} 로 파싱됨"


# ─────────────────────────────────────────────────────────────
# 2. 빈 필드가 다음 줄 섹션 헤더를 흡수하면 안 됨
# ─────────────────────────────────────────────────────────────

def test_empty_field_does_not_capture_next_line():
    fields = fm.parse_profile_fields(PROFILE_WITH_EMPTY)
    assert "## 개인 최고 기록" not in fields["weight"]
    assert "#" not in fields["weight"]
    # 다른 필드는 정상 파싱 (회귀 확인)
    assert fields["nickname"] == "고고조"
    assert fields["age"] == "38"
    assert fields["height"] == "175cm"
    assert "42분 13초" in fields["pb_10k"]
    assert "1시간 38분" in fields["pb_half"]


# ─────────────────────────────────────────────────────────────
# 3. 빈 필드에 값 저장 시 다음 섹션 헤더가 삭제되면 안 됨
# ─────────────────────────────────────────────────────────────

def test_update_empty_field_preserves_next_section(workspace):
    fm.update_profile_field("weight", "72kg")
    text = workspace.read_text(encoding="utf-8")

    # 다음 섹션 헤더와 PB 줄 보존
    assert "## 개인 최고 기록" in text, "체중 갱신이 섹션 헤더를 삭제함"
    assert "42분 13초" in text
    # 체중 값이 같은 줄에 기입됐는지
    fields = fm.parse_profile_fields(text)
    assert fields["weight"] == "72kg", f"체중={fields['weight']!r}"
    # 다른 필드 무손상
    assert fields["nickname"] == "고고조"
    assert fields["age"] == "38"


# ─────────────────────────────────────────────────────────────
# 4. 기존 값 있는 필드 업데이트는 정상 동작
# ─────────────────────────────────────────────────────────────

def test_update_existing_field(workspace):
    fm.update_profile_field("nickname", "고고조2")
    fm.update_profile_field("pb_10k", "41분 30초")
    text = workspace.read_text(encoding="utf-8")
    fields = fm.parse_profile_fields(text)

    assert fields["nickname"] == "고고조2"
    assert "41분 30초" in fields["pb_10k"]
    # 갱신이 다른 필드를 건드리지 않음
    assert fields["age"] == "38"
    assert fields["height"] == "175cm"
    # 줄 수 유지 (행 흡수/삭제 없음)
    assert text.count("## 개인 최고 기록") == 1


# ─────────────────────────────────────────────────────────────
# 5. 백슬래시 포함 닉네임 저장 회귀 — 예외 없이 값 보존
# ─────────────────────────────────────────────────────────────

def test_backslash_nickname_roundtrip(workspace):
    weird = r"test\1name"
    # 예외 없이 저장돼야 함
    fm.update_profile_field("nickname", weird)
    text = workspace.read_text(encoding="utf-8")
    fields = fm.parse_profile_fields(text)
    # lambda 치환이므로 백슬래시/그룹참조 해석 없이 그대로 저장
    assert fields["nickname"] == weird, f"닉네임={fields['nickname']!r}"
    # 다른 필드·섹션 무손상
    assert "## 개인 최고 기록" in text
    assert fields["age"] == "38"
