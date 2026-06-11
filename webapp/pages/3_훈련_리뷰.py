"""훈련 리뷰 페이지 — /workout-review 스킬 UI (이미지 vision 포함)."""

import os
import sys
import datetime

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import file_manager as fm  # noqa: E402
from utils import prompts  # noqa: E402
from utils import page_common as pc  # noqa: E402

st.set_page_config(page_title="훈련 리뷰", page_icon="📊", layout="wide")
pc.api_status_sidebar()

st.title("📊 훈련 리뷰")
st.caption("완료한 훈련을 데이터 기반으로 심층 분석합니다.")

WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]

with st.form("review_form"):
    review_date = st.date_input("훈련 날짜", value=datetime.date.today())

    st.markdown("**훈련 결과 (아는 것만 입력)**")
    c1, c2, c3 = st.columns(3)
    with c1:
        distance = st.text_input("거리 (km)", placeholder="예: 8")
        avg_hr = st.text_input("평균 심박 (bpm)", placeholder="예: 148")
    with c2:
        duration = st.text_input("시간 (분 또는 분:초)", placeholder="예: 45")
        max_hr = st.text_input("최대 심박 (bpm)", placeholder="예: 165")
    with c3:
        pace = st.text_input("평균 페이스 (min/km)", placeholder="예: 5:38")
        cadence = st.text_input("케이던스 (spm)", placeholder="예: 172")

    image_file = st.file_uploader(
        "Garmin/Strava 스크린샷 (선택)", type=["png", "jpg", "jpeg"]
    )

    fatigue = st.slider("피로도 (1-10)", 1, 10, 5)
    has_pain = st.checkbox("통증 있음")
    pain_detail = ""
    pain_level = 0
    if has_pain:
        pc1, pc2 = st.columns([2, 1])
        with pc1:
            pain_detail = st.text_input("통증 부위/상황", placeholder="예: 왼쪽 무릎")
        with pc2:
            pain_level = st.slider("통증 수준 (1-10)", 1, 10, 3)

    feeling = st.text_area("소감 / 자유 메모", placeholder="훈련 중 느낀 점, 컨디션 등", height=80)
    submitted = st.form_submit_button("리뷰 생성", type="primary")

if submitted:
    date_str = review_date.strftime("%Y-%m-%d")
    weekday = WEEKDAY_KR[review_date.weekday()]

    profile = fm.read_profile()
    _, plan_content = fm.get_current_week_plan(review_date)
    today_session = fm.extract_today_session(plan_content, review_date) if plan_content else ""

    pain_line = (
        f"통증 있음 — {pain_detail or '부위 미입력'} / 수준 {pain_level}/10"
        if has_pain
        else "통증 없음"
    )

    metrics = []
    for label, val in [
        ("거리", distance), ("시간", duration), ("페이스", pace),
        ("평균 심박", avg_hr), ("최대 심박", max_hr), ("케이던스", cadence),
    ]:
        if val.strip():
            metrics.append(f"{label}: {val}")
    metrics_text = " / ".join(metrics) if metrics else "(수치 데이터 없음)"

    image_data = None
    image_media_type = "image/png"
    if image_file is not None:
        image_data = image_file.getvalue()
        image_media_type = image_file.type or "image/png"

    user_msg = f"""아래 훈련 결과를 심층 리뷰하라.

[훈련 날짜] {date_str} ({weekday})

[입력 수치] {metrics_text}
[피로도] {fatigue}/10
[통증] {pain_line}
[소감] {feeling or '(없음)'}
{"[첨부 이미지] Garmin/Strava 스크린샷이 첨부됨 — 거리/시간/페이스/심박/케이던스/랩 데이터를 읽어 분석에 반영하라." if image_data else "[첨부 이미지] 없음"}

[오늘 계획된 세션]
{today_session or '(주간 계획에서 해당 세션 없음 — "주간 계획 없음" 처리)'}

[프로필 / 부상 이력]
{profile or '(프로필 없음)'}

SKILL 출력 형식에 맞춰 계획 대비 수행, 품질 평가, 회복 필요도(🔴/🟡/🟢)를 작성하라.
통증 4/10+ 이면 성과 분석을 멈추고 회복 판단을 우선하라.
"""

    with st.spinner("코치가 훈련을 분석하는 중..."):
        result, err = pc.run_coach(
            prompts.WORKOUT_REVIEW_PROMPT, user_msg,
            image_data=image_data, image_media_type=image_media_type,
        )

    if err:
        st.error(err)
    else:
        st.session_state["review_result"] = result
        st.session_state["review_date_str"] = date_str
        st.session_state["review_weekday"] = weekday
        st.session_state["review_metrics"] = metrics_text
        st.session_state["review_fatigue"] = fatigue
        st.session_state["review_pain"] = pain_line
        st.session_state["review_feeling"] = feeling

if st.session_state.get("review_result"):
    st.divider()
    st.subheader("훈련 리뷰 결과")
    st.markdown(st.session_state["review_result"])

    st.divider()
    if st.button("일별 기록으로 저장", type="primary"):
        date_str = st.session_state["review_date_str"]
        weekday = st.session_state["review_weekday"]
        content = f"""# 훈련 기록 — {date_str} ({weekday})

## 훈련 내용
- 수치: {st.session_state['review_metrics']}
- 피로도: {st.session_state['review_fatigue']}/10
- 통증: {st.session_state['review_pain']}
- 소감: {st.session_state['review_feeling'] or '(없음)'}

## 훈련 리뷰
{st.session_state['review_result']}
"""
        path = fm.save_daily_log(date_str, content)
        st.success(f"저장 완료: {path}")
        st.caption(
            "주간 계획의 훈련 기록 표는 '4 계획 조정' 또는 직접 파일에서 갱신할 수 있습니다."
        )
