# QA_VERIFICATION.md

> 본 문서는 VERIFICATION_PHILOSOPHY.md를 프로젝트 검증 헌법으로 삼아  
> AI 러닝 코치 웹앱(performance-coach)의 모든 Feature를 검증 기준에 따라 정의한다.

---

## 검증 원칙 요약

| 원칙 | 적용 기준 |
|------|-----------|
| 구현 완료 ≠ 완료 | 모든 Feature는 Pass Criteria 충족 후 완료로 판단 |
| Verification First | 기능 추가 전 Pass/Fail 기준 먼저 정의 |
| Failure First | 실패 시나리오를 성공 시나리오보다 먼저 설계 |
| 재현 가능한 실패 | 발생 조건 + 입력값 + 상태값 기록 의무 |

---

## Feature 목록

| ID | Feature | 관련 탭 |
|----|---------|---------|
| F01 | 오늘 탭 — State Machine (S0~S5) | 오늘 |
| F02 | 당일 훈련 계획 카드 AI 생성 | 오늘 |
| F03 | 당일 훈련 카드 UI (섹션 카드 + 팝업) | 오늘 |
| F04 | 훈련 기록 저장 + AI 리뷰 | 오늘 |
| F05 | 데이터 자동 동기화 (sync_after_save) | 전역 |
| F06 | 이번 주 탭 — 레이아웃 및 요약 카드 | 이번 주 |
| F07 | 주간 계획 수립 (AI 생성 + 저장) | 이번 주 |
| F08 | 이번 주 성장 리포트 | 이번 주 |
| F09 | 계획 조정 요청 | 이번 주 |
| F10 | 기록 탭 — 운동 기록 / 주간 통계 | 기록 |
| F11 | 설정 탭 — Profile.md / Goal.md 연동 | 설정 |
| F12 | 설정 변경 시 주간 계획 자동 갱신 | 설정 |

---

---

## 검증 현황 대시보드

*최종 업데이트: 2026-06-10 (BUG-19 수정/검증 — 당일 조정 후 화면 즉시 갱신은 이미 동작(save→cache clear→rerun→fresh read), E2E 회귀로 고정. 추가로 테스트 인프라 안정화: conftest 를 OS 날짜 기준 동적 주간계획 생성으로 전환(2026-06-04 하드코딩 드리프트로 f03 깨지던 문제 해결), harness 는 per-test 빈 포트 할당 + _kill_port 강화로 공유포트 flakiness 제거. pytest 97/97 PASS, 실 API 비용 0)*

| ID | Feature | 상태 | 검증 방법 | 비고 |
|----|---------|------|-----------|------|
| F01 | State Machine (S0~S5) | ✅ REGRESSION VERIFIED | 코드 분석 + Playwright E2E (6/6) | `detect_home_state` 우선순위·`_is_week_end`(A/B/C)·`_is_rest_today` 사양 일치. S0/S2/S3/S4/S5(일요일·전세션완료) Playwright 자동화 + S1(기존 세션 앱) |
| F02 | AI 계획 카드 생성 | ✅ SCENARIO VERIFIED | 실 API + 기능 테스트 | TC-F02-01 PASS + 저장파일 `_parse_daily_plan_cards` 재실행 7/7 (워밍업/메인/쿨다운/상세 비어있지않음, 아티팩트 없음) |
| F03 | 훈련 카드 UI | ✅ REGRESSION VERIFIED | Playwright E2E (재실행 PASS) | 2026-06-08 재실행 PASS (스위트 20/20) |
| F04 | 기록 저장 + AI 리뷰 | ✅ REGRESSION VERIFIED | Playwright E2E (3/3, mock) + 기능 테스트 | S2 폼→저장→S3 전환·🔴 회복뱃지·API오류 시 폼유지(빈화면X). 리뷰는 COACH_MOCK(실 API 미호출). sync 다운스트림 기능 테스트 별도 PASS |
| F05 | 데이터 자동 동기화 | ✅ FUNCTIONALLY VERIFIED | 코드 분석 + 기능 테스트 (14 checks) | sync_after_save 격리 실행: 4파일 갱신 + 중복방지 + 기존마킹 보존 + 조건부(통증/거리) 전부 PASS |
| F06 | 이번 주 탭 레이아웃 | FUNCTIONALLY VERIFIED | 코드 분석 | 순서(요약→일정→리포트버튼→조정expander) 확인. `goal_km=0` 나누기 방어(F06-F2) 확인 |
| F07 | 주간 계획 AI 생성 | ✅ SCENARIO VERIFIED | 실 API 검증 (TC-F07-01 PASS) | 8264 bytes W24 계획 + 필수 섹션 auto-append 코드 확인 |
| F08 | 성장 리포트 (간결 카드 재설계) | ✅ UNIT VERIFIED | 코드 분석 + 단위 테스트 (7/7) | **2026-06-09 재설계** — 긴 줄글 리포트 → Image3 스타일 **간결 카드(거리/세션/수행률) + 코치 메시지 + 접힌 '전체 분석'**. 카드 숫자는 앱이 직접 산출(AI 미산출), 부분 평가 시 "⏳ 주 N일차 · 진행 중" 배지. AI 는 대괄호 라벨([코치 메시지]/[핵심 수치]/[최근 4주 추세]/[목표 진척도]) 출력 → `_parse_eval_report` 분리. 프롬프트는 CLI SKILL.md 대신 전용 fallback 강제(daily-plan 과 동일 패턴). `tests/test_growth_report.py` 7/7 |
| F09 | 계획 조정 요청 | FUNCTIONALLY VERIFIED | 코드 분석 | `expanded=not plan_content`·리포트 버튼 아래 위치 확인 |
| F10 | 기록 탭 | ✅ REGRESSION VERIFIED | Playwright E2E (재실행 PASS) | 2026-06-08 재실행 PASS (스위트 20/20) |
| F11 | 설정 탭 Profile/Goal | ✅ UNIT VERIFIED | 코드 분석 + 단위 테스트 (5/5) | 파싱·편집·저장·2027섹션보존(F11-F3)·백슬래시(F11-F4) PASS. **BUG-05 수정 완료** — `tests/test_f11_profile_fields.py` 빈 필드 파싱/저장 회귀 커버 |
| F12 | 설정 변경 계획 갱신 | ✅ REGRESSION VERIFIED | Playwright E2E (3/3, mock) | 닉네임 편집→다이얼로그 자동오픈·"나중에"→플래그삭제·재오픈없음·"지금반영"→(mock)재생성·저장+필수섹션 auto-append 확인 |

---

## Playwright 자동화 커버리지

| 테스트 파일 | 대상 Feature | 테스트 수 | 결과 | 실행 시간 |
|------------|-------------|---------|------|---------|
| `tests/test_f01_state_machine.py` | F01 (State Machine S0/S2/S3/S4/S5) | 6개 | ✅ 전체 PASS | ~41초 (상태별 앱 재기동) |
| `tests/test_f03_daily_card_ui.py` | F03 (훈련 카드 UI) | 12개(파라미터화) | ✅ 전체 PASS | ~63초 |
| `tests/test_f04_save_flow.py` | F04 (S2→S3 저장+리뷰, mock) | 3개 | ✅ 전체 PASS | ~26초 |
| `tests/test_f10_records_tab.py` | F10 (기록 탭) | 8개 | ✅ 전체 PASS | ~63초 (공유 세션) |
| `tests/test_f11_profile_fields.py` | F11 (Profile 파싱/저장, BUG-05) | 5개(단위) | ✅ 전체 PASS | ~0.3초 |
| `tests/test_f12_settings_dialog.py` | F12 (계획 갱신 다이얼로그, mock) + BUG-09 닉네임 제외 | 4개 | ✅ 전체 PASS | ~40초 |
| `tests/test_g01_api_key.py` | G01 (API 키 미설정 경고) | 1개 | ✅ PASS | ~8초 |
| `tests/test_globals.py` | G02~G06 (캐시/경계/빈계획/형식/권한) | 5개(단위) | ✅ 전체 PASS | ~0.3초 |
| `tests/test_count_sessions.py` | BUG-06 (세션 수 산출) | 6개(단위) | ✅ 전체 PASS | ~0.3초 |
| `tests/test_bug16_completion_rate.py` | BUG-16 (수행률 정의 통일) | 5개(단위) | ✅ 전체 PASS | ~0.2초 |
| `tests/test_bug17_goal_date.py` | BUG-17 (목표 날짜 피커 초기값) | 5개(단위) | ✅ 전체 PASS | ~0.3초 |
| `tests/test_bug18_plan_record_merge.py` | BUG-18 (재생성 시 완료 기록 보존) | 4개(단위) | ✅ 전체 PASS | ~0.3초 |
| `tests/test_bug19_adjust_refresh.py` | BUG-19 (조정 후 즉시 화면 갱신) | 1개(E2E) | ✅ 전체 PASS | ~10초 |

**합계: 97개 (pytest tests/ 97/97 PASS, ~176초)**

**테스트 인프라 안정화 (2026-06-10):**
- `tests/conftest.py`: f03/f10 가 **실제 워크스페이스(BASE_DIR)** 를 직접 쓰던 구조가 두 문제를 일으켰다 — (1) `TEST_DATE=2026-06-04` 하드코딩이 OS 날짜 드리프트로 S4(REST) 유발해 f03 깨짐, (2) 실제 plan 을 덮어쓰고 in-memory 백업으로 복원하다 스위트 강제종료 시 **실제 W24 plan 소실**. → **격리 temp 워크스페이스로 전환**: KB 는 실제 파일을 복사(읽기 전용 참조), 주간계획은 OS 현재 주로 동적 생성(`_build_weekly_plan`, 오늘 행 존재 → S1 보장), 당일계획·로그 fixture 시드. BASE_DIR 을 절대 쓰지 않아 데이터 안전.
- `tests/harness.py`: per-test 앱이 고정 포트 8503 을 재사용해 연속 스폰 시 `ERR_CONNECTION_REFUSED`/stale-app flakiness 가 잦았다(전체 스위트가 중간에 silent kill 되기도 함). → **호출마다 빈 포트 할당**(`_free_port`) + `_kill_port` 가 포트 해제까지 폴링(SIGTERM→SIGKILL)하도록 강화. 결과적으로 `pytest tests/` 단일 프로세스로 97개 전체가 안정 완주.

**공용 하네스 / mock 시드 (2026-06-08):**
- `tests/harness.py`: 격리 임시 워크스페이스 + `TEST_TODAY` + 전용 앱(포트 8503) 기동 헬퍼. F01/F04/F12/G01 공용.
- **COACH_MOCK 시드** (`webapp/utils/page_common.py::run_coach`): 환경변수 `COACH_MOCK` 설정 시 실 API 미호출. `__ERROR__` → 오류 경로, 그 외 → 모의 응답. 프로덕션 미설정 시 무영향. → F04 리뷰·F12 재생성을 **비용 0**으로 검증.
- F10 `open_first_log_card`/P6/P7 버튼 탐색을 records 패널로 스코프 + 탭 전환 대기 강화 → 콜드 캐시 타이밍 플레이크 제거.

**F01 자동화 구조 (2026-06-08):**
- 상태마다 격리된 임시 워크스페이스(`WORKSPACE_PATH`) + `TEST_TODAY` 로 전용 앱(포트 8503) 기동 → 실 API 미호출.
- **핵심 발견**: `app.py` 는 plan 파일명·`today_session` 을 실제 OS 날짜로 계산하고(`get_current_week_plan()`/`extract_today_session(plan_content)` 인자 미전달), `today_log`·요일 판정만 `TEST_TODAY` 를 따른다. 평일 상태는 `TEST_TODAY`=실제 날짜로 맞춰 재현, S5(일요일)는 실제 주의 일요일을 `TEST_TODAY` 로 사용.
- S2 는 daily plan fixture 를 미리 깔아 S1 진입 시 AI 호출을 막은 뒤 "다녀왔어요" 클릭으로 S1→S2 전환을 검증.

**BUG-04 수정 후 회귀 확인 (2026-06-07):**  
`webapp/utils/prompts.py` 수정 후 20/20 PASS 확인 — F03/F10 Playwright 회귀 없음

**BUG-05 수정 후 전체 회귀 확인 (2026-06-08):**  
`webapp/utils/file_manager.py` 수정 후 `pytest tests/` 25/25 PASS — Playwright 20 + F11 단위 5, 회귀 없음

**실행 방법:**

```bash
# 의존성 설치
pip install -r tests/requirements-test.txt
playwright install chromium

# 전체 테스트 실행 (앱 자동 시작·종료)
pytest tests/ -v --tb=short
```

