"""주간 계획 페이지 — /weekly-plan 스킬 UI."""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import file_manager as fm  # noqa: E402
from utils import prompts  # noqa: E402
from utils import page_common as pc  # noqa: E402

st.set_page_config(page_title="주간 계획", page_icon="📋", layout="wide")
pc.api_status_sidebar()

st.title("📋 주간 훈련 계획")
st.caption(f"{fm.current_week_label()} 계획을 수립합니다.")

# 기존 계획 안내
existing_name, existing = fm.get_current_week_plan()
if existing:
    st.warning(f"이번 주 계획 파일이 이미 있습니다: {existing_name}", icon="⚠️")
    with st.expander("기존 계획 보기"):
        st.markdown(existing)

st.divider()

# 입력 폼
with st.form("weekly_form"):
    schedule = st.text_area(
        "이번 주 일정 / 못 하는 날",
        placeholder="예: 수요일 회식, 금요일 야근, 목요일 출장 (헬스장 불가)",
        height=100,
    )
    condition = st.selectbox("현재 컨디션", ["좋음", "보통", "저하"], index=1)
    has_pain = st.checkbox("통증 있음")
    pain_detail = ""
    pain_level = 0
    if has_pain:
        c1, c2 = st.columns([2, 1])
        with c1:
            pain_detail = st.text_input("통증 부위/상황", placeholder="예: 왼쪽 무릎 뻐근")
        with c2:
            pain_level = st.slider("통증 수준 (1-10)", 1, 10, 3)
    submitted = st.form_submit_button("계획 생성", type="primary")

if submitted:
    profile = fm.read_profile()
    goal = fm.read_goal()
    recent = fm.get_recent_week_plans(weeks=3)
    recent_text = "\n\n".join(
        f"=== {r['filename']} ===\n{r['content']}" for r in recent
    ) or "(최근 훈련 기록 파일 없음 — 복귀/첫 주로 간주)"

    pain_line = (
        f"통증 있음 — {pain_detail or '부위 미입력'} / 수준 {pain_level}/10"
        if has_pain
        else "통증 없음"
    )

    user_msg = f"""아래 정보를 바탕으로 이번 주 주간 훈련 계획을 생성하라.

[이번 주]
- 주차/기간: {fm.current_week_label()}
- 오늘 날짜: {fm.today_str()}

[사용자 입력]
- 이번 주 일정/제약: {schedule or '특별한 제약 없음'}
- 컨디션: {condition}
- {pain_line}

[프로필]
{profile or '(프로필 파일 없음)'}

[목표]
{goal or '(목표 파일 없음)'}

[최근 주간 기록 (최신순)]
{recent_text}

위 데이터로 SKILL의 출력 형식에 맞춰 주간 계획을 작성하라.
공휴일/주말 점심 헬스장 세션 배정 금지. 통증 1/10 이상이면 🟡 이하로 고정.
"""

    with st.spinner("코치가 주간 계획을 작성하는 중..."):
        result, err = pc.run_coach(prompts.WEEKLY_PLAN_PROMPT, user_msg)

    if err:
        st.error(err)
    else:
        st.session_state["weekly_plan_result"] = result

# 결과 표시 + 저장
if st.session_state.get("weekly_plan_result"):
    st.divider()
    st.subheader("생성된 주간 계획")
    result = st.session_state["weekly_plan_result"]
    st.markdown(result)

    st.divider()
    save_col, _ = st.columns([1, 3])
    if existing:
        st.info(
            "기존 계획이 있어 저장 시 덮어쓰여집니다. 이미 기록된 훈련(✅/⚠️/❌)이 있으면 확인 후 진행하세요.",
            icon="ℹ️",
        )
    with save_col:
        if st.button("파일로 저장", type="primary"):
            # SKILL 형식에 맞춰 훈련 기록/주간 평가 섹션을 보강
            content = result
            if "## 훈련 기록" not in content:
                content += (
                    "\n\n## 훈련 기록 (실행 후 기입)\n"
                    "| 날짜 | 계획 실행 여부 | 비고 |\n"
                    "|------|--------------|------|\n"
                )
            if "## 주간 평가" not in content:
                content += "\n\n## 주간 평가 (주 종료 후 작성)\n\n_미작성_\n"
            path = fm.save_weekly_plan(content)
            st.success(f"저장 완료: {path}")
