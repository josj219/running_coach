"""F01 오늘 탭 State Machine E2E 테스트 (S0/S2/S3/S4/S5).

기존 conftest 세션 앱(S1, PRE_WORKOUT)이 커버하지 못하는 상태를 검증한다.
공용 기동/날짜 로직은 tests/harness.py 참고(실 API 미호출).
"""

import shutil

from harness import (
    FIXTURES,
    REAL_MD,
    REAL_STR,
    SUNDAY_STR,
    running_app,
    scaffold,
    wait_ready,
    weekly_plan,
    write_weekly,
)
from playwright.sync_api import expect


# ─────────────────────────────────────────────────────────────
# 상태별 워크스페이스 setup
# ─────────────────────────────────────────────────────────────

def setup_s0(tmp):
    """주간 계획 파일 없음 → plan_content 비어 NO_PLAN."""
    scaffold(tmp)  # weekly 디렉토리만, plan 파일은 쓰지 않음


def setup_s2(tmp):
    """계획 있음 + 오늘 워크아웃 + daily plan fixture(=API 미호출) → S1 진입용."""
    scaffold(tmp)
    write_weekly(tmp, weekly_plan("러닝 | 쉬운 달리기 6km | 40분 |", f"| {REAL_MD} |  |  |"))
    shutil.copy(
        FIXTURES / "daily_plan_fixture.md",
        tmp / "40-training-log" / "daily" / f"{REAL_STR}_plan.md",
    )


def setup_s3(tmp):
    """오늘 log 에 '## 훈련 리뷰' 존재 → REVIEWED (완료 컬럼 비움 → week_end 아님)."""
    scaffold(tmp)
    write_weekly(tmp, weekly_plan("러닝 | 쉬운 달리기 6km | 40분 |", f"| {REAL_MD} |  |  |"))
    log = f"""# 훈련 기록 — {REAL_STR}

## 훈련 내용
- 종류: 쉬운 달리기
- 수치: 거리: 6.2 / 페이스: 5:05 / 평균 심박: 148 / 케이던스: 172
- 피로도: 😊 괜찮아요 / 3/10
- 불편함: 통증 없음

## 훈련 리뷰
- 🟢 양호: 동일 페이스에서 평균 심박이 안정적이다. 유산소 효율이 향상되고 있다.
"""
    (tmp / "40-training-log" / "daily" / f"{REAL_STR}.md").write_text(log, encoding="utf-8")


def setup_s4(tmp):
    """오늘 세션이 휴식 키워드 → REST_DAY."""
    scaffold(tmp)
    write_weekly(tmp, weekly_plan("휴식 | 완전 휴식 | - |", f"| {REAL_MD} |  |  |"))


def setup_s5_sunday(tmp):
    """일요일(조건 A) → WEEK_END."""
    scaffold(tmp)
    write_weekly(tmp, weekly_plan("러닝 | 쉬운 달리기 6km | 40분 |", f"| {REAL_MD} |  |  |"))


def setup_s5_all_done(tmp):
    """전 세션 완료(조건 B: done==total>0) → 평일에도 WEEK_END.

    요일별 계획 훈련 3세션(오늘+추가 2) 전부 ✅ → done==total==3.
    """
    scaffold(tmp)
    rows = f"| {REAL_MD} | ✅ | 러닝 6km |\n| 98/1 | ✅ | 인터벌 |\n| 98/2 | ⚠️ | 롱런 |"
    write_weekly(tmp, weekly_plan("러닝 | 쉬운 달리기 6km | 40분 |", rows, extra_training=True))


# ─────────────────────────────────────────────────────────────
# 테스트 — 오늘 탭은 기본 활성 탭
# ─────────────────────────────────────────────────────────────

def test_s0_no_plan(page):
    """S0: 주간 계획 없음 → '아직 없어요' 히어로 + 계획 세우기 버튼."""
    with running_app(REAL_STR, setup_s0) as (url, _):
        page.goto(url)
        wait_ready(page)
        expect(page.get_by_text("아직 없어요")).to_be_visible()
        expect(page.get_by_role("button", name="이번 주 계획 세우기")).to_be_visible()
        expect(page.get_by_text("수고했어요")).to_have_count(0)


def test_s2_post_workout(page):
    """S2: S1 에서 '다녀왔어요' 클릭 → '수고했어요' + 기록 폼."""
    with running_app(REAL_STR, setup_s2) as (url, _):
        page.goto(url)
        wait_ready(page)
        record_btn = page.get_by_role("button", name="다녀왔어요")
        expect(record_btn).to_be_visible()
        record_btn.click()
        wait_ready(page)
        expect(page.get_by_text("수고했어요")).to_be_visible()
        expect(page.get_by_role("button", name="기록 저장하기")).to_be_visible()
        expect(page.get_by_text("거리 (km)")).to_be_visible()


def test_s3_reviewed(page):
    """S3: 오늘 log 에 '## 훈련 리뷰' → 결과 카드(완료/코치 분석)."""
    with running_app(REAL_STR, setup_s3) as (url, _):
        page.goto(url)
        wait_ready(page)
        expect(page.get_by_text("오늘 완료")).to_be_visible()
        expect(page.get_by_text("코치 분석")).to_be_visible()
        expect(page.get_by_text("전체 분석 보기")).to_be_visible()
        expect(page.get_by_role("button", name="기록 저장하기")).to_have_count(0)


def test_s4_rest_day(page):
    """S4: 오늘 세션이 휴식 키워드 → '오늘은 쉬는 날이에요' + 가볍게 뛰었어요 버튼."""
    with running_app(REAL_STR, setup_s4) as (url, _):
        page.goto(url)
        wait_ready(page)
        expect(page.get_by_text("오늘은 쉬는 날이에요")).to_be_visible()
        expect(page.get_by_role("button", name="가볍게 뛰었어요")).to_be_visible()


def test_s5_week_end_sunday(page):
    """S5(조건 A): 일요일 → '이번 주 훈련 종료' 주간 마무리 히어로."""
    with running_app(SUNDAY_STR, setup_s5_sunday) as (url, _):
        page.goto(url)
        wait_ready(page)
        expect(page.get_by_text("이번 주 훈련 종료")).to_be_visible()
        expect(page.get_by_text("주간 리포트")).to_be_visible()


def test_s5_week_end_all_done(page):
    """S5(조건 B): 평일이라도 전 세션 완료(done==total) → WEEK_END."""
    with running_app(REAL_STR, setup_s5_all_done) as (url, _):
        page.goto(url)
        wait_ready(page)
        expect(page.get_by_text("이번 주 훈련 종료")).to_be_visible()
        expect(page.get_by_text("오늘은 쉬는 날이에요")).to_have_count(0)
