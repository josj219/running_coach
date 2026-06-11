# AI 러닝 코치 앱 종합 점검 리포트

- 팀: kkirikkiri-analysis-20260606-1432-6cdc
- 점검 일자: 2026-06-06
- 점검 관점: 전체 구조/아키텍처 · 코드 품질 · 사용성/UX
- 점검 대상: webapp/app.py, webapp/utils/, .claude/skills/, CLAUDE.md, 데이터 레이어

---

## 요약

| 관점 | 이슈 수 | 치명 | 주의 | 경미 |
|------|--------|------|------|------|
| 구조/아키텍처 | 7건 | 2건 | 2건 | 3건 |
| 코드 품질 | 14건 | 3건 | 6건 | 5건 |
| 사용성/UX | 7건 | 1건 | 4건 | 2건 |
| **합계** | **28건** | **6건** | **12건** | **10건** |

---

## 파트 1 — 구조/아키텍처

### [치명] S1: app.py 2,065줄 단일 파일

```
파일: webapp/app.py:1~2065
```

탭 UI 로직 4개 전체가 단일 파일에 인라인. CSS(220줄) + 전역 헬퍼 함수(30개) + with tab_X 블록(각 수백 줄)이 혼재.

- `with tab_home:` 블록: ~541줄 (추정)
- `with tab_week:` 블록: L1547~1833 (약 286줄)
- `with tab_record:` 블록: 내부 서브탭 포함 수백 줄
- `with tab_settings:` 블록: 약 130줄

**영향**: 특정 탭 기능 수정 시 전체 파일 탐색 필요. 버그 격리 불가. 테스트 작성 불가.

**개선 방향**: `webapp/tabs/tab_home.py`, `tab_week.py`, `tab_record.py`, `tab_settings.py` 로 분리. app.py는 탭 조합과 공통 초기화만 담당.

---

### [치명] S2: pages/ 레거시 파일 미삭제

```
파일: webapp/pages/_*.py (5개, 621줄)
```

app.py가 탭 구조로 전환되며 pages/ 5개 파일이 비활성화됐지만 삭제되지 않음. git status에서 `D` (삭제 예정)으로 표시. `__pycache__`의 `.pyc`가 잔류해 혼란 유발.

**영향**: Streamlit이 pages/ 파일을 감지해 사이드바 네비게이션을 생성할 수 있음 (현재 CSS로 `display:none` 강제 숨김 — app.py:66). pages/ 파일에 수정을 가하면 실제로 적용되지 않는데 적용된 것으로 착각 가능.

**개선 방향**: `git rm webapp/pages/_*.py` + `__pycache__` 정리.

---

### [주의] S3: `_session_counts` / `_count_sessions` 중복 구현

```
파일: app.py:355~374 (함수명: _session_counts)
파일: sync.py:184~203 (함수명: _count_sessions)
```

동일한 주간 계획 표에서 세션 수를 파싱하는 로직이 두 파일에 독립 구현됨. 함수명만 다를 뿐 로직 동일. 파싱 규칙이 변경되면 두 곳 모두 수정해야 함.

**개선 방향**: `file_manager.py`에 단일 함수로 통합. app.py와 sync.py 모두 그것을 호출.

---

### [주의] S4: `eval_path` 경로 직접 조합

```
파일: app.py:1123~1127
```

`os.path.join(fm.get_base_dir(), "40-training-log", "weekly", fname)` 방식으로 하드코딩. file_manager에 동일 패턴의 경로 헬퍼가 있는데 weekly evaluation path 헬퍼만 누락됨.

**개선 방향**: `file_manager.py`에 `_weekly_eval_path()` 헬퍼 추가.

---

### [경미] S5: 모델명 하드코딩

```
파일: webapp/utils/claude_client.py:17
MODEL = "claude-sonnet-4-6"
```

환경변수나 설정값으로 관리되지 않음.

**개선 방향**: `os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")` 또는 app_settings.json에 추가.

---

### [경미] S6: 미사용 상수 `DAILY_PLAN_PROMPT`

```
파일: webapp/utils/prompts.py:125~166
```

`DAILY_PLAN_PROMPT` 정의됐으나 app.py에서 사용되지 않음. `DAILY_PLAN_CARD_PROMPT`만 사용.

**개선 방향**: 삭제하거나 주석으로 "미사용 — DAILY_PLAN_CARD_PROMPT 사용" 표시.

---

