# 발견 사항 & 공유 자료

---

## 2026-06-06T14:45 — structure-explorer: 구조 분석 결과

### 파일 트리 + LOC

```
performance-coach/
├── CLAUDE.md                          # 코치 워크플로우 정의 (코칭 철학 + 5개 책임 + 워크플로우)
├── 20-knowledge-base/
│   ├── 01_PROFILE.md                  # 사용자 프로필
│   ├── 02_GOAL.md                     # 목표 (레이스/기록 목표)
│   ├── 03_RUNNING_HISTORY.md          # 러닝 기록 누적 테이블
│   ├── 04_CURRENT_STATUS.md           # 최신 상태 (sync.py가 자동 덮어씀)
│   ├── 05_INJURY_HISTORY.md           # 부상/통증 이력
│   └── app_settings.json              # 앱 설정 (닉네임, 목표, 심박, VO2)
├── 40-training-log/
│   ├── daily/
│   │   ├── 2026-06-03.md              # 훈련 결과 로그
│   │   └── 2026-06-06_plan.md         # 당일 AI 훈련 카드 캐시
│   └── weekly/
│       ├── 2026-W22_evaluation.md     # 주간 평가 파일
│       └── 2026-W23_plan.md           # 이번 주 훈련 계획
├── .claude/skills/                    # Claude Code 스킬 (AI 코칭 워크플로우)
│   ├── daily-training-plan/SKILL.md
│   ├── plan-adjustment/SKILL.md
│   ├── weekly-evaluation/SKILL.md
│   ├── weekly-training-plan/SKILL.md
│   └── workout-review/SKILL.md
└── webapp/
    ├── app.py                         # 2,065줄 — 메인 Streamlit 앱 (단일 파일)
    ├── requirements.txt               # 5개 의존성
    ├── pages/                         # 레거시 멀티페이지 파일 (현재 비활성)
    │   ├── _1_주간_계획.py            # 121줄
    │   ├── _2_오늘_계획.py            # 108줄
    │   ├── _3_훈련_리뷰.py            # 146줄
    │   ├── _4_계획_조정.py            # 111줄
    │   └── _5_주간_평가.py            # 135줄
    └── utils/
        ├── __init__.py                # 0줄 (빈 파일)
        ├── file_manager.py            # 409줄 — 파일 읽기/쓰기 + 경로 헬퍼
        ├── claude_client.py           # 113줄 — Anthropic API 래퍼
        ├── page_common.py             # 49줄 — .env 로드 + run_coach() 래퍼
        ├── prompts.py                 # 292줄 — 스킬별 시스템 프롬프트 상수
        └── sync.py                    # 375줄 — daily log 저장 후 4파일 자동 업데이트
```

**총 Python LOC: 3,923줄**
- app.py: 2,065줄 (전체의 52.6%)
- utils/: 1,238줄 (31.6%)
- pages/: 621줄 (15.8%, 레거시)

### 모듈 의존성 맵

```
app.py
├── utils.file_manager (fm)      — 61회 호출 (경로 헬퍼 + CRUD 전체)
├── utils.page_common (pc)       — run_coach() 호출 (AI 응답 래퍼)
├── utils.prompts                — WEEKLY_PLAN_PROMPT, DAILY_PLAN_CARD_PROMPT,
│                                   WORKOUT_REVIEW_PROMPT, WEEKLY_EVALUATION_PROMPT
└── utils.sync                   — sync_after_save() (daily log 저장 후)

page_common.py
└── utils.claude_client (cc)     — get_coaching_system_prompt(), get_coaching_response()

claude_client.py
├── utils.file_manager           — get_base_dir() (CLAUDE.md 경로 조회)
└── anthropic                    — Anthropic() 클라이언트

sync.py
└── utils.file_manager (fm)      — 읽기/쓰기 전체 위임

pages/_*.py (레거시, 5개 파일 모두 동일 패턴)
├── utils.file_manager (fm)
├── utils.prompts
└── utils.page_common (pc)

외부 라이브러리:
- streamlit>=1.51.0
- anthropic>=0.40.0
- python-dotenv>=1.0.0
- python-dateutil
- Pillow
```

### CLAUDE.md 워크플로우 ↔ 코드 연결 테이블

