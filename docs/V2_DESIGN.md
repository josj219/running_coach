# v2 아키텍처 전환 설계서 — FastAPI + PostgreSQL + PWA

> 대상: 고고조 AI 러닝 코치
> 현재(v1): Streamlit 단일 앱 + Markdown/JSON 파일 저장 + Anthropic Claude(sonnet-4-6) + Docker/Railway
> 목표(v2): FastAPI(REST/SSE) + PostgreSQL + PWA(프론트엔드 분리) + Docker Compose + GitLab CI/CD
> 작성일: 2026-06-10

---

## 0. 전환 동기 & 설계 원칙

### 왜 전환하는가

| v1 한계 | v2 해결 |
|---------|---------|
| Streamlit 단일 프로세스 — 상태 전환마다 전체 리렌더, `st.rerun()`/캐시 타이밍 버그(BUG-19) | API/UI 분리 — 클라이언트 상태와 서버 상태를 명확히 격리 |
| Markdown 파일 = DB. 모든 집계가 regex 파싱(BUG-12~18 대부분이 파싱 버그) | 정규화된 관계형 스키마 — 집계는 SQL, 파싱 불필요 |
| 동시성/멀티 디바이스 불가(파일 lock 없음) | DB 트랜잭션 + 단일 진실 공급원(SSOT) |
| 오프라인/모바일 설치 불가 | PWA — 홈 화면 설치 + 오프라인 캐시 |
| Railway 단일 서비스 | Compose로 api/db/web 분리, 로컬=운영 동형 |

### 설계 원칙

1. **데이터는 DB가 SSOT.** Markdown은 "AI에게 넘기는 컨텍스트 직렬화 포맷"으로만 존재(런타임 생성, 영구 저장 X).
2. **파싱 로직을 버린다.** v1 버그의 70%가 Markdown regex 파싱이었다. v2는 구조화 저장 → 집계는 SQL.
3. **AI 호출은 서버에서만.** API 키를 클라이언트에 노출하지 않음. SSE로 스트리밍.
4. **기능 동등성 우선.** F01~F12 동작을 100% 보존한 뒤 확장. 신규 기능은 v2.1로 미룬다.

---

## 1. 기능 재분류: F01~F12 → API / DB / Frontend

v1 기능은 "탭별 UI 덩어리"였다. v2에서는 **Frontend(렌더/상호작용) / API(엔드포인트) / DB(테이블·집계)** 3계층으로 분해한다.