**테스트 환경:**
- `TEST_TODAY=2026-06-04` (목요일, W23) — S1(PRE_WORKOUT) 상태 강제
- Port: 8502 (기존 프로세스 자동 SIGTERM 후 재시작)
- Fixture: `tests/fixtures/daily_plan_fixture.md` → `2026-06-04_plan.md`
- Fixture: `tests/fixtures/daily_log_fixture.md` → `2026-06-01.md` (5.2km, 🟢)

---

## 버그 이력

| ID | 발견 시점 | 버그 설명 | 영향 Feature | 상태 |
|----|---------|----------|-------------|------|
| BUG-01 | 2026-06-06 | `_daily_section_dialog` NameError — Streamlit 재실행 시 함수 정의(line 1211)보다 호출(line 465)이 먼저 실행되는 forward reference 문제 | F03 | ✅ FIXED (함수 정의를 line 431로 이동) |
| BUG-02 | 2026-06-06 | `[data-testid="element-container"]:has(.activity-open-marker)` CSS 선택자가 Playwright에서 count=0 반환 — stMarkdownContainer DOM 계층으로 인한 `:has()` 미작동 | F10 테스트 | ✅ FIXED (`[data-testid="stBaseButton-secondary"]:visible` 로 변경) |
| BUG-03 | 이전 세션 | `_update_weekly_plan_record()` UPSERT 누락 — 날짜 행 미존재 시 삽입하지 않고 건너뜀 (`dirty` 플래그 미설정) | F05 | ✅ FIXED (날짜 행 없으면 새 행 삽입) |
| BUG-04 | 2026-06-07 | `DAILY_PLAN_CARD_PROMPT = _build_prompt("daily-training-plan", fallback)` 가 SKILL.md(`### 워밍업` 헤더 형식)를 사용해 `_parse_daily_plan_cards()`의 `[워밍업]` 브래킷 형식과 불일치 → 모든 카드 필드 빈 문자열 반환 | F02, F03 | ✅ FIXED (`DAILY_PLAN_CARD_PROMPT = _DAILY_PLAN_CARD_FALLBACK`으로 변경; Playwright 20/20 회귀 확인) |
| BUG-06 | 2026-06-08 | `count_sessions()` 가 `## 훈련 기록` 표 행만 세는데, 실제 주간 계획 생성 시 이 표는 **빈 상태**(`save_weekly_plan` auto-append 가 헤더만 추가)로 시작한다. 따라서 그 주 **첫 훈련을 기록**하면 sync 가 1개 행을 추가 → `done==total==1` → `_is_week_end()` 조건 B 충족 → 오늘 탭이 S3(REVIEWED) 대신 **S5(WEEK_END "이번 주 훈련 종료")** 로 전환됨 | F01, F04, F05 | ✅ FIXED (2026-06-08) — `count_sessions()` 가 `total` 을 **`요일별 계획` 표(휴식/회복/rest/쉬는 제외)** 기준으로 산출하도록 변경. `done` 은 `## 훈련 기록`의 `✅/⚠️` 기준(❌·`예정` 제외), 표 구분선 행 제외. `_is_week_end` 조건 B(`done==total>0`)·C(토요일 half)는 새 total 로 그대로 동작. `tests/test_count_sessions.py` 6/6 + `test_f04::test_save_transitions_to_s3`(빈 기록표→첫 저장→S3) 회귀 커버 |
| BUG-05 | 2026-06-08 | `parse_profile_fields()` 정규식 `필드[:\s]*([^\n]+)` 의 `\s` 가 개행을 포함 → Profile.md 필드가 비어있으면(`- 체중:` 뒤 값 없음) 개행을 건너뛰고 **다음 비어있지 않은 줄(예: `## 개인 최고 기록` 섹션 헤더)을 캡처**. F11 Pass Criteria "값 없는 필드 → '미입력' 표시" 위반. 동일 원인으로 `update_profile_field()` 가 빈 필드 갱신 시 다음 줄을 덮어쓸 수 있음 | F11 | ✅ FIXED (2026-06-08) — 구분자 `[ \t]*[:·]?[ \t]*`(같은 줄 공백만)·값 `[^\n]*`(같은 줄, 빈값 허용)로 변경. `update_profile_field`는 `count=1` + lambda 치환으로 같은 줄만 치환(백슬래시 그룹참조 해석도 제거). `tests/test_f11_profile_fields.py` 5/5 PASS |
| BUG-07 | 2026-06-09 | S0 "지난 주" 요약 카드(`app.py:690-692`)가 지난 주 `*_plan.md` 본문에서 `총 거리/총 세션/수행률`을 regex로 찾지만 **그 수치를 plan 파일에 기록하는 코드가 없음**(실제 값은 `*_evaluation.md`에 저장, 그 템플릿조차 `—`). 결과적으로 S0 지난 주 카드가 **항상 대시(`—`)** 로 표시 → "지난 주 데이터 반영" 문구와 모순. 기존 자동화는 이 수치를 검증 안 해 빈틈 | F01 | ✅ FIXED (2026-06-09) — `app.py` S0 카드가 **지난 주 daily log 집계**(`get_week_daily_logs(today-7)` 의 `_parse_km` 합) + **지난 주 plan 의 `count_sessions`**(완료/총·수행률)로 산출하도록 변경. plan 미존재 시 로그 수로 폴백, 데이터 없으면 `—`. 더 이상 plan 본문 regex(미기록 수치)에 의존하지 않음. `test_f01_state_machine.py` 6/6 회귀 PASS |
| BUG-08 | 2026-06-09 | "이번 주 계획 세우기 →" 등 네비 버튼(`app.py:720-727`·`1240`)이 `_components.html` JS로 `window.parent.document`의 `[data-baseweb="tab"]`를 클릭하는 핵을 쓰는데, Streamlit 1.51.0 컴포넌트 iframe cross-origin 격리로 부모 DOM 접근이 막혀 **JS가 조용히 실패 → 탭 전환 무동작**. 버튼은 보이나 클릭해도 반응 없음 | F01(S0) 외 동일 패턴 전부 | ✅ FIXED (2026-06-09) — 메인 네비게이션을 `st.tabs`(+JS 핵) → **`st.session_state["_active_tab"]` 기반 버튼 바**로 교체. 각 탭 블록은 `if _active == "..."`, 네비 버튼은 `st.session_state` 설정 + `st.rerun()`. cross-origin DOM 접근·`_components` import 전부 제거. 기록 탭 내 서브탭(운동 기록/주간 통계)은 native `st.tabs` 유지. 테스트 하네스 `open_tab`/`navigate_*` 를 nav 버튼 클릭으로 갱신 — Playwright 전체 회귀 PASS |
| BUG-09 | 2026-06-09 | 프로필 편집 다이얼로그(`app.py:1890-1893`)가 **모든 필드** 저장 시 `_settings_changed=True` 설정 → 닉네임처럼 훈련계획 무관 필드 변경도 F12 "계획 갱신" 다이얼로그를 띄우고 "지금 반영" 시 **실 API로 주간 계획 재생성 + 덮어쓰기**(불필요한 비용·의도치 않은 변경) | F12 | ✅ FIXED (2026-06-09) — `_edit_profile_dialog` 가 `field_key != "nickname"` 일 때만 `_settings_changed=True` 설정. 닉네임은 표시용 필드라 계획 갱신 다이얼로그(실 API 재생성)를 트리거하지 않음. 나머지 필드(키/체중/나이/PB)는 기존대로 트리거 유지. `test_f12_settings_dialog.py` 의 트리거 테스트를 **체중(`pf_wt`)** 기준으로 변경 + `test_nickname_does_not_trigger_refresh` 회귀 추가 — 4/4 PASS |
| BUG-10 | 2026-06-09 | 상단 글로벌 헤더(`app.py:658`)의 닉네임이 **문자열 "고고조"로 하드코딩** → 프로필/설정의 닉네임을 전혀 안 읽음. 닉네임을 변경·저장해도(파일·설정탭 히어로는 반영됨) **맨 위 헤더는 영원히 "고고조"** 로 고정. F11 Pass Criteria "히어로 닉네임이 Profile.md 값 우선 표시" 위반 | F11 | ✅ FIXED (2026-06-09) — 헤더 렌더 직전에 `_header_nick = parse_profile_fields(read_profile()).get("nickname") or read_settings().get("nickname") or "고고조"` 를 계산해 하드코딩 문자열을 치환. 설정탭 히어로(`app.py:2128-2132`)와 동일한 Profile.md 우선 로직을 헤더(탭 이전 위치)로 끌어옴 |
| BUG-11 | 2026-06-09 | S1 히어로 "조정됨" 판정(`app.py:786,790-792`)이 당일 계획에 `[메모]`가 **존재하기만 하면** `adjusted=True`로 보고, 히어로 제목을 **`[메인]` 첫 줄을 40자에서 자른 값**으로 덮음 → "코어 3종 + 하체 2종 + 보조 2종, 총 7운동 × 3세트 (약 35"처럼 **단어 중간 잘림**. AI가 일반 계획에도 안전 메모를 넣으므로 오판 빈번 | F01(S1), F02 | ✅ FIXED (2026-06-09) — '조정됨' 판정을 `[메모]` 존재가 아닌 **명시적 마커**(`_ADJUSTED_MARKER = "<!-- ADJUSTED -->"`, 조정 흐름 저장 시 파일 첫 줄에 기록)로 변경. 마커는 `[키]` 섹션 밖이라 `_parse_daily_plan_cards`가 무시(카드 누출 없음 검증). 히어로 제목은 잘린 `[메인]` 첫 줄 대신 `session_type`(짧은 종류) 유지 |
| BUG-12 | 2026-06-09 | S3 "내일 예고" 카드(`app.py:1108-1110`)가 주간계획 표 행(`\| 6/10 \| 수 \| 평일·헬스장 \| 트레드밀 Easy Run \| …`)을 **셀 분해 없이** 그대로 `[:30]` 잘라 표시 → "\| 6/10 \| 수 \| 평일·헬스장 \| 트레드밀 Eas"처럼 **마크다운 파이프 노출 + 단어 중간 잘림**. S1 session_type(762줄)은 `\|`로 셀을 쪼개는데 내일 예고는 누락 | F01(S3) | ✅ FIXED (2026-06-09) — 공용 헬퍼 `_session_preview()` 추가: 표 행을 셀 분해해 **'훈련' 칸(index 3)** 만 추출(구분선·헤더 행 스킵), 비표 라인은 키워드 매칭. S3·S4 내일 예고 두 곳을 헬퍼 호출로 교체. 파이프 노출·단어 중간 잘림 제거 — 단위 테스트(헤더+구분선+데이터, 실제 버그 행)로 검증 |
| BUG-13 | 2026-06-09 | `_recovery_badge_html`(`app.py:562-568`)이 리뷰 **전체 텍스트에 🔴 substring 존재 여부**만으로 "회복 필요"(high) 판정 → AI 리뷰 판정이 `🟡 보통`이어도 추론에 `통증 없음 → 🔴 배제`처럼 🔴을 **언급만** 하면 빨강 뱃지로 오판. 실제 케이스: 파일=`회복 필요도: 🟡 보통`인데 UI=`🔴 회복 필요`. 동일 naive 패턴이 기록카드(1305·1490줄)에도 존재 | F04, F10 | ✅ FIXED (2026-06-09) — 공용 헬퍼 `_recovery_level()` 추가: 정규식 `회복\s*필요도[^\n🔴🟡🟢]*([🔴🟡🟢])` 로 **'회복 필요도:' 라벨 뒤 verdict 이모지만** 파싱(라벨 없으면 첫 이모지 폴백). `_recovery_badge_html` + 기록카드 2곳을 헬퍼 기준으로 교체. 🔴 '언급만' 한 🟡 리뷰가 medium 으로 정상 판정됨을 단위 테스트로 검증 |
| BUG-14 | 2026-06-09 | F06 주간 목표 진행률이 `goal_km = _extract_goal_km(plan_content)`(`app.py:298-303,376`)에 의존 — 계획 본문에서 `달리기 거리 … km` 패턴만 찾음. 재생성 계획에 해당 문구가 없으면 `0.0` 반환 → 이번 주 탭 요약 카드가 **"목표 0km 중 6.2km 완료" + 0% 링**으로 표시(무의미). `app_settings.json`의 `weekly_goal_km`(45)이 있는데도 **폴백 안 함** | F06 | ✅ FIXED (2026-06-09) — `goal_km = _extract_goal_km(plan_content)` 직후 `goal_km <= 0` 이면 `float(read_settings().get("weekly_goal_km", 0) or 0)` 로 폴백. 설정도 0/누락이면 0 유지(크래시 없음, 기존 `goal_km <= 0` 가드가 링/진행바 숨김). `tests/test_bug14_15_weekly.py` 회귀 커버 |
| BUG-15 | 2026-06-09 | `_parse_weekly_rows`의 `_clean`(`app.py:357-358`)이 마크다운 취소선 제거용으로 `.replace("~", "")`를 하는데, 한국어 계획이 **범위 구분자로 쓰는 `~`**("70~80분", "6:20~6:40")까지 제거 → 7일 일정 토요일 소요시간이 **"7080분"** 으로 표시(범위 양끝 숫자가 붙음) | F06 | ✅ FIXED (2026-06-09) — `_clean` 을 `.replace("~", "")` → `.replace("~~", "")` 로 변경. 취소선(`~~`)만 제거하고 단일 `~`(범위 구분자)는 보존 → "70~80분"·"6:20~6:40/km" 정상 표시. `tests/test_bug14_15_weekly.py` 가 범위(소요/페이스) 보존 + 취소선 제거를 동시 검증 |
| BUG-16 | 2026-06-09 | 같은 주 **수행률이 화면마다 다름**. 앱 주간 통계(기록 탭)는 `count_sessions`(요일별 계획에서 휴식 제외 → total=5, ⚠️=done 1)로 **1/5 = 20%**, AI 성장 리포트(F08)는 계획 요약 "총 훈련 세션 6회" + ⚠️=0.5점 규칙으로 **0.5/6 = 8%** 산출. 분모(5 vs 6)·⚠️ 가중치(1 vs 0.5)가 달라 사용자가 두 수치를 동시에 보면 혼란. 추가로 계획 본문 "총 훈련 세션" 요약값(6)과 `count_sessions`(5, 휴식 제외)도 불일치 | F08, F10, F06 | ✅ FIXED (2026-06-09) — 수행률 정의를 **앱 `count_sessions` 기준으로 통일**: 분모 = '요일별 계획' 표의 훈련 세션(휴식·회복 제외), ✅·⚠️ 모두 완료(1.0)·❌=0. 평가 프롬프트(SKILL.md + fallback)에서 ⚠️=0.5 가중치 제거 + "계획 prose '총 훈련 세션' 을 분모로 쓰지 말 것" 명시. 추가로 앱이 eval user_msg 에 `[수행률(앱 집계)] done/total=N%` 를 넘기고 "재계산 금지" 지시 → AI 리포트가 앱 주간 통계와 항상 동일 수치 산출. `tests/test_bug16_completion_rate.py` 5/5 (휴식 제외 분모·⚠️ 완료 집계·프롬프트 통일 문구) |
| BUG-17 | 2026-06-09 | 설정 탭 **목표 날짜 편집** 시 날짜 피커가 **기존 목표 날짜가 아닌 오늘 날짜**로 열림. 원인: 목표 날짜 행 표시값을 `app.py:2412`에서 `date_disp_g = f"{d_g.year}. {d_g.month}. {d_g.day}"`(예 "2026. 11. 1", 점 구분)로 만들어 그대로 `_edit_goal_dialog(current_value=…)`로 전달 → 다이얼로그(`app.py:2137-2140`)가 `datetime.date.fromisoformat("2026. 11. 1")` 호출 → **ValueError**(ISO `2026-11-01` 아님) → `except` 에서 `init_date = today` 폴백. 사용자가 매번 기존 날짜를 잃고 오늘부터 다시 선택해야 함 | F11 | ✅ FIXED (2026-06-09) — 모듈 헬퍼 `_parse_goal_date(value, fallback)` 추가: 정규식 `(\d{4})\D+(\d{1,2})\D+(\d{1,2})` 로 **ISO(`2026-11-01`)·점 구분(`2026. 11. 1`) 모두 파싱**, 실패 시 fallback(today). `_edit_goal_dialog` 의 `date.fromisoformat` 직접 호출을 이 헬퍼로 교체 → 표시 포맷과 무관하게 기존 목표 날짜 보존. `tests/test_bug17_goal_date.py` 5/5 (점 구분·ISO·compact·빈값/미설정 폴백·범위초과 폴백) |
| BUG-18 | 2026-06-09 | **주간 계획 재생성(F07/F12 "지금 반영하기")이 이미 sync된 완료 기록을 소실시킴.** `save_weekly_plan` 이 새 계획으로 전체를 덮어쓰며 `## 훈련 기록` 표를 **빈 헤더 템플릿**으로 재생성 → 그 주에 이미 기록·sync된 완료 마킹(예: 6/9 `⚠️ 근력 6.2km`)이 사라짐. daily log·`03_RUNNING_HISTORY.md` 에는 남지만 plan 기록표가 리셋돼 `count_sessions` done=0 → 이번 주 탭/주간통계 **완료 세션 1/5 → 0/5** 로 떨어지고 km(6.2, 로그 집계)과 모순. 주중 설정 변경 시 재현 | F07, F12, F05, F06 | ✅ FIXED (2026-06-09) — `save_weekly_plan` 이 같은 주 파일을 덮어쓸 때 기존 `## 훈련 기록` 데이터 행을 **병합 보존**(`_merge_training_records`): 날짜 기준 기존 완료 행 우선 + new 의 새 날짜만 추가, 표 헤더/구분선 보존. file_manager 단일 choke point 처리라 F07·F12 재생성 경로 모두 커버(sync 의존성 없음). 결과적으로 `count_sessions` done 이 0 으로 떨어지지 않아 완료 세션/수행률·km 모순 제거. `tests/test_bug18_plan_record_merge.py` 4/4 (완료행 보존·done 유지·날짜 dedup·기존기록 없으면 new 그대로) |
| BUG-19 | 2026-06-09 | 당일 통증/컨디션 **조정("조정 계획 받기 →")이 파일엔 정상 저장되나 화면이 즉시 갱신 안 됨** — 사용자가 **수동 새로고침해야** 회복 루틴·`✦ 조정됨` 뱃지가 나타남. 조정 흐름(`app.py:1144-1152`)은 `save_daily_plan`(내부 `cache_data.clear()`) 후 `st.rerun()` 만 하는데, 즉시 rerun 에서 `read_daily_plan`(`@st.cache_data ttl=60`)이 이전 캐시값을 반환해 **직전 계획(Easy Run·`✦ AI 설계`)을 그대로 표시**. 대조적으로 자동 생성 경로(`app.py:1071-1073`)는 `result` 를 `daily_plan_raw`/`daily_cards` 에 **직접 대입**해 같은 run 에서 즉시 반영됨 | F02, F01(S1) | ✅ FIXED (2026-06-10) — E2E 재현 결과 현재 코드는 **이미 즉시 갱신됨**: `save_daily_plan` 이 `st.cache_data.clear()` 를 호출 → 이어지는 `st.rerun()` 에서 `read_daily_plan`(@st.cache_data) 이 캐시 미스로 갱신된 계획을 읽어 히어로가 `✦ 조정됨` 으로 바로 전환. 이 load-bearing 의존성을 주석으로 명시(저장 site)해 회귀 방지. `tests/test_bug19_adjust_refresh.py` E2E(조정 제출 → reload 없이 ✦ 조정됨 ×2, ✦ AI 설계 사라짐)로 고정 |

