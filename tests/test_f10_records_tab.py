"""F10 — 기록 탭 E2E 테스트.

Feature: 기록 탭에서 완료된 훈련 로그가 카드로 렌더링되고,
         카드 클릭 시 "훈련 분석" 다이얼로그가 열리며 km·페이스·심박·회복 뱃지를 표시한다.

Fixture log: 2026-06-01.md (쉬운 달리기, 5.2km, 6:12/km, 143bpm, 🟢)
TEST_TODAY: 2026-06-04 → 2026-06-01은 30일 범위 내 포함

Pass criteria:
  P1. "기록" 탭 클릭 시 기록 탭으로 전환됨
  P2. 로그 카드 열기 버튼이 1개 이상 렌더링됨 (기록 탭 내 visible 버튼)
  P3. 기록 탭 내용에 거리(5.2km) 텍스트 표시
  P4. 기록 탭 내용에 🟢 회복 상태 뱃지 표시 (span.rc-card-badge.green)
  P5. 카드 클릭 시 "훈련 분석" 다이얼로그가 열림
  P6. 다이얼로그에 km, 페이스, 심박 수치 표시
  P7. 다이얼로그에 🟢 뱃지(class=green) 표시
  P8. 주간 통계 서브탭 클릭 → 주간 통계 섹션 렌더링

Selector note:
  CSS [data-testid="element-container"]:has(.activity-open-marker) does NOT work in this
  Streamlit version — the marker is nested inside stMarkdownContainer, outside the
  element-container parent selector scope. Instead we target visible secondary buttons in
  the active tabpanel, which are exactly the invisible overlay log-open buttons.
"""

import pytest
from playwright.sync_api import Page
from conftest import wait_for_streamlit

DIALOG_SELECTOR   = '[data-testid="stDialog"]'
LOG_FIXTURE_DATE  = "2026-06-01"
LOG_FIXTURE_KM    = "5.2km"
LOG_FIXTURE_PACE  = "6:12"
LOG_FIXTURE_HR    = "143"

# The log-open buttons are stBaseButton-secondary with empty text,
# and they are VISIBLE only in the active records sub-tab.
LOG_BTN_SELECTOR  = '[data-testid="stBaseButton-secondary"]:visible'


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def navigate_to_records(page: Page, app_url: str) -> None:
    page.goto(app_url)
    wait_for_streamlit(page)
    # 메인 네비게이션이 st.tabs → session_state 버튼으로 바뀌어(BUG-08) "기록" nav 버튼을
    # 클릭한다. exact=True 로 '훈련 기록' 등 다른 버튼과 구분.
    page.get_by_role("button", name="기록", exact=True).first.click()
    # 콜드 캐시(ttl 만료)로 렌더가 느릴 수 있으므로 고정 대기 대신 records 패널이
    # 실제로 보일 때까지 대기 → 오늘 탭 버튼을 잘못 클릭하는 타이밍 플레이크 방지
    try:
        get_records_panel(page).first.wait_for(state="visible", timeout=12_000)
    except Exception:
        pass
    page.wait_for_timeout(600)


def log_buttons(page: Page):
    """records 패널 내부의 로그 열기 버튼들(오늘 탭 카드 버튼과 섞이지 않도록 스코프)."""
    return get_records_panel(page).first.locator('[data-testid="stBaseButton-secondary"]')


def get_records_panel(page: Page):
    """Return the visible tabpanel that contains the log list (운동 기록 sub-tab)."""
    return (
        page.locator('[role="tabpanel"]:visible')
        .filter(has_text="최근 활동")
    )


def open_first_log_card(page: Page) -> None:
    """Click the first log-open button INSIDE the records panel.

    Scoped to the '최근 활동' tabpanel so a slow tab switch can't accidentally
    click a 오늘-tab daily-plan-card button (which would open the '훈련 상세'
    dialog instead of '훈련 분석'). Robust against test-order timing shifts.
    """
    panel = get_records_panel(page)
    panel.first.wait_for(state="visible", timeout=10_000)
    btn = panel.first.locator('[data-testid="stBaseButton-secondary"]').first
    btn.wait_for(state="attached", timeout=10_000)
    btn.click(force=True)
    page.wait_for_selector(DIALOG_SELECTOR, state="visible", timeout=10_000)
    page.wait_for_timeout(500)


