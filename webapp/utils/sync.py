"""daily log 저장 후 관련 파일을 자동 동기화한다.

sync_after_save(date_str) 한 번 호출로 4개 파일을 업데이트한다.
  1. weekly plan    → 훈련 기록 표 해당 날짜 행 자동 기입
  2. 04_CURRENT_STATUS.md → 최신 상태 덮어쓰기
  3. 05_INJURY_HISTORY.md → 통증 기록 행 추가 (통증 있을 때만)
  4. 03_RUNNING_HISTORY.md → 러닝 기록 행 추가 (거리 > 0 일 때만)
"""

import os
import re
import datetime

from . import file_manager as fm

_KB_FILES = {
    "current_status": "04_CURRENT_STATUS.md",
    "injury_history": "05_INJURY_HISTORY.md",
    "running_history": "03_RUNNING_HISTORY.md",
}

_INJURY_HEADER = (
    "# 부상/통증 이력\n\n"
    "| 날짜 | 부위 | 수준 | 훈련 종류 | 비고 |\n"
    "|------|------|------|---------|------|\n"
)

_RUNNING_HEADER = (
    "# 러닝 기록\n\n"
    "| 날짜 | 종류 | 거리 | 페이스 | 평균 심박 | 케이던스 | 피로도 |\n"
    "|------|------|------|--------|---------|---------|--------|\n"
)


# ─────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────

def sync_after_save(date_str: str) -> None:
    """daily log 저장 직후 호출. 관련 파일 4개를 자동 업데이트한다."""
    content = fm.read_daily_log(date_str)
    if not content:
        return

    try:
        d = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return

    _, plan_content = fm.get_current_week_plan(d)
    parsed = _parse_daily_log(content, plan_content, d)

    # 1. weekly plan 훈련 기록 표 (먼저 — current_status 집계에 반영되도록)
    _update_weekly_plan_record(d, parsed, plan_content)

    # 2. current status (업데이트된 plan 파일을 재읽어 세션 수 반영)
    _, updated_plan = fm.get_current_week_plan(d)
    _update_current_status(date_str, d, parsed, updated_plan)

    # 3. 부상/통증 이력 (통증 있을 때만)
    if parsed["has_pain"]:
        _append_injury_history(date_str, parsed)

    # 4. 러닝 기록 (달리기 거리 있을 때만)
    if parsed["distance_km"] > 0:
        _append_running_history(date_str, parsed)


# ─────────────────────────────────────────────────────────────
# 파싱
# ─────────────────────────────────────────────────────────────

def _parse_daily_log(content: str, plan_content: str, date: datetime.date) -> dict:
    """daily log 텍스트를 파싱해 업데이트에 필요한 데이터를 반환한다."""
    result = {
        "workout_type": "",
        "fatigue_label": "",
        "fatigue_num": 0,
        "pain_text": "통증 없음",
        "pain_part": "",
        "pain_level": 0,
        "has_pain": False,
        "distance_km": 0.0,
        "pace": "",
        "avg_hr": "",
        "cadence": "",
        "recovery_level": "",
        "completion_status": "✅",
    }

    lines = content.splitlines()
    in_content = False
    in_review = False

    for line in lines:
        s = line.strip()

        # 섹션 전환
        if s.startswith("## 훈련 내용"):
            in_content, in_review = True, False
            continue
        if s.startswith("## 훈련 리뷰"):
            in_content, in_review = False, True
            continue
        if s.startswith("## ") and (in_content or in_review):
            in_content = in_review = False

        if in_content:
            # 종류
            m = re.match(r"-\s*종류:\s*(.+)", s)
            if m:
                result["workout_type"] = m.group(1).strip()

            # 피로도 — 저장 형식: "😊 괜찮아요 / 3/10"
            m = re.match(r"-\s*피로도:\s*(.+)", s)
            if m:
                raw = m.group(1)
                result["fatigue_label"] = raw.split("/")[0].strip()
                nm = re.search(r"(\d+)/10", raw)
                if nm:
                    result["fatigue_num"] = int(nm.group(1))

            # 불편함 — 저장 형식: "통증 없음" or "통증 — 왼쪽 무릎 / 3/10"
            m = re.match(r"-\s*불편함:\s*(.+)", s)
            if m:
                pain_raw = m.group(1).strip()
                result["pain_text"] = pain_raw
                if "없음" not in pain_raw:
                    pm = re.search(r"통증\s*[—\-]\s*(.+?)\s*/\s*(\d+)/10", pain_raw)
                    if pm:
                        result["pain_part"] = pm.group(1).strip()
                        result["pain_level"] = int(pm.group(2))
                        result["has_pain"] = result["pain_level"] > 0

            # 수치 — 저장 형식: "거리: 6.2 / 페이스: 5:05 / 평균 심박: 148 / ..."
            m = re.match(r"-\s*수치:\s*(.+)", s)
            if m:
                metrics = m.group(1)
                dm = re.search(r"거리:\s*([\d.]+)", metrics)
                if dm:
                    result["distance_km"] = float(dm.group(1))
                pm = re.search(r"페이스:\s*([\d]+:[\d]+)", metrics)
                if pm:
                    result["pace"] = pm.group(1)
                hm = re.search(r"평균 심박:\s*(\d+)", metrics)
                if hm:
                    result["avg_hr"] = hm.group(1)
                cm = re.search(r"케이던스:\s*(\d+)", metrics)
                if cm:
                    result["cadence"] = cm.group(1)

        # 훈련 리뷰 섹션 — 첫 번째 회복 이모지 추출
        if in_review and not result["recovery_level"]:
            if "🔴" in s:
                result["recovery_level"] = "🔴"
            elif "🟡" in s:
                result["recovery_level"] = "🟡"
            elif "🟢" in s:
                result["recovery_level"] = "🟢"

    # 종류가 없으면 주간 계획 세션 텍스트에서 키워드 추출
    if not result["workout_type"] and plan_content:
        session_text = fm.extract_today_session(plan_content, date)
        kws = [
            "인터벌", "롱런", "페이스런", "회복 조깅", "쉬운 달리기", "템포",
            "근력", "헬스", "드릴", "코어", "가동성", "러닝", "조깅",
        ]
        result["workout_type"] = next(
            (kw for kw in kws if kw in session_text), "훈련"
        )

    # 완료 상태 결정
    rv = result["recovery_level"]
    if rv in ("🔴", "🟡") or result["pain_level"] >= 4:
        result["completion_status"] = "⚠️"

    return result