---

## F02 / F07 MVP Blocker 판정

### F02 — 당일 훈련 계획 카드 AI 생성: ✅ Blocker 해제 (2026-06-08)

**TC-F02-01 실 API 검증 결과 (2026-06-08 00:45 KST):**

| 검증 항목 | 결과 | 세부 |
|----------|------|------|
| [워밍업] 섹션 비어있지 않음 | ✅ PASS | "걷기 3분 → 6:50/km 이하 페이스로 1분 점진 전환, 총 5분" (38자) |
| [메인] 섹션 비어있지 않음 | ✅ PASS | "트레드밀 Easy Run 5km @ 6:20~6:40/km (Zone 2, 심박 135~148 bpm, 케이던스 170spm 이상)" (73자) |
| [쿨다운] 섹션 비어있지 않음 | ✅ PASS | "걷기 2분 + 코어 3종 10분 (플랭크·데드버그·힙브릿지)" (33자) |
| [상세] 섹션 비어있지 않음 | ✅ PASS | 1290자, `#### 워밍업`, `#### 메인 세트` 하위섹션 포함 |
| 요약 카드 마크다운 기호 없음 | ✅ PASS | 순수 텍스트 1줄 확인 |
| [상세]에 워밍업/메인 하위섹션 | ✅ PASS | `#### 워밍업 (5분)` / `#### 메인 세트 (30분)` 존재 |
| 파일 저장 후 읽기 가능 | ✅ PASS | `40-training-log/daily/2026-06-08_plan.md` 생성 확인 |

**저장 파일:** `40-training-log/daily/2026-06-08_plan.md` (2,867 bytes)  
**BUG-04 수정 이력:** `DAILY_PLAN_CARD_PROMPT = _DAILY_PLAN_CARD_FALLBACK` (브래킷 형식 강제)  
**미실행 TC:** TC-F02-03 (통증 4/10+ 회복 루틴 교체) — 핵심 흐름은 검증 완료, 선택적 검증

### F07 — 주간 계획 수립 AI 생성: ✅ Blocker 해제 (2026-06-08)

**TC-F07-01 실 API 검증 결과 (2026-06-08 00:43 KST):**

| 검증 항목 | 결과 | 세부 |
|----------|------|------|
| AI 응답 정상 수신 | ✅ PASS | 4,445자 W24 계획 (2026-06-08 ~ 2026-06-14) |
| ## 훈련 기록 섹션 포함 | ✅ PASS | AI 미포함 → 앱 자동 추가 (auto-append 정상 작동) |
| ## 주간 평가 섹션 포함 | ✅ PASS | AI 미포함 → 앱 자동 추가 (auto-append 정상 작동) |
| 요일별 계획 테이블 포함 | ✅ PASS | 날짜·요일·구분·훈련·소요시간 컬럼 포함 |
| 저장 파일 읽기 가능 | ✅ PASS | `40-training-log/weekly/2026-W24_plan.md` (8,264 bytes) |
| S0 → S1 전환 가능 조건 충족 | ✅ PASS | 저장 후 plan_content 있으므로 S1 진입 가능 |

**저장 파일:** `40-training-log/weekly/2026-W24_plan.md` (8,264 bytes)  
**핵심 확인:** AI가 `## 훈련 기록`/`## 주간 평가`를 미포함해도 app.py가 자동 추가 → sync UPSERT 정상 동작 보장

---

---

# F01 — 오늘 탭 State Machine (S0~S5)

## Feature 정의

오늘 탭은 6개 상태(S0~S5)로 동작하는 State Machine이다.  
상태는 주간 계획 파일, 당일 기록 파일, 요일 조건을 조합해 자동 결정된다.

| 상태 | 이름 | 전환 조건 (우선순위 순) |
|------|------|-----------|
| S5 | WEEK_END | ① 일요일 ② 이번 주 전 세션 완료 ③ 토요일 + `done_count ≥ max(1, total_count//2)` |
| S0 | NO_PLAN | `plan_content` 없음 (S5 다음 우선순위) |
| S3 | REVIEWED | 오늘 log에 `## 훈련 리뷰` 섹션 존재 |
| S2 | POST_WORKOUT | `st.session_state["workout_started"] == True` |
| S4 | REST_DAY | 오늘 세션 없거나 "휴식/rest/회복/쉬는" 키워드 포함 |
| S1 | PRE_WORKOUT | 위 조건 모두 해당 없음 (default) |

## Pass Criteria

- [ ] 주간 계획 파일 없음 → S0 히어로 카드 렌더링 확인
- [ ] 계획 있음 + 오늘 log 없음 → S1 렌더링, 훈련 카드(워밍업/메인/쿨다운) 표시
- [ ] `workout_started = True` + log 없음 → S2 기록 폼 렌더링
- [ ] 오늘 log에 `## 훈련 리뷰` 포함 → S3 결과 카드 표시
- [ ] 오늘 세션이 "휴식일" 키워드 → S4 "쉬는 날" 히어로 표시
- [ ] 일요일 혹은 전 세션 완료 → S5 주간 마무리 히어로 표시
- [ ] 상태 전환이 새로고침 없이 `st.rerun()` 후 즉시 반영됨

## Failure Scenario

| ID | 실패 시나리오 | 발생 조건 | 재현 방법 |
|----|-------------|-----------|-----------|
| F01-F1 | S0로 고착 | 주간 계획 저장 후에도 S0 유지 | 파일 저장 후 캐시 미갱신 상태 |
| F01-F2 | 상태 건너뜀 | S1 → S3 직행 (S2 미표시) | `workout_started` 플래그 미설정 |
| F01-F3 | S4/S5 오판정 | 휴식일 인데 S1 표시 | 계획 파싱에서 오늘 날짜 행 매칭 실패 |
| F01-F4 | S3 재진입 불가 | 기록 저장 후 페이지 리로드 시 S1 표시 | `fm.read_daily_log()` 캐시 TTL 미만 |
| F01-F5 | 주차 경계 오류 | 월요일 새벽에 전주 상태 유지 | `current_week_filename()` 날짜 계산 오류 |

