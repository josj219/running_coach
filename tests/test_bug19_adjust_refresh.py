"""BUG-19 회귀 E2E — 당일 조정 계획 저장 후 화면 즉시 갱신.

S1 에서 기존 당일 계획(Easy Run · '✦ AI 설계')이 있는 상태에서
'계획 조정이 필요해요' → '조정 계획 받기 →' 제출 시, **수동 새로고침 없이**
같은 rerun 에서 히어로가 '✦ 조정됨' 으로 바뀌어야 한다(회복 루틴 반영).

조정 저장은 COACH_MOCK(실 API 미호출) 응답을 쓰며, 앱이 `_ADJUSTED_MARKER` 를
첫 줄에 붙여 저장한다. read_daily_plan 캐시 staleness 로 직전 계획이 남던 BUG-19 방지.
"""

from harness import (
    REAL_STR,
    running_app,
    scaffold,
    wait_ready,
    weekly_plan,
    write_profile,
    write_weekly,
)
from playwright.sync_api import expect

# 조정 응답(회복 루틴) — 앱이 run_coach 결과로 받는 mock. 카드 파싱 가능한 형식.
_MOCK_ADJUSTED = """[워밍업]
걷기 5분 + 가벼운 가동성 스트레칭
[메인]
회복 루틴 — 폼롤러 + 정적 스트레칭 20분 (러닝 대체)
[쿨다운]
심호흡 + 종아리/햄스트링 스트레칭 5분
[메모]
통증으로 인해 러닝을 회복 루틴으로 교체.
[상세]
## 워밍업
걷기 5분
## 메인
폼롤러 10분 + 정적 스트레칭 10분
## 쿨다운
심호흡 + 스트레칭 5분
"""

# 초기(조정 전) 당일 계획 — 마커 없음 → '✦ AI 설계'
_INITIAL_PLAN = """[워밍업]
걷기 5분 + 다이내믹 스트레칭
[메인]
쉬운 달리기 5km @ 6:30/km
[쿨다운]
걷기 5분 + 정적 스트레칭
[상세]
## 워밍업
걷기 5분
## 메인
쉬운 달리기 5km
## 쿨다운
걷기 5분
"""


def _setup(tmp):
    scaffold(tmp)
    # 오늘 세션 = 쉬운 달리기 → S1(PRE_WORKOUT)
    write_weekly(tmp, weekly_plan("러닝 | 쉬운 달리기 5km | 40분 |", ""))
    write_profile(tmp, nickname="고고조")
    # 기존 당일 계획(마커 없음) → 자동 생성 경로 미진입, '✦ AI 설계' 표시
    (tmp / "40-training-log" / "daily" / f"{REAL_STR}_plan.md").write_text(
        _INITIAL_PLAN, encoding="utf-8"
    )


def test_adjustment_updates_hero_without_reload(page):
    """조정 제출 후 reload 없이 히어로가 '✦ 조정됨' 으로 갱신된다."""
    with running_app(REAL_STR, _setup, coach_mock=_MOCK_ADJUSTED) as (url, _):
        page.goto(url)
        wait_ready(page)

        # 초기: 조정 전이므로 '✦ AI 설계' 뱃지
        expect(page.get_by_text("✦ AI 설계")).to_be_visible()
        expect(page.get_by_text("✦ 조정됨")).to_have_count(0)

        # 조정 폼 열기 → 제출
        page.get_by_role("button", name="계획 조정이 필요해요").click()
        wait_ready(page)
        page.get_by_role("button", name="조정 계획 받기").click()
        wait_ready(page)

        # reload 없이 즉시 '✦ 조정됨' 으로 갱신(히어로 + 상세 뱃지 2곳) + 직전 'AI 설계' 사라짐
        expect(page.get_by_text("✦ 조정됨").first).to_be_visible()
        expect(page.get_by_text("✦ 조정됨")).to_have_count(2)
        expect(page.get_by_text("✦ AI 설계")).to_have_count(0)