### [경미] S7: .claude/skills/ ↔ prompts.py 이중 관리

```
파일: .claude/skills/ (5개 SKILL.md) vs webapp/utils/prompts.py (5개 상수)
```

CLI 스킬과 webapp 프롬프트가 동기화 없이 이중 관리됨. 코칭 로직 변경 시 두 곳 모두 수정 필요.

**개선 방향**: webapp이 `.claude/skills/` SKILL.md를 직접 읽어 시스템 프롬프트로 사용하거나, SKILL.md를 prompts.py 생성의 단일 소스로 지정.

---

## 파트 2 — 코드 품질

### [치명] C1: 모듈 레벨 파일 I/O — 매 rerun마다 재실행

```
파일: webapp/app.py 상단 (approximate line ~200~280)
```

Streamlit 앱은 사용자 인터랙션마다 전체 스크립트를 재실행함. 모듈 레벨에서 `fm.read_profile()`, `fm.read_goal()`, `fm.get_current_week_plan()` 등 최소 7개의 파일 읽기가 캐시 없이 실행됨.

**영향**: 버튼 클릭 한 번마다 7회 이상의 파일 시스템 접근 → 반응 지연. 파일이 많아질수록 선형 악화.

**개선 방향**:
```python
@st.cache_data(ttl=60)
def load_profile():
    return fm.read_profile()
```
읽기 전용 함수에 `@st.cache_data` 적용. 쓰기 후 `st.cache_data.clear()` 호출.

---

### [치명] C2: `_write_kb()` — 예외 처리 없는 파일 쓰기

```
파일: webapp/utils/file_manager.py (내부 함수)
```

`_sync_settings_to_markdown()` 내 파일 쓰기에 try/except 없음. 파일 권한 오류나 디스크 풀 시 앱이 500 에러로 종료됨.

**개선 방향**:
```python
try:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
except OSError as e:
    st.error(f"설정 저장 실패: {e}")
```

---

### [치명] C3: `_upsert_line` lambda 버그

```
파일: webapp/utils/file_manager.py (_sync_settings_to_markdown 함수 내)
```

`_upsert_line` 함수 정의만 있고 실제로 호출되지 않음 (내부적으로 정의 후 미사용). lambda 내부 로직에 그룹 인덱스 오류가 있음 (groups 수 계산 방식 불일치).

**영향**: 현재는 직접 re.sub로 우회하고 있어 표면상 동작하나, 향후 이 함수를 사용하면 예상치 못한 치환 결과 발생.

**개선 방향**: `_upsert_line` 함수 제거 또는 버그 수정 후 실제 사용.

---

### [주의] C4: `_session_counts` / `_count_sessions` 중복 로직 (구조 이슈와 동일 — 코드 관점)

```
파일: app.py:355 / sync.py:184
```

두 파싱 로직이 달라질 경우 "완료 세션 수"가 앱 표시와 sync.py 처리에서 불일치 발생 가능.

---

### [주의] C5: `done_dates` 루프 내 파일 I/O 7회+

```
파일: webapp/app.py (이번 주 탭 / _week_stats 함수 계열)
```

weekly stats 계산 시 최근 28일치 daily log를 루프로 반복 읽기. 파일당 1회 I/O → 최대 28회 파일 읽기.

**개선 방향**: `fm.get_daily_logs(days=28)` 1회 호출로 일괄 로드 후 메모리에서 파싱. 이미 이렇게 구현된 것 같으나 재확인 필요.

---

### [주의] C6: `icon` 변수 미사용

```
파일: webapp/app.py (session_state 또는 상태 계산 블록)
```

`icon` 변수가 계산되나 UI에서 사용되지 않는 것으로 확인됨.

---

### [주의] C7: `show_adjust` session_state 미해제

```
파일: webapp/app.py (tab_home S1 또는 S3 상태)
```

`st.session_state["show_adjust"]` 를 True로 세팅 후 False로 되돌리지 않는 경로 존재. 다음 rerun 시 의도치 않게 조정 UI가 열릴 수 있음.

---

### [주의] C8: 설정 탭 toggle — 매 rerun마다 settings 재로드

```
파일: webapp/app.py (with tab_settings: 블록)
```

`fm.read_settings()` 가 `with tab_settings:` 내에서 매 rerun마다 호출됨. 설정 저장 직후 `st.rerun()` 이 발생하면 변경 사항이 반영되나, 불필요한 JSON 파싱이 반복됨.

