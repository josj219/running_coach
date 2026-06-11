"""Shared Playwright fixtures for F03 and F10 E2E tests.

Session setup:
  1. Write fixture files into the daily log dir before starting the app
  2. Launch Streamlit on port 8502 with TEST_TODAY=2026-06-04 (Thursday, W23)
  3. Yield the base URL to each test
  4. Terminate the app and remove any fixture files created here
"""

import datetime
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest
import requests

BASE_DIR   = Path(__file__).parent.parent
DAILY_DIR  = BASE_DIR / "40-training-log" / "daily"
WEEKLY_DIR = BASE_DIR / "40-training-log" / "weekly"
FIXTURES   = Path(__file__).parent / "fixtures"
APP_PORT   = 8502
APP_URL    = f"http://localhost:{APP_PORT}"

# app.py 는 today_session·plan 파일명을 **실제 OS 날짜**로 계산하므로(TEST_TODAY 는
# 요일/로그 판정에만 사용), TEST_DATE 를 하드코딩하면 OS 날짜가 그 주를 벗어난 뒤
# 오늘 세션을 못 찾아 S4(REST)로 떨어진다(과거 2026-06-04 고정 → 드리프트로 f03 깨짐).
# 따라서 OS 날짜에 맞춰 동적으로 잡고, 같은 주 주간계획을 fixture 로 생성한다.
# 일요일이면 S5(WEEK_END)라 S1 검증이 불가하므로 토요일로 당겨 잡는다.
_OS_TODAY = datetime.date.today()
if _OS_TODAY.weekday() == 6:  # Sunday
    _OS_TODAY = _OS_TODAY - datetime.timedelta(days=1)
TEST_DATE = _OS_TODAY.isoformat()
# 같은 주 월요일(오늘과 다른 날) — F10 로그 fixture 용
_MONDAY = _OS_TODAY - datetime.timedelta(days=_OS_TODAY.weekday())
LOG_DATE = (_MONDAY if _MONDAY != _OS_TODAY else _MONDAY + datetime.timedelta(days=1)).isoformat()


# ─────────────────────────────────────────────────────────────
# Fixture file management
# ─────────────────────────────────────────────────────────────

def _build_weekly_plan(today: datetime.date) -> str:
    """현재 OS 주(월~일) 모든 날을 '쉬운 달리기'로 채운 주간 계획.

    app 이 OS 날짜로 today_session 을 찾으므로, 어떤 평일에 돌려도 오늘 행이 존재해
    S1(PRE_WORKOUT)이 보장된다. 훈련 기록은 비워 S5(WEEK_END) 오판을 막는다.
    """
    monday = today - datetime.timedelta(days=today.weekday())
    wk = ["월", "화", "수", "목", "금", "토", "일"]
    rows = []
    for i in range(7):
        d = monday + datetime.timedelta(days=i)
        rows.append(f"| {d.month}/{d.day} | {wk[i]} | 평일 | 쉬운 달리기 5km | 40분 |")
    body = "\n".join(rows)
    return (
        "## 주간 훈련 계획 — 이번 주\n\n"
        "> 유산소 베이스를 다지는 주.\n"
        "달리기 거리 | 30km\n\n"
        "### 요일별 계획\n"
        "| 날짜 | 요일 | 구분 | 훈련 | 소요시간 |\n"
        "|------|------|------|------|----------|\n"
        f"{body}\n\n"
        "## 훈련 기록 (실행 후 기입)\n"
        "| 날짜 | 계획 실행 여부 | 비고 |\n"
        "|------|--------------|------|\n\n"
        "## 주간 평가 (주 종료 후 작성)\n\n_미작성_\n"
    )


