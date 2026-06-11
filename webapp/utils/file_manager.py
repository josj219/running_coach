"""파일 읽기/쓰기 유틸리티.

기존 워크스페이스 구조(20-knowledge-base, 40-training-log)를 그대로 사용한다.
경로는 BASE_DIR 기준으로 계산하며, BASE_DIR은 환경변수 WORKSPACE_PATH가 있으면
그것을, 없으면 webapp의 부모 디렉토리(프로젝트 루트)를 사용한다.
"""

import os
import datetime
import re


def get_base_dir() -> str:
    """워크스페이스 루트 경로를 반환한다."""
    env_path = os.environ.get("WORKSPACE_PATH")
    if env_path:
        return env_path
    # 이 파일: {BASE_DIR}/webapp/utils/file_manager.py
    # 부모의 부모의 부모 = BASE_DIR
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------------------
# 경로 헬퍼
# ---------------------------------------------------------------------------

def _kb_dir() -> str:
    return os.path.join(get_base_dir(), "20-knowledge-base")


def _weekly_dir() -> str:
    return os.path.join(get_base_dir(), "40-training-log", "weekly")


def _daily_dir() -> str:
    return os.path.join(get_base_dir(), "40-training-log", "daily")


def _read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""
    except Exception as e:  # noqa: BLE001
        return f"(파일 읽기 실패: {e})"


# ---------------------------------------------------------------------------
# 날짜/주차 헬퍼
# ---------------------------------------------------------------------------

def today_str() -> str:
    return datetime.date.today().strftime("%Y-%m-%d")


def current_week_filename(date: datetime.date | None = None) -> str:
    """이번 주 plan 파일명. 예: 2026-W23_plan.md"""
    d = date or datetime.date.today()
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}_plan.md"


def current_week_eval_filename(date: datetime.date | None = None) -> str:
    d = date or datetime.date.today()
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}_evaluation.md"


def current_week_label(date: datetime.date | None = None) -> str:
    """이번 주 라벨. 예: '2026년 23주차 (6/1 ~ 6/7)'"""
    d = date or datetime.date.today()
    iso = d.isocalendar()
    monday = d - datetime.timedelta(days=d.weekday())
    sunday = monday + datetime.timedelta(days=6)
    return (
        f"{iso[0]}년 {iso[1]}주차 "
        f"({monday.month}/{monday.day} ~ {sunday.month}/{sunday.day})"
    )


# ---------------------------------------------------------------------------
# 지식 베이스
# ---------------------------------------------------------------------------

def read_profile() -> str:
    return _read_file(os.path.join(_kb_dir(), "01_PROFILE.md"))


def read_goal() -> str:
    return _read_file(os.path.join(_kb_dir(), "02_GOAL.md"))


def read_running_history() -> str:
    return _read_file(os.path.join(_kb_dir(), "03_RUNNING_HISTORY.md"))


def read_current_status() -> str:
    return _read_file(os.path.join(_kb_dir(), "04_CURRENT_STATUS.md"))


def read_injury_history() -> str:
    return _read_file(os.path.join(_kb_dir(), "05_INJURY_HISTORY.md"))


# ---------------------------------------------------------------------------
# 주간 계획
# ---------------------------------------------------------------------------

def get_current_week_plan(date: datetime.date | None = None) -> tuple[str, str]:
    """(파일명, 내용) 반환. 없으면 ('', '')."""
    fname = current_week_filename(date)
    path = os.path.join(_weekly_dir(), fname)
    content = _read_file(path)
    if not content:
        return ("", "")
    return (fname, content)


def get_recent_week_plans(weeks: int = 3) -> list[dict]:
    """최근 N주치 주간 계획/평가 파일 목록을 최신순으로 반환."""
    d = _weekly_dir()
    out = []
    if not os.path.isdir(d):
        return out
    files = sorted(os.listdir(d), reverse=True)
    for f in files:
        if not f.endswith(".md"):
            continue
        out.append({"filename": f, "content": _read_file(os.path.join(d, f))})
        if len(out) >= weeks * 2:  # plan + evaluation
            break
    return out