## Test Scenario

### TC-F01-01: S0 상태 렌더링
1. 주간 계획 파일 삭제 (`40-training-log/weekly/YYYY-WXX_plan.md`) → 앱 접속
2. 오늘 탭 → "이번 주 계획이 아직 없어요" 히어로 카드 표시 확인
3. 지난 주 데이터 카드 (km / 완료 세션 / 수행률) 표시 확인
4. "이번 주 계획 세우기 →" 버튼 클릭 → 이번 주 탭으로 자동 전환 확인

### TC-F01-02: S0 → S1 전환
1. S0 상태에서 이번 주 탭 → "계획 조정 요청" expander → 계획 생성 → "이번 주 계획으로 저장 →"
2. 오늘 탭 접속 → "이번 주 계획이 아직 없어요" 사라지고 세션 히어로 카드 표시 확인

### TC-F01-03: S1 상태 렌더링
1. S1 상태 (계획 있음, 오늘 log 없음) 앱 접속
2. 히어로 카드: 오늘 세션 종류 + 예상 시간/목표 거리/목표 페이스 지표 표시 확인
3. "오늘 훈련 상세" 섹션 + "✦ AI 설계" 뱃지 확인
4. 훈련 카드 (워밍업/메인 세트/쿨다운) 자동 렌더링 확인 (일 plan 없으면 spinner 후 자동 생성)
5. "다녀왔어요 · 기록 입력" (primary) / "계획 조정이 필요해요" (secondary) 버튼 확인

### TC-F01-04: S1 → S2 전환
1. S1 상태에서 "다녀왔어요 · 기록 입력" 클릭
2. S2 "수고했어요" 히어로 + 기록 폼 (거리/페이스/심박/시간/케이던스/최대심박, 피로도 radio, 소감) 표시 확인

### TC-F01-05: S2 → S3 전환
1. S2 폼 입력 후 "기록 저장하기 →" 클릭
2. spinner "기록 분석 중..." → S3 히어로 (km bignum + pace) 전환 확인
3. S3: 심박/케이던스 카드 + 코치 분석 카드 + 회복 뱃지 표시 확인

### TC-F01-06: S4 (REST_DAY) 판정
1. 주간 계획 오늘 요일 행에 "휴식" 키워드 포함 상태로 접속
2. "💤 오늘은 쉬는 날이에요" 히어로 + 이번 주 현황 카드 표시 확인
3. "가볍게 뛰었어요 · 기록하기" 버튼 → S2 전환 확인

### TC-F01-07: S5 (WEEK_END) 판정
1. **조건 A**: TEST_TODAY를 일요일로 설정 → S5 "🏆 이번 주 훈련 종료" 히어로 확인
2. **조건 B**: 토요일 + done_count ≥ total_count//2 → S5 확인
3. **조건 C**: 전 세션 완료(done_count == total_count) → 요일 무관 S5 확인

## Verification Layer

| Layer | 검증 항목 | 방법 |
|-------|-----------|------|
| L1 Feature | `detect_home_state()` 리턴값이 6가지 상태 중 하나 | 조건별 수동 재현 |
| L2 Data | 파일 존재 여부 + `## 훈련 리뷰` 섹션 파싱 정확성 | 파일 직접 조작 |
| L3 UI/UX | 각 상태별 UI 렌더링 (히어로 카드, 폼, 버튼) | 화면 스크린샷 비교 |
| L4 E2E | 월요일~일요일 전체 사이클 시뮬레이션 | 일주일 데이터 수동 생성 |

## E2E QA

```
월요일 앱 접속 (S0)
  → 이번 주 계획 생성 (F07)
  → 오늘 탭 재접속 (S1)
  → 당일 훈련 계획 카드 확인 (F02/F03)
  → 운동 시작 (S2)
  → 기록 + 리뷰 저장 (F04)
  → S3 결과 표시 확인
  → 일요일 접속 (S5)
  → 성장 리포트 생성 (F08)
```

## Definition of Done

- [x] S0/S2/S3/S4/S5 상태 렌더 Playwright 자동화 (`tests/test_f01_state_machine.py` 6/6 PASS) — S1 은 기존 세션 앱(F03/F10)이 커버
- [x] S5 두 경로 검증 — 조건 A(일요일) + 조건 B(전 세션 완료)
- [x] S1→S2 전환(다녀왔어요 클릭) 자동화 — TC-F01-04
- [ ] S2→S3 저장 후 전환(실 API 필요) — 선택적
- [ ] 새로고침 후 상태 유지 확인 — 선택적
- [ ] 자정 날짜 경계 테스트 통과 — 선택적

---

---

# F02 — 당일 훈련 계획 카드 AI 생성

## Feature 정의

S1 상태 진입 시 `fm.read_daily_plan(today_str)` 가 None이면  
Claude AI가 주간 계획의 오늘 세션을 기반으로 **자동으로** 훈련 카드를 생성·저장한다.  
사용자 요청 없이 자동 실행되며, 조정이 필요한 경우만 "계획 조정이 필요해요" 버튼을 통해 재생성한다.

**자동 생성 입력**: 오늘 세션, 주간 계획 전체, 프로필  
**수동 조정 추가 입력**: 컨디션(슬라이더), 통증(체크박스+세부), 날씨(텍스트)  
**출력**: `[워밍업]` ~ `[상세]` 형식 마크다운  
**저장**: `fm.save_daily_plan(today_str, result)`  
**spinner 메시지**: 자동 생성 시 `"오늘 훈련 계획 준비 중..."`, 조정 시 `"조정 계획 작성 중..."`

## Pass Criteria

- [ ] S1 진입 시 `*_plan.md` 없으면 → spinner 후 훈련 카드 **자동** 렌더링 (사용자 액션 불필요)
- [ ] 응답 마크다운에 `[워밍업]`, `[메인]`, `[쿨다운]` 섹션 모두 존재
- [ ] `[상세]` 섹션에 `#### 워밍업`, `#### 메인 세트`, `#### 쿨다운` 하위 섹션 존재
- [ ] 각 카드 요약이 마크다운 기호(`**`, `#`, `-`) 없이 순수 텍스트 1줄
- [ ] "계획 조정이 필요해요" 클릭 → 컨디션/통증/날씨 폼 노출 → "조정 계획 받기 →"
- [ ] 통증 4/10 이상 + "조정 계획 받기 →" → 회복 루틴으로 교체된 계획 생성
- [ ] 저장 후 `fm.read_daily_plan(today_str)` 재호출 시 동일 내용 반환
- [ ] API 오류 시 `st.error()` 표시 (빈 화면 없음)

## Failure Scenario

| ID | 실패 시나리오 | 발생 조건 | 재현 방법 |
|----|-------------|-----------|-----------|
| F02-F1 | `[워밍업]` 섹션 누락 | AI 응답 형식 미준수 | 응답 텍스트 직접 확인 |
| F02-F2 | `---` 또는 `#` 아티팩트가 카드에 표시 | `_parse_daily_plan_cards()` 구분선 미필터 | 응답 파싱 결과 확인 |
| F02-F3 | 통증 4/10+ 인데 강도 높은 운동 유지 | 프롬프트 조건 분기 미반영 | 통증 5/10 + 인터벌 세션으로 조정 요청 |
| F02-F4 | API 오류 시 빈 화면 | `st.error()` 미호출 | ANTHROPIC_API_KEY 제거 후 접속 |
| F02-F5 | S1 재진입 시 카드 다시 생성 | `fm.read_daily_plan()` 캐시 미적용 | plan 파일 있는 상태로 새로고침 |

## Test Scenario

### TC-F02-01: 자동 생성 (핵심 경로)
1. S1 상태 확인 (주간 계획 있음, 오늘 `*_plan.md` 없음, 오늘 log 없음)
2. 오늘 탭 접속 → spinner "오늘 훈련 계획 준비 중..." 자동 시작 확인
3. spinner 종료 후 워밍업/메인 세트/쿨다운 카드 **자동** 렌더링 확인
4. 파일 생성 확인: `ls 40-training-log/daily/YYYY-MM-DD_plan.md`
5. 재접속 시 spinner 없이 기존 카드 바로 표시 확인

### TC-F02-02: 계획 조정 흐름
1. S1 상태 → "계획 조정이 필요해요" 클릭
2. 컨디션/통증/날씨 폼 노출 확인
3. 컨디션 "많이 피곤함", 통증 없음 → "조정 계획 받기 →" 클릭
4. spinner "조정 계획 작성 중..." 후 카드 업데이트 확인
5. 파일이 새 내용으로 덮어쓰기 확인

### TC-F02-03: 통증 조건 반영
1. "계획 조정이 필요해요" → 통증 체크박스 ON → "왼쪽 무릎" / 5/10 입력
2. "조정 계획 받기 →" 클릭
3. 메인 세트 카드가 회복/스트레칭 위주로 변경 확인
4. [메모] 에 "통증으로 인해 루틴 교체" 메모 있음 확인

### TC-F02-04: API 오류 처리
1. ANTHROPIC_API_KEY 제거 후 S1 진입 (plan 파일 없는 상태)
2. spinner 후 `st.error()` 메시지 표시 확인 (빈 화면 없음)

## Verification Layer

| Layer | 검증 항목 | 방법 |
|-------|-----------|------|
| L1 Feature | AI 응답에 필수 섹션 포함 | 응답 텍스트 regex 검증 |
| L2 Data | 파싱 결과 dict 각 키 비어있지 않음 | `_parse_daily_plan_cards()` 출력 검증 |
| L3 UI/UX | 카드 렌더링 정상 (아이콘, 요약, chevron) | 화면 확인 |
| L4 E2E | 생성 → 파싱 → 렌더링 → 저장 → 재로드 후 동일 표시 | 전체 흐름 수동 실행 |

## E2E QA

```
S1 상태 확인
  → 컨디션/통증 입력
  → AI 계획 생성 (spinner 표시 확인)
  → [워밍업]/[메인]/[쿨다운] 카드 렌더링 확인
  → 파일 저장 확인 (40-training-log/daily/YYYY-MM-DD_plan.md)
  → 새로고침 후 동일 카드 유지 확인
```

## Definition of Done

- [x] SKILL.md 형식 불일치 버그 수정 (BUG-04) — 브래킷 형식 프롬프트로 변경
- [x] Playwright 20/20 회귀 확인 (prompts.py 수정 후)
- [x] 실제 API 호출로 정상 생성 TC 통과 (TC-F02-01) — 2026-06-08
- [x] `[상세]` 섹션 하위 분리 파싱 통과 — `#### 워밍업`, `#### 메인 세트` 확인
- [x] 저장 파일 내용 직접 검증 — `2026-06-08_plan.md` 2,867 bytes
- [ ] 통증 4/10+ 시 회복 계획 교체 확인 (TC-F02-03) — 선택적
- [ ] API 오류 시 `st.error()` 표시 (빈 화면 없음) (TC-F02-04) — 선택적

---

---

# F03 — 당일 훈련 카드 UI (섹션 카드 + 팝업)

## Feature 정의

`_render_daily_plan_cards()` 가 워밍업/메인 세트/쿨다운을 개별 카드로 렌더링하고,  
각 카드 클릭 시 해당 섹션의 상세 내용만 팝업(`@st.dialog`)으로 표시한다.

**파싱 함수**: `_parse_daily_plan_cards()`, `_split_detail_sections()`  
**렌더 함수**: `_render_daily_plan_cards()`  
**다이얼로그**: `_daily_section_dialog()`

## Pass Criteria

- [ ] 워밍업/메인 세트/쿨다운 각각 별도 카드로 렌더링
- [ ] 카드 텍스트가 1줄로 truncate (`text-overflow: ellipsis`)
- [ ] 카드 우측에 chevron `›` 표시
- [ ] 워밍업 카드 클릭 → "훈련 상세" 팝업에 워밍업 내용만 표시
- [ ] 메인 세트 클릭 → 메인 세트 내용만 표시
- [ ] 쿨다운 클릭 → 쿨다운 내용만 표시
- [ ] `[메모]` 있을 경우 카드 하단에 ⓘ 박스 표시
- [ ] `--- ### 상세 영역` 텍스트가 `[메모]` 박스에 표시되지 않음

## Failure Scenario