**개선 방향**: `@st.cache_data` 적용 + 저장 시 캐시 무효화.

---

### [주의] C9: `eval_result_home` f-string 직접 삽입

```
파일: webapp/app.py (tab_home S3 또는 S5 상태)
```

AI 코치 응답 텍스트를 `html_lib.escape()` 없이 f-string으로 HTML에 직접 삽입. AI 응답이 `<script>` 등의 태그를 포함하면 XSS 가능성.

**개선 방향**: `html_lib.escape(eval_result_home)` 적용 또는 `st.markdown()`으로 대체.

---

### [경미] C10: `tab_home` with 블록 541줄

```
파일: webapp/app.py (~400~940 추정)
```

탭 로직이 함수로 분리되지 않아 단일 블록이 541줄에 달함.

---

### [경미] C11: 거리 파싱 regex 5회 중복

```
파일: webapp/app.py (여러 위치)
```

`r"(\d+\.?\d*)\s*km"` 패턴이 최소 5곳에서 반복. 함수로 추출 시 유지보수 간소화.

---

### [경미] C12: HTML 히어로 카드 패턴 4회 중복

```
파일: webapp/app.py (tab_home 각 상태별)
```

히어로 카드 HTML 생성 코드가 S0/S1/S3/S4 상태마다 유사하게 반복. `_hero_card_html()` 함수로 추출 가능.

---

### [경미] C13: 변수명 한영 혼용

```
파일: webapp/app.py (전체)
```

`week_km`, `done_count`, `total_count`는 영어지만 일부 변수는 `페이스값`, `심박값` 식의 한국어 혼용. 팀 작업 시 혼란 유발.

---

### [경미] C14: pages/ 레거시 미정리 (구조 이슈 S2와 동일)

```
파일: webapp/pages/_*.py
```

코드 품질 관점에서도 미사용 코드가 저장소에 남아 있는 것은 유지보수 혼란 유발.

---

## 파트 3 — 사용성/UX

### [치명] U1: `--label-quaternary` 미정의 CSS 변수 5곳 사용

```
파일: webapp/app.py (CSS 변수 참조 위치 다수)
파일: webapp/utils/page_common.py (CSS 변수 정의 블록)
```

`page_common.py`에 CSS 변수 19개가 정의돼 있으나 `--label-quaternary`는 없음. 5곳에서 참조되는데 브라우저가 fallback(투명 또는 black)으로 처리. 의도한 색상이 표시되지 않음.

**개선 방향**: `page_common.py` CSS에 `--label-quaternary: rgba(60,60,67,0.18);` 추가.

---

### [주의] U2: 하드코딩 색상 22+ 인스턴스

```
파일: webapp/app.py (다수 위치)
```

`rgb(28,28,30)`, `rgba(0,0,0,0.05)` 등이 CSS 변수 대신 직접 입력됨. 다크 모드 지원이나 테마 변경 시 이 값들은 자동으로 바뀌지 않음.

**주요 위치**: 히어로 카드 그림자, 세션 카드 배경, 날짜 배지 색상 등.

**개선 방향**: CSS 변수 추가 정의 후 하드코딩 값을 변수로 교체.

---

### [주의] U3: 이번 주 탭 정보 위계 역전

```
파일: webapp/app.py (with tab_week: 블록)
```

시각적으로 가장 큰 요소가 SVG 링 차트 (진행률 %)이나, 러닝 코치 앱에서 사용자의 1차 정보 요구는 "오늘/이번 주에 뭘 해야 하나"임. 7일 스케줄이 링 차트 아래에 위치해 스크롤 없이는 보이지 않을 수 있음.

**개선 방향**: 7일 스케줄을 상단으로 올리고 링 차트는 보조 정보로 우측 또는 하단 배치 검토.

---

### [주의] U4: S1 탭 (훈련 전) 저장 후 피드백 누락

```
파일: webapp/app.py (S2-POST_WORKOUT → 저장 버튼 핸들러)
```

훈련 기록 저장 후 `st.rerun()`으로 S3 상태로 전환되지만 저장 성공/실패 여부 메시지가 없음. 저장이 빠르면 사용자가 저장됐는지 모를 수 있음.

**개선 방향**: `st.success("훈련 기록이 저장됐어요 ✓")` 또는 상태 전환 애니메이션 추가.

---

### [주의] U5: 오늘/이번 주/기록 탭 버튼 레이블 스타일 혼용