| ID | v1 기능 | Frontend (PWA) | API (FastAPI) | DB / 집계 |
|----|---------|----------------|---------------|-----------|
| **F01** | 오늘 탭 State Machine (S0~S5) | `<TodayView>` — 상태별 카드 렌더 | `GET /api/today` → `{state, ...payload}` | 상태는 서버가 계산(`plan`/`daily_log`/`session`/`week_progress` 조회 후 판정). 파일 기반 `detect_home_state` 로직을 SQL 쿼리로 재현 |
| **F02** | 당일 훈련 계획 AI 생성 | "오늘 계획 생성" 버튼 → SSE 구독 | `POST /api/daily-plans` (스트리밍 SSE) | `daily_plans` insert (status=generating→ready). 컨텍스트는 DB에서 조립 |
| **F03** | 당일 훈련 카드 UI (섹션 카드+팝업) | `<DailyPlanCard>` + 모달. 워밍업/메인/쿨다운/메모/상세 | `GET /api/daily-plans/{date}` | `daily_plans.sections` (JSONB: warmup/main/cooldown/note/detail) — v1 `[브래킷]` 파싱 제거, 구조화 저장 |
| **F04** | 훈련 기록 저장 + AI 리뷰 | `<WorkoutLogForm>` → 저장 → 리뷰 표시 | `POST /api/workout-logs` → `POST /api/workout-logs/{id}/review`(SSE) | `workout_logs` insert + `workout_reviews` insert. 회복필요도=enum 컬럼(이모지 파싱 제거) |
| **F05** | 데이터 자동 동기화(sync_after_save) | (없음 — 서버 부수효과) | `POST /api/workout-logs` 내부 트랜잭션 | **v1의 4파일 sync가 사라짐.** running_history/injury/current_status가 정규화 테이블의 파생 뷰가 됨. insert 1건이 곧 동기화 |
| **F06** | 이번 주 탭 레이아웃·요약 카드 | `<WeekView>` — 진행률 바, 일정 리스트 | `GET /api/weeks/{iso_week}` | `weekly_plans` + `sessions` join. 주간 km/수행률은 `SUM`/`COUNT` 집계(BUG-14/16 근본 제거) |
| **F07** | 주간 계획 AI 생성+저장 | `<WeeklyPlanWizard>`(일정 입력→생성) | `POST /api/weekly-plans`(SSE) | `weekly_plans` + `sessions` bulk insert. AI는 JSON 스키마로 응답 → 행으로 저장 |
| **F08** | 이번 주 성장 리포트 | `<GrowthReportCard>`(3숫자+코치메시지+접힘) | `POST /api/weeks/{iso_week}/evaluation`(SSE) | 카드 숫자는 **앱이 SQL로 산출**(AI 미산출, BUG-16 합의 유지). AI는 서술만 → `weekly_evaluations` |
| **F09** | 계획 조정 요청 | `<PlanAdjustDrawer>` | `POST /api/weekly-plans/{id}/adjust`(SSE) | `sessions` 부분 update. 기존 완료 세션 보존(BUG-18 → FK/트랜잭션으로 구조적 보장) |
| **F10** | 기록 탭 — 운동기록/주간통계 | `<HistoryView>` 서브탭 2개 | `GET /api/workout-logs?range=`, `GET /api/stats/weekly` | `workout_logs` 페이지네이션 + 주차별 집계 뷰 |
| **F11** | 설정 탭 — Profile/Goal 편집 | `<SettingsView>` 폼 | `GET/PATCH /api/profile`, `GET/PATCH /api/goal`, `GET/PATCH /api/settings` | `user_profile`, `goals`, `app_settings` 컬럼 직접 update(BUG-05/17 regex 파싱 제거) |
| **F12** | 설정 변경 시 계획 자동 갱신 | 변경 후 확인 다이얼로그 → 재생성 호출 | `PATCH /api/profile` 응답에 `plan_refresh_suggested: bool` → 프론트가 `POST .../adjust` | 닉네임 등 표시용 필드는 플래그 안 켬(BUG-09 유지). 트레이닝 관련 필드만 트리거 |

### 횡단 관심사 (전 기능 공통)

| 관심사 | v1 | v2 |
|--------|----|----|
| AI 호출 | `page_common.run_coach` (동기, blocking) | `services/coach.py` — async + SSE 스트리밍, `COACH_MOCK` 환경변수 유지 |
| 시스템 프롬프트 | `CLAUDE.md` 파일 읽기 | 동일(`CLAUDE.md` 유지) + 스킬별 프롬프트는 `prompts/` 모듈 |
| 컨텍스트 조립 | Markdown 파일 cat | DB 조회 → Markdown 직렬화 함수(`render_context_md()`) |
| 인증 | 없음(단일 사용자) | v2.0은 단일 사용자 전제. `user_id` 컬럼은 미리 둠(멀티유저 확장 대비) |

---

## 2. PostgreSQL 테이블 초안

> 단일 사용자지만 `user_id`를 전 테이블에 둬서 향후 멀티유저 확장 시 마이그레이션 비용 0. v2.0에서는 `user_id=1` 고정.