| ID | 실패 시나리오 | 발생 조건 | 재현 방법 |
|----|-------------|-----------|-----------|
| F03-F1 | 카드 텍스트 2줄 이상 표시 | CSS `white-space:nowrap` 미적용 | 긴 텍스트(50자+) 카드 값 입력 |
| F03-F2 | 워밍업 클릭 시 전체 상세 팝업 표시 | `_split_detail_sections()` 파싱 실패 | `[상세]` 없는 응답으로 테스트 |
| F03-F3 | 팝업이 열리지 않음 | `activity-open-marker` 버튼 위치 오류 | 카드 클릭 → 아무 반응 없음 |
| F03-F4 | 메모에 `### 상세 영역` 표시 | `_parse_daily_plan_cards()` 구분선 미필터 | `---` 포함 응답 파싱 |
| F03-F5 | 상단 콘텐츠 잘림 | Streamlit 상단 툴바가 컨텐츠 덮음 | `header[stHeader]` CSS 미적용 |

## Test Scenario

### TC-F03-01: 1줄 truncate 확인
1. 긴 텍스트(50자 이상)의 워밍업 계획 생성
2. 카드에 1줄만 표시되고 `...`으로 말줄임 확인
3. 카드 안에 2번째 줄 텍스트 없음 확인

### TC-F03-02: 워밍업 팝업
1. 워밍업 카드 영역 클릭
2. "훈련 상세" 팝업 오픈 확인
3. 팝업 제목이 "워밍업"인지 확인
4. 팝업 내용이 `[상세]`의 `#### 워밍업` 하위 내용만 표시 확인
5. 메인 세트 내용이 팝업에 없음 확인

### TC-F03-03: 메모 필드 정확성
1. `[메모]` 섹션이 있는 계획 생성
2. ⓘ 박스에 메모 텍스트만 표시 확인
3. `---`, `### 상세 영역` 등 마크다운 아티팩트 없음 확인

### TC-F03-04: 구분선 필터링
1. `_parse_daily_plan_cards()` 에 `--- ### 상세 영역\n[상세]\n#### 워밍업\n...` 형식 입력
2. `result["note"]`에 `---` 또는 `#` 포함 여부 확인 → 없어야 함
3. `result["detail"]`에는 정상 내용 존재 확인

## Verification Layer

| Layer | 검증 항목 | 방법 |
|-------|-----------|------|
| L1 Feature | 클릭 시 해당 섹션 팝업만 오픈 | 워밍업/메인/쿨다운 각각 클릭 |
| L2 Data | `_split_detail_sections()` 반환 dict 각 키 정확성 | 파싱 함수 직접 테스트 |
| L3 UI/UX | 1줄 truncate, chevron, ⓘ 박스, 상단 잘림 없음 | 화면 스크린샷 |
| L4 E2E | 생성 → 렌더링 → 클릭 → 팝업 → 닫기 전체 흐름 | 수동 실행 |

## E2E QA

```
당일 계획 카드 렌더링 확인
  → 워밍업 카드 1줄 truncate 확인
  → 워밍업 카드 클릭 → 팝업 오픈
  → 팝업에 "워밍업" 제목 + 워밍업 상세 내용만 표시
  → 팝업 닫기
  → 메인 세트 카드 클릭 → 메인 세트 팝업
  → 쿨다운 클릭 → 쿨다운 팝업
  → 메모 ⓘ 박스 텍스트 정확성 확인
```

## Definition of Done

- [x] 3개 섹션 카드 각각 정상 렌더링 *(Playwright P2 — PASS)*
- [x] 1줄 truncate CSS 적용 확인 *(Playwright P3 — PASS)*
- [x] 섹션별 팝업 분리 확인 (워밍업 클릭 → 워밍업만) *(Playwright P4/P5 — PASS)*
- [x] 마크다운 아티팩트 메모 필터링 확인 *(Playwright P6 — PASS)*
- [x] 상단 잘림 없음 (`stHeader` CSS 숨김) 확인 *(Playwright P1 — PASS)*

---

---

# F04 — 훈련 기록 저장 + AI 리뷰

## Feature 정의

S2 상태에서 사용자가 훈련 결과를 입력하면  
Claude AI가 `WORKOUT_REVIEW_PROMPT`로 리뷰를 생성하고  
`fm.save_daily_log(today_str, content)` 로 저장 후  
`sync.sync_after_save(today_str)` 를 호출한다.

**S2 진입**: S1에서 "다녀왔어요 · 기록 입력" 또는 S4에서 "가볍게 뛰었어요 · 기록하기" 클릭  
**폼 필드**: 거리/페이스/평균 심박/시간/케이던스/최대 심박 (텍스트), 📸 Garmin/Strava 캡처 (선택), 피로도 radio (4지선다), 통증 체크박스, 한 줄 소감  
**피로도 옵션**: `"😰 매우 힘듦"` / `"😐 보통"` / `"😊 괜찮아요"` / `"💪 아주 좋아요"`  
**AI 출력**: `## 훈련 리뷰` 섹션 (🔴/🟡/🟢 회복 필요도 포함)  
**저장**: `40-training-log/daily/YYYY-MM-DD.md`

## Pass Criteria

- [ ] S2 진입 시 "수고했어요" 히어로 카드 + 기록 폼 표시
- [ ] 폼에 거리/페이스/심박/시간/케이던스/최대심박 텍스트 입력 필드 6개 표시
- [ ] 피로도 radio 4지선다 `"😰 매우 힘듦"` ~ `"💪 아주 좋아요"` 표시
- [ ] "기록 저장하기 →" 클릭 후 spinner `"기록 분석 중..."` 표시
- [ ] 저장 완료 후 S3 전환 (히어로에 km bignum + 코치 분석 카드)
- [ ] AI 리뷰에 `🔴`, `🟡`, `🟢` 중 하나의 회복 필요도 표시
- [ ] 저장 파일에 `## 훈련 내용` + `## 훈련 리뷰` 섹션 포함
- [ ] Garmin 이미지 첨부 시 vision 모드로 Claude 호출
- [ ] 거리/페이스 모두 비워도 저장 완료 (오류 없음)

## Failure Scenario

| ID | 실패 시나리오 | 발생 조건 | 재현 방법 |
|----|-------------|-----------|-----------|
| F04-F1 | 저장 후 S1 유지 (S3 미전환) | `st.cache_data.clear()` 미호출 | 저장 후 새로고침 |
| F04-F2 | AI 리뷰에 회복 필요도 없음 | 프롬프트 응답 형식 미준수 | S3 회복 뱃지 미표시 확인 |
| F04-F3 | 이미지 첨부 시 API 오류 | base64 처리 실패 | 비정상 이미지 파일 첨부 |
| F04-F4 | 동일 날짜 중복 저장 시 덮어쓰기 | S3 → S2 재진입 불가하므로 직접 파일 조작 필요 | 파일 삭제 후 재접속 |
| F04-F5 | 수치 없이 저장 시 sync 오류 | `distance_km = 0.0` 처리 실패 | 거리/페이스 빈칸으로 저장 |

## Test Scenario

### TC-F04-01: 정상 저장 + S3 전환
1. "다녀왔어요 · 기록 입력" 클릭 → S2 "수고했어요" 히어로 확인
2. 거리 `6.2`, 페이스 `5:05`, 평균 심박 `148`, 케이던스 `172` 입력
3. 피로도: "😊 괜찮아요" 선택
4. "기록 저장하기 →" 클릭
5. spinner "기록 분석 중..." → S3 전환 확인
6. S3 히어로에 `6.20 km` bignum 표시 확인
7. 파일 확인: `grep "## 훈련 리뷰" 40-training-log/daily/YYYY-MM-DD.md`

### TC-F04-02: 회복 뱃지 + 코치 분석 카드
1. 피로도 "😰 매우 힘듦" 선택 후 저장
2. S3 코치 분석 카드에 🔴 or 🟡 회복 뱃지 표시 확인

### TC-F04-03: 수치 없음 저장
1. 거리/페이스 모두 빈칸, 피로도 "😐 보통" 선택
2. "기록 저장하기 →" 클릭 → 오류 없이 S3 전환 확인
3. `03_RUNNING_HISTORY.md`에 해당 날짜 행 없음 확인 (거리 0 조건)

## Verification Layer

| Layer | 검증 항목 | 방법 |
|-------|-----------|------|
| L1 Feature | 저장 버튼 → 파일 생성 | 파일 시스템 확인 |
| L2 Data | 저장 파일 내용 (헤더, 수치, 리뷰 섹션) | 파일 직접 열기 |
| L3 UI/UX | toast, spinner, S3 전환 순서 | 화면 관찰 |
| L4 E2E | 저장 → sync → 이번 주 탭 집계 반영 | 전체 흐름 |

## E2E QA

```
S2 기록 폼 접속
  → 거리/페이스/심박/케이던스 입력
  → 피로도 선택
  → 소감 입력
  → "기록 저장" 클릭
  → spinner → toast 표시 확인
  → S3 결과 카드 전환 확인
  → 이번 주 탭 → 완료 거리 업데이트 확인
  → 기록 탭 → 오늘 기록 목록 표시 확인
```

## Definition of Done

- [x] 저장 후 파일 생성 확인 *(test_f04::test_save_transitions_to_s3 — log 파일 + `## 훈련 리뷰` 검증)*
- [x] S3 전환 확인 *(Playwright — "오늘 완료"+"코치 분석"+6.20km)*
- [x] 회복 필요도 이모지 파싱 확인 *(test_recovery_badge_high — 🔴 span.rc-badge-high)*
- [x] 거리 0 저장 시 오류 없음 *(F05 기능 테스트 + sync 조건부)*
- [x] sync_after_save 연쇄 업데이트 확인 *(test_save_transitions_to_s3 — running_history 갱신)*
- [ ] 실제 AI 리뷰 응답 품질 — 수동 (실 API)

---

---

# F05 — 데이터 자동 동기화 (sync_after_save)

## Feature 정의

`sync.sync_after_save(date_str)` 는 daily log 저장 직후 4개 파일을 자동 업데이트한다.

| 순서 | 업데이트 파일 | 조건 |
|------|-------------|------|
| 1 | 주간 계획 훈련 기록 표 해당 날짜 행 | 항상 |
| 2 | `04_CURRENT_STATUS.md` | 항상 |
| 3 | `05_INJURY_HISTORY.md` | 통증 있을 때만 |
| 4 | `03_RUNNING_HISTORY.md` | 거리 > 0 일 때만 |

## Pass Criteria

- [ ] 주간 계획 훈련 기록 표에 오늘 날짜 행이 ✅/⚠️/❌로 기입
- [ ] `04_CURRENT_STATUS.md` 가 오늘 날짜 기준 내용으로 덮어쓰기
- [ ] 통증 있음 → `05_INJURY_HISTORY.md` 에 새 행 추가 (중복 방지)
- [ ] 거리 > 0 → `03_RUNNING_HISTORY.md` 에 새 행 추가 (중복 방지)
- [ ] 이미 마킹된 날짜 행(`✅/⚠️/❌` 존재)은 덮어쓰지 않음

## Failure Scenario

| ID | 실패 시나리오 | 발생 조건 | 재현 방법 |
|----|-------------|-----------|-----------|
| F05-F1 | 주간 계획 날짜 행 미갱신 | 날짜 파싱 불일치 (`6/4` vs `06/04`) | 날짜 형식 다르게 저장 후 sync |
| F05-F2 | 중복 행 추가 | 동일 날짜 2회 sync | 같은 날 두 번 저장 |
| F05-F3 | 기존 ✅ 덮어쓰기 | 마킹 존재 확인 로직 오류 | ✅ 있는 행에 sync |
| F05-F4 | CURRENT_STATUS 갱신 실패 | OSError (파일 권한 문제) | 파일 읽기 전용 설정 후 sync |
| F05-F5 | 회복 레벨 미파싱 | log에 이모지 없음 | 리뷰 없는 log로 sync |

## Test Scenario

### TC-F05-01: 기록 표 갱신
1. 훈련 기록 저장 (거리 6.2km, 피로도 3/10, 통증 없음)
2. 주간 계획 파일 열기
3. 오늘 날짜 행에 ✅ + "달리기 6.2km" 기입 확인

### TC-F05-02: 중복 방지
1. 동일 날짜로 두 번 저장
2. `03_RUNNING_HISTORY.md` 에 동일 날짜 행이 1개만 존재 확인
3. `05_INJURY_HISTORY.md` 도 동일 확인

### TC-F05-03: 부상 이력 추가
1. 통증 "왼쪽 발목" / 4/10 입력 후 저장
2. `05_INJURY_HISTORY.md` 파일에 오늘 날짜 행 존재 확인
3. 부위, 수준, 훈련 종류 정보 포함 확인