# ─────────────────────────────────────────────────────────────
# 세션 수 집계 (plan 파싱)
# ─────────────────────────────────────────────────────────────



# ─────────────────────────────────────────────────────────────
# Update A — weekly plan 훈련 기록 표
# ─────────────────────────────────────────────────────────────

def _update_weekly_plan_record(date: datetime.date, parsed: dict, plan_content: str) -> None:
    """훈련 기록 표의 해당 날짜 행에 완료 상태를 기입한다.
    이미 ✅/⚠️/❌가 기입된 행은 덮어쓰지 않는다.
    날짜 행이 없으면 표 끝에 새 행을 삽입한다 (UPSERT).
    """
    if not plan_content:
        return

    md = f"{date.month}/{date.day}"  # "6/4"
    lines = plan_content.splitlines()
    new_lines = []
    in_record = False
    updated = False   # 해당 날짜 행이 처리됐는지 (중복 삽입 방지용)
    dirty = False     # 실제 파일 내용이 변경됐는지
    last_table_row_idx = None  # 훈련 기록 표의 마지막 | 행 위치 (UPSERT 삽입점)

    for line in lines:
        s = line.strip()

        if "## 훈련 기록" in s:
            in_record = True
            new_lines.append(line)
            continue

        if in_record and s.startswith("## "):
            in_record = False

        if in_record and "|" in line and not updated:
            cells = [c for c in line.strip().strip("|").split("|")]
            if cells:
                date_cell = cells[0].strip().replace("*", "").replace("~", "").strip()
                if date_cell == md:
                    status_cell = cells[1].strip() if len(cells) > 1 else ""
                    # 이미 마킹된 행 — 보존하고 중복 삽입만 막음
                    if any(mark in status_cell for mark in ("✅", "⚠️", "❌")):
                        new_lines.append(line)
                        updated = True
                        continue
                    # 미마킹 행 기입
                    cells[1] = f" {parsed['completion_status']} "
                    if len(cells) > 2:
                        note = parsed["workout_type"]
                        if parsed["distance_km"] > 0:
                            note += f" {parsed['distance_km']:.1f}km"
                        cells[2] = f" {note} "
                    new_lines.append("|" + "|".join(cells) + "|")
                    updated = True
                    dirty = True
                    continue

        new_lines.append(line)
        # 훈련 기록 섹션 내 표 행 마지막 위치 추적
        if in_record and "|" in line:
            last_table_row_idx = len(new_lines) - 1

    # 날짜 행이 없으면 표 끝에 새 행 삽입 (UPSERT)
    if not updated and last_table_row_idx is not None:
        note = parsed["workout_type"]
        if parsed["distance_km"] > 0:
            note += f" {parsed['distance_km']:.1f}km"
        new_row = f"| {md} | {parsed['completion_status']} | {note} |"
        new_lines.insert(last_table_row_idx + 1, new_row)
        dirty = True

    if dirty:
        fm.save_weekly_plan("\n".join(new_lines), date)