| CLAUDE.md Primary Responsibility | 구현 위치 | 연결 방식 |
|----------------------------------|-----------|-----------|
| 1. 주간 훈련 계획 수립 | app.py:1733~1784 (tab_week expander) | prompts.WEEKLY_PLAN_PROMPT → pc.run_coach() → fm.save_weekly_plan() |
| 2. 당일 훈련 계획 생성 | app.py:768~855 (S1-PRE_WORKOUT state) | prompts.DAILY_PLAN_CARD_PROMPT → pc.run_coach() → fm.save_daily_plan() |
| 3. 훈련 결과 분석 | app.py:876~965 (S2-POST_WORKOUT state) | prompts.WORKOUT_REVIEW_PROMPT → pc.run_coach() → fm.save_daily_log() |
| 4. 회복 관리 | app.py:544~551 (_recovery_badge_html) + sync.py:280~303 | 🔴/🟡/🟢 이모지 파싱 → current_status 자동 업데이트 |
| 5. 성장 추적 | app.py:1142~1186 (S5-WEEK_END) + app.py:1786~1833 (tab_week) | prompts.WEEKLY_EVALUATION_PROMPT → pc.run_coach() → fm.save_weekly_evaluation() |

| CLAUDE.md 워크플로우 | 탭/State | 핵심 함수 |
|----------------------|----------|-----------|
| Weekly Planning (Step 1~4) | tab_week (L1547~1833) | fm.get_recent_week_plans(), fm.save_weekly_plan() |
| Daily Planning | tab_home S1-PRE_WORKOUT (L709~855) | fm.read_daily_plan(), fm.save_daily_plan(), fm.extract_today_session() |
| Workout Review | tab_home S2-POST_WORKOUT (L860~965) | fm.save_daily_log(), sync.sync_after_save() |
| .claude/skills/ | 미연결 (Claude Code CLI 전용) | app.py는 동일 로직을 prompts.py로 인라인 재구현 |

**스킬 파일 연결 상태:**
- `.claude/skills/` 5개 파일은 Claude Code CLI 스킬 전용
- webapp은 동일 로직을 `utils/prompts.py` 5개 상수로 재구현
- 두 시스템이 분리되어 병렬 운영 중 → 동기화 없음

### 데이터 레이어 구조

**file_manager.py 함수 ↔ 파일 매핑:**

| 함수 | 읽는 파일 | 쓰는 파일 |
|------|----------|----------|
| read_profile() | 20-knowledge-base/01_PROFILE.md | — |
| read_goal() | 20-knowledge-base/02_GOAL.md | — |
| read_running_history() | 20-knowledge-base/03_RUNNING_HISTORY.md | — |
| read_current_status() | 20-knowledge-base/04_CURRENT_STATUS.md | — |
| read_injury_history() | 20-knowledge-base/05_INJURY_HISTORY.md | — |
| read_settings() / save_settings() | app_settings.json | app_settings.json + 01, 02_*.md |
| get_current_week_plan() | 40-training-log/weekly/YYYY-WNN_plan.md | — |
| save_weekly_plan() | — | 40-training-log/weekly/YYYY-WNN_plan.md |
| save_weekly_evaluation() | — | 40-training-log/weekly/YYYY-WNN_evaluation.md |
| read_daily_log() | 40-training-log/daily/YYYY-MM-DD.md | — |
| save_daily_log() | — | 40-training-log/daily/YYYY-MM-DD.md |
| read_daily_plan() | 40-training-log/daily/YYYY-MM-DD_plan.md | — |
| save_daily_plan() | — | 40-training-log/daily/YYYY-MM-DD_plan.md |

**sync.py가 자동 업데이트하는 파일 (sync_after_save 호출 시):**
1. 40-training-log/weekly/YYYY-WNN_plan.md — 훈련 기록 표 해당 날짜 행 기입
2. 20-knowledge-base/04_CURRENT_STATUS.md — 최신 상태 전체 덮어쓰기
3. 20-knowledge-base/05_INJURY_HISTORY.md — 통증 행 추가 (통증 있을 때만)
4. 20-knowledge-base/03_RUNNING_HISTORY.md — 러닝 기록 행 추가 (거리 > 0 일 때만)

### 구조 이슈 목록