```sql
-- ─────────────────────────────────────────────────────────────
-- 사용자 / 프로필 / 목표  (F11)
-- ─────────────────────────────────────────────────────────────

CREATE TABLE users (
    id           BIGSERIAL PRIMARY KEY,
    email        TEXT UNIQUE NOT NULL,
    nickname     TEXT NOT NULL DEFAULT '고고조',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE user_profiles (
    user_id      BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    height_cm    NUMERIC(5,1),
    weight_kg    NUMERIC(5,1),
    age          INT,
    max_hr       INT,
    resting_hr   INT,
    vo2_max      NUMERIC(4,1),
    pb_10k       INTERVAL,         -- 개인 최고기록
    pb_half      INTERVAL,
    pb_full      INTERVAL,
    avatar_url   TEXT,             -- 프로필 이미지(오브젝트 스토리지 키 또는 data URI)
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE goals (
    id           BIGSERIAL PRIMARY KEY,
    user_id      BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    race_type    TEXT NOT NULL,           -- '풀마라톤'
    target_time  INTERVAL,                -- sub 3:30 → '3:30:00'
    target_date  DATE,                    -- D-day 계산(BUG-17: DATE 타입이라 파싱 불필요)
    is_active    BOOLEAN NOT NULL DEFAULT true,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_goals_active ON goals(user_id) WHERE is_active;

CREATE TABLE app_settings (
    user_id          BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    weekly_goal_km   NUMERIC(5,1) NOT NULL DEFAULT 45,
    pace_unit        TEXT NOT NULL DEFAULT '분/km',
    distance_unit    TEXT NOT NULL DEFAULT 'km',
    notify_training        BOOLEAN NOT NULL DEFAULT true,
    notify_after_workout   BOOLEAN NOT NULL DEFAULT true,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─────────────────────────────────────────────────────────────
-- 주간 계획 / 세션  (F06, F07, F09)
-- ─────────────────────────────────────────────────────────────

CREATE TABLE weekly_plans (
    id           BIGSERIAL PRIMARY KEY,
    user_id      BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    iso_year     INT NOT NULL,
    iso_week     INT NOT NULL,            -- 2026-W23 → (2026, 23)
    week_start   DATE NOT NULL,           -- 월요일
    direction    TEXT,                    -- 주간 방향성(v1 '> ' quote)
    goal_km      NUMERIC(5,1),            -- 그 주 목표 거리(없으면 settings.weekly_goal_km 폴백)
    intensity    TEXT,                    -- 예상 강도
    raw_md       TEXT,                    -- AI 원문 백업(디버깅/재현용, 표시엔 미사용)
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, iso_year, iso_week)  -- 주당 1계획(재생성=update)
);

CREATE TYPE session_kind AS ENUM (
    '인터벌','롱런','템포','페이스런','회복조깅','쉬운달리기',
    '근력','헬스','드릴','코어','가동성','휴식'
);
CREATE TYPE session_status AS ENUM ('예정','완료','부분완료','미수행'); -- ✅/⚠️/❌ 대체

CREATE TABLE sessions (
    id           BIGSERIAL PRIMARY KEY,
    plan_id      BIGINT NOT NULL REFERENCES weekly_plans(id) ON DELETE CASCADE,
    session_date DATE NOT NULL,
    weekday      SMALLINT NOT NULL,       -- 0=월
    kind         session_kind NOT NULL,
    title        TEXT,                    -- '트레드밀 Easy Run'
    duration_min INT,                     -- 소요시간(범위는 min/max로, BUG-15 회피)
    duration_min_max INT,
    target_pace  TEXT,                    -- '6:20~6:40/km'
    note         TEXT,
    status       session_status NOT NULL DEFAULT '예정',
    is_rest      BOOLEAN NOT NULL DEFAULT false,  -- 수행률 분모 제외(BUG-16)
    UNIQUE (plan_id, session_date)
);
CREATE INDEX idx_sessions_date ON sessions(session_date);

-- ─────────────────────────────────────────────────────────────
-- 당일 AI 계획  (F02, F03)
-- ─────────────────────────────────────────────────────────────

CREATE TYPE gen_status AS ENUM ('generating','ready','error');

CREATE TABLE daily_plans (
    id           BIGSERIAL PRIMARY KEY,
    user_id      BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_date    DATE NOT NULL,
    session_id   BIGINT REFERENCES sessions(id) ON DELETE SET NULL,
    sections     JSONB NOT NULL DEFAULT '{}',  -- {warmup, main, cooldown, note, detail}
    is_adjusted  BOOLEAN NOT NULL DEFAULT false, -- v1 <!-- ADJUSTED --> 마커 대체(BUG-11)
    adjust_reason TEXT,                     -- 통증/컨디션/날씨
    status       gen_status NOT NULL DEFAULT 'ready',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, plan_date)             -- 당일 1계획(조정=update, BUG-19 캐시문제 구조적 제거)
);

-- ─────────────────────────────────────────────────────────────
-- 훈련 기록 / 리뷰  (F04, F05, F10)
-- ─────────────────────────────────────────────────────────────

CREATE TYPE recovery_level AS ENUM ('낮음','보통','높음'); -- 🟢/🟡/🔴 (BUG-13 파싱 제거)

CREATE TABLE workout_logs (
    id            BIGSERIAL PRIMARY KEY,
    user_id       BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id    BIGINT REFERENCES sessions(id) ON DELETE SET NULL,
    log_date      DATE NOT NULL,
    kind          session_kind NOT NULL,
    distance_km   NUMERIC(5,2) NOT NULL DEFAULT 0,
    duration_sec  INT,
    avg_pace      TEXT,
    avg_hr        INT,
    cadence       INT,
    elevation_m   INT,
    fatigue_label TEXT,                    -- '괜찮아요'
    fatigue_num   SMALLINT,                -- 3/10 → 3
    pain_part     TEXT,
    pain_level    SMALLINT NOT NULL DEFAULT 0,  -- >=4 → 부분완료 트리거
    user_comment  TEXT,
    image_url     TEXT,                    -- Garmin/Strava 스크린샷
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, log_date)
);
CREATE INDEX idx_logs_user_date ON workout_logs(user_id, log_date DESC);

CREATE TABLE workout_reviews (
    id            BIGSERIAL PRIMARY KEY,
    log_id        BIGINT NOT NULL UNIQUE REFERENCES workout_logs(id) ON DELETE CASCADE,
    strengths     TEXT,
    improvements  TEXT,
    recovery      recovery_level,          -- enum 컬럼 → 뱃지 렌더 시 파싱 불필요
    coach_comment TEXT,
    raw_md        TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─────────────────────────────────────────────────────────────
-- 주간 평가 / 성장 리포트  (F08)
-- ─────────────────────────────────────────────────────────────

CREATE TABLE weekly_evaluations (
    id            BIGSERIAL PRIMARY KEY,
    plan_id       BIGINT NOT NULL UNIQUE REFERENCES weekly_plans(id) ON DELETE CASCADE,
    total_km      NUMERIC(6,1) NOT NULL,   -- 앱 산출(SQL 집계)
    done_sessions INT NOT NULL,
    total_sessions INT NOT NULL,
    completion_rate INT NOT NULL,          -- 단일 정의(BUG-16): done/total
    coach_message TEXT,                    -- AI 서술
    detail_md     TEXT,                    -- [핵심수치]/[추세]/[진척도]
    is_partial    BOOLEAN NOT NULL DEFAULT false,  -- 주중 진행 평가
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 파생 데이터 = 뷰 (v1의 03/04/05 .md를 대체)

v1의 `03_RUNNING_HISTORY.md` / `04_CURRENT_STATUS.md` / `05_INJURY_HISTORY.md`는 **저장 테이블이 아니라 워크아웃 로그의 파생물**이었다. v2에서는 별도 저장하지 않고 뷰/쿼리로 만든다.

```sql
-- 러닝 이력(03) = workout_logs WHERE distance_km > 0
CREATE VIEW v_running_history AS
SELECT log_date, kind, distance_km, avg_pace, avg_hr, cadence, fatigue_label
FROM workout_logs WHERE distance_km > 0 ORDER BY log_date DESC;

