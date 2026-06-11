"""주간 평가 페이지 — /weekly-evaluation 스킬 UI."""

import os
import sys
import re
import datetime

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import file_manager as fm  # noqa: E402
from utils import prompts  # noqa: E402
from utils import page_common as pc  # noqa: E402

st.set_page_config(page_title="주간 평가", page_icon="📈", layout="wide")
pc.api_status_sidebar()

st.title("📈 주간 평가")
st.caption(f"{fm.current_week_label()} 기록을 집계해 성장 추세를 분석합니다.")

# 주 종료 가드
today = datetime.date.today()
week_end = today + datetime.timedelta(days=(6 - today.weekday()))
if today < week_end:
    st.info(
        f"이번 주가 아직 끝나지 않았습니다. (오늘: {today.month}/{today.day}, "
        f"종료: {week_end.month}/{week_end.day}) — 중간(부분) 평가로 진행됩니다.",
        icon="ℹ️",
    )

# 자동 집계
plan_name, plan_content = fm.get_current_week_plan()
week_logs = fm.get_week_daily_logs()


def parse_distance(text: str) -> float:
    m = re.search(r"거리[:\s]*([\d.]+)\s*km", text)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return 0.0
    return 0.0


st.subheader("자동 집계")
agg_rows = []
total_km = 0.0
for log in week_logs:
    km = parse_distance(log["content"])
    total_km += km
    agg_rows.append({"날짜": log["date"], "거리(km)": km if km else "—"})

c1, c2, c3 = st.columns(3)
c1.metric("기록된 daily log", f"{len(week_logs)}건")
c2.metric("합산 달리기 거리", f"{total_km:.1f} km")
c3.metric("주간 계획", "있음" if plan_content else "없음")

if agg_rows:
    st.table(agg_rows)
else:
    st.caption("이번 주 daily log가 없습니다. 훈련 기록 표만으로 집계합니다.")

st.divider()

if st.button("주간 평가 생성", type="primary"):
    profile = fm.read_profile()
    recent = fm.get_recent_week_plans(weeks=4)
    recent_text = "\n\n".join(
        f"=== {r['filename']} ===\n{r['content']}" for r in recent
    ) or "(최근 주간 파일 없음)"
    logs_text = "\n\n".join(
        f"=== {l['filename']} ===\n{l['content']}" for l in week_logs
    ) or "(이번 주 daily log 없음)"

    partial = "예 (주 미종료, 부분 평가)" if today < week_end else "아니오"

    user_msg = f"""아래 데이터로 이번 주 평가 리포트를 생성하라.

[이번 주] {fm.current_week_label()}
[오늘] {fm.today_str()}
[부분 평가 여부] {partial}
[자동 집계 합산 거리] {total_km:.1f} km / daily log {len(week_logs)}건

[이번 주 주간 계획]
{plan_content or '(주간 계획 없음 — daily log만으로 집계)'}

[이번 주 daily log]
{logs_text}

[최근 주간 파일 (추세용, 최신순)]
{recent_text}

[프로필 / 목표 / 부상]
{profile or '(프로필 없음)'}

규칙:
- 수행률은 ✅=1.0, ⚠️=0.5, ❌=0.0 로 계산. — 는 오늘 이전이면 ❌, 이후면 제외.
- 조정 이력이 있으면 원계획/조정 후 수행률 이중 표기.
- 달리기 0km 주도 맥락 중심으로 의미 있게 평가하라.
SKILL 출력 형식을 따르라.
"""

    with st.spinner("코치가 주간 평가를 작성하는 중..."):
        result, err = pc.run_coach(prompts.WEEKLY_EVALUATION_PROMPT, user_msg)

    if err:
        st.error(err)
    else:
        st.session_state["eval_result"] = result

if st.session_state.get("eval_result"):
    st.divider()
    st.subheader("주간 평가 결과")
    result = st.session_state["eval_result"]
    st.markdown(result)

    st.divider()
    if st.button("평가 파일로 저장", type="primary"):
        label = fm.current_week_label()
        content = f"""# 주간 훈련 평가 — {label}

{result}

## 평가 메타
- 평가 시점: {fm.today_str()}
- 부분 평가 여부: {'예' if today < week_end else '아니오'}
"""
        path = fm.save_weekly_evaluation(content)
        st.success(f"저장 완료: {path}")
        st.caption(
            "참고: knowledge-base(03/04/05) 갱신은 코치 대화 스킬에서 수행됩니다. "
            "이 페이지는 evaluation.md 저장까지 처리합니다."
        )
