"""G01 ANTHROPIC_API_KEY 미설정 시 경고 표시 (Playwright).

빈 키로 앱을 띄워(=dotenv override=False 가 덮어쓰지 않음) 상단 경고가 보이는지
확인한다. AI 호출 자체는 하지 않는 NO_PLAN 상태에서 검증(비용 0).

API 오류 경로(키는 있으나 호출 실패)는 test_f04_save_flow.py 의
test_save_api_error_keeps_form 에서 COACH_MOCK=__ERROR__ 로 커버.
"""

from harness import REAL_STR, running_app, scaffold, wait_ready
from playwright.sync_api import expect


def _setup_no_plan(tmp):
    scaffold(tmp)


def test_g01_missing_api_key_warning(page):
    with running_app(REAL_STR, _setup_no_plan, api_key=None) as (url, _):
        page.goto(url)
        wait_ready(page)
        expect(page.get_by_text("API 키 미설정")).to_be_visible()
