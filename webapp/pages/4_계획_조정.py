"""계획 조정 페이지 — /plan-adjustment 스킬 UI."""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import file_manager as fm  # noqa: E402
from utils import prompts  # noqa: E402
from utils import page_common as pc  # noqa: E402

st.set_page_config(page_title="계획 조정", page_icon="🔧", layout="wide")
pc.api_status_sidebar()

st.title("🔧 훈련 계획 조정")
st.caption("이번 주 남은 세션만 보수적으로 조정합니다. 이미 수행한 세션은 건드리지 않습니다.")

plan_name, plan_content = fm.get_current_week_plan()
if not plan_content:
    st.warning("이번 주 주간 계획이 없습니다. '1 주간 계획'에서 먼저 계획을 세워주세요.", icon="⚠️")
    st.stop()

st.subheader("현재 주간 계획")
with st.expander("주간 계획 전체 보기", expanded=False):
    st.markdown(plan_content)

st.divider()

with st.form("adjust_form"):
    reason = st.selectbox(
        "조정 이유",
        ["피로 누적", "통증 발생", "일정 변경", "기타"],
    )
    detail = st.text_area(
        "상세 입력",
        placeholder="예: 피로도 8/10, 수면 5시간 / 목요일 출장으로 헬스장 불가 / 왼쪽 무릎 3/10",
        height=100,
    )
    submitted = st.form_submit_button("조정안 생성", type="primary")

if submitted:
    profile = fm.read_profile()
    recent_logs = fm.get_daily_logs(days=7)
    logs_text = "\n\n".join(
        f"=== {l['filename']} ===\n{l['content']}" for l in recent_logs
    ) or "(최근 7일 daily log 없음)"

    user_msg = f"""아래 정보를 바탕으로 이번 주 남은 세션의 조정안을 생성하라.

[오늘 날짜] {fm.today_str()}
[조정 이유] {reason}
[상세] {detail or '(상세 미입력)'}

[현재 주간 계획]
{plan_content}

[최근 7일 daily log (workout-review 포함)]
{logs_text}

[프로필 / 부상 이력]
{profile or '(프로필 없음)'}

규칙:
- 이미 수행된 세션(오늘 이전, ✅/⚠️/❌ 기입 행)은 절대 수정하지 마라.
- 오늘 포함 이후의 '— | —' 상태 날짜만 조정 대상이다.
- 변경 세션마다 변경 전/후와 근거를 명시하라.
- 통증 4/10+ 이면 강제 조정. 🔴 조건이 3개+ 세션에 영향이면 /weekly-plan 권유.
SKILL 출력 형식을 따르라.
"""

    with st.spinner("코치가 조정안을 작성하는 중..."):
        result, err = pc.run_coach(prompts.PLAN_ADJUSTMENT_PROMPT, user_msg)

    if err:
        st.error(err)
    else:
        st.session_state["adjust_result"] = result
        st.session_state["adjust_original"] = plan_content

if st.session_state.get("adjust_result"):
    st.divider()
    st.subheader("조정안 (변경 전 / 후)")

    col_before, col_after = st.columns(2)
    with col_before:
        st.markdown("**변경 전 (현재 계획)**")
        with st.expander("펼치기", expanded=True):
            st.markdown(st.session_state.get("adjust_original", plan_content))
    with col_after:
        st.markdown("**조정안**")
        st.markdown(st.session_state["adjust_result"])

    st.divider()
    st.info(
        "조정안은 텍스트로 제안됩니다. 승인하면 주간 계획 파일 하단에 '조정 이력'으로 기록합니다. "
        "요일별 계획 표의 세부 행은 검토 후 직접 반영하세요.",
        icon="ℹ️",
    )
    if st.button("승인 & 조정 이력 저장", type="primary"):
        content = plan_content
        if "## 조정 이력" not in content:
            content = content.rstrip() + "\n\n## 조정 이력\n"
        content = content.rstrip() + (
            f"\n- {fm.today_str()} 조정 ({reason}): "
            f"{(detail or '상세 미입력').strip()}\n"
            f"\n<!-- 조정안 -->\n{st.session_state['adjust_result']}\n"
        )
        path = fm.save_weekly_plan(content)
        st.success(f"조정 이력 저장 완료: {path}")
