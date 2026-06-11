"""주간 성장 리포트(간결 카드 + 코치 메시지 + 접힌 상세) 파싱 단위 테스트.

`_parse_eval_report` / `_coach_msg_html` / `_eval_report_markdown` 가
대괄호 라벨 형식([코치 메시지]/[핵심 수치]/[최근 4주 추세]/[목표 진척도]/[규칙])을
올바로 분리·정리하는지 검증한다. (Image 3 기준 간결 리포트)
"""

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("WORKSPACE_PATH", tempfile.mkdtemp(prefix="qa_growth_"))
os.environ.setdefault("COACH_MOCK", "1")
sys.path.insert(0, str(Path(__file__).parent.parent / "webapp"))

import app  # noqa: E402

_SAMPLE = """[코치 메시지]
📈 템포 런 평균 페이스가 **5:12 → 5:08**로 개선됐어요.
다음 주 임계 구간 5분 연장을 권장해요.

[핵심 수치]
| 항목 | 이번 주 |
|------|---------|
| 총 러닝 거리 | 41.2 km |
| 완료 세션 | 5/6 |

[최근 4주 추세]
| 주차 | 총 거리 | 세션 | 수행률 |
|------|--------|------|--------|
| W24 | 41.2km | 5/6 | 83% |

[목표 진척도]
| 항목 | 현재 |
|------|------|
| 준비도 | 중 |

[규칙]
- 줄글 금지
"""


def test_parse_splits_coach_and_detail():
    p = app._parse_eval_report(_SAMPLE)
    assert p["coach"].startswith("📈 템포 런")
    assert "임계 구간 5분 연장" in p["coach"]
    assert "핵심 수치" in p["detail"]
    assert "최근 4주 추세" in p["detail"]
    assert "sub 3:30 목표 진척도" in p["detail"]


def test_rules_section_dropped():
    p = app._parse_eval_report(_SAMPLE)
    assert "줄글 금지" not in p["coach"]
    assert "줄글 금지" not in p["detail"]
    assert "[규칙]" not in p["detail"]


def test_coach_box_preserves_bold():
    p = app._parse_eval_report(_SAMPLE)
    html = app._coach_msg_html(p["coach"])
    assert "<strong>5:12 → 5:08</strong>" in html
    # 원본 ** 마커는 남지 않아야 한다
    assert "**" not in html


def test_detail_only_includes_present_sections():
    """일부 섹션만 있는 출력도 안전하게 처리."""
    partial = "[코치 메시지]\n📈 좋아요.\n\n[핵심 수치]\n| 항목 | 값 |\n|--|--|\n| 거리 | 5km |"
    p = app._parse_eval_report(partial)
    assert "핵심 수치" in p["detail"]
    assert "최근 4주 추세" not in p["detail"]
    assert "목표 진척도" not in p["detail"]


def test_eval_markdown_head_and_partial_badge():
    full = app._eval_report_markdown(_SAMPLE, 41.2, 5, 6, 83, 0)
    assert full.splitlines()[0] == "**총 거리 41.2km · 완료 세션 5/6 · 수행률 83%**"
    assert "## 코치 한마디" in full
    # 부분 평가(주 2일차)면 진행 중 배지가 붙는다
    partial = app._eval_report_markdown(_SAMPLE, 6.2, 1, 6, 8, 2)
    assert "주 2일차 · 진행 중" in partial.splitlines()[0]


def test_empty_input():
    p = app._parse_eval_report("")
    assert p == {"coach": "", "detail": ""}
    assert app._parse_eval_report(None) == {"coach": "", "detail": ""}


def test_zero_total_sessions_card_markdown():
    """완료 세션 분모가 0이면 '—' 로 표기(나누기 방어는 호출부)."""
    md = app._eval_report_markdown("[코치 메시지]\n📈 복귀 주.", 0.0, 0, 0, 0, 0)
    assert "완료 세션 0/—" in md