| # | 파일:라인 | 심각도 | 설명 |
|---|----------|--------|------|
| 1 | app.py:1~2065 | HIGH | 단일 파일 2,065줄에 CSS(220줄) + 전역 헬퍼(30개 함수) + 4개 탭 UI 로직 전체 인라인. 탭별 분리 없음. with tab_X 블록 내에 수백 줄 HTML 생성 코드가 직접 존재 |
| 2 | webapp/pages/ 전체 | HIGH | pages/_*.py 5개 파일(621줄)이 레거시로 남아 있음. app.py가 탭 구조로 전환되면서 이 파일들은 실질적으로 비활성(git status에서 삭제 예정으로 표시). 그러나 pycache에 컴파일된 .pyc가 남아 혼란 유발 |
| 3 | app.py:355~374 / sync.py:184~203 | MEDIUM | _session_counts() 함수가 app.py(L355)와 sync.py의 _count_sessions()(L184)에 중복 구현. 동일한 주간 계획 표를 파싱하는 로직인데 함수명만 다름. 동기화 불일치 위험 |
| 4 | app.py:1123~1127 | MEDIUM | eval_path 직접 os.path.join으로 조합 (fm.get_base_dir() + 하드코딩 경로). file_manager에 이미 경로 헬퍼 함수들이 있는데 해당 경로만 누락. 경로 변경 시 버그 위험 |
| 5 | claude_client.py:17 | LOW | MODEL = "claude-sonnet-4-6" 하드코딩. 환경변수나 설정값으로 관리되지 않음. 모델 업그레이드 시 코드 수정 필요 |
| 6 | prompts.py:125~166 | LOW | DAILY_PLAN_PROMPT 상수가 정의되어 있으나 app.py 어디에서도 사용되지 않음. DAILY_PLAN_CARD_PROMPT만 사용됨. 미사용 상수 |
| 7 | .claude/skills/ ↔ prompts.py | LOW | CLI 스킬(.claude/skills/)과 webapp 프롬프트(prompts.py)가 이중 관리. 코칭 로직 변경 시 두 곳을 모두 수정해야 함. 단일 진실 공급원(single source of truth) 없음 |

### 한계 / 불확실 영역

- pages/ 파일들이 git status상 삭제 예정(D)인데 실제로 Streamlit이 해당 파일을 사이드바 네비게이션으로 노출하는지 미확인 (sidebar가 CSS로 `display:none`으로 강제 숨김 — L66)
- `design/` 폴더의 JSX 프로토타입과 webapp의 관계: 미확인 (참고용 디자인 시안으로 추정)
- railway.toml, Dockerfile의 배포 환경에서 WORKSPACE_PATH 환경변수 설정 여부 미확인 (file_manager.get_base_dir()가 이 변수에 의존)

---

## [15:30] — code-reviewer: 코드 품질 감사 결과

### 치명 이슈

---

**[C1] module-level 파일 I/O — 매 rerun마다 무조건 재실행 (app.py:236-351)**

재현 시나리오: 사용자가 설정 탭에서 toggle을 클릭하면 `st.rerun()`이 호출됨. app.py 전체가 재실행되면서 아래 I/O가 매번 반복된다.
- `app.py:236` `fm.get_current_week_plan()` — 주간 계획 파일 read
- `app.py:238` `fm.read_daily_log(today_str)` — 당일 로그 read
- `app.py:239` `fm.get_week_daily_logs()` — 이번 주 7일치 파일 scan
- `app.py:346-351` (7회 루프) `fm.read_daily_log()` × 7일 — done_dates 집계
- `app.py:382` `fm.read_goal()` — 목표 파일 read

`@st.cache_data` 미사용. toggle 1회 클릭 = 최소 10+ 파일 read. 데이터가 많아질수록 응답 지연이 선형 증가한다.

수정 방향: `fm.get_current_week_plan`, `fm.get_week_daily_logs`, `fm.read_daily_log`, `fm.read_goal` 등에 `@st.cache_data(ttl=30)` 적용. 캐시 무효화가 필요한 저장 직후에는 `st.cache_data.clear()` 호출.

---

**[C2] _write_kb() — 예외 처리 없는 파일 쓰기 (sync.py:371-375)**

```python
def _write_kb(key: str, content: str) -> None:
    path = _kb_path(key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:  # try/except 없음
        f.write(content)
```

재현 시나리오: `WORKSPACE_PATH` 환경변수가 잘못 설정되거나 디스크 권한 문제가 있을 때 `open()`이 `PermissionError`를 올림. `sync_after_save()`는 `app.py:959`에서 `try/except Exception: pass`로 감싸져 있어 에러가 무음 처리된다. 결과: 훈련 기록이 UI에서는 저장된 것처럼 보이지만 실제로는 knowledge-base 동기화가 실패해 AI 코치가 오래된 데이터를 기반으로 코칭한다.