@pytest.fixture(scope="session")
def fixture_files(tmp_path_factory):
    """격리된 임시 워크스페이스를 구성하고 그 경로를 yield 한다.

    과거에는 실제 워크스페이스(BASE_DIR)에 fixture 를 덮어쓰고 teardown 에 복원했는데,
    스위트가 중간에 강제종료되면 in-memory 백업이 사라져 실제 plan 파일이 소실됐다.
    이제 BASE_DIR 을 절대 건드리지 않고 temp 워크스페이스에서만 동작한다.

    구성: KB(20-knowledge-base)는 실제 파일을 복사(읽기 전용 참조), 주간 계획은 OS
    현재 주로 동적 생성(오늘 행 존재 → S1 보장), 당일 계획·완료 로그 fixture 시드.
    """
    ws = tmp_path_factory.mktemp("conftest_ws")
    (ws / "40-training-log" / "weekly").mkdir(parents=True)
    (ws / "40-training-log" / "daily").mkdir(parents=True)

    src_kb = BASE_DIR / "20-knowledge-base"
    if src_kb.is_dir():
        shutil.copytree(src_kb, ws / "20-knowledge-base")
    else:
        (ws / "20-knowledge-base").mkdir(parents=True)

    iso = datetime.date.today().isocalendar()
    (ws / "40-training-log" / "weekly" / f"{iso[0]}-W{iso[1]:02d}_plan.md").write_text(
        _build_weekly_plan(datetime.date.today()), encoding="utf-8"
    )
    shutil.copy(FIXTURES / "daily_plan_fixture.md",
                ws / "40-training-log" / "daily" / f"{TEST_DATE}_plan.md")
    shutil.copy(FIXTURES / "daily_log_fixture.md",
                ws / "40-training-log" / "daily" / f"{LOG_DATE}.md")

    yield ws

    shutil.rmtree(ws, ignore_errors=True)


# ─────────────────────────────────────────────────────────────
# App server
# ─────────────────────────────────────────────────────────────

def _kill_port(port: int) -> None:
    """Kill any process listening on the given port."""
    import signal
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True, text=True
        )
        for pid in result.stdout.strip().splitlines():
            try:
                os.kill(int(pid), signal.SIGTERM)
            except ProcessLookupError:
                pass
        time.sleep(1)
    except Exception:
        pass


@pytest.fixture(scope="session")
def app_process(fixture_files):
    """Start the Streamlit app once per session; yield the base URL."""
    _kill_port(APP_PORT)
    env = os.environ.copy()
    env["TEST_TODAY"]    = TEST_DATE
    # 실제 워크스페이스가 아닌 격리 temp 워크스페이스를 가리킨다(데이터 안전).
    env["WORKSPACE_PATH"] = str(fixture_files)
    env.setdefault("ANTHROPIC_API_KEY", "test-key-placeholder")

    proc = subprocess.Popen(
        [
            "streamlit", "run", "webapp/app.py",
            f"--server.port={APP_PORT}",
            "--server.headless=true",
            "--server.runOnSave=false",
            "--browser.gatherUsageStats=false",
        ],
        env=env,
        cwd=str(BASE_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # 전체 스위트에서 여러 전용 앱(F01/F04/F12/G01)이 함께 기동되어 부하가 커질 수
    # 있으므로 기동 대기를 60초로 둔다(부하 시 40초 초과로 인한 간헐 ERROR 방지).
    startup_timeout = 60
    deadline = time.time() + startup_timeout
    ready = False
    while time.time() < deadline:
        try:
            r = requests.get(APP_URL, timeout=2)
            if r.status_code == 200:
                ready = True
                break
        except Exception:
            pass
        time.sleep(1)

    if not ready:
        proc.terminate()
        raise RuntimeError(f"Streamlit app did not start at {APP_URL} within {startup_timeout}s")

    # Extra settle time for Streamlit WebSocket init
    time.sleep(3)
    yield APP_URL

    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="session")
def app_url(app_process):
    return app_process


# ─────────────────────────────────────────────────────────────
# Playwright browser — headed=False for CI
# ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "viewport": {"width": 390, "height": 844}}


# ─────────────────────────────────────────────────────────────
# Shared page helpers
# ─────────────────────────────────────────────────────────────

def wait_for_streamlit(page, timeout_ms: int = 15_000) -> None:
    """Block until Streamlit finishes its initial render."""
    page.wait_for_selector('[data-testid="stApp"]', timeout=timeout_ms)
    # Wait for any running spinner to disappear
    try:
        page.wait_for_selector('[data-testid="stSpinner"]', state="hidden", timeout=5_000)
    except Exception:
        pass
    page.wait_for_timeout(800)