```
파일: webapp/app.py (다수 위치)
```

버튼 레이블에 `→`와 `·` 혼용. 일부는 "훈련 계획 보기 →", 일부는 "분석 보기" 형태.

**개선 방향**: 모든 주 CTA 버튼에 `→` 통일. 보조 버튼은 화살표 없음.

---

### [주의] U6: 빈 상태 처리 불균등

```
파일: webapp/app.py (각 탭 조건부 렌더링)
```

- 오늘 탭 (S0): "이번 주 계획이 없어요" 명확한 안내 ✓
- 운동 기록 탭: "기록이 없어요" 안내 있음 ✓
- 주간 통계 탭: `fm.get_daily_logs(days=28)` 없으면 표시 안 함 (조건부)
- 이번 주 탭: 계획 없으면 계획 세우기 유도 있음 ✓

주간 통계 탭 빈 상태에서 첫 사용자 유도 메시지("첫 훈련을 기록해보세요") 없음.

---

### [경미] U7: 이번 주 탭 리포트 저장 버튼 레이아웃 불일치

```
파일: webapp/app.py (tab_week 성장 리포트 저장 버튼)
```

대부분의 버튼은 `use_container_width=True` 사용하는데 해당 버튼만 미적용. 버튼 크기가 일관되지 않음.

---

## 파트 4 — 구조 맵 (현황 요약)

```
webapp/
├── app.py (2,065줄) ← 모든 로직의 95%가 여기에
│   ├── CSS 블록 (~220줄)
│   ├── 전역 헬퍼 함수 (~30개)
│   ├── with tab_home: (~541줄)
│   ├── with tab_week: (~286줄)
│   ├── with tab_record: (~200줄)
│   └── with tab_settings: (~130줄)
└── utils/
    ├── file_manager.py — 파일 CRUD + 경로 헬퍼 (잘 분리됨)
    ├── claude_client.py — API 래퍼 (간결)
    ├── prompts.py — 시스템 프롬프트 상수 (CLI 스킬과 이중화)
    └── sync.py — daily 저장 후 자동 업데이트 (app.py:959에서 호출)

데이터 레이어:
20-knowledge-base/ — AI 코치 장기 메모리 (5개 md + 1개 json)
40-training-log/   — 훈련 기록 (daily/ + weekly/)

.claude/skills/ ← Claude Code CLI 전용 (webapp과 미연결)
```

---

## 우선순위 액션 리스트

### 즉시 처리 (치명 — 6건)

| # | 파일 | 설명 |
|---|------|------|
| C1 | app.py 상단 | `@st.cache_data` 적용으로 매 rerun I/O 제거 |
| C2 | file_manager.py | `_write_kb()` try/except 추가 |
| C3 | file_manager.py | `_upsert_line` lambda 버그 수정 또는 제거 |
| U1 | page_common.py | `--label-quaternary` CSS 변수 추가 |
| S1 | app.py | 탭별 파일 분리 검토 (대형 작업) |
| S2 | pages/ | `git rm webapp/pages/_*.py` + pycache 정리 |

### 단기 처리 (주의 — 12건)

| # | 파일 | 설명 |
|---|------|------|
| C9 | app.py | `eval_result_home` → `html_lib.escape()` 적용 |
| C7 | app.py | `show_adjust` session_state 해제 경로 추가 |
| S3/C4 | app.py + sync.py | `_session_counts` 통합 → file_manager |
| S4 | app.py | `eval_path` → file_manager 헬퍼로 |
| U2 | app.py | 주요 하드코딩 색상 CSS 변수 교체 |
| U4 | app.py | 저장 성공 피드백 추가 |
| U5 | app.py | 버튼 레이블 `→` 통일 |

### 선택적 개선 (경미 — 10건)

| # | 설명 |
|---|------|
| C11 | 거리 파싱 regex → 공통 함수 |
| C12 | 히어로 카드 HTML → `_hero_card_html()` 헬퍼 |
| S5 | 모델명 환경변수 관리 |
| S6 | DAILY_PLAN_PROMPT 미사용 상수 제거 |
| S7 | CLI 스킬 ↔ prompts.py 단일 소스 정리 |
| U3 | 이번 주 탭 정보 위계 재검토 |
| U7 | 리포트 저장 버튼 `use_container_width=True` |

---

*생성: analysis-lead / kkirikkiri team · 2026-06-06*
