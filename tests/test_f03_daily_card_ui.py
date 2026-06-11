"""F03 — 오늘 훈련 카드 UI E2E 테스트.

Feature: 오늘 탭 S1(PRE_WORKOUT) 상태에서 워밍업/메인/쿨다운 카드가 렌더링되고,
         각 카드 클릭 시 해당 섹션 상세 팝업(훈련 상세 다이얼로그)이 열린다.

TEST_TODAY=2026-06-04 (목) — PRE_WORKOUT state 조건:
  - W23 주간 계획 존재
  - 2026-06-04_plan.md 존재 (fixture)
  - 2026-06-04.md 없음 (오늘 로그 없음)
  - 일요일 아님 → WEEK_END 미진입

Pass criteria:
  P1. Streamlit 헤더(stHeader)가 CSS display:none으로 숨겨짐
  P2. 워밍업/메인 세트/쿨다운 3개 카드가 모두 표시됨
  P3. 각 카드 내용이 1줄(38자) 기준으로 truncated
  P4. 각 카드 클릭 시 "훈련 상세" 다이얼로그가 열림
  P5. 다이얼로그에 해당 섹션 제목(h4)이 표시됨
  P6. 다이얼로그 내용에 마크다운 artifact(--- / 고립 #)가 없음
"""

import pytest
from playwright.sync_api import Page, expect
from conftest import wait_for_streamlit


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

SECTION_LABELS = ["워밍업", "메인 세트", "쿨다운"]
DIALOG_SELECTOR = '[data-testid="stDialog"]'
HEADER_SELECTOR = 'header[data-testid="stHeader"]'


def navigate_to_home(page: Page, app_url: str) -> None:
    page.goto(app_url)
    wait_for_streamlit(page)
    # 메인 네비게이션이 st.tabs → session_state 버튼으로 바뀌어(BUG-08) "오늘" nav 버튼을
    # 클릭한다(기본 활성 탭이지만 명시적으로 보장). exact=True 로 다른 버튼과 구분.
    btn = page.get_by_role("button", name="오늘", exact=True)
    if btn.count() > 0:
        btn.first.click()
        page.wait_for_timeout(600)


def open_section_dialog(page: Page, nth: int) -> None:
    """Click the nth '열기' button (force=True to bypass CSS opacity:0)."""
    btn = page.get_by_role("button", name="열기").nth(nth)
    btn.wait_for(state="attached", timeout=10_000)
    btn.click(force=True)
    page.wait_for_selector(DIALOG_SELECTOR, state="visible", timeout=8_000)
    page.wait_for_timeout(400)


def close_dialog(page: Page) -> None:
    """Close the open dialog by pressing Escape."""
    page.keyboard.press("Escape")
    page.wait_for_selector(DIALOG_SELECTOR, state="hidden", timeout=5_000)
    page.wait_for_timeout(300)


# ─────────────────────────────────────────────────────────────
# P1 — Header hidden
# ─────────────────────────────────────────────────────────────

def test_p1_header_hidden(page: Page, app_url: str) -> None:
    """Streamlit 상단 헤더가 CSS로 숨겨져야 한다."""
    navigate_to_home(page, app_url)
    header = page.locator(HEADER_SELECTOR)
    # The header element must have display: none (set by app CSS)
    display = header.evaluate("el => getComputedStyle(el).display")
    assert display == "none", f"FAIL P1: header display={display!r}, expected 'none'"


# ─────────────────────────────────────────────────────────────
# P2 — 3 cards rendered with correct section labels
# ─────────────────────────────────────────────────────────────

def test_p2_three_cards_visible(page: Page, app_url: str) -> None:
    """워밍업/메인 세트/쿨다운 카드 3개가 모두 렌더링돼야 한다."""
    navigate_to_home(page, app_url)

    section_detail = page.locator("div.rc-detail-key")
    count = section_detail.count()
    assert count >= 3, (
        f"FAIL P2: rc-detail-key count={count}, expected ≥3\n"
        "  → 오늘 탭이 S1(PRE_WORKOUT) 상태가 아니거나 plan fixture 파일이 없을 수 있음"
    )

    labels_found = [section_detail.nth(i).inner_text() for i in range(count)]
    for expected_label in SECTION_LABELS:
        assert expected_label in labels_found, (
            f"FAIL P2: '{expected_label}' 카드가 없음. 발견된 라벨: {labels_found}"
        )