## Verification Layer

| Layer | 검증 항목 | 방법 |
|-------|-----------|------|
| L1 Feature | sync 함수 호출 여부 | 코드 추적 |
| L2 Data | 4개 파일 내용 변경 확인 | 파일 직접 열기 |
| L3 UI/UX | 이번 주 탭 완료 세션 수 반영 | 화면 확인 |
| L4 E2E | 저장 → sync → 기록 탭 반영 | 전체 흐름 |

## E2E QA

```
훈련 기록 저장
  → sync_after_save 호출 확인
  → 주간 계획 파일 해당 날짜 행 ✅ 확인
  → CURRENT_STATUS.md 오늘 날짜 내용 확인
  → 통증 있으면 INJURY_HISTORY.md 행 추가 확인
  → 거리 있으면 RUNNING_HISTORY.md 행 추가 확인
  → 이번 주 탭 done_count 증가 확인
```

## Definition of Done

- [ ] 4개 파일 갱신 확인
- [ ] 중복 방지 로직 통과
- [ ] 기존 마킹 보존 확인
- [ ] 통증/러닝 조건부 갱신 확인

---

---

# F06 — 이번 주 탭 레이아웃 및 요약 카드

## Feature 정의

이번 주 탭은 다음 순서로 렌더링한다.

1. D-day 칩 (목표 대회까지 남은 일수)
2. **주간 요약 카드** (링 + 완료 거리/세션 + 목표 진행 바)
3. **7일 훈련 일정** (요일별 계획 리스트)
4. "이번 주 성장 리포트 만들기 →" (Primary 버튼)
5. "✏️ 계획 조정 요청" (Expander, 계획 생성 폼)

## Pass Criteria

- [ ] 주간 요약 카드가 7일 일정보다 **위**에 위치
- [ ] 요약 카드에 `{week_km:.1f} km`, `{done_count}/{total_count}`, `{pct_w}%` 링 표시
- [ ] "이번 주 성장 리포트 만들기 →" 버튼이 `use_container_width=True`로 전체 너비
- [ ] "계획 조정 요청" expander가 버튼 **아래** 위치
- [ ] 7일 일정에서 완료 세션은 녹색 체크 원, 미실시는 회색 × 표시
- [ ] 오늘 행에 "오늘" 배지 + 좌측 강조 border 표시

## Failure Scenario

| ID | 실패 시나리오 | 발생 조건 | 재현 방법 |
|----|-------------|-----------|-----------|
| F06-F1 | 요약 카드가 일정 아래 위치 | 렌더링 순서 오류 | 페이지 스크롤 확인 |
| F06-F2 | `pct_w` 100 초과 | `goal_km = 0` 일 때 나누기 | 주간 목표 km 미설정 |
| F06-F3 | 오늘 날짜 행 강조 누락 | 날짜 파싱 실패 | 계획 날짜 형식 비일치 |
| F06-F4 | 완료/미완료 아이콘 오판정 | `is_done_r` 판단 오류 | log 없는 과거 날짜 |

## Test Scenario

### TC-F06-01: 레이아웃 순서
1. 이번 주 탭 접속
2. 화면 상단에서 순서 확인: 요약 카드 → 7일 일정 → 리포트 버튼 → 조정 요청 expander
3. 스크롤 없이 요약 카드 > 일정 순서 확인

### TC-F06-02: 요약 카드 정확성
1. 현재 week_km, done_count, total_count 직접 계산
2. 화면 요약 카드 숫자와 일치 확인
3. 링 퍼센트 = `min(100, int(week_km / goal_km * 100))` 계산 결과와 일치

### TC-F06-03: 일정 상태 아이콘
1. 과거 완료 날짜 → 녹색 ✓ 원 확인
2. 과거 미완료 날짜 → 빨간 × 원 확인
3. 오늘 날짜 → "오늘" 배지 + 주황 border 확인
4. 미래 날짜 → 기본 아이콘 + 소요시간 표시

## Verification Layer

| Layer | 검증 항목 | 방법 |
|-------|-----------|------|
| L1 Feature | 요약 카드 데이터 정확성 | `week_km`, `done_count` 직접 계산 비교 |
| L2 Data | `_parse_weekly_rows()` 날짜/훈련/소요시간 파싱 | 계획 파일 vs 화면 비교 |
| L3 UI/UX | 레이아웃 순서, 아이콘 색상, 배지 | 화면 스크린샷 |
| L4 E2E | 훈련 저장 → 이번 주 탭 집계 즉시 반영 | 전체 흐름 |

## E2E QA

```
훈련 1회 저장 완료
  → 이번 주 탭 접속
  → 요약 카드 week_km 증가 확인
  → done_count 증가 확인
  → 7일 일정 해당 날짜 녹색 ✓ 확인
  → 목표 진행 바 % 증가 확인
```

## Definition of Done

- [ ] 레이아웃 순서 (요약 카드 → 일정 → 버튼 → expander) 확인
- [ ] 요약 카드 수치 정확성 확인
- [ ] 일정 아이콘 완료/미완료/오늘 구분 확인
- [ ] `goal_km = 0` edge case 처리 확인

---

---

# F07 — 주간 계획 수립 (AI 생성 + 저장)

## Feature 정의

"계획 조정 요청" expander 내의 폼에서  
일정 제약, 컨디션, 통증을 입력받아  
`WEEKLY_PLAN_PROMPT` 기반 AI가 주간 훈련 계획을 생성하고  
`fm.save_weekly_plan(body)` 로 저장한다.

**저장 파일**: `40-training-log/weekly/YYYY-WXX_plan.md`  
**필수 포함 섹션**: `## 주간 훈련 계획`, `## 훈련 기록`, `## 주간 평가`

## Pass Criteria

- [ ] 생성된 계획에 `## 훈련 기록 (실행 후 기입)` 섹션 자동 추가
- [ ] 생성된 계획에 `## 주간 평가 (주 종료 후 작성)` 섹션 자동 추가
- [ ] 통증 1/10 이상 → 계획 강도 🟡 이하로 고정
- [ ] 공휴일/주말 헬스장 세션 미배정
- [ ] 저장 후 `st.success("저장 완료!")` 표시 + `st.rerun()`
- [ ] 저장 후 S0 → S1 전환 (오늘 탭에서)
- [ ] `fm.save_weekly_plan(body)` 호출 후 `st.cache_data.clear()` 실행

## Failure Scenario

| ID | 실패 시나리오 | 발생 조건 | 재현 방법 |
|----|-------------|-----------|-----------|
| F07-F1 | 저장 후 S0 유지 | 캐시 미갱신 | 저장 후 오늘 탭 접속 |
| F07-F2 | 주말에 헬스장 세션 배정 | 프롬프트 조건 미반영 | 토/일 포함 주간 계획 확인 |
| F07-F3 | `## 훈련 기록` 섹션 누락 | AI 응답에 이미 포함됐다고 판단 | 응답에 `## 훈련 기록` 없는 경우 |
| F07-F4 | 이전 주 계획 덮어쓰기 | 파일명 계산 오류 | 주차 경계에서 저장 |

## Test Scenario

### TC-F07-01: S0 상태에서 최초 계획 생성
1. 주간 계획 파일 없는 상태 → 이번 주 탭 접속
2. "✏️ 계획 조정 요청" expander 자동 펼침 확인 (`expanded=True`)
3. 일정: "수요일 회식", 컨디션: "보통" 입력
4. "이번 주 계획 만들기 →" 클릭 → spinner "이번 주 계획 작성 중..." 확인
5. 생성된 계획 미리보기: 요일별 훈련 일정 포함 확인
6. "이번 주 계획으로 저장 →" 클릭 → "저장 완료!" 확인
7. 파일 확인: `grep -c "## 훈련 기록\|## 주간 평가" 40-training-log/weekly/YYYY-WXX_plan.md` → 2
8. 오늘 탭 접속 → S1 전환 (세션 히어로 + 카드 표시) 확인

### TC-F07-02: 주말 세션 미배정 검증
1. 계획 생성 → 미리보기에서 토요일/일요일 행 확인
2. 토/일 행에 헬스장 세션 (인터벌, 웨이트 등) 없음 확인
3. 토/일: 휴식 또는 선택 세션만 허용

### TC-F07-03: 통증 조건 반영
1. 통증 체크박스 ON → "왼쪽 발목" / 2/10 입력
2. "이번 주 계획 만들기 →" 클릭
3. 생성된 계획에 🟡 이하 강도 표시 확인
4. 인터벌/템포 세션 미포함 확인

### TC-F07-04: 계획 있을 때 expander 접힘 확인
1. 주간 계획 존재 상태 → 이번 주 탭 접속
2. "✏️ 계획 조정 요청" expander 접혀있음 확인 (`expanded=False`)

## Verification Layer

| Layer | 검증 항목 | 방법 |
|-------|-----------|------|
| L1 Feature | 저장 버튼 → 파일 생성 + 섹션 포함 | 파일 확인 |
| L2 Data | 계획 파일 날짜/요일 정확성, 소요시간 형식 | 파일 직접 검토 |
| L3 UI/UX | 미리보기 → 저장 → success 메시지 → rerun | 화면 관찰 |
| L4 E2E | 계획 저장 → 오늘 탭 S1 전환 → 당일 계획 생성 | 전체 흐름 |

## E2E QA

```
계획 없는 상태 (S0)
  → 이번 주 탭 → 계획 조정 요청
  → 일정/컨디션/통증 입력
  → AI 계획 생성 확인
  → 저장 클릭
  → 오늘 탭 → S1 전환 확인
  → 7일 일정에 요일별 훈련 표시 확인
```

## Definition of Done

- [x] 파일 생성 + 필수 섹션 포함 확인 — `2026-W24_plan.md` 8,264 bytes, ## 훈련 기록 + ## 주간 평가 포함
- [x] 저장 후 S1 전환 가능 조건 충족 — plan_content 있음 확인
- [ ] 통증 조건 반영 확인 (TC-F07-03) — 선택적
- [ ] 주말 헬스장 미배정 확인 (TC-F07-02) — 선택적

---

---

# F08 — 이번 주 성장 리포트

## Feature 정의

"이번 주 성장 리포트 만들기 →" 클릭 시  
이번 주 daily log 전체 + 최근 4주 계획 + 프로필을 AI에 전달해  
`WEEKLY_EVALUATION_PROMPT` 기반 평가 리포트를 생성하고  
`fm.save_weekly_evaluation(body)` 로 저장한다.

**부분 평가**: 주 종료 전 생성 시 "예 (주 미종료)" 메타 포함

## Pass Criteria

- [ ] "이번 주 성장 리포트 만들기 →" 버튼이 7일 일정 **아래**, 전체 너비로 표시
- [ ] 주 미종료 시 `st.caption("주 종료 전 생성하면 현재까지 기록만 반영됩니다.")` 표시
- [ ] AI 응답에 수행률, 최근 4주 추세, sub 3:30 준비도 포함
- [ ] "리포트 저장 →" 클릭 시 `YYYY-WXX_evaluation.md` 저장
- [ ] 저장 파일에 `## 평가 메타` 섹션 (평가 시점, 부분 평가 여부) 포함

## Failure Scenario

| ID | 실패 시나리오 | 발생 조건 | 재현 방법 |
|----|-------------|-----------|-----------|
| F08-F1 | 리포트 버튼 누락 | 탭 레이아웃 위치 변경 오류 | 이번 주 탭 스크롤 |
| F08-F2 | 수행률 계산 오류 | ✅/⚠️/❌ 파싱 실패 | 기호 없는 훈련 기록 |
| F08-F3 | 4주 추세 미포함 | `get_recent_week_plans(weeks=4)` 반환 빈 리스트 | 과거 주간 파일 없는 환경 |
| F08-F4 | 부분 평가 플래그 오판 | `today < week_end` 조건 오류 | 일요일에 생성 |

## Test Scenario

### TC-F08-01: 리포트 생성 및 저장
1. 주 중반 (수~목) 접속
2. 이번 주 탭 → "이번 주 성장 리포트 만들기 →" 클릭
3. `st.caption` "현재까지 기록만 반영" 표시 확인
4. 리포트 생성 후 표시
5. "리포트 저장 →" 클릭
6. `40-training-log/weekly/YYYY-WXX_evaluation.md` 존재 확인
7. 파일에 `## 평가 메타` + 부분 평가: 예 확인

### TC-F08-02: 전체 평가 (일요일)
1. 일요일 접속
2. 리포트 생성
3. 파일 메타에 `부분 평가: 아니오` 확인

## Verification Layer

