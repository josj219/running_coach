"""실 API 육안/E2E 수동 테스트용 런처.

격리된 임시 워크스페이스를 시드하고 앱을 8504 포트로 띄운 뒤 살려둔다.
실제 40-training-log/ 를 오염시키지 않는다.

사용:
    python tests/manual_launch.py f02     # 통증 회복 교체
    python tests/manual_launch.py f07      # 주간 계획(주말/통증)
    python tests/manual_launch.py f08      # 성장 리포트(로그 시드 포함)
    python tests/manual_launch.py f12      # 프로필 반영
    python tests/manual_launch.py e2e1     # 신규 첫 주(빈 상태 S0)
    python tests/manual_launch.py e2e3     # 통증 코칭 사이클
    python tests/manual_launch.py sat      # 자정경계: 토요일
    python tests/manual_launch.py sun      # 자정경계: 일요일(같은 주)

Ctrl-C 로 종료. 워크스페이스 경로를 출력하니 저장 파일 검사 후 직접 지운다.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import harness as H  # noqa: E402

scenario = sys.argv[1] if len(sys.argv) > 1 else "base"

tmp = Path(tempfile.mkdtemp(prefix=f"manual_{scenario}_"))
H.scaffold(tmp)
H.write_profile(tmp)

test_today = H.REAL_STR  # 평일 상태는 실제 날짜에 맞춤(plan 파일명 함정 회피)

# 시나리오별 시드
if scenario in ("f02", "f07", "f12", "e2e3"):
    H.write_weekly(tmp, H.weekly_plan(
        today_cells="러닝 | 인터벌 5km | 50분", record_rows="", goal_km=30))
elif scenario == "f08":
    # 리포트가 의미 있으려면 로그가 쌓여 있어야 함
    H.write_weekly(tmp, H.weekly_plan(
        today_cells="러닝 | 이지런 5km | 40분",
        record_rows="| %s | ✅ | 이지런 5.2km |" % H.REAL_MD, goal_km=30))
    (tmp / "40-training-log" / "daily" / f"{H.REAL_STR}.md").write_text(
        f"# 훈련 기록 — {H.REAL_STR}\n\n## 훈련 내용\n- 거리: 5.2km\n- 페이스: 6:20/km\n"
        "- 평균 심박: 145\n\n## 훈련 리뷰\n동일 페이스 대비 심박 안정. 🟢 회복 양호.\n",
        encoding="utf-8")
elif scenario == "e2e1":
    pass  # weekly 미생성 → S0 재현 (프로필만)
elif scenario == "sat":
    test_today = (H.SUNDAY.replace()  # SUNDAY-1 = 토요일
                  .__class__.fromordinal(H.SUNDAY.toordinal() - 1).isoformat())
    H.write_weekly(tmp, H.weekly_plan(
        today_cells="러닝 | 롱런 12km | 80분", record_rows="", goal_km=30))
elif scenario == "sun":
    test_today = H.SUNDAY_STR
    H.write_weekly(tmp, H.weekly_plan(
        today_cells="휴식 | 휴식 | -", record_rows="", goal_km=30))

env = os.environ.copy()
env["WORKSPACE_PATH"] = str(tmp)
env["TEST_TODAY"] = test_today
env.pop("COACH_MOCK", None)  # ★ 실 API 사용 (.env 의 ANTHROPIC_API_KEY 필요)

print(f"\n{'='*60}")
print(f"  시나리오 : {scenario}")
print(f"  TEST_TODAY: {test_today}")
print(f"  workspace : {tmp}")
print(f"  URL       : http://localhost:8504")
print(f"  종료 후 검사: ls -R {tmp}/40-training-log")
print(f"{'='*60}\n")

subprocess.run(
    ["streamlit", "run", "webapp/app.py",
     "--server.port=8504", "--server.headless=false",
     "--browser.gatherUsageStats=false"],
    env=env, cwd=str(H.BASE_DIR))
