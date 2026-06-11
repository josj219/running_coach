"""F04 훈련 기록 저장 + AI 리뷰 → S3 전환 E2E.

S2 기록 폼 입력 → '기록 저장하기' → (COACH_MOCK 모의 리뷰) → daily log 저장 +
sync → S3(REVIEWED) 전환을 검증한다. 실 API 미호출(COACH_MOCK).

TC-F04-01(정상 저장+S3), TC-F04-02(회복 뱃지), G01b(API 오류 시 빈 화면 없음) 커버.
"""

import shutil

from harness import (
    FIXTURES,
    REAL_MD,
    REAL_STR,
    running_app,
    scaffold,
    wait_ready,
    weekly_plan,
    write_weekly,
)
from playwright.sync_api import expect

# 모의 리뷰: 🟢 회복 뱃지 + 코치 코멘트 한 줄(파싱 가능 형식)
MOCK_REVIEW = (
    "🟢 양호 — 계획 대비 충실히 수행했다.\n"
    "동일 페이스에서 평균 심박이 안정적이다. 유산소 효율이 향상되고 있다.\n"
    "다음 훈련은 케이던스 175 목표로 미세 조정 권장."
)
MOCK_REVIEW_HARD = (
    "🔴 회복 필요 — 피로 누적이 뚜렷하다.\n"
    "심박이 목표 구간을 초과했다. 다음 세션은 강도 50% 이하 회복주 권장."
)


def _setup_s1(tmp):
    """S1 진입(계획 + 오늘 워크아웃 + daily plan fixture → API 미호출).

    BUG-06 회귀 검증: 훈련 기록 표를 **비워** 둔다(실제 신규 계획과 동일).
    요일별 계획은 훈련 3세션(extra_training) → total_count=3. 오늘 1세션만 저장하면
    done=1 < total=3 → WEEK_END 가 아니라 S3 로 전환돼야 한다.
    """
    scaffold(tmp)
    write_weekly(
        tmp,
        weekly_plan("러닝 | 쉬운 달리기 6km | 40분 |", f"| {REAL_MD} |  |  |", extra_training=True),
    )
    shutil.copy(
        FIXTURES / "daily_plan_fixture.md",
        tmp / "40-training-log" / "daily" / f"{REAL_STR}_plan.md",
    )


def _go_to_form(page, url):
    page.goto(url)
    wait_ready(page)
    page.get_by_role("button", name="다녀왔어요").click()
    wait_ready(page)
    expect(page.get_by_text("수고했어요")).to_be_visible()


def test_save_transitions_to_s3(page):
    """TC-F04-01: 폼 입력 → 저장 → S3 결과 카드 + 로그 파일 생성."""
    with running_app(REAL_STR, _setup_s1, coach_mock=MOCK_REVIEW) as (url, tmp):
        _go_to_form(page, url)
        page.get_by_placeholder("6.2").fill("6.2")       # 거리
        page.get_by_placeholder("5:05").fill("5:05")     # 페이스
        page.get_by_placeholder("148").fill("148")       # 평균 심박
        page.get_by_text("😊 괜찮아요").click()
        page.get_by_role("button", name="기록 저장하기").click()
        wait_ready(page)

        # S3 전환
        expect(page.get_by_text("오늘 완료")).to_be_visible()
        expect(page.get_by_text("코치 분석")).to_be_visible()
        # km bignum 반영
        expect(page.get_by_text("6.20")).to_be_visible()

        # 파일 저장 검증
        log_path = tmp / "40-training-log" / "daily" / f"{REAL_STR}.md"
        assert log_path.exists(), "daily log 파일 미생성"
        body = log_path.read_text(encoding="utf-8")
        assert "## 훈련 리뷰" in body
        assert "## 훈련 내용" in body
        assert "거리: 6.2" in body
        # sync 다운스트림: running_history 갱신
        run_hist = tmp / "20-knowledge-base" / "03_RUNNING_HISTORY.md"
        assert run_hist.exists() and REAL_STR in run_hist.read_text(encoding="utf-8")


def test_recovery_badge_high(page):
    """TC-F04-02: 🔴 회복 필요 리뷰 → S3 회복 뱃지 표시."""
    with running_app(REAL_STR, _setup_s1, coach_mock=MOCK_REVIEW_HARD) as (url, _):
        _go_to_form(page, url)
        page.get_by_placeholder("6.2").fill("5.0")
        page.get_by_text("😰 매우 힘듦").click()
        page.get_by_role("button", name="기록 저장하기").click()
        wait_ready(page)
        expect(page.get_by_text("오늘 완료")).to_be_visible()
        # 🔴 회복 뱃지(_recovery_badge_html → span.rc-badge-high) — 클래스로 정확히 타깃
        expect(page.locator("span.rc-badge-high")).to_be_visible()


def test_save_api_error_keeps_form(page):
    """G01b/F02-F4: AI 오류 시 st.error 표시 + 빈 화면 아님(폼 유지)."""
    with running_app(REAL_STR, _setup_s1, coach_mock="__ERROR__") as (url, tmp):
        _go_to_form(page, url)
        page.get_by_placeholder("6.2").fill("6.2")
        page.get_by_text("😐 보통").click()
        page.get_by_role("button", name="기록 저장하기").click()
        wait_ready(page)
        # 에러 메시지 표시(빈 화면 없음), S3 전환 안 됨
        expect(page.get_by_text("테스트 모의 오류")).to_be_visible()
        expect(page.get_by_text("오늘 완료")).to_have_count(0)
        # 로그 파일 미생성(저장은 성공 응답에서만)
        assert not (tmp / "40-training-log" / "daily" / f"{REAL_STR}.md").exists()