-- 부상 이력(05) = workout_logs WHERE pain_level > 0
CREATE VIEW v_injury_history AS
SELECT log_date, pain_part, pain_level, kind
FROM workout_logs WHERE pain_level > 0 ORDER BY log_date DESC;

-- 현재 상태(04)는 "가장 최근 로그 + 이번주 집계" → 쿼리로 그때그때 조립
```

이로써 v1의 sync_after_save 4파일 동기화 + BUG-18(완료기록 소실)이 **구조적으로 불가능**해진다.

---

## 3. FastAPI 라우터 설계

```
app/
├── main.py                 # FastAPI 인스턴스, 미들웨어, 라우터 등록
├── config.py               # pydantic-settings (DATABASE_URL, ANTHROPIC_API_KEY, COACH_MOCK)
├── db/
│   ├── session.py          # async engine, get_session 의존성
│   └── models.py           # SQLAlchemy 2.0 ORM
├── schemas/                # pydantic 요청/응답 모델
├── routers/
│   ├── today.py            # F01
│   ├── daily_plans.py      # F02, F03
│   ├── workout_logs.py     # F04, F05, F10
│   ├── weekly_plans.py     # F06, F07, F09
│   ├── evaluations.py      # F08
│   ├── profile.py          # F11, F12
│   └── stats.py            # F10 통계
├── services/
│   ├── coach.py            # Claude 호출(async) + SSE 스트림 + COACH_MOCK
│   ├── context.py          # DB → Markdown 컨텍스트 직렬화
│   ├── state_machine.py    # F01 S0~S5 판정(SQL 기반)
│   └── plan_parser.py      # AI JSON 응답 → sessions 행
└── prompts/                # 스킬별 프롬프트(v1 prompts.py 이식)
```

### 엔드포인트 표

| 메서드 · 경로 | 기능 | 요청 | 응답 |
|---------------|------|------|------|
| `GET /api/today` | F01 | — | `{state: "S1", dday, hero, session, week_progress}` |
| `POST /api/daily-plans` | F02 | `{date, condition, weather?}` | **SSE**: `token` 이벤트 스트림 → `done`{plan_id} |
| `GET /api/daily-plans/{date}` | F03 | — | `{sections, is_adjusted, status}` |
| `POST /api/daily-plans/{date}/adjust` | F09(당일) | `{reason, pain?, condition?}` | **SSE** → 갱신된 sections |
| `POST /api/workout-logs` | F04·F05 | `{date, metrics, fatigue, pain, comment, image?}` | `{log_id}` (트랜잭션: log+파생 일괄) |
| `POST /api/workout-logs/{id}/review` | F04 | — | **SSE** → `{review: {recovery, strengths,...}}` |
| `GET /api/workout-logs` | F10 | `?from&to&limit` | `[{log, review}]` |
| `GET /api/weeks/{iso_week}` | F06 | — | `{plan, sessions[], progress}` |
| `POST /api/weekly-plans` | F07 | `{schedule, condition}` | **SSE** → `{plan_id, sessions[]}` |
| `POST /api/weekly-plans/{id}/adjust` | F09 | `{reason, remaining_only:true}` | **SSE** → 갱신 sessions |
| `POST /api/weeks/{iso_week}/evaluation` | F08 | — | `{card:{km,done,total,rate}, coach, detail}` (카드=SQL, 서술=SSE) |
| `GET /api/stats/weekly` | F10 | `?weeks=4` | `[{iso_week, km, rate}]` |
| `GET/PATCH /api/profile` | F11 | `{height_cm,...}` | `{profile, plan_refresh_suggested}` |
| `GET/PATCH /api/goal` | F11 | `{race_type, target_time, target_date}` | `{goal}` |
| `GET/PATCH /api/settings` | F11 | `{weekly_goal_km,...}` | `{settings}` |
| `GET /api/health` | 헬스체크 | — | `{status:"ok"}` |

### SSE 패턴(AI 스트리밍)

v1은 blocking 호출이라 생성 중 화면이 멈췄다. v2는 `StreamingResponse`로 토큰을 흘린다:

```python
@router.post("/api/daily-plans")
async def create_daily_plan(req: DailyPlanReq, db=Depends(get_session)):
    ctx = await build_daily_context(db, req.date, req.condition, req.weather)
    async def event_stream():
        chunks = []
        async for token in coach.stream(DAILY_PLAN_PROMPT, ctx):
            chunks.append(token)
            yield f"event: token\ndata: {json.dumps(token)}\n\n"
        sections = plan_parser.parse_daily(''.join(chunks))
        plan = await save_daily_plan(db, req.date, sections)
        yield f"event: done\ndata: {json.dumps({'plan_id': plan.id})}\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