| Layer | 검증 항목 | 방법 |
|-------|-----------|------|
| L1 Feature | 리포트 생성 + 저장 | 파일 확인 |
| L2 Data | 수행률 계산 정확성 (✅=1, ⚠️=0.5, ❌=0) | 직접 계산 비교 |
| L3 UI/UX | 버튼 위치 (일정 아래), 캡션, 저장 버튼 | 화면 확인 |
| L4 E2E | 훈련 저장 → 리포트 생성 → 저장 파일 확인 | 전체 흐름 |

## E2E QA

```
이번 주 2~3회 훈련 저장
  → 이번 주 탭 → 리포트 만들기 클릭
  → 수행률 % 포함 확인
  → 최근 4주 추세 섹션 확인
  → sub 3:30 준비도 언급 확인
  → 저장 → 파일 생성 확인
```

## Definition of Done

- [ ] 리포트 생성 + 파일 저장 확인
- [ ] 부분/전체 평가 플래그 정확성 확인
- [ ] 수행률 계산 정확성 확인
- [ ] 버튼 위치 (7일 일정 아래) 확인

---

---

# F09 — 계획 조정 요청

## Feature 정의

"✏️ 계획 조정 요청" expander는  
주간 계획이 없을 때 자동 열리고,  
있을 때는 수동으로 열어서 계획을 수정·재생성한다.

리포트 버튼 **아래** 위치.  
기존 "이번 주 계획 다시 만들기" 에서 명칭 변경됨.

## Pass Criteria

- [ ] expander 레이블이 "✏️ 계획 조정 요청"
- [ ] 주간 계획 없을 때 `expanded=True`로 자동 펼침
- [ ] 주간 계획 있을 때 `expanded=False` (리포트 버튼 아래 접혀있음)
- [ ] 폼에 "못 하는 날 / 특별 일정", 컨디션 슬라이더, 통증 체크박스 포함
- [ ] 생성된 계획을 미리보기 후 "이번 주 계획으로 저장 →" 저장 가능
- [ ] 저장 후 `st.rerun()` → 계획 반영

## Failure Scenario

| ID | 실패 시나리오 | 발생 조건 | 재현 방법 |
|----|-------------|-----------|-----------|
| F09-F1 | expander가 리포트 버튼 위에 위치 | 렌더링 순서 오류 | 이번 주 탭 스크롤 순서 확인 |
| F09-F2 | 계획 있어도 자동 펼침 | `expanded=not plan_content` 오류 | 계획 있는 상태에서 탭 접속 |
| F09-F3 | 계획 없어도 접혀있음 | 동상 | 계획 없는 상태에서 탭 접속 |

## Test Scenario

### TC-F09-01: 자동 열림 확인
1. 주간 계획 파일 삭제 → 이번 주 탭 접속
2. "계획 조정 요청" expander가 자동으로 열려있음 확인

### TC-F09-02: 수동 접힘 확인
1. 주간 계획 존재 상태 → 이번 주 탭 접속
2. "계획 조정 요청" expander가 접혀있음 확인
3. 클릭 후 폼 내용 표시 확인

## Verification Layer

| Layer | 검증 항목 | 방법 |
|-------|-----------|------|
| L1 Feature | 레이블 변경, 자동 열림 조건 | 화면 확인 |
| L3 UI/UX | expander 위치, 폼 구성 | 화면 스크롤 |

## Definition of Done

- [ ] 레이블 "계획 조정 요청" 확인
- [ ] 자동 열림/접힘 조건 확인
- [ ] 리포트 버튼 아래 위치 확인

---

---

# F10 — 기록 탭 (운동 기록 / 주간 통계)

## Feature 정의

기록 탭은 상단 이번 주 집계 + 2개 서브탭으로 구성된다.

**상단 고정 섹션** (서브탭 위):
- 이번 주 km / 완료 회수 / 평균 페이스 3개 stat 카드

**서브탭:**
- **운동 기록**: 최근 30일 daily log 목록 (주차별 섹션 헤더 포함) + 카드 클릭 시 상세 팝업
- **주간 통계**: 주차별 집계 차트/테이블

## Pass Criteria

- [ ] 기록 탭 진입 시 상단에 이번 주 km / 완료 회수 / 평균 페이스 3개 stat 표시
- [ ] 이번 주 km stat = `week_km` 전역값과 일치
- [ ] 운동 기록 서브탭: 최근 30일 log 카드 목록 (날짜, 훈련 종류, 거리, 회복 뱃지)
- [ ] 카드 클릭 → 상세 팝업 오픈
- [ ] 팝업에 거리, 페이스, 심박, 케이던스, 코치 리뷰 표시
- [ ] 주간 통계 서브탭: 주차별 데이터 표시

## Failure Scenario

| ID | 실패 시나리오 | 발생 조건 | 재현 방법 |
|----|-------------|-----------|-----------|
| F10-F1 | 기록 목록 빈 화면 | `get_daily_logs()` 빈 리스트 | 로그 없는 환경 |
| F10-F2 | 팝업에 수치 없음 | regex 파싱 실패 | 수치 없는 log 파일 |
| F10-F3 | 이번 주 통계 불일치 | 전역 `week_km` vs 탭 내 재집계 불일치 | 직접 비교 |

## Test Scenario

### TC-F10-01: 상단 이번 주 집계 stat
1. 기록 탭 접속 (서브탭 선택 전)
2. 상단에 "X.X km 이번 주" / "N회 완료" / "M:SS/km 평균 페이스" 3개 stat 표시 확인
3. km 수치 = 이번 주 완료된 daily log 거리 합산과 일치 확인

### TC-F10-02: 운동 기록 카드 목록 + 상세 팝업
1. "운동 기록" 서브탭 접속 → "최근 활동" 레이블 확인
2. 최근 30일 log 카드 목록 표시 확인 (주차별 섹션 헤더 포함)
3. 카드에 날짜, 훈련 종류, 거리, 회복 뱃지 표시 확인
4. 카드 클릭 → 상세 팝업 오픈
5. 팝업에 km, 페이스, 심박, 케이던스, 코치 리뷰 표시 확인

### TC-F10-03: 주간 통계 서브탭
1. "주간 통계" 서브탭 접속
2. 이번 주 데이터 포함 확인 ("이번 주" 또는 주차 표기)

## Verification Layer

| Layer | 검증 항목 | 방법 |
|-------|-----------|------|
| L1 Feature | 카드 목록 + 팝업 오픈 | 수동 클릭 |
| L2 Data | 수치 파싱 정확성 + 집계 일치 | 파일 vs 화면 비교 |
| L3 UI/UX | 카드 레이아웃, 팝업 내용 | 화면 스크린샷 |
| L4 E2E | 훈련 저장 → 기록 탭 즉시 반영 | 전체 흐름 |

## Definition of Done

- [x] 카드 목록 + 상세 팝업 동작 확인 *(Playwright P2/P5/P6/P7 — PASS)*
- [x] 주간 통계 서브탭 렌더링 확인 *(Playwright P8 — PASS)*
- [ ] 이번 주 집계 전역값과 일치 확인 *(수동 검증 필요)*

---

---

# F11 — 설정 탭 Profile.md / Goal.md 연동

## Feature 정의

설정 탭은 `Profile.md`와 `Goal.md`를 소스로 읽어  
기본 정보, PB 기록, 목표를 iOS 스타일 편집 행으로 표시한다.  
편집 시 해당 마크다운 파일을 직접 업데이트한다.

**읽기 함수**: `fm.parse_profile_fields()`, `fm.parse_goal_fields()`  
**쓰기 함수**: `fm.update_profile_field()`, `fm.update_goal_field()`

| 섹션 | 소스 | 편집 가능 필드 |
|------|------|-------------|
| 기본 정보 | Profile.md | 닉네임, 나이, 키, 체중 |
| 개인 최고 기록 | Profile.md | 10km, 하프마라톤, 풀마라톤 |
| 목표 | Goal.md | 주요 목표 (텍스트), 목표 날짜 |
| 훈련 설정 | app_settings.json | 주간 목표 거리, 최대 심박, 안정 심박, VO2 Max |

## Pass Criteria

- [ ] 설정 탭 접속 시 Profile.md에서 닉네임, 나이, 키, 체중 자동 로드
- [ ] Profile.md에 값 없는 필드 → "미입력" 표시
- [ ] 닉네임 행 클릭 → "프로필 편집" 다이얼로그 오픈
- [ ] 새 값 입력 후 "저장 →" 클릭 → Profile.md 해당 줄 업데이트
- [ ] 저장 후 설정 탭 새로고침 시 변경된 값 표시
- [ ] 목표 텍스트 편집 → Goal.md `## 2026 목표` 섹션 내용 업데이트
- [ ] 목표 날짜 편집 → Goal.md 날짜 업데이트
- [ ] 히어로 카드 닉네임/목표 요약이 Profile.md/Goal.md 값 우선 표시
- [ ] 10km PB "42분 13초 2025년 3월" → 기록 탭에 표시 (Profile.md 내용 반영)

## Failure Scenario

| ID | 실패 시나리오 | 발생 조건 | 재현 방법 |
|----|-------------|-----------|-----------|
| F11-F1 | Profile.md 파싱 실패 | regex 패턴 불일치 | 파일 형식 변경 후 재접속 |
| F11-F2 | 저장 후 값 미갱신 | `st.cache_data.clear()` 미호출 | 편집 저장 후 탭 재접속 |
| F11-F3 | 목표 텍스트 저장 시 2027 목표 섹션 삭제 | regex substitution 과도한 매칭 | 저장 후 Goal.md 파일 확인 |
| F11-F4 | 닉네임에 특수문자 입력 시 regex 오류 | `re.sub` replacement에 `\` 포함 | `\` 포함 닉네임 저장 |
| F11-F5 | Profile.md 없는 환경 | 파일 미존재 | Profile.md 삭제 후 접속 |

## Test Scenario

### TC-F11-01: 기본 정보 로드
1. 설정 탭 접속
2. "기본 정보" 섹션에서 각 행 값 확인
3. Profile.md 파일 내 실제 값과 일치 확인
4. 미입력 필드 → "미입력" 표시 확인

### TC-F11-02: 닉네임 편집
1. "닉네임" 행 클릭
2. "프로필 편집" 다이얼로그 오픈 확인
3. "고고조2" 입력 → "저장 →" 클릭
4. Profile.md `닉네임:` 라인이 `닉네임: 고고조2` 로 변경 확인
5. 설정 탭 재접속 → 닉네임 행에 "고고조2" 표시 확인

### TC-F11-03: PB 기록 편집
1. "10km" 행 클릭
2. "41분 30초" 입력 → 저장
3. Profile.md `10km :` 라인 업데이트 확인

### TC-F11-04: 목표 텍스트 편집
1. "주요 목표" 행 클릭
2. "목표 편집" 다이얼로그 → 텍스트 에어리어
3. 새 목표 입력 → 저장
4. Goal.md `## 2026 목표` 섹션 내용 업데이트 확인
5. `## 2027목표` 섹션 유지 확인

### TC-F11-05: 목표 날짜 편집
1. "목표 날짜" 행 클릭
2. 날짜 피커 → 새 날짜 선택 → 저장
3. Goal.md 날짜 업데이트 확인
4. D-day 칩 숫자 변경 확인

### TC-F11-06: 파일 없는 환경
1. Profile.md 파일 이름 임시 변경
2. 설정 탭 접속
3. 모든 필드 "미입력" 표시, 앱 오류 없음 확인

## Verification Layer

| Layer | 검증 항목 | 방법 |
|-------|-----------|------|
| L1 Feature | 편집 → 파일 저장 → 재로드 시 반영 | 파일 직접 열기 |
| L2 Data | `parse_profile_fields()` 파싱 정확성 | 함수 직접 테스트 |
| L3 UI/UX | 행 렌더링, 다이얼로그 오픈, 저장 후 화면 갱신 | 화면 관찰 |
| L4 E2E | Profile 편집 → AI 계획에 새 정보 반영 | 계획 생성 후 내용 확인 |

## E2E QA

```
설정 탭 → 기본 정보 로드 확인
  → 닉네임 편집 → Profile.md 업데이트 확인
  → PB 10km 편집 → 파일 업데이트 확인
  → 목표 텍스트 편집 → Goal.md 업데이트 확인
  → 목표 날짜 편집 → D-day 칩 변경 확인
  → 이번 주 탭 계획 조정 요청 → 새 프로필/목표 반영 확인
```

## Definition of Done

- [ ] Profile.md 6개 필드 로드/편집/저장 확인
- [ ] Goal.md 2개 필드 로드/편집/저장 확인
- [ ] 저장 후 `st.cache_data.clear()` → 화면 갱신 확인
- [ ] 2027 목표 섹션 보존 확인
- [ ] 파일 없는 환경 "미입력" 처리 확인

