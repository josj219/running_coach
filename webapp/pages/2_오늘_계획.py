"""오늘 계획 페이지 — /today-plan (계획 모드) 스킬 UI."""

import os
import sys
import datetime

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import file_manager as fm  # noqa: E402
from utils import prompts  # noqa: E402
from utils import page_common as pc  # noqa: E402

st.set_page_config(page_title="오늘 계획", page_icon="🏃", layout="wide")
pc.api_status_sidebar()

today = datetime.date.today()
weekday_kr = ["월", "화", "수", "목", "금", "토", "일"][today.weekday()]

st.title("🏃 오늘의 훈련 계획")
st.caption(f"오늘: {today.strftime('%Y-%m-%d')} ({weekday_kr})")

# 주간 계획에서 오늘 세션 자동 로드
plan_name, plan_content = fm.get_current_week_plan()
today_session = fm.extract_today_session(plan_content) if plan_content else ""

if not plan_content:
    st.warning(
        "이번 주 주간 계획이 없습니다. '1 주간 계획'에서 먼저 주간 계획을 세워주세요.",
        icon="⚠️",
    )
else:
    st.subheader("오늘의 주간 계획 세션")
    if today_session:
        st.code(today_session, language="markdown")
    else:
        st.info("주간 계획에서 오늘 날짜의 세션을 찾지 못했습니다. (휴식일이거나 표 형식 차이)")

st.divider()

with st.form("daily_form"):
    condition = st.selectbox(
        "오늘 컨디션",
        ["가능 / 컨디션 좋음", "가능 / 컨디션 보통", "가능 / 컨디션 저하 또는 통증", "오늘 훈련 불가"],
        index=0,
    )
    pain_detail = ""
    pain_level = 0
    if "통증" in condition:
        c1, c2 = st.columns([2, 1])
        with c1:
            pain_detail = st.text_input("통증 부위/상황", placeholder="예: 왼쪽 발목 뻐근")
        with c2:
            pain_level = st.slider("통증 수준 (1-10)", 1, 10, 3)
    weather = st.text_input(
        "오늘 날씨 (야외 세션 시 참고, 선택)",
        placeholder="예: 맑음 24도 / 비 예보 강수확률 80%",
    )
    submitted = st.form_submit_button("오늘 계획 생성", type="primary")

if submitted:
    profile = fm.read_profile()
    pain_line = (
        f"통증 있음 — {pain_detail or '부위 미입력'} / 수준 {pain_level}/10"
        if "통증" in condition
        else "통증 없음"
    )

    user_msg = f"""오늘의 상세 훈련 계획을 생성하라.

[오늘]
- 날짜: {today.strftime('%Y-%m-%d')} ({weekday_kr})

[주간 계획에서 오늘 세션]
{today_session or '(오늘 세션을 찾지 못함 — 주간 방향을 참고해 합리적으로 제안)'}

[주간 계획 전체 맥락]
{plan_content or '(주간 계획 없음)'}

[오늘 상태]
- 컨디션: {condition}
- {pain_line}
- 날씨: {weather or '미확인'}

[프로필]
{profile or '(프로필 없음)'}

SKILL 출력 형식에 맞춰 워밍업/메인/쿨다운 포함 상세 계획을 작성하라.
주간 계획과 달라지면 변경 이유를 명시하라. 통증 4/10+ 이면 회복 루틴으로 교체.
'훈련 불가'면 오늘 취소 안내와 주간 계획 조정 검토를 제안하라.
"""

    with st.spinner("코치가 오늘 계획을 작성하는 중..."):
        result, err = pc.run_coach(prompts.DAILY_PLAN_PROMPT, user_msg)

    if err:
        st.error(err)
    else:
        st.session_state["daily_plan_result"] = result

if st.session_state.get("daily_plan_result"):
    st.divider()
    st.subheader("오늘의 훈련 계획")
    st.markdown(st.session_state["daily_plan_result"])
    st.caption(
        "참고: 당일 계획은 화면 표시 전용입니다. 훈련 완료 후 '3 훈련 리뷰'에서 기록을 저장하세요."
    )