**AI 응답 구조화**: v1은 `[워밍업]` 브래킷 텍스트를 regex 파싱(BUG-04). v2는 프롬프트에서 **JSON 출력**을 요구하고 `plan_parser`가 검증 → 실패 시 1회 재요청. 이로써 F02/F03/F07/F08의 파싱 버그류가 사라진다.

---

## 4. 기존 md 파일 → DB 마이그레이션 전략

일회성 ETL 스크립트(`scripts/migrate_v1.py`). v1 `file_manager`/`sync` 파서를 **재사용**해 읽고, ORM으로 적재한다.

### 단계

```
1. users/app_settings 시드
   - 02_GOAL.md, 01_PROFILE.md, app_settings.json
     → users, user_profiles, goals, app_settings
   - parse_profile_fields() / parse_goal_fields() 그대로 호출

2. weekly_plans + sessions
   - 40-training-log/weekly/*_plan.md 순회
   - _parse_weekly_rows() (app.py) → '요일별 계획' 표 → sessions
   - _count_planned_sessions / _count_done_records → status 매핑
   - '## 훈련 기록' 표의 ✅/⚠️/❌ → session_status

3. workout_logs + reviews
   - 40-training-log/daily/YYYY-MM-DD.md 순회(_plan.md 제외)
   - sync._parse_daily_log() 재사용 → workout_logs
   - '## 훈련 리뷰' 블록 → workout_reviews (회복이모지→enum)

4. daily_plans
   - daily/*_plan.md → _parse_daily_plan_cards() → sections JSONB
   - <!-- ADJUSTED --> 존재 → is_adjusted=true

5. weekly_evaluations
   - weekly/*_evaluation.md → weekly_evaluations
   - 없으면 SQL 집계로 재산출 가능하므로 best-effort

6. 검증
   - 마이그레이션 후 count_sessions(SQL) == count_sessions(파일) 대조
   - 주별 total_km 합 일치 확인 → 리포트 출력
```