수정 방향: `_write_kb`에 `try/except OSError` 추가 후 로그 출력 또는 호출자에게 예외 전파. `sync_after_save`의 catch-all `except Exception: pass`를 `except Exception as e: logging.warning(f"sync failed: {e}")` 로 교체.

---

**[C3] _upsert_line — 미사용이지만 버그 있는 람다 (file_manager.py:382-386)**

```python
def _upsert_line(text: str, key_pattern: str, key_label: str, value: str) -> str:
    if re.search(key_pattern, text, re.IGNORECASE):
        return re.sub(key_pattern + r"([^\n]+)", lambda m: f"{m.group()[:len(m.group())-len(m.group(len(m.groups())))]}{value}", text, flags=re.IGNORECASE)
    return text
```

`_upsert_line`은 `_sync_settings_to_markdown` 내에 정의되어 있지만 실제로 호출되지 않는다 (함수 내 어디에도 `_upsert_line(` 호출 없음). 호출될 경우 람다 내 `m.group(len(m.groups()))` 계산이 groups 수에 따라 IndexError를 낼 수 있다. 또한 `key_label` 파라미터가 시그니처에 있으나 함수 내에서 전혀 사용되지 않는 dead parameter이다.

수정 방향: 함수 전체 삭제하거나, 실제 사용 시 람다를 단순 패턴으로 교체: `re.sub(f"({key_pattern})[^\n]+", rf"\g<1>{value}", text)`.

---

### 주의 이슈

---

**[W1] _session_counts (app.py:355) vs _count_sessions (sync.py:184) — 동일 로직 중복**

두 함수는 동일한 `## 훈련 기록` 표를 파싱해 `(done, total)` 튜플을 반환한다. 파싱 조건도 동일 (`"## 훈련 기록"` 헤더, `|` 포함, `---` 제외, 첫 칸 헤더 제외, `✅/⚠️/❌` 마킹). 로직을 한쪽에서 수정하면 다른 쪽은 일치하지 않게 된다.

대안: `sync.py`에 공용 함수 정의 후 `app.py`에서 import, 또는 `file_manager.py`에 유틸로 이동.

---

**[W2] done_dates 집계 루프 — 모듈 레벨에서 7회 추가 파일 read (app.py:346-351)**

```python
done_dates: set[str] = set()
for i in range(7):
    d  = monday + datetime.timedelta(days=i)
    ds = d.strftime("%Y-%m-%d")
    if _log_is_complete(fm.read_daily_log(ds)):  # 최대 7회 read
        done_dates.add(ds)
```

`get_week_daily_logs()`가 이미 이번 주 로그를 읽어 반환한다 (`app.py:239` `week_logs`). 이 정보를 재활용하면 `fm.read_daily_log()` 7회 중복 read를 제거할 수 있다.

대안: `done_dates = {l["date"] for l in week_logs if _log_is_complete(l["content"])}`

---

**[W3] icon 변수 미사용 — render_day_strip (app.py:602-614)**

```python
if is_dn and highlight_done:
    css = "done"
    icon = "✓"    # 할당만 하고 HTML에 미사용
elif is_td:
    css = "today"
    icon = "●"    # 동일
else:
    css = ""
    icon = "·"    # 동일
```

생성되는 HTML(app.py:611-614)에는 `{icon}`이 없다. `icon` 변수는 3개 분기 모두에서 할당만 되고 출력에 쓰이지 않는다. 설계 의도(요일 텍스트 위에 아이콘 표시)가 구현에서 누락된 것으로 보인다.

---

**[W4] show_adjust session_state 미해제 (app.py:1049)**

```python
if st.button("계획 조정이 필요해요", type="secondary"):
    st.session_state["show_adjust"] = True
```

`show_adjust` 키는 `True`로 설정되지만 어디에서도 `False`로 리셋하거나 `.pop()` 하지 않는다. 반면 같은 기능의 `show_daily_adjust`(app.py:818/854)는 toggle 방식 + 저장 후 `pop()` 처리가 되어 있다. S3 상태에서 "계획 조정" 버튼을 클릭한 뒤 상태가 바뀌어 다른 state로 전환돼도 `show_adjust = True`가 session_state에 남는다.

---

**[W5] eval_result_home — AI 응답을 st.markdown에 직접 전달 (app.py:1172, 1820)**

```python
st.markdown(st.session_state["eval_result_home"])
```