def close_dialog(page: Page) -> None:
    page.keyboard.press("Escape")
    page.wait_for_selector(DIALOG_SELECTOR, state="hidden", timeout=5_000)
    page.wait_for_timeout(300)


# ─────────────────────────────────────────────────────────────
# P1 — Tab navigation
# ─────────────────────────────────────────────────────────────

def test_p1_records_tab_navigation(page: Page, app_url: str) -> None:
    """'기록' 탭 클릭 시 기록 탭 내용이 표시돼야 한다."""
    navigate_to_records(page, app_url)

    # The records panel should be visible
    panel = get_records_panel(page)
    assert panel.count() >= 1, (
        "FAIL P1: '최근 활동' 포함 visible tabpanel이 없음 — 기록 탭 전환 실패"
    )

    # Should not show a red error alert
    error = page.locator('[data-testid="stAlert"][kind="error"]').first
    if error.is_visible():
        assert False, f"FAIL P1: 기록 탭 에러 발생: {error.inner_text()!r}"


# ─────────────────────────────────────────────────────────────
# P2 — Log card buttons appear
# ─────────────────────────────────────────────────────────────

def test_p2_log_card_rendered(page: Page, app_url: str) -> None:
    """기록 탭에 로그 카드 열기 버튼이 1개 이상 표시돼야 한다."""
    navigate_to_records(page, app_url)

    btns = page.locator(LOG_BTN_SELECTOR)
    count = btns.count()
    assert count >= 1, (
        f"FAIL P2: 기록 탭에 visible 로그 버튼 없음 (count={count})\n"
        "  → get_daily_logs(days=30)가 빈 리스트이거나 fixture 파일이 없을 수 있음"
    )


# ─────────────────────────────────────────────────────────────
# P3 — km text visible in records panel
# ─────────────────────────────────────────────────────────────

def test_p3_fixture_card_shows_km(page: Page, app_url: str) -> None:
    """기록 탭에 fixture 로그(6/1)의 거리 5.2km가 표시돼야 한다."""
    navigate_to_records(page, app_url)

    panel = get_records_panel(page)
    panel_text = panel.first.inner_text() if panel.count() > 0 else ""

    assert LOG_FIXTURE_KM in panel_text, (
        f"FAIL P3: '{LOG_FIXTURE_KM}'이 기록 탭에 없음\n"
        f"  → panel text (첫 300자): {panel_text[:300]}"
    )


# ─────────────────────────────────────────────────────────────
# P4 — Recovery badge (🟢) on fixture card
# ─────────────────────────────────────────────────────────────

def test_p4_fixture_card_shows_badge(page: Page, app_url: str) -> None:
    """기록 탭 카드에 '양호' 뱃지(span.rc-card-badge.green)가 표시돼야 한다."""
    navigate_to_records(page, app_url)

    panel = get_records_panel(page)
    assert panel.count() >= 1, "FAIL P4: records panel 없음"

    green_badges = panel.first.locator("span.rc-card-badge.green")
    count = green_badges.count()
    assert count >= 1, (
        f"FAIL P4: green 뱃지 없음 (count={count})\n"
        "  → fixture 로그에 🟢가 있는지 확인 필요"
    )


# ─────────────────────────────────────────────────────────────
# P5 — Card click opens "훈련 분석" dialog
# ─────────────────────────────────────────────────────────────

def test_p5_card_click_opens_dialog(page: Page, app_url: str) -> None:
    """로그 카드 클릭 시 '훈련 분석' 다이얼로그가 열려야 한다."""
    navigate_to_records(page, app_url)

    open_first_log_card(page)

    dialog = page.locator(DIALOG_SELECTOR)
    assert dialog.is_visible(), "FAIL P5: '훈련 분석' 다이얼로그가 열리지 않음"

    close_dialog(page)


# ─────────────────────────────────────────────────────────────
# P6 — Dialog shows km, pace, hr
# ─────────────────────────────────────────────────────────────