# ─────────────────────────────────────────────────────────────
# P3 — Card summary is 1-line (≤38 chars visible)
# ─────────────────────────────────────────────────────────────

def test_p3_card_summary_truncated(page: Page, app_url: str) -> None:
    """카드 내 요약 텍스트가 38자 이내이거나 '…'으로 잘려야 한다."""
    navigate_to_home(page, app_url)

    val_els = page.locator("div.rc-detail-val")
    count = val_els.count()
    assert count >= 3, f"FAIL P3: rc-detail-val count={count}, expected ≥3"

    for i in range(min(count, 3)):
        text = val_els.nth(i).inner_text().strip()
        # Either fits in 38 chars, or ends with ellipsis character
        assert len(text) <= 38 or text.endswith("…"), (
            f"FAIL P3: card[{i}] text length={len(text)} without truncation: {text!r}"
        )


# ─────────────────────────────────────────────────────────────
# P4 — Clicking each card opens "훈련 상세" dialog
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("nth,section", [(0, "워밍업"), (1, "메인 세트"), (2, "쿨다운")])
def test_p4_card_click_opens_dialog(page: Page, app_url: str, nth: int, section: str) -> None:
    """카드 클릭 시 '훈련 상세' 다이얼로그가 열려야 한다."""
    navigate_to_home(page, app_url)

    open_section_dialog(page, nth)

    dialog = page.locator(DIALOG_SELECTOR)
    assert dialog.is_visible(), f"FAIL P4: 다이얼로그가 열리지 않음 (section={section})"

    close_dialog(page)


# ─────────────────────────────────────────────────────────────
# P5 — Dialog shows correct h4 section title
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("nth,section", [(0, "워밍업"), (1, "메인 세트"), (2, "쿨다운")])
def test_p5_dialog_shows_section_title(page: Page, app_url: str, nth: int, section: str) -> None:
    """다이얼로그 내에 섹션 제목 h4가 표시돼야 한다."""
    navigate_to_home(page, app_url)

    open_section_dialog(page, nth)

    dialog = page.locator(DIALOG_SELECTOR)
    h4 = dialog.locator("h4")
    assert h4.count() > 0, f"FAIL P5: 다이얼로그에 h4 요소 없음 (section={section})"
    title_text = h4.first.inner_text().strip()
    assert section in title_text, (
        f"FAIL P5: h4 text={title_text!r}에 '{section}'이 없음"
    )

    close_dialog(page)


# ─────────────────────────────────────────────────────────────
# P6 — No stray markdown artifacts in dialog content
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("nth,section", [(0, "워밍업"), (1, "메인 세트"), (2, "쿨다운")])
def test_p6_dialog_no_markdown_artifacts(page: Page, app_url: str, nth: int, section: str) -> None:
    """다이얼로그 내용에 '---' 구분선 또는 고립 '#' 아티팩트가 없어야 한다."""
    navigate_to_home(page, app_url)

    open_section_dialog(page, nth)

    dialog = page.locator(DIALOG_SELECTOR)
    full_text = dialog.inner_text()

    assert "---" not in full_text, (
        f"FAIL P6: 다이얼로그에 '---' 아티팩트 발견 (section={section})"
    )
    # Raw lone '#' at start of a word (not inside content)
    lines_starting_with_hash = [
        ln for ln in full_text.splitlines()
        if ln.strip().startswith("#") and len(ln.strip()) <= 3
    ]
    assert not lines_starting_with_hash, (
        f"FAIL P6: 고립 '#' 아티팩트 발견: {lines_starting_with_hash} (section={section})"
    )

    close_dialog(page)