AI 응답을 `unsafe_allow_html` 없이 `st.markdown`에 직접 전달한다. Streamlit의 기본 마크다운 렌더러는 일부 HTML 태그를 허용하므로 Claude 응답에 예상치 못한 HTML이 포함될 경우 렌더링될 수 있다. `eval_result`(tab_week, app.py:1820)도 동일 패턴이다. 신뢰된 모델 응답이므로 실제 위험은 낮으나, 일관성을 위해 `st.markdown(..., unsafe_allow_html=False)` 명시 권장.

---

**[W6] 설정 toggle — 매 rerun마다 settings 파일 3개 write (app.py:2012-2023)**

```python
c_not_t = st.toggle("훈련일 알림", value=s_notify_t, key="toggle_notify_t")
if c_not_t != s_notify_t:
    cfg["notify_training"] = c_not_t
    fm.save_settings(cfg)   # JSON + 01_PROFILE.md + 02_GOAL.md write
    st.rerun()
```

`save_settings`는 JSON 저장 + `_sync_settings_to_markdown()`으로 01_PROFILE.md, 02_GOAL.md 2개를 추가 write하는 무거운 함수다. toggle 1회 클릭 = 파일 3개 write + 전체 app rerun. notify 설정만 변경하는 경우에도 마크다운 동기화가 불필요하게 실행된다.

---

### 개선 기회 (경미)

---

**[M1] with tab_home: 541줄짜리 블록 (app.py:652-1192)**

S0/S1/S2/S3/S4/S5 6개 state의 렌더링 로직이 단일 `with tab_home:` 블록 내 if/elif 체인으로 541줄을 차지한다. `tab_record`: 237줄, `tab_week`: 287줄. 각 state별 렌더 함수로 분리하면 가독성 및 테스트 가능성이 향상된다.

제안 분리 단위:
```python
def _render_s0_no_plan(): ...         # ~40줄 (app.py:660-704)
def _render_s1_pre_workout(): ...     # ~150줄 (app.py:709-855)
def _render_s2_post_workout(): ...    # ~110줄 (app.py:860-965)
def _render_s3_reviewed(): ...        # ~85줄 (app.py:970-1053)
def _render_s4_rest_day(): ...        # ~40줄 (app.py:1058-1097)
def _render_s5_week_end(): ...        # ~90줄 (app.py:1102-1191)
```

---

**[M2] 거리 파싱 regex — 5개 위치에서 독립적으로 정의**

동일한 `r"거리[:\s]*([\d.]+)\s*(?:km)?"` 패턴이 아래 5곳에서 반복된다:
- `app.py:253` `_parse_km()`
- `app.py:977` S3 state inline
- `app.py:1370` tab_record inline
- `app.py:1645` tab_week inline (+ `re.IGNORECASE`)
- `sync.py:354` `_extract_km()`

`_parse_km()`과 `_extract_km()`은 사실상 동일 함수다. `file_manager.py`에 단일 `parse_km(text) -> float` 유틸을 두고 모두 import하면 패턴 변경 시 한 곳만 수정하면 된다.

---

**[M3] Hero 카드 HTML linear-gradient — 4회 복사 (app.py:750, 865, 992, 1111)**

아래 패턴이 S1/S2/S3/S5 state마다 복사-붙여넣기되어 있다:
```
f'<div class="rc-hero" style="background:linear-gradient(150deg,rgba({rgb},1) 0%,rgba({rgb},0.82) 60%,rgba({rgb},0.92) 100%);box-shadow:0 10px 30px rgba({rgb},0.30)">'
```

헬퍼 함수 `_hero_open(rgb: str) -> str`으로 추출하면 60+ 글자 × 4 중복 제거 가능.

---

**[M4] 변수명 일관성 이슈**

- `pain_detail_r`, `pain_level_r` (app.py:899-902): suffix `_r`은 "record"를 의미하는 것으로 추정되나 다른 곳에서는 suffix 없이 `pain_detail`, `pain_level` 사용. 동일한 폼 내에서 변수명이 다른 패턴을 따른다.
- `pv_km`, `pv_pace`, `pv_km_s`, `pv_pace_s`, `pv_stats` (app.py:793-797): `pv_` prefix의 의미가 주석 없이 불명확 (`prev_`의 축약으로 추정).
- `_r` suffix 사용 (S2: `_r`), `_w` suffix 사용 (tab_week: `pain_w`, `pain_level_w`) — 탭마다 다른 suffix 규칙 혼용.

---

**[M5] pages/ 레거시 파일 미정리**

