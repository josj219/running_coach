"""F12 설정 변경 → 계획 갱신 다이얼로그 E2E.

설정 탭에서 훈련계획에 영향 있는 프로필 필드(체중 등) 편집 저장 → _settings_changed
플래그 → 재렌더 시 '계획 갱신' 다이얼로그 자동 오픈. '나중에' → 플래그 삭제(재오픈
없음). '지금 반영하기' → (COACH_MOCK 모의 계획) 재생성·저장 + 플래그 삭제.

TC-F12-01(자동 오픈), TC-F12-02(지금 반영), TC-F12-03(나중에) 커버. 실 API 미호출.

추가: BUG-09 회귀 — 닉네임은 훈련계획 무관 필드이므로 편집해도 계획 갱신 다이얼로그가
뜨지 않아야 한다(test_nickname_does_not_trigger_refresh).
"""

from harness import (
    REAL_MD,
    REAL_STR,
    open_tab,
    running_app,
    scaffold,
    wait_ready,
    weekly_plan,
    write_profile,
    write_weekly,
)
from playwright.sync_api import expect

MOCK_PLAN = weekly_plan("러닝 | 쉬운 달리기 7km | 45분 |", f"| {REAL_MD} | 예정 | 러닝 |")


def _setup(tmp):
    """계획 + 프로필 존재(프로필 편집 대상)."""
    scaffold(tmp)
    write_weekly(tmp, weekly_plan("러닝 | 쉬운 달리기 6km | 40분 |", f"| {REAL_MD} | 예정 | 러닝 |"))
    write_profile(tmp, nickname="고고조")


def _edit_profile_field(page, st_key, new_val):
    """설정 탭 → 지정한 프로필 행(st-key-<st_key>) 편집 버튼 클릭 → 다이얼로그 저장."""
    open_tab(page, "설정")
    # _cfg_profile_row 의 빈 라벨 버튼은 st-key-<st_key> 컨테이너 안에 있다.
    page.locator(f".st-key-{st_key} button").click()
    wait_ready(page)
    expect(page.get_by_text("프로필 편집")).to_be_visible()
    # 다이얼로그 내 텍스트 입력
    page.get_by_role("textbox").last.fill(new_val)
    page.get_by_role("button", name="저장").click()
    wait_ready(page)


def test_dialog_auto_opens_after_edit(page):
    """TC-F12-01: 훈련계획 영향 필드(체중) 편집 저장 → '계획 갱신' 다이얼로그 자동 오픈."""
    with running_app(REAL_STR, _setup) as (url, _):
        page.goto(url)
        wait_ready(page)
        _edit_profile_field(page, "pf_wt", "72kg")
        expect(page.get_by_text("프로필 또는 목표 정보가 변경됐어요")).to_be_visible()
        expect(page.get_by_role("button", name="지금 반영하기")).to_be_visible()
        expect(page.get_by_role("button", name="나중에")).to_be_visible()


def test_later_clears_flag(page):
    """TC-F12-03: '나중에' → 다이얼로그 닫힘 + 설정 재진입 시 재오픈 없음."""
    with running_app(REAL_STR, _setup) as (url, _):
        page.goto(url)
        wait_ready(page)
        _edit_profile_field(page, "pf_wt", "72kg")
        expect(page.get_by_text("프로필 또는 목표 정보가 변경됐어요")).to_be_visible()
        page.get_by_role("button", name="나중에").click()
        wait_ready(page)
        # 다이얼로그 닫힘
        expect(page.get_by_text("프로필 또는 목표 정보가 변경됐어요")).to_have_count(0)
        # 다른 탭 갔다가 설정 재진입 → 다이얼로그 재오픈 없음(플래그 삭제 확인)
        open_tab(page, "오늘")
        open_tab(page, "설정")
        expect(page.get_by_text("프로필 또는 목표 정보가 변경됐어요")).to_have_count(0)


def test_apply_now_regenerates_plan(page):
    """TC-F12-02: '지금 반영하기' → (mock) 재생성·저장 + 성공 메시지."""
    with running_app(REAL_STR, _setup, coach_mock=MOCK_PLAN) as (url, tmp):
        page.goto(url)
        wait_ready(page)
        _edit_profile_field(page, "pf_wt", "72kg")
        expect(page.get_by_text("프로필 또는 목표 정보가 변경됐어요")).to_be_visible()
        page.get_by_role("button", name="지금 반영하기").click()
        wait_ready(page)
        # st.success 후 즉시 st.rerun 되므로 메시지는 일시적 → 결과(저장 파일)로 검증.
        # 다이얼로그 닫힘 확인
        expect(page.get_by_text("프로필 또는 목표 정보가 변경됐어요")).to_have_count(0)
        # 저장된 계획에 모의 내용(7km) 반영 + 필수 섹션 auto-append
        from harness import real_week_plan_name
        plan_path = tmp / "40-training-log" / "weekly" / real_week_plan_name()
        body = plan_path.read_text(encoding="utf-8")
        assert "쉬운 달리기 7km" in body, "재생성 계획 미반영"
        assert "## 훈련 기록" in body and "## 주간 평가" in body


def test_nickname_does_not_trigger_refresh(page):
    """BUG-09 회귀: 닉네임 편집 저장은 '계획 갱신' 다이얼로그를 띄우지 않는다.

    닉네임은 훈련계획과 무관한 표시용 필드이므로 _settings_changed 를 설정하지 않아야
    하고, 따라서 실 API 재생성/덮어쓰기로 이어지는 다이얼로그가 뜨면 안 된다.
    """
    with running_app(REAL_STR, _setup) as (url, _):
        page.goto(url)
        wait_ready(page)
        _edit_profile_field(page, "pf_nick", "고고조2")
        # 닉네임 저장 직후 재렌더돼도 계획 갱신 다이얼로그가 없어야 함
        expect(page.get_by_text("프로필 또는 목표 정보가 변경됐어요")).to_have_count(0)
        # 닉네임은 실제로 반영돼야 한다(설정 탭 재진입 시 표시)
        open_tab(page, "오늘")
        open_tab(page, "설정")
        expect(page.get_by_text("고고조2").first).to_be_visible()