### 매핑 주의점

| v1 표현 | v2 컬럼 | 변환 |
|---------|---------|------|
| `✅`/`⚠️`/`❌`/`예정` | `session_status` | 완료/부분완료/미수행/예정 |
| `🔴`/`🟡`/`🟢` | `recovery_level` | 높음/보통/낮음 |
| `"70~80분"` | `duration_min`, `duration_min_max` | 범위 분해(BUG-15 영구 해소) |
| `"거리: 6.2"` | `distance_km` | float |
| 휴식/회복 행 | `is_rest=true` | `_row_is_rest()` 재사용 |

원본 `.md`는 삭제하지 않고 `archive/v1-markdown/`으로 이동 보관(롤백 안전망).

---

## 5. Docker Compose 구성안

```yaml
# docker-compose.yml  (로컬 개발 = 운영 동형)
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: coach
      POSTGRES_USER: coach
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U coach"]
      interval: 5s
      retries: 5
    ports: ["5432:5432"]   # 운영 compose에선 제거

  api:
    build: ./api
    environment:
      DATABASE_URL: postgresql+asyncpg://coach:${DB_PASSWORD}@db:5432/coach
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      CLAUDE_MODEL: claude-sonnet-4-6
      COACH_MOCK: ${COACH_MOCK:-}     # 테스트/CI에서만 설정
    depends_on:
      db: {condition: service_healthy}
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
    ports: ["8000:8000"]

  web:
    build: ./web                       # PWA(Vite/React) 정적 빌드 → nginx
    depends_on: [api]
    ports: ["80:80"]
    # nginx가 /api → api:8000 프록시, 그 외 → SPA + service worker

volumes:
  pgdata:
```