`webapp/pages/_1_주간_계획.py` ~ `_5_주간_평가.py` 5개 파일이 존재하나 현재 앱은 app.py 단일 탭 구조를 사용한다. Streamlit은 `pages/` 폴더의 파일을 자동으로 사이드바 페이지로 등록하려 시도하므로 잠재적 충돌 가능성이 있다. 현재는 CSS로 사이드바를 숨김 처리(`app.py:66`)로 우회 중이나, 파일 자체를 정리하는 것이 명확하다.

---

### 미검증 가정

1. **마크다운 표 구조 불변 가정** (`_parse_weekly_rows`, `_session_counts`, `_update_weekly_plan_record`): 주간 계획 파일의 `## 요일별 계획` 표가 항상 `날짜|요일|구분|훈련|소요시간` 5열 구조라고 가정한다. AI가 다른 컬럼 순서나 추가 컬럼으로 생성하면 `cells[3]`, `cells[4]` 접근이 빈 문자열을 반환하거나 IndexError를 낼 수 있다.

2. **`## 훈련 기록` 표의 날짜 형식 고정 가정** (`sync.py:217`): `md = f"{date.month}/{date.day}"` 로 `"6/4"` 형식을 생성해 표 셀과 비교한다. AI가 `"06/04"` 또는 `"2026/6/4"` 형식으로 생성하면 매칭이 실패해 weekly plan 업데이트가 조용히 건너뛰어진다.

3. **`## 훈련 내용` 섹션 존재 가정** (`_extract_workout_type`, `_parse_daily_log`): 로그 파일에 `## 훈련 내용` 섹션이 없으면 `_extract_workout_type`은 `"달리기"` 폴백을 반환하고, `_parse_daily_log`는 빈 workout_type으로 진행한다. 에러는 없지만 `sync.py`의 running history에 `"달리기"`가 기록된다.

4. **`extract_today_session` 날짜 형식 매칭** (`file_manager.py:255`): `md = f"{d.month}/{d.day}"` (패딩 없음). 주간 계획 표 셀이 `"| 6/4 |"` 형식일 때만 매칭된다. `"| **6/4** |"` (볼드) 형식은 `replace("*", "")` 처리로 대응하지만, `"| 6월4일 |"` 등 한글 형식이면 매칭 실패.

5. **자정 넘어 앱 재시작 없이 유지 시 today 고정 문제** (`app.py:230`): `today = datetime.date.today()`가 모듈 레벨에서 한 번만 실행된다. Streamlit은 세션이 유지되는 동안 모듈을 재로드하지 않으므로, 자정이 지나도 앱을 재시작하지 않으면 `today`가 어제 날짜로 남아 당일 로그/계획 파일 경로가 잘못 계산된다.

---

---

## [2026-06-06T15:10] — ux-auditor: UX/디자인 감사 결과

---

### 사용자 여정 (탭별)

#### 탭 1: 오늘 (tab_home)
- **핵심 목적**: 당일 상태(S0~S5)에 따른 맞춤 UX 제공
- **정보 위계 1위**: Hero 카드 (전체 화면 폭 컬러 그라디언트 블록) — 상태별로 제목이 달라짐
- **1차 CTA**:
  - S0(계획 없음): "이번 주 계획 세우기" Primary (line:701)
  - S1(훈련 전): "다녀왔어요 · 기록 입력" Primary (line:813)
  - S2(기록 전): "기록 저장하기 →" Form submit (line:905)
  - S3(리뷰 완료): "계획 조정이 필요해요" Secondary (line:1048) — 완료 상태인데 "조정"이 유일한 CTA, 위계 역전
  - S4(휴식일): "가볍게 뛰었어요 — 기록하기" Secondary (line:1094) — Secondary가 유일한 CTA, primary 부재
  - S5(주말): "이번 주 성장 리포트 만들기 →" Primary (line:1140)
- **흐름 끊김**:
  - S0: 버튼 클릭 → `st.info()`로 "이번 주 탭으로 가세요" 안내만 표시, 실제 탭 전환 없음 (line:703)
  - S2: `st.form` 내에서 `st.markdown('<div class="rc-label">몸 상태</div>')` 사용 (line:889) — 위젯과 raw HTML 레이블 혼용, form 레이아웃 일관성 깨짐
  - S1: "계획 조정이 필요해요" 실패 시 에러 표시 후 폼 상태 미해제, 재제출 여부 불명확

