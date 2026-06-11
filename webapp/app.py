"""🏃 고고조 AI 러닝 코치 — 홈 대시보드.

실행: streamlit run webapp/app.py
필요 환경변수: ANTHROPIC_API_KEY (코칭 생성 시)
선택 환경변수: WORKSPACE_PATH (없으면 webapp의 부모를 워크스페이스 루트로 사용)
"""

import os
import sys
import re

import streamlit as st

# utils 패키지 import 경로 보장
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import file_manager as fm  # noqa: E402

st.set_page_config(
    page_title="고고조 AI 러닝 코치",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# 사이드바: API 키 상태 + 이번 주 훈련 기록 표
# ---------------------------------------------------------------------------

def render_sidebar():
    st.sidebar.title("🏃 러닝 코치")
    st.sidebar.caption("고고조 전용 AI 코치")

    if os.environ.get("ANTHROPIC_API_KEY"):
        st.sidebar.success("API 연결 준비됨", icon="✅")
    else:
        st.sidebar.warning(
            "ANTHROPIC_API_KEY 미설정\n\n터미널에서 설정 후 재실행하세요.", icon="⚠️"
        )

    st.sidebar.divider()
    st.sidebar.subheader("이번 주 훈련 기록")

    fname, content = fm.get_current_week_plan()
    if not content:
        st.sidebar.info("이번 주 계획이 아직 없습니다.\n'주간 계획'에서 생성하세요.")
        return

    rows = _parse_training_record(content)
    if rows:
        st.sidebar.table(rows)
    else:
        st.sidebar.caption("훈련 기록 표를 찾지 못했습니다.")
    st.sidebar.caption(f"파일: {fname}")


def _parse_training_record(content: str) -> list[dict]:
    """`## 훈련 기록` 섹션의 표를 파싱해 행 리스트로 반환."""
    lines = content.splitlines()
    capture = False
    rows = []
    for line in lines:
        if line.strip().startswith("## 훈련 기록"):
            capture = True
            continue
        if capture and line.strip().startswith("## "):
            break
        if capture and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            # 헤더/구분선 스킵
            if not cells or set("".join(cells)) <= set("-: "):
                continue
            if cells[0] in ("날짜",):
                continue
            row = {"날짜": cells[0]}
            if len(cells) > 1:
                row["실행"] = cells[1] or "—"
            if len(cells) > 2:
                row["비고"] = cells[2] or "—"
            rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# 본문
# ---------------------------------------------------------------------------

def render_goal():
    goal = fm.read_goal()
    st.subheader("🎯 현재 목표")
    if goal.strip():
        st.markdown(goal)
    else:
        st.info("02_GOAL.md 파일을 찾지 못했습니다.")


def render_week_summary():
    st.subheader(f"📅 이번 주 진행 상황 — {fm.current_week_label()}")
    fname, content = fm.get_current_week_plan()
    if not content:
        st.info("이번 주 계획이 없습니다. '1 주간 계획' 페이지에서 계획을 생성하세요.")
        return

    # 이번 주 방향 한 줄 추출
    direction = _extract_section_oneliner(content, "## 이번 주 방향")
    if direction:
        st.markdown(f"> {direction}")

    # 진행률 (훈련 기록 표 기준)
    rows = _parse_training_record(content)
    if rows:
        done = sum(1 for r in rows if r.get("실행", "—") not in ("", "—"))
        total = len(rows)
        st.progress(done / total if total else 0.0, text=f"수행 {done} / {total}")
    with st.expander("주간 계획 전체 보기"):
        st.markdown(content)


def _extract_section_oneliner(content: str, header: str) -> str:
    lines = content.splitlines()
    capture = False
    for line in lines:
        if line.strip().startswith(header):
            capture = True
            continue
        if capture:
            s = line.strip().lstrip(">").strip()
            if s and not s.startswith("---"):
                return s
            if s.startswith("## "):
                break
    return ""


SKILL_CARDS = [
    ("📋", "주간 계획", "이번 주 훈련 계획 수립", "pages/1_주간_계획.py"),
    ("🏃", "오늘 계획", "당일 상세 훈련 계획 생성", "pages/2_오늘_계획.py"),
    ("📊", "훈련 리뷰", "완료한 훈련 심층 분석", "pages/3_훈련_리뷰.py"),
    ("🔧", "계획 조정", "남은 주간 세션 조정", "pages/4_계획_조정.py"),
    ("📈", "주간 평가", "주간 집계 및 성장 분석", "pages/5_주간_평가.py"),
]


def render_skill_cards():
    st.subheader("🛠️ 코칭 기능")
    cols = st.columns(len(SKILL_CARDS))
    for col, (icon, title, desc, page) in zip(cols, SKILL_CARDS):
        with col:
            st.markdown(f"### {icon}")
            st.markdown(f"**{title}**")
            st.caption(desc)
            if hasattr(st, "page_link"):
                st.page_link(page, label=f"{title} 열기 →")
            else:
                st.write(f"← 사이드바에서 '{title}' 선택")


def main():
    render_sidebar()
    st.title("🏃 고고조 AI 러닝 코치")
    st.caption(
        "목표·일정·컨디션·훈련 이력을 종합해 장기 성장을 지원하는 데이터 기반 러닝 코치"
    )
    st.divider()

    left, right = st.columns([1, 1])
    with left:
        render_goal()
    with right:
        render_week_summary()

    st.divider()
    render_skill_cards()


if __name__ == "__main__":
    main()
