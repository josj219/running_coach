"""F01/F04/F12/Globals E2E 공용 하네스.

상태마다 격리된 임시 워크스페이스(WORKSPACE_PATH) + TEST_TODAY 로 전용 Streamlit
앱(포트 8503)을 띄운다. 실 API 는 COACH_MOCK 환경변수로 우회한다(비용 0).

날짜 주의: app.py 는 plan 파일명·today_session 을 실제 OS 날짜로 계산하고
(get_current_week_plan()/extract_today_session(plan_content) 인자 미전달),
today_log·요일 판정만 TEST_TODAY 를 따른다. 그래서 평일 상태는 TEST_TODAY 를 실제
날짜에 맞추고, S5(일요일)는 실제 '이번 주'의 일요일을 TEST_TODAY 로 쓴다.

이 파일은 test_*.py 가 아니므로 pytest 가 테스트로 수집하지 않는다(import 전용).
"""

import datetime
import os
import shutil
import signal
import subprocess
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

import requests

BASE_DIR = Path(__file__).parent.parent
FIXTURES = Path(__file__).parent / "fixtures"
APP_PORT = 8503
APP_URL = f"http://localhost:{APP_PORT}"

REAL_TODAY = datetime.date.today()
REAL_STR = REAL_TODAY.isoformat()
REAL_MD = f"{REAL_TODAY.month}/{REAL_TODAY.day}"
_MONDAY = REAL_TODAY - datetime.timedelta(days=REAL_TODAY.weekday())
SUNDAY = _MONDAY + datetime.timedelta(days=6)
SUNDAY_STR = SUNDAY.isoformat()


# ─────────────────────────────────────────────────────────────
# 워크스페이스 구성 헬퍼
# ─────────────────────────────────────────────────────────────

def scaffold(tmp: Path) -> None:
    (tmp / "20-knowledge-base").mkdir(exist_ok=True)
    (tmp / "40-training-log" / "weekly").mkdir(parents=True, exist_ok=True)
    (tmp / "40-training-log" / "daily").mkdir(parents=True, exist_ok=True)


def real_week_plan_name() -> str:
    """앱이 실제로 읽는 plan 파일명(실제 OS 날짜의 ISO 주차)."""
    iso = datetime.date.today().isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}_plan.md"


def write_weekly(tmp: Path, content: str) -> None:
    (tmp / "40-training-log" / "weekly" / real_week_plan_name()).write_text(
        content, encoding="utf-8"
    )


def weekly_plan(today_cells: str, record_rows: str, goal_km: int = 30,
                extra_training: bool = False) -> str:
    """요일별 계획 + 훈련 기록 표를 가진 주간 계획.

    today_cells: 오늘(REAL_MD) 행의 '구분 | 훈련 | 소요시간' 부분
    record_rows: '## 훈련 기록' 표 데이터 행(✅/⚠️ 만 done 으로 집계)
    extra_training: True 면 추가 훈련일 2행을 더해 total_count 를 3으로 만든다
                    (BUG-06 검증용 — 빈 훈련 기록 표에서도 total>1 이 되도록).

    total_count 는 '요일별 계획' 표(휴식 제외) 기준으로 산출됨에 유의(BUG-06 수정).
    """
    day_rows = f"| {REAL_MD} | - | {today_cells} |"
    if extra_training:
        day_rows += "\n| 98/1 | - | 러닝 | 인터벌 5km | 50분 |"
        day_rows += "\n| 98/2 | - | 러닝 | 롱런 12km | 80분 |"
    return f"""## 주간 훈련 계획 — 이번 주

> 이번 주는 유산소 베이스를 다진다.
달리기 거리 | {goal_km}km

### 요일별 계획
| 날짜 | 요일 | 구분 | 훈련 | 소요시간 |
|------|------|------|------|---------|
{day_rows}

## 훈련 기록 (실행 후 기입)
| 날짜 | 완료 | 내용 |
|------|------|------|
{record_rows}

## 주간 평가 (주 종료 후 작성)

_미작성_
"""


def write_profile(tmp: Path, nickname: str = "고고조") -> Path:
    p = tmp / "20-knowledge-base" / "01_PROFILE.md"
    p.write_text(
        f"""# 프로필

- 닉네임: {nickname}
- 나이: 38
- 키: 175cm
- 체중: 70kg

## 개인 최고 기록
- 10km · 42분 13초 2025년 3월
- 21km · 1시간 38분
- 풀 마라톤 · 미입력
""",
        encoding="utf-8",
    )
    return p