#### 탭 2: 이번 주 (tab_week)
- **핵심 목적**: 주간 계획 확인 + 계획 수립 + 주간 리포트 생성
- **정보 위계 1위**: 64px SVG 링 차트 + 완료 거리/세션 카드 (line:1584~1608)
- **1차 CTA**: 불명확. plan 있을 때 expander가 접혀있고 리포트 버튼이 스크롤 최하단 (line:1794)
- **흐름 끊김**:
  - 링 차트→7일 스케줄→계획 expander→리포트 버튼 순서. 스케줄이 길면 계획 만들기 expander가 시야 밖
  - plan_content 파싱 실패(rows=[]) 시 `st.expander("전체 주간 계획 보기")` 만 표시 (line:1728), 파싱 오류 명시 없음

#### 탭 3: 기록 (tab_record)
- **핵심 목적**: 운동 이력 조회 + 주간 통계 확인 (조회 전용)
- **정보 위계 1위**: 이번 주 3-stat 바 (KM / 완료 횟수 / 평균 페이스) (line:1321~1337)
- **1차 CTA**: 없음 (조회 전용으로 의도적)
- **흐름 끊김**:
  - 활동 카드 클릭: 투명 오버레이 버튼 트릭 (line:1436~1441) — aria-label 없는 빈 버튼으로 접근성 미흡
  - 주간 통계 서브탭의 `›` 아이콘이 있으나 실제 클릭 이벤트 없음 (line:1535) — 클릭 가능한 것처럼 보임

#### 탭 4: 설정 (tab_settings)
- **핵심 목적**: 러너 프로필, 훈련 설정, 연동 관리
- **정보 위계 1위**: 프로필 히어로 카드 (아바타 + 닉네임 + 목표) (line:1967~1981)
- **1차 CTA**: 각 설정 행 클릭 → 다이얼로그 편집 (명확함)
- **흐름 끊김**:
  - 설정 다이얼로그 저장 후 `st.rerun()` (line:1876) — 다이얼로그 닫히며 성공 메시지 없음
  - 가민/스트라바 행에 `›` 아이콘이 있으나 클릭 시 아무것도 안 됨 (연동 예정 상태)

---

### 디자인 체계 이슈

#### CSS 변수 정의 현황 (app.py line:35~64)
28개 변수 정의됨. **미정의 변수 `--label-quaternary` 5곳 사용** — 치명

#### 치명: 미정의 CSS 변수 사용
- `var(--label-quaternary)` 가 `:root`에 없음에도 5곳에서 사용
  - `webapp/app.py:1434` 기록 탭 활동 카드 `›` 아이콘
  - `webapp/app.py:1535` 주간 통계 서브탭 `›` 아이콘
  - `webapp/app.py:1720` 이번 주 탭 스케줄 행 `›` 아이콘
  - `webapp/app.py:1892` 설정 탭 cfg_row `›` 아이콘
  - `webapp/app.py:1927` 설정 탭 icon_row `›` 아이콘
- 브라우저 폴백 없이 `›` 기호가 투명 또는 기본색으로 렌더링됨

#### 하드코딩된 색상 (CSS 변수 미사용)
| 위치 | 값 | 비고 |
|------|-----|------|
| app.py:1075 | `rgba(142,142,147,...)` | --gray 동일값 하드코딩 (휴식일 Hero) |
| app.py:1655 | `rgba(142,142,147,0.12)` | --gray 하드코딩 (이번 주 탭 휴식 원형) |
| app.py:1672 | `rgba(142,142,147,0.50)` | --gray 하드코딩 (부분 완료 원형) |
| app.py:2035 | `rgb(0,151,208)` | Garmin 브랜드색 (변수 없음) |
| app.py:2039 | `rgb(252,76,2)` | Strava 브랜드색 (변수 없음) |
| app.py:1501,1575 | `rgba(120,120,128,0.12)` | --fill-tertiary 유사값 불일치 |

#### 카드 border-radius 혼재
- `.rc-card` 정의: 20px (line:94)
- `.rc-progress` 정의: 16px (line:106)
- 인라인: 14px (line:1260), 16px (line:443), 20px (line:1477, 1617)
- CSS 변수 `--radius-lg(16px)`, `--radius-xl(22px)`, `--radius-2xl(26px)` 존재하나 카드 컴포넌트에 미적용

#### rc-label과 inline label 혼용
- `.rc-label` CSS 클래스 정의 있음 (line:75)
- 동일 스타일을 인라인으로 재정의: line:761~763 (`오늘 훈련 상세` 레이블)