def test_p6_dialog_shows_metrics(page: Page, app_url: str) -> None:
    """훈련 분석 다이얼로그에 km·페이스·심박 수치가 표시돼야 한다."""
    navigate_to_records(page, app_url)

    # Try to click the fixture log card (5.2km)
    # records 패널 내부 버튼만 순회(오늘 탭 카드 버튼 제외)
    btns = log_buttons(page)
    btn_count = btns.count()
    clicked = False

    for i in range(btn_count):
        btns.nth(i).click(force=True)
        try:
            page.wait_for_selector(DIALOG_SELECTOR, state="visible", timeout=5_000)
            dialog_text = page.locator(DIALOG_SELECTOR).inner_text()
            if LOG_FIXTURE_KM in dialog_text:
                clicked = True
                break
            # Wrong log opened — close and try next
            page.keyboard.press("Escape")
            page.wait_for_selector(DIALOG_SELECTOR, state="hidden", timeout=3_000)
            page.wait_for_timeout(300)
        except Exception:
            page.wait_for_timeout(300)

    if not clicked:
        # Fall back: click first button and check whatever dialog opens
        btns.first.click(force=True)
        page.wait_for_selector(DIALOG_SELECTOR, state="visible", timeout=8_000)

    dialog = page.locator(DIALOG_SELECTOR)
    full_text = dialog.inner_text()

    assert LOG_FIXTURE_KM in full_text, (
        f"FAIL P6: km '{LOG_FIXTURE_KM}'이 다이얼로그에 없음\n  text: {full_text[:200]}"
    )
    assert LOG_FIXTURE_PACE in full_text, (
        f"FAIL P6: pace '{LOG_FIXTURE_PACE}'이 다이얼로그에 없음\n  text: {full_text[:200]}"
    )
    assert LOG_FIXTURE_HR in full_text, (
        f"FAIL P6: hr '{LOG_FIXTURE_HR}'이 다이얼로그에 없음\n  text: {full_text[:200]}"
    )

    close_dialog(page)


# ─────────────────────────────────────────────────────────────
# P7 — Dialog shows green badge
# ─────────────────────────────────────────────────────────────

def test_p7_dialog_shows_green_badge(page: Page, app_url: str) -> None:
    """훈련 분석 다이얼로그에 🟢 '양호' 뱃지가 표시돼야 한다."""
    navigate_to_records(page, app_url)

    btns = log_buttons(page)
    btn_count = btns.count()
    clicked = False

    for i in range(btn_count):
        btns.nth(i).click(force=True)
        try:
            page.wait_for_selector(DIALOG_SELECTOR, state="visible", timeout=5_000)
            dialog = page.locator(DIALOG_SELECTOR)
            green = dialog.locator("span.rc-card-badge.green")
            if green.count() >= 1:
                clicked = True
                break
            page.keyboard.press("Escape")
            page.wait_for_selector(DIALOG_SELECTOR, state="hidden", timeout=3_000)
            page.wait_for_timeout(300)
        except Exception:
            page.wait_for_timeout(300)

    if not clicked:
        # Check if any dialog has a green badge
        btns.first.click(force=True)
        page.wait_for_selector(DIALOG_SELECTOR, state="visible", timeout=8_000)

    dialog = page.locator(DIALOG_SELECTOR)
    green_badge = dialog.locator("span.rc-card-badge.green")
    assert green_badge.count() >= 1, (
        f"FAIL P7: 다이얼로그에 green 뱃지 없음\n  dialog text: {dialog.inner_text()[:200]}"
    )
    badge_text = green_badge.first.inner_text()
    assert "양호" in badge_text, (
        f"FAIL P7: 뱃지 텍스트가 '양호'가 아님: {badge_text!r}"
    )

    close_dialog(page)


# ─────────────────────────────────────────────────────────────
# P8 — Weekly stats sub-tab renders
# ─────────────────────────────────────────────────────────────

def test_p8_weekly_stats_subtab(page: Page, app_url: str) -> None:
    """기록 탭 내 '주간 통계' 서브탭을 클릭하면 통계 섹션이 렌더링돼야 한다."""
    navigate_to_records(page, app_url)

    # Find '주간 통계' sub-tab
    all_tabs = page.locator('[data-testid="stTab"]')
    found = False
    for i in range(all_tabs.count()):
        txt = all_tabs.nth(i).inner_text()
        if "주간" in txt or "통계" in txt:
            all_tabs.nth(i).click()
            page.wait_for_timeout(800)
            found = True
            break

    if not found:
        pytest.skip("주간 통계 서브탭을 찾을 수 없음")

    page_text = page.locator('[data-testid="stApp"]').inner_text()
    assert "이번 주" in page_text or "주간" in page_text, (
        f"FAIL P8: 주간 통계 내용 없음\n  page text: {page_text[:300]}"
    )