# ─────────────────────────────────────────────────────────────
# 앱 기동
# ─────────────────────────────────────────────────────────────

def _free_port() -> int:
    """사용 가능한 임시 포트를 잡아 반환한다(per-test 앱 격리용)."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _port_pids(port: int) -> list[int]:
    try:
        r = subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True)
        return [int(p) for p in r.stdout.strip().splitlines() if p.strip()]
    except Exception:
        return []


def _kill_port(port: int, timeout: float = 12.0) -> None:
    """포트를 점유한 프로세스를 종료하고 **실제로 풀릴 때까지** 대기한다.

    단일 공유 포트(8503)를 여러 app 테스트가 연속 사용하므로, 종료가 느리면 다음
    테스트가 ERR_CONNECTION_REFUSED / 이전 앱 응답(stale)을 만난다. SIGTERM → 미해제
    시 SIGKILL → 포트 free 폴링으로 back-to-back 스폰을 안정화한다.
    """
    for pid in _port_pids(port):
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.time() + timeout
    while time.time() < deadline:
        pids = _port_pids(port)
        if not pids:
            time.sleep(0.3)  # OS 가 소켓을 완전히 회수할 짧은 여유
            return
        for pid in pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        time.sleep(0.4)


@contextmanager
def running_app(test_date: str, setup, coach_mock: str | None = None, api_key: str | None = "test-key-placeholder"):
    """임시 워크스페이스 구성 후 전용 Streamlit 앱을 띄우고 URL 을 yield.

    coach_mock: 설정 시 COACH_MOCK 환경변수로 전달(실 API 미호출).
    api_key:    None 이면 빈 키('')로 띄워 'API 키 미설정' 경로를 재현.
    """
    tmp = Path(tempfile.mkdtemp(prefix="qa_app_"))
    setup(tmp)
    # 고정 포트(8503)를 모든 per-test 앱이 재사용하면 연속 스폰 시 충돌/ERR_CONNECTION_REFUSED
    # 가 잦다. 호출마다 빈 포트를 잡아 격리한다(공유 포트 flakiness 제거).
    port = _free_port()
    url = f"http://localhost:{port}"
    _kill_port(port)

    env = os.environ.copy()
    env["TEST_TODAY"] = test_date
    env["WORKSPACE_PATH"] = str(tmp)
    # api_key=None → 빈 문자열(존재하지만 falsy) → dotenv override=False 가 덮어쓰지 않음
    env["ANTHROPIC_API_KEY"] = api_key if api_key is not None else ""
    if coach_mock is not None:
        env["COACH_MOCK"] = coach_mock
    else:
        env.pop("COACH_MOCK", None)

    proc = subprocess.Popen(
        [
            "streamlit", "run", "webapp/app.py",
            f"--server.port={port}",
            "--server.headless=true",
            "--server.runOnSave=false",
            "--browser.gatherUsageStats=false",
        ],
        env=env,
        cwd=str(BASE_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + 40
        ready = False
        while time.time() < deadline:
            try:
                if requests.get(url, timeout=2).status_code == 200:
                    ready = True
                    break
            except Exception:
                pass
            time.sleep(1)
        if not ready:
            raise RuntimeError(f"app did not start at {url} within 40s")
        time.sleep(3)
        yield url, tmp
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
        # 포트가 완전히 풀린 뒤 다음 테스트가 스폰하도록 보장.
        _kill_port(port)
        shutil.rmtree(tmp, ignore_errors=True)


def wait_ready(page, timeout_ms: int = 15_000) -> None:
    page.wait_for_selector('[data-testid="stApp"]', timeout=timeout_ms)
    try:
        page.wait_for_selector('[data-testid="stSpinner"]', state="hidden", timeout=5_000)
    except Exception:
        pass
    page.wait_for_timeout(800)


def open_tab(page, name: str) -> None:
    """상단 탭 클릭(오늘/이번 주/기록/설정).

    탭 네비게이션이 st.tabs(role=tab)에서 session_state 기반 버튼으로 바뀌어(BUG-08)
    이름이 정확히 일치하는 nav 버튼을 클릭한다(exact=True 로 '기록 저장하기' 등과 구분).
    """
    page.get_by_role("button", name=name, exact=True).first.click()
    page.wait_for_timeout(600)