---

### 빈 상태/피드백 이슈

#### 빈 상태 처리 현황
| 탭 | 상태 | 처리 수준 |
|----|------|-----------|
| 오늘 S0 | 계획 없음 | Hero "계획 없어요" + 지난 주 요약 (**양호**) |
| 이번 주 | 계획 없음 | expander만 펼침 — Hero 빈 상태 없음 (**미흡**) |
| 이번 주 | 파싱 실패 | expander 표시 — 파싱 오류 안내 없음 (**미흡**) |
| 기록 > 운동 기록 | 기록 없음 | 아이콘 + 안내 문구 + 설명 (**양호**) |
| 기록 > 주간 통계 | 기록 없음 | 아이콘 + 안내 문구 (**양호**) |
| 설정 | 미설정 | 기본값 표시 (의도적) |

#### 상호작용 피드백 현황
| 액션 | 피드백 | 평가 |
|------|--------|------|
| AI 계획/분석/리포트 생성 | st.spinner 있음 (line:778,848,936,1163) | 양호 |
| S2 기록 저장 성공 | st.rerun()만 실행 (line:965) | 치명: 성공 메시지 없음 |
| 설정 다이얼로그 저장 | st.rerun()만 실행 (line:1876) | 주의: 성공 메시지 없음 |
| 토글(알림) 변경 | st.rerun() 즉시 (line:2016,2023) | 주의: 시각 확인 없음 |
| 주간 계획/리포트 저장 | st.success("저장 완료!") (line:1782,1831) | 양호 |

---

### 톤앤매너 이슈

#### 버튼 레이블 구분자 혼용 (3가지)
- `·` (middle dot): line:813 "다녀왔어요 · 기록 입력"
- `—` (em dash): line:1094 "가볍게 뛰었어요 — 기록하기"
- `→` (arrow): line:834, 905, 1140, 1173, 1749, 1775 등

#### 동일 기능 레이블 불일치
- "이번 주 성장 리포트 만들기" (line:1045) vs "이번 주 성장 리포트 만들기 →" (line:1140, 1794)
- "리포트 저장 →" (line:1173) vs "리포트 저장" (line:1821)

#### 한국어/영어 혼용 (노출 텍스트)
- 기록 탭 stat 키: `KM 이번 주` (line:1326) — 다른 키(`회 완료`, `평균 페이스`)와 불일치

---

### UX 개선 우선순위

#### 치명 (즉시 수정)

1. **`--label-quaternary` 미정의 변수** — `webapp/app.py:1434, 1535, 1720, 1892, 1927`
   - 수정: `:root`에 `--label-quaternary: rgba(60,60,67,0.18);` 추가

2. **S2 기록 저장 성공 피드백 누락** — `webapp/app.py:957~965`
   - `st.rerun()` 전에 `st.success("기록이 저장됐어요!")` 추가

3. **주간 통계 `›` 아이콘: 클릭 유도 후 인터랙션 없음** — `webapp/app.py:1535`
   - 아이콘 제거 또는 상세 다이얼로그 연결

#### 주의 (다음 스프린트)

4. **설정 저장 성공 메시지 없음** — `webapp/app.py:1876`
   - `st.toast("저장됐어요")` 또는 배지 표시 권고

5. **이번 주 탭 빈 상태 및 CTA 불명확**
   - 계획 없을 때 Hero 빈 상태 카드 추가 (오늘 탭 S0 패턴 참조)

6. **S0 탭 전환 미연동** — `webapp/app.py:701~703`
   - 버튼 레이블을 "이번 주 탭에서 계획 세우기"로 변경해 컨텍스트 명확화

7. **카드 border-radius 불일치** — `app.py:94, 106, 443, 1260, 1477`
   - 정의된 CSS 변수(--radius-lg/xl/2xl) 적용 통일

#### 경미 (백로그)

8. **버튼 화살표 규칙 통일**: 저장=화살표 없음, 생성/진행=`→`
9. **`KM 이번 주` → `km 이번 주`** (line:1326)
10. **S4 secondary-only CTA**: "가볍게 뛰었어요" primary 변경 또는 "내일 미리보기" primary 추가 (line:1094)
11. **`--gray-raw: 142,142,147` 변수 추가**: `rgba(var(--gray-raw), 0.12)` 패턴으로 하드코딩 제거

---

# DEAD_ENDS (시도했으나 실패한 접근)

(아직 없음 — 실패한 접근이 생기면 여기에 기록)