# ─────────────────────────────────────────────────────────────
# Update B — 04_CURRENT_STATUS.md
# ─────────────────────────────────────────────────────────────

def _update_current_status(
    date_str: str,
    date: datetime.date,
    parsed: dict,
    plan_content: str,
) -> None:
    """현재 상태 파일을 최신 훈련 정보로 덮어쓴다."""
    weekday_names = ["월", "화", "수", "목", "금", "토", "일"]
    weekday = weekday_names[date.weekday()]

    done_count, total_count = fm.count_sessions(plan_content)

    week_logs = fm.get_week_daily_logs(date)
    week_km = sum(_extract_km(l["content"]) for l in week_logs)

    recovery_map = {
        "🔴": "🔴 높음 — 강도 50% 이하 권장",
        "🟡": "🟡 보통 — 강도 유지 또는 10% 하향",
        "🟢": "🟢 낮음 — 계획대로 진행",
    }
    recovery_display = recovery_map.get(parsed["recovery_level"], "—")
    fatigue_display = (
        f"{parsed['fatigue_label']} ({parsed['fatigue_num']}/10)"
        if parsed["fatigue_num"] else parsed["fatigue_label"] or "—"
    )

    content = (
        f"# 현재 상태 — {date_str} ({weekday}) 기준\n\n"
        "## 최근 훈련\n"
        f"- 마지막 훈련일: {date_str} ({weekday})\n"
        f"- 훈련 종류: {parsed['workout_type'] or '—'}\n"
        f"- 회복 필요도: {recovery_display}\n\n"
        "## 이번 주 현황\n"
        f"- 완료 세션: {done_count}/{total_count}회\n"
        f"- 누적 달리기 거리: {week_km:.1f} km\n\n"
        "## 현재 컨디션\n"
        f"- 피로도: {fatigue_display}\n"
        f"- 통증/불편함: {parsed['pain_text']}\n"
    )
    _write_kb("current_status", content)


# ─────────────────────────────────────────────────────────────
# Update C — 05_INJURY_HISTORY.md
# ─────────────────────────────────────────────────────────────

def _append_injury_history(date_str: str, parsed: dict) -> None:
    """통증 기록을 누적 이력에 추가한다. 동일 날짜 중복 방지."""
    existing = _read_kb("injury_history")
    if date_str in existing:
        return
    if not existing.strip():
        existing = _INJURY_HEADER

    level_str = f"{parsed['pain_level']}/10" if parsed["pain_level"] else "—"
    row = (
        f"| {date_str} | {parsed['pain_part'] or '—'} "
        f"| {level_str} | {parsed['workout_type'] or '—'} | |\n"
    )
    _write_kb("injury_history", existing.rstrip("\n") + "\n" + row)


# ─────────────────────────────────────────────────────────────
# Update D — 03_RUNNING_HISTORY.md
# ─────────────────────────────────────────────────────────────

def _append_running_history(date_str: str, parsed: dict) -> None:
    """러닝 기록을 누적 이력에 추가한다. 동일 날짜 중복 방지."""
    existing = _read_kb("running_history")
    if date_str in existing:
        return
    if not existing.strip():
        existing = _RUNNING_HEADER

    row = (
        f"| {date_str} | {parsed['workout_type'] or '달리기'} "
        f"| {parsed['distance_km']:.1f}km "
        f"| {parsed['pace'] or '—'} "
        f"| {parsed['avg_hr'] or '—'} "
        f"| {parsed['cadence'] or '—'} "
        f"| {parsed['fatigue_label'] or '—'} |\n"
    )
    _write_kb("running_history", existing.rstrip("\n") + "\n" + row)


# ─────────────────────────────────────────────────────────────
# 유틸
# ─────────────────────────────────────────────────────────────

def _extract_km(content: str) -> float:
    return fm.parse_km(content)


def _kb_path(key: str) -> str:
    return os.path.join(fm.get_base_dir(), "20-knowledge-base", _KB_FILES[key])


def _read_kb(key: str) -> str:
    try:
        with open(_kb_path(key), "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def _write_kb(key: str, content: str) -> None:
    path = _kb_path(key)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError as e:
        import streamlit as st
        st.warning(f"지식베이스 저장 실패 ({key}): {e}")