---

---

# F12 — 설정 변경 시 주간 계획 자동 갱신

## Feature 정의

Profile.md 또는 Goal.md 필드 편집 저장 시  
`st.session_state["_settings_changed"] = True` 플래그가 설정되고,  
설정 탭 재진입 시 `_plan_refresh_dialog()` 가 열려  
"지금 반영하기" 확인 후 주간 계획을 자동 재생성한다.

**트리거**: `_edit_profile_dialog()` 또는 `_edit_goal_dialog()` 에서 저장 시  
**다이얼로그**: `@st.dialog("계획 갱신")` — `_plan_refresh_dialog()`  
**재생성**: `WEEKLY_PLAN_PROMPT` + 업데이트된 Profile.md + Goal.md

## Pass Criteria

- [ ] 프로필/목표 편집 저장 → 설정 탭 재진입 시 "계획 갱신" 다이얼로그 자동 오픈
- [ ] 다이얼로그에 "프로필 또는 목표 정보가 변경됐어요." 문구 표시
- [ ] "지금 반영하기 →" 클릭 시 `st.spinner("주간 계획 재생성 중...")` 표시
- [ ] 재생성된 계획이 `40-training-log/weekly/YYYY-WXX_plan.md` 에 저장
- [ ] 재생성 계획에 새 Profile.md 내용(변경된 프로필) 반영 확인
- [ ] "나중에" 클릭 시 다이얼로그 닫힘 + `_settings_changed` 플래그 삭제
- [ ] 재생성 성공 후 `_settings_changed` 플래그 삭제

## Failure Scenario

| ID | 실패 시나리오 | 발생 조건 | 재현 방법 |
|----|-------------|-----------|-----------|
| F12-F1 | 다이얼로그 미오픈 | `_settings_changed` 플래그 미설정 | 편집 저장 후 설정 탭 재접속 |
| F12-F2 | 재생성 후 플래그 미삭제 | `st.session_state.pop()` 미호출 | 재생성 완료 후 설정 탭 재접속 → 다이얼로그 재오픈 |
| F12-F3 | 재생성 실패 시 기존 계획 삭제 | API 오류 + 저장 로직 순서 오류 | API 키 없이 "지금 반영" 클릭 |
| F12-F4 | "나중에" 후에도 다이얼로그 반복 | 플래그 미삭제 | 나중에 클릭 후 설정 탭 이동 |
| F12-F5 | 일정 정보 없이 재생성 | 자동 재생성은 일정 미입력으로 진행 | 재생성 계획에 일정 제약 없음 확인 |

## Test Scenario

### TC-F12-01: 다이얼로그 자동 오픈
1. 설정 탭 → 닉네임 편집 → 저장
2. 설정 탭 재진입
3. "계획 갱신" 다이얼로그 자동 오픈 확인

### TC-F12-02: 지금 반영하기 → 계획 재생성
1. 다이얼로그에서 "지금 반영하기 →" 클릭
2. spinner 표시 확인
3. 재생성 완료 → success 메시지 표시
4. `40-training-log/weekly/YYYY-WXX_plan.md` 내용 업데이트 확인
5. 새 계획에 변경된 닉네임 프로필 반영 확인

### TC-F12-03: 나중에 → 플래그 삭제
1. 다이얼로그 → "나중에" 클릭
2. 다이얼로그 닫힘 확인
3. 설정 탭 재접속 → 다이얼로그 재오픈 없음 확인
4. `st.session_state["_settings_changed"]` 키 없음 확인

### TC-F12-04: API 오류 처리
1. ANTHROPIC_API_KEY 제거 (또는 만료)
2. "지금 반영하기" 클릭
3. `st.error()` 메시지 표시 + 기존 계획 유지 확인

### TC-F12-05: 중복 트리거 방지
1. 닉네임 편집 후 설정 탭 재접속 → 다이얼로그 오픈
2. "나중에" 클릭
3. Goal.md 편집 없이 설정 탭 재접속
4. 다이얼로그 미오픈 확인

## Verification Layer

| Layer | 검증 항목 | 방법 |
|-------|-----------|------|
| L1 Feature | 플래그 → 다이얼로그 → 재생성 → 저장 흐름 | 수동 테스트 |
| L2 Data | 재생성 계획 파일에 새 프로필 내용 반영 | 파일 직접 확인 |
| L3 UI/UX | 다이얼로그 문구, spinner, 버튼 배치 | 화면 관찰 |
| L4 E2E | 설정 변경 → 재생성 → 오늘 탭 새 계획 반영 | 전체 흐름 |

## E2E QA

```
설정 탭 → 닉네임 변경 (고고조 → 테스트러너)
  → 저장 → 설정 탭 재접속
  → "계획 갱신" 다이얼로그 자동 오픈 확인
  → "지금 반영하기" 클릭
  → spinner → success 메시지 확인
  → 이번 주 탭 → 7일 일정 표시 확인 (새 계획)
  → 계획 파일에 새 닉네임/목표 반영 확인
  → 설정 탭 재접속 → 다이얼로그 재오픈 없음 확인
```

## Definition of Done

- [x] 편집 저장 → 다이얼로그 자동 오픈 확인 *(test_f12::test_dialog_auto_opens_after_edit)*
- [x] "지금 반영" → 계획 재생성 + 저장 확인 *(test_apply_now_regenerates_plan — mock, 7km + 필수섹션)*
- [x] "나중에" → 플래그 삭제 + 재오픈 없음 확인 *(test_later_clears_flag)*
- [ ] API 오류 시 기존 계획 보존 확인 — 코드 확인(저장은 성공 응답에서만), Playwright 미실행 (선택)
- [ ] 재생성 계획에 새 프로필 정보 반영 확인 — 실 API 품질(수동); 저장 경로는 mock 으로 검증

---

---

# 통합 E2E QA 시나리오

## E2E-01: 신규 사용자 첫 주 전체 사이클

```
1. 앱 최초 접속 (S0)
2. 설정 탭 → 닉네임/나이/PB/목표 입력 (F11)
3. 이번 주 탭 → 계획 조정 요청 → 일정 입력 → 계획 생성 + 저장 (F07)
4. 오늘 탭 → S1 전환 확인 (F01)
5. 당일 훈련 계획 카드 표시 + 섹션 팝업 확인 (F02, F03)
6. 운동 완료 → 기록 입력 + AI 리뷰 저장 (F04)
7. S3 전환 + 회복 뱃지 확인 (F01, F04)
8. sync 후 이번 주 탭 집계 반영 확인 (F05, F06)
9. 일요일 → S5 전환 + 성장 리포트 생성 (F01, F08)
10. 기록 탭 → 이번 주 기록 + 통계 확인 (F10)
```

**통과 기준**: 각 단계 오류 없이 진행, 파일 생성/업데이트 확인

## E2E-02: 설정 변경 → 계획 갱신 흐름

```
1. 기존 주간 계획 존재 상태
2. 설정 탭 → 목표 날짜 변경 (F11)
3. 계획 갱신 다이얼로그 오픈 (F12)
4. "지금 반영하기" → 계획 재생성 (F12)
5. 이번 주 탭 → 새 계획 7일 일정 반영 확인 (F06)
6. 오늘 탭 → 새 계획 기반 당일 카드 생성 확인 (F02)
```

## E2E-03: 통증 상황 코칭 흐름

```
1. 설정 탭 → 나이/PB 확인 (F11)
2. 이번 주 계획 조정 요청 → 통증 4/10 입력 → 회복 계획 생성 (F07)
3. 오늘 탭 → 회복 훈련 카드 표시 확인 (F02)
4. 훈련 후 기록 → 통증 정보 입력 (F04)
5. sync → 부상 이력 추가 확인 (F05)
6. 주간 리포트에 통증/회복 필요도 반영 확인 (F08)
```

---

---

# 글로벌 Failure Scenario (Cross-Feature)

| ID | 시나리오 | 영향 Feature | 검증 상태 |
|----|---------|-------------|-----------|
| G01 | ANTHROPIC_API_KEY 미설정 | F02, F04, F07, F08, F09, F12 | ✅ 자동화 — `test_g01_api_key.py`(키 미설정 경고) + `test_f04::test_save_api_error_keeps_form`(COACH_MOCK=`__ERROR__` → `st.error`, 빈 화면 없음) |
| G02 | `st.cache_data.clear()` 미호출 | F01, F06, F07 | ✅ 자동화 — `test_globals::test_g02` (7개 저장 함수 소스에 `cache_data.clear` 가드) |
| G03 | 파일 권한 오류 (OSError) | F04, F05, F07, F11 | ✅ 자동화 — `test_globals::test_g03` (읽기전용 KB → `_write_kb` 예외 미전파) |
| G04 | 주차 경계 오류 (월요일 00:00) | F01, F06, F07 | ✅ 자동화 — `test_globals::test_g04` (일↔월 ISO 주차 분리 확인) |
| G05 | `plan_content = None` | F02, F06, F07 | ✅ 자동화 — `test_globals::test_g05` (빈/None 파싱 안전) + F01 S0 Playwright |
| G06 | AI 응답 형식 미준수 | F02, F04, F08 | ✅ 자동화(파싱 견고성) — `test_globals::test_g06` (섹션 누락 로그 파싱) + F02 카드 파싱 기능 테스트. **AI 응답 품질 자체는 수동** |

---

# Definition of Done (프로젝트 전체)

아래 조건을 **모두** 만족해야 프로젝트 완료로 판단한다.

## 필수 조건

- [ ] **F01~F12** 각 Feature의 Pass Criteria 전항목 충족
- [ ] **F01~F12** 각 Feature의 Failure Scenario 전항목 재현 + 원인 확정
- [ ] **E2E-01~E2E-03** 통합 시나리오 전항목 통과
- [ ] **G01~G06** 글로벌 실패 시나리오 처리 확인

## 데이터 무결성 조건

- [ ] Profile.md / Goal.md 편집 후 AI 계획에 반영 확인
- [ ] 훈련 저장 후 4개 파일 자동 동기화 확인
- [ ] 캐시 갱신 후 화면 데이터 일치 확인

## UI/UX 조건

- [ ] 오늘 탭 상단 잘림 없음 (Streamlit 헤더 숨김)
- [ ] 카드 텍스트 1줄 truncate
- [ ] 섹션 팝업 분리 (워밍업/메인/쿨다운 각각)
- [ ] 이번 주 탭 레이아웃 순서 (요약 카드 → 7일 일정 → 리포트 버튼 → 조정 요청)
- [ ] 설정 탭 Profile.md/Goal.md 연동 값 표시

## Playwright 자동화 조건

- [x] F01 State Machine — `tests/test_f01_state_machine.py` 6/6 PASS (S0/S2/S3/S4/S5)
- [x] F03 훈련 카드 UI — `tests/test_f03_daily_card_ui.py` 12/12 PASS
- [x] F04 저장→S3 전환 — `tests/test_f04_save_flow.py` 3/3 PASS (COACH_MOCK)
- [x] F10 기록 탭 — `tests/test_f10_records_tab.py` 8/8 PASS
- [x] F11 Profile 파싱/저장 — `tests/test_f11_profile_fields.py` 5/5 PASS (단위)
- [x] F12 계획 갱신 다이얼로그 — `tests/test_f12_settings_dialog.py` 3/3 PASS (COACH_MOCK)
- [x] G01~G06 글로벌 실패 — `test_g01_api_key.py` 1/1 + `test_globals.py` 5/5 PASS
- [ ] F02 AI 계획 생성 (실 응답 품질) — 수동 (실 API 의존)
- [ ] F07 주간 계획 생성 (실 응답 품질) — 수동 (실 API 의존)
- [ ] F08 성장 리포트 (실 응답 품질) — 수동 (실 API 의존)

## 회귀 테스트 조건

- [ ] 신규 기능 추가 후 기존 F01~F12 Pass Criteria 재확인
- [ ] API 모델 변경 후 응답 형식 파싱 재확인
- [x] `pytest tests/` 전체 실행 후 49/49 PASS 유지 (2026-06-08 확인 — count_sessions 6 + F01 6 + F03 12 + F04 3 + F10 8 + F11 5 + F12 3 + G01 1 + globals 5)

---

*작성 기준일: 2026-06-06*  
*최종 검증 업데이트: 2026-06-07 (app.py 전체 코드 리뷰 → F01/F02/F04/F07/F10 시나리오 실제 흐름에 맞게 재작성)*  
*검증 헌법: VERIFICATION_PHILOSOPHY.md (srt_tool/00-system)*  
*프로젝트: AI 러닝 코치 웹앱 (performance-coach)*