- **마이그레이션**: api 컨테이너 기동 시 `alembic upgrade head` 자동 실행.
- **운영(`docker-compose.prod.yml` override)**: db 포트 비공개, web에 TLS(예: caddy/traefik), 리소스 제한.
- v1 Railway는 단일 서비스였으나, Railway에서도 multi-service로 db/api/web 분리 배포 가능(또는 Compose를 그대로 single host에).

---

## 6. GitLab CI/CD 파이프라인 초안

```yaml
# .gitlab-ci.yml
stages: [lint, test, build, deploy]

variables:
  POSTGRES_DB: coach
  POSTGRES_USER: coach
  POSTGRES_PASSWORD: ci
  DATABASE_URL: "postgresql+asyncpg://coach:ci@postgres:5432/coach"

lint:
  stage: lint
  image: python:3.11-slim
  script:
    - pip install ruff
    - ruff check api/

test:api:
  stage: test
  image: python:3.11-slim
  services: [postgres:16-alpine]
  variables:
    COACH_MOCK: "1"            # 실 API 미호출 → 비용 0 (v1 패턴 유지)
  script:
    - pip install -r api/requirements.txt -r api/requirements-test.txt
    - alembic upgrade head
    - pytest api/tests -q       # F01~F12 회귀 이식(v1 tests/ 기반)

test:web:
  stage: test
  image: node:20-alpine
  script:
    - cd web && npm ci && npm run test && npm run build

build:
  stage: build
  image: docker:27
  services: [docker:27-dind]
  script:
    - docker build -t $CI_REGISTRY_IMAGE/api:$CI_COMMIT_SHA ./api
    - docker build -t $CI_REGISTRY_IMAGE/web:$CI_COMMIT_SHA ./web
    - docker push $CI_REGISTRY_IMAGE/api:$CI_COMMIT_SHA
    - docker push $CI_REGISTRY_IMAGE/web:$CI_COMMIT_SHA
  only: [main]

deploy:prod:
  stage: deploy
  environment: production
  script:
    - ssh $DEPLOY_HOST "cd /srv/coach &&
        export TAG=$CI_COMMIT_SHA &&
        docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d &&
        docker compose exec -T api alembic upgrade head"
  when: manual                  # 수동 승인 배포
  only: [main]
```

- **마이그레이션 안전**: 배포 후 `alembic upgrade head`. 파괴적 변경은 expand/contract 2단계.
- **테스트 비용 0**: `COACH_MOCK`으로 실 Claude 호출 차단(v1에서 검증된 패턴).
- **시크릿**: `ANTHROPIC_API_KEY`, `DB_PASSWORD`, `DEPLOY_HOST`는 GitLab CI/CD Variables(protected/masked).

---

## 7. v1 → v2 단계별 작업 목록

위험을 줄이기 위해 **백엔드 먼저, 기능 단위 수직 슬라이스**로 옮긴다. 각 단계 끝에 동작하는 산출물이 있어야 한다.

### Phase 0 — 기반 (1주)
- [ ] 모노레포 구조(`api/`, `web/`, `scripts/`) + Compose + GitLab CI 골격
- [ ] SQLAlchemy 모델 + Alembic 초기 마이그레이션(섹션 2 스키마)
- [ ] `services/coach.py` async 이식 + `COACH_MOCK` + `CLAUDE.md` 시스템 프롬프트
- [ ] `services/context.py` — DB→Markdown 직렬화(AI 컨텍스트 동등성 확보)

### Phase 1 — 읽기 경로 + 마이그레이션 (1주)
- [ ] `scripts/migrate_v1.py` (섹션 4) + 검증 리포트
- [ ] `GET /api/today`(F01) — state_machine SQL 이식
- [ ] `GET /api/weeks/{week}`(F06), `GET /api/workout-logs`(F10), `GET /api/profile`(F11)
- [ ] PWA 셸: 4탭 네비, `<TodayView>`/`<WeekView>`/`<HistoryView>`/`<SettingsView>` 읽기 전용 렌더
- [ ] **체크포인트**: 마이그레이션된 데이터가 v1과 동일하게 보이는지 시각 대조