def save_weekly_plan(content: str, date: datetime.date | None = None) -> str:
    """주간 계획을 저장하고 파일 경로 반환."""
    fname = current_week_filename(date)
    d = _weekly_dir()
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def weekly_plan_exists(date: datetime.date | None = None) -> bool:
    path = os.path.join(_weekly_dir(), current_week_filename(date))
    return os.path.exists(path)


def save_weekly_evaluation(content: str, date: datetime.date | None = None) -> str:
    fname = current_week_eval_filename(date)
    d = _weekly_dir()
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


# ---------------------------------------------------------------------------
# 일별 로그
# ---------------------------------------------------------------------------

def get_daily_logs(days: int = 7) -> list[dict]:
    """오늘부터 거꾸로 N일치 daily log를 최신순으로 반환.

    각 항목: {date, filename, content}
    """
    d = _daily_dir()
    out = []
    today = datetime.date.today()
    for i in range(days):
        day = today - datetime.timedelta(days=i)
        fname = day.strftime("%Y-%m-%d") + ".md"
        path = os.path.join(d, fname)
        if os.path.exists(path):
            out.append(
                {
                    "date": day.strftime("%Y-%m-%d"),
                    "filename": fname,
                    "content": _read_file(path),
                }
            )
    return out


def get_week_daily_logs(date: datetime.date | None = None) -> list[dict]:
    """이번 주(월~일) 범위의 daily log를 날짜순으로 반환."""
    d = _daily_dir()
    base = date or datetime.date.today()
    monday = base - datetime.timedelta(days=base.weekday())
    out = []
    for i in range(7):
        day = monday + datetime.timedelta(days=i)
        fname = day.strftime("%Y-%m-%d") + ".md"
        path = os.path.join(d, fname)
        if os.path.exists(path):
            out.append(
                {
                    "date": day.strftime("%Y-%m-%d"),
                    "filename": fname,
                    "content": _read_file(path),
                }
            )
    return out


def read_daily_log(date_str: str) -> str:
    path = os.path.join(_daily_dir(), f"{date_str}.md")
    return _read_file(path)


def save_daily_log(date_str: str, content: str) -> str:
    """일별 훈련 기록 저장. date_str: 'YYYY-MM-DD'."""
    d = _daily_dir()
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{date_str}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


# ---------------------------------------------------------------------------
# 주간 계획에서 특정 날짜 세션 추출
# ---------------------------------------------------------------------------

def extract_today_session(plan_content: str, date: datetime.date | None = None) -> str:
    """주간 계획 텍스트에서 오늘(M/D) 행/세션 요약을 추출한다.

    `## 요일별 계획` 표의 행과 `### M/D ...` 세션 블록을 함께 모은다.
    찾지 못하면 빈 문자열.
    """
    if not plan_content:
        return ""
    d = date or datetime.date.today()
    md = f"{d.month}/{d.day}"  # 예: 6/3
    lines = plan_content.splitlines()
    found = []

    # 표 행 (| 6/3 | ... )
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            # 첫 칸이 날짜(볼드 포함 가능)인지 검사
            first = cells[0].replace("*", "").replace("~", "").strip() if cells else ""
            if first == md:
                found.append(line)

    # 세션 블록 (### 6/3 ... 다음 ### 까지)
    block = []
    capturing = False
    for line in lines:
        if re.match(r"^#{2,4}\s", line):
            header = line.lstrip("#").strip()
            if header.startswith(md):
                capturing = True
                block.append(line)
                continue
            elif capturing:
                break
        if capturing:
            block.append(line)

    parts = []
    if found:
        parts.append("[요일별 계획 행]\n" + "\n".join(found))
    if block:
        parts.append("[세션 상세]\n" + "\n".join(block).strip())
    return "\n\n".join(parts)