### Phase 2 — AI 생성 경로 (2주)
- [ ] `POST /api/weekly-plans`(F07) + JSON 스키마 파서 → sessions
- [ ] `POST /api/daily-plans`(F02) + `<DailyPlanCard>`(F03) SSE 스트리밍
- [ ] `POST /api/workout-logs` + `/review`(F04) — 트랜잭션 + 파생(F05 자동)
- [ ] `POST /api/weeks/{week}/evaluation`(F08) — 카드=SQL, 서술=AI
- [ ] `POST .../adjust`(F09) — 잔여 세션만 update

### Phase 3 — 설정·갱신·PWA 마감 (1주)
- [ ] `PATCH /api/profile|goal|settings`(F11) + `plan_refresh_suggested`(F12)
- [ ] PWA: manifest + service worker(오프라인 캐시, 설치 프롬프트), 푸시 알림(`notify_*` 연동)
- [ ] 프로필 이미지 업로드(F11) — 오브젝트 스토리지 또는 DB bytea

### Phase 4 — 검증·컷오버 (1주)
- [ ] v1 `tests/`의 F01~F12 회귀를 API 통합 테스트로 이식(특히 BUG-05~19 회귀 케이스)
- [ ] 병렬 운영(v1 읽기전용 + v2) 후 데이터 재동기화 → 컷오버
- [ ] v1 Streamlit/Railway 디코미션, `.md` 아카이브 보관

> 총 약 6주. Phase 1 종료 시점에 "읽기 전용 v2"가 떠서 조기 검증 가능.

---

## 8. v2 유지 / 제외 기능

### 유지 (기능 동등 — F01~F12 전부)
- F01~F12 모든 동작. 단, **구현은 정규화 DB 기반으로 재작성**(파싱 제거).
- `CLAUDE.md` 코칭 철학 = 시스템 프롬프트(그대로).
- 5개 스킬 워크플로(weekly/daily/review/adjust/evaluation) → 프롬프트 모듈로 이식.
- `COACH_MOCK` 테스트 시드.
- 성장 리포트 합의 포맷(3숫자 카드 + 코치 메시지 + 접힌 상세, BUG-16 수행률 단일정의).
- 부분완료(⚠️)·회복 필요도·통증 트리거 로직(enum으로).

### 제외 / 폐기 (v1 부채)
- **Markdown 파일을 SSOT로 쓰는 구조 전체** — DB로 대체.
- `sync_after_save` 4파일 동기화 — 트랜잭션 + 뷰로 대체(BUG-18 원인 제거).
- 모든 regex 파싱 헬퍼(`_parse_weekly_rows`, `_parse_daily_plan_cards`, `_recovery_level`, `count_sessions` 등) — SQL/JSONB로 대체.
- `<!-- ADJUSTED -->` 텍스트 마커 — `daily_plans.is_adjusted` 컬럼.
- Streamlit `st.session_state`/`st.rerun()`/`@st.cache_data` 상태관리 — 클라이언트 상태 + REST.
- `st.dialog` 등 Streamlit 위젯 — PWA 컴포넌트.

### v2.0 보류 → v2.1+ (이번 범위 제외)
- 멀티유저 인증/계정(스키마는 `user_id`로 대비만).
- Garmin/Strava 자동 연동, 자동 날씨 조회(PRD Future Scope).
- 부상 위험 예측·시즌 자동 계획 등 ML 기능.
- 실시간 협업/공유.

---

## 부록: 핵심 위험 & 완화

| 위험 | 완화 |
|------|------|
| AI 컨텍스트가 v1과 달라져 코칭 품질 저하 | `context.py`가 v1과 **동일한 Markdown**을 생성하도록 골든 테스트(파일 vs DB 직렬화 diff) |
| AI JSON 출력 불안정 | pydantic 검증 + 1회 재요청 + `raw_md` 백업 보존 |
| 마이그레이션 데이터 손실 | `.md` 아카이브 보관 + 집계 대조 검증 + 병렬 운영 컷오버 |
| 단일 사용자에 과설계 | `user_id`만 두고 인증은 v2.1로 유보, 스키마/엔드포인트는 최소 |
```
