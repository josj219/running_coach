# V2 아키텍처 설계서

> 연관: [V2_MVP_SCOPE.md](./V2_MVP_SCOPE.md) · [V2_MIGRATION_PLAN.md](./V2_MIGRATION_PLAN.md) · [V2_TEST_STRATEGY.md](./V2_TEST_STRATEGY.md)
> 스택: FastAPI(async) + PostgreSQL 16 + SQLAlchemy 2.0/Alembic + React PWA(Vite) + Docker Compose + GitLab CI/CD
> 작성일: 2026-06-10

---

## 1. 시스템 구성

```
┌─────────────┐   HTTPS    ┌──────────────────┐   asyncpg   ┌────────────┐
│  PWA (web)  │ ─────────► │  FastAPI (api)   │ ──────────► │ PostgreSQL │
│ React+Vite  │ ◄───SSE─── │  uvicorn         │             │  (db)      │
│ nginx 정적   │            │  services/coach  │ ──HTTPS──►  Anthropic API
└─────────────┘            └──────────────────┘
   service worker             COACH_MOCK 분기
   (오프라인 셸)
```

- **web**: 정적 빌드 → nginx. `/api/*` 는 api로 프록시, 그 외 SPA fallback.
- **api**: stateless. AI 키 보유. SSE로 토큰 스트림.
- **db**: 단일 진실 공급원(SSOT). Markdown은 런타임 직렬화 산출물(영구 저장 X).

---

## 2. PostgreSQL 물리 스키마

> 전 테이블 `user_id` 보유(v2.0은 `=1` 고정, 멀티유저 확장 대비). 시간은 `TIMESTAMPTZ`.
> **Markdown 원문 보존 컬럼 정책**: AI가 생성하는 산출물(`weekly_plans`, `daily_plans`, `workout_reviews`, `weekly_evaluations`)에만 `raw_md TEXT NULL` 을 둔다 — 재현·디버깅·AI 파싱 실패 시 폴백용. 사용자 입력/정형 데이터(profile, goal, workout_logs, sessions)에는 두지 않는다. 표시 로직은 raw_md를 절대 파싱하지 않는다(구조화 컬럼만 사용).

### 2.1 ENUM 정의

```sql
CREATE TYPE session_kind AS ENUM (
  '인터벌','롱런','템포','페이스런','회복조깅','쉬운달리기',
  '근력','헬스','드릴','코어','가동성','휴식','기타');
CREATE TYPE session_status   AS ENUM ('예정','완료','부분완료','미수행');  -- v1 ✅/⚠️/❌/예정
CREATE TYPE recovery_level   AS ENUM ('낮음','보통','높음');               -- v1 🟢/🟡/🔴
CREATE TYPE gen_status       AS ENUM ('generating','ready','error');
```

### 2.2 테이블 명세

#### `users`
| 컬럼 | 타입 | Null | Default | 제약 |
|------|------|------|---------|------|
| id | BIGSERIAL | NO | | PK |
| email | TEXT | NO | | UNIQUE |
| nickname | TEXT | NO | `'고고조'` | |
| created_at | TIMESTAMPTZ | NO | `now()` | |

#### `user_profiles`
| 컬럼 | 타입 | Null | Default | 제약 |
|------|------|------|---------|------|
| user_id | BIGINT | NO | | PK, FK→users(id) ON DELETE CASCADE |
| height_cm | NUMERIC(5,1) | YES | | |
| weight_kg | NUMERIC(5,1) | YES | | |
| age | INT | YES | | |
| career_years | NUMERIC(3,1) | YES | | |
| max_hr | INT | YES | | |
| resting_hr | INT | YES | | |
| vo2_max | NUMERIC(4,1) | YES | | |
| pb_10k | INTERVAL | YES | | |
| pb_half | INTERVAL | YES | | |
| pb_full | INTERVAL | YES | | |
| body_note | TEXT | YES | | 체형·선호·훈련가능시간 자유서술 |
| avatar_url | TEXT | YES | | |
| updated_at | TIMESTAMPTZ | NO | `now()` | |

#### `goals`
| 컬럼 | 타입 | Null | Default | 제약 |
|------|------|------|---------|------|
| id | BIGSERIAL | NO | | PK |
| user_id | BIGINT | NO | | FK→users CASCADE |
| race_type | TEXT | NO | | '풀마라톤' |
| target_time | INTERVAL | YES | | sub3:30 → '3:30:00' |
| target_date | DATE | YES | | D-day 계산(타입 DATE → 파싱 불필요, BUG-17 제거) |
| description | TEXT | YES | | |
| is_active | BOOLEAN | NO | `true` | |
| created_at | TIMESTAMPTZ | NO | `now()` | |

- index: `CREATE UNIQUE INDEX uq_goal_active ON goals(user_id) WHERE is_active;` (활성 목표 1개 보장)

#### `app_settings`
| 컬럼 | 타입 | Null | Default |
|------|------|------|---------|
| user_id | BIGINT | NO | PK, FK→users CASCADE |
| weekly_goal_km | NUMERIC(5,1) | NO | `45` |
| pace_unit | TEXT | NO | `'분/km'` |
| distance_unit | TEXT | NO | `'km'` |
| notify_training | BOOLEAN | NO | `true` |
| notify_after_workout | BOOLEAN | NO | `true` |
| updated_at | TIMESTAMPTZ | NO | `now()` |

#### `weekly_plans`
| 컬럼 | 타입 | Null | Default | 제약 |
|------|------|------|---------|------|
| id | BIGSERIAL | NO | | PK |
| user_id | BIGINT | NO | | FK→users CASCADE |
| iso_year | INT | NO | | |
| iso_week | INT | NO | | |
| week_start | DATE | NO | | 월요일 |
| direction | TEXT | YES | | 주간 방향성 |
| goal_km | NUMERIC(5,1) | YES | | 없으면 settings 폴백(BUG-14) |
| intensity | TEXT | YES | | |
| raw_md | TEXT | YES | | AI 원문 백업 |
| created_at | TIMESTAMPTZ | NO | `now()` | |
| | | | | **UNIQUE(user_id, iso_year, iso_week)** |

#### `sessions`  (계획된 1회 훈련 단위 — `weekly_plans` 1:N)
| 컬럼 | 타입 | Null | Default | 제약 |
|------|------|------|---------|------|
| id | BIGSERIAL | NO | | PK |
| plan_id | BIGINT | NO | | FK→weekly_plans(id) ON DELETE CASCADE |
| session_date | DATE | NO | | |
| weekday | SMALLINT | NO | | 0=월 |
| kind | session_kind | NO | | |
| title | TEXT | YES | | '트레드밀 Easy Run' |
| duration_min | INT | YES | | 범위 하한 |
| duration_min_max | INT | YES | | 범위 상한(BUG-15: "70~80분" 분해) |
| target_pace | TEXT | YES | | '6:20~6:40/km' |
| note | TEXT | YES | | |
| status | session_status | NO | `'예정'` | |
| is_rest | BOOLEAN | NO | `false` | 수행률 분모 제외(BUG-16) |
| | | | | **UNIQUE(plan_id, session_date)** |
- index: `idx_sessions_date ON sessions(session_date)`

#### `daily_plans`  (당일 상세 AI 카드 — `sessions` 0..1:1)
| 컬럼 | 타입 | Null | Default | 제약 |
|------|------|------|---------|------|
| id | BIGSERIAL | NO | | PK |
| user_id | BIGINT | NO | | FK→users CASCADE |
| plan_date | DATE | NO | | |
| session_id | BIGINT | YES | | FK→sessions(id) ON DELETE SET NULL |
| sections | JSONB | NO | `'{}'` | {warmup,main,cooldown,note,detail} |
| is_adjusted | BOOLEAN | NO | `false` | v1 `<!-- ADJUSTED -->` 대체(BUG-11) |
| adjust_reason | TEXT | YES | | |
| status | gen_status | NO | `'ready'` | |
| raw_md | TEXT | YES | | |
| created_at | TIMESTAMPTZ | NO | `now()` | |
| | | | | **UNIQUE(user_id, plan_date)** (당일 1계획, BUG-19 캐시문제 구조 제거) |

#### `workout_logs`  (실제 수행 기록 — `sessions` 0..1:1)
| 컬럼 | 타입 | Null | Default | 제약 |
|------|------|------|---------|------|
| id | BIGSERIAL | NO | | PK |
| user_id | BIGINT | NO | | FK→users CASCADE |
| session_id | BIGINT | YES | | FK→sessions(id) ON DELETE SET NULL |
| log_date | DATE | NO | | |
| kind | session_kind | NO | | |
| distance_km | NUMERIC(5,2) | NO | `0` | |
| duration_sec | INT | YES | | |
| avg_pace | TEXT | YES | | '6:12' |
| avg_hr | INT | YES | | |
| cadence | INT | YES | | |
| elevation_m | INT | YES | | |
| fatigue_label | TEXT | YES | | '괜찮아요' |
| fatigue_num | SMALLINT | YES | | 0~10 |
| pain_part | TEXT | YES | | |
| pain_level | SMALLINT | NO | `0` | ≥4 → 세션 부분완료 트리거 |
| user_comment | TEXT | YES | | |
| image_url | TEXT | YES | | Garmin/Strava 스크린샷 |
| created_at | TIMESTAMPTZ | NO | `now()` | |
| | | | | **UNIQUE(user_id, log_date)** |
- index: `idx_logs_user_date ON workout_logs(user_id, log_date DESC)`

#### `workout_reviews`  (`workout_logs` 1:1)
| 컬럼 | 타입 | Null | Default | 제약 |
|------|------|------|---------|------|
| id | BIGSERIAL | NO | | PK |
| log_id | BIGINT | NO | | FK→workout_logs(id) CASCADE, **UNIQUE** |
| strengths | TEXT | YES | | |
| improvements | TEXT | YES | | |
| recovery | recovery_level | YES | | enum(파싱 제거, BUG-13) |
| coach_comment | TEXT | YES | | |
| raw_md | TEXT | YES | | |
| created_at | TIMESTAMPTZ | NO | `now()` | |

#### `weekly_evaluations`  (`weekly_plans` 1:1)
| 컬럼 | 타입 | Null | Default | 제약 |
|------|------|------|---------|------|
| id | BIGSERIAL | NO | | PK |
| plan_id | BIGINT | NO | | FK→weekly_plans CASCADE, **UNIQUE** |
| total_km | NUMERIC(6,1) | NO | | 앱 산출(SQL) |
| done_sessions | INT | NO | | |
| total_sessions | INT | NO | | |
| completion_rate | INT | NO | | done/total(BUG-16 단일정의) |
| coach_message | TEXT | YES | | AI 서술 |
| detail_md | TEXT | YES | | |
| is_partial | BOOLEAN | NO | `false` | 주중 진행 평가 |
| raw_md | TEXT | YES | | |
| created_at | TIMESTAMPTZ | NO | `now()` | |

### 2.3 관계 요약

```
users ─1:1─ user_profiles
users ─1:N─ goals (활성 1)
users ─1:1─ app_settings
users ─1:N─ weekly_plans ─1:N─ sessions
                  │                 │
                  │                 ├─0..1:1─ daily_plans  (session_id, 당일 상세 카드)
                  │                 └─0..1:1─ workout_logs (session_id, 실제 수행)
                  └─1:1─ weekly_evaluations
workout_logs ─1:1─ workout_reviews
```

- **sessions ↔ workout_logs**: 계획(session)과 실제(log)를 `session_id` FK로 연결. 계획 외 운동(즉흥)도 `session_id=NULL`로 기록 가능. 수행률 = `sessions` 중 매칭 log가 완료된 비율.
- **weekly_plans ↔ daily_plans**: 직접 FK 없음. `daily_plans → sessions → weekly_plans` 경로로 연결(당일 카드는 세션의 상세화). 주 단위 조회는 `sessions.session_date BETWEEN week_start AND +6`.
- **파생 뷰**: `v_running_history`(logs WHERE distance_km>0), `v_injury_history`(logs WHERE pain_level>0). v1의 03/05 .md를 대체 — 별도 쓰기 없음(BUG-18 구조 제거).

---

## 3. API 계약서

> Base: `/api`. 요청/응답 `application/json` (스트리밍은 `text/event-stream`).
> 시간 필드 ISO8601. 날짜 `YYYY-MM-DD`. 모든 응답에 `X-Request-Id`.

### 3.1 공통 실패 응답 포맷

```json
{ "error": { "code": "VALIDATION_ERROR", "message": "log_date is required",
             "details": [{"field":"log_date","issue":"missing"}] } }
```

| code | HTTP | 의미 |
|------|------|------|
| VALIDATION_ERROR | 422 | 요청 스키마 위반(pydantic) |
| NOT_FOUND | 404 | 리소스 없음 |
| CONFLICT | 409 | 멱등성/유니크 충돌(중복 저장) |
| AI_UNAVAILABLE | 503 | Claude 호출 실패(타임아웃·5xx·키 누락) |
| INTERNAL | 500 | 기타 |

### 3.2 멱등성 / 중복 저장 정책

- **자연키 기반 upsert**: `workout_logs(user_id,log_date)`, `daily_plans(user_id,plan_date)`, `sessions(plan_id,session_date)`, `weekly_plans(user_id,iso_year,iso_week)` 는 자연키 충돌 시 **update**(덮어쓰기) — 같은 날 두 번 저장해도 행 1개.
- **Idempotency-Key 헤더(선택)**: POST에 `Idempotency-Key: <uuid>` 전달 시 24h 내 같은 키 재요청은 최초 결과를 재반환(네트워크 재시도 안전). 미전달 시 자연키 정책만 적용.
- **리뷰**: `workout_reviews(log_id)` UNIQUE → 재생성 요청은 기존 리뷰 update(덮어쓰기). 명시적 `?force=true` 없이도 덮어씀(리뷰는 1개만 유효).

### 3.3 AI 호출 실패 시 동작 (핵심 규칙)

> **불변식: 사용자 데이터(로그)는 AI와 독립적으로 먼저 커밋한다.** AI는 그 위에 붙는 부가물.

1. `POST /workout-logs` (기록 저장) — **AI 미호출**. 항상 즉시 커밋. → 빈 화면 불가(BUG-04 정신).
2. `POST /workout-logs/{id}/review` (리뷰) — log는 이미 존재. AI 실패 시:
   - `503 AI_UNAVAILABLE` 반환, `workout_reviews` 미생성.
   - 프론트는 "리뷰 생성 실패 — 기록은 저장됨, 재시도" 표시. **기록 화면은 유지**.
   - 재시도는 같은 엔드포인트 재호출(멱등).
3. `COACH_MOCK` 설정 시 실 API 미호출(테스트/CI). `__ERROR__` → 위 503 경로 그대로.

### 3.4 엔드포인트 명세 (Phase 1 = M1~M7)

#### `GET /api/profile` (M1)
- **200**
```json
{ "nickname":"고고조","height_cm":178,"weight_kg":80,"age":35,
  "career_years":2,"pb_10k":"00:42:13","pb_half":"01:38:00","pb_full":"03:51:00",
  "body_note":"...","avatar_url":null }
```

#### `GET /api/goal` (M2)
- **200**
```json
{ "race_type":"풀마라톤","target_time":"03:30:00","target_date":"2026-11-01",
  "dday":144,"description":"안정적인 호흡과 상태로" }
```
- 목표 없으면 `target_date:null, dday:null`.

#### `GET /api/today` (M3)
- **200**
```json
{ "today":"2026-06-10","weekday":"수",
  "state":"PRE_WORKOUT",        // S0 NO_PLAN | S1 PRE_WORKOUT | S2 POST_WORKOUT | S3 REVIEWED | S4 REST_DAY | S5 WEEK_END
  "dday":144,
  "session":{ "id":42,"kind":"쉬운달리기","title":"트레드밀 Easy Run",
              "duration_min":30,"target_pace":"6:20~6:40/km","is_rest":false },
  "daily_plan":{ "sections":{"warmup":"...","main":"...","cooldown":"...","note":"...","detail":"..."},
                 "is_adjusted":false },
  "week_progress":{ "done":1,"total":5,"completion_rate":20,"week_km":6.2,"goal_km":45 } }
```
- `daily_plan:null` 가능(당일 카드 미생성 — Phase 1은 마이그레이션분만).

#### `GET /api/weeks/{iso_week}` (M4)  — `iso_week` = `2026-W23`
- **200**
```json
{ "iso_week":"2026-W23","week_start":"2026-06-01","direction":"🟡 기초 복귀 단계",
  "goal_km":45,"progress":{"done":1,"total":2,"completion_rate":50,"week_km":6.2},
  "sessions":[ {"session_date":"2026-06-06","weekday":"토","kind":"드릴","title":"야외 빠른 걷기 + 폼 드릴",
                "duration_min":30,"status":"완료","is_rest":false},
               {"session_date":"2026-06-07","weekday":"일","kind":"쉬운달리기","title":"트레드밀 복귀 조깅",
                "duration_min":40,"status":"예정","is_rest":false} ] }
```
- **404 NOT_FOUND** 해당 주 계획 없음.

#### `GET /api/workout-logs` (M7)
- query: `?from=2026-06-01&to=2026-06-10&limit=30`
- **200**
```json
{ "items":[ {"id":7,"log_date":"2026-06-03","kind":"드릴","distance_km":0,
             "fatigue_label":"괜찮아요","pain_level":0,
             "review":{"recovery":"낮음","coach_comment":"..."} } ],
  "next_cursor":null }
```

#### `POST /api/workout-logs` (M5)
- **request**
```json
{ "log_date":"2026-06-10","kind":"쉬운달리기","distance_km":5.2,"duration_sec":1932,
  "avg_pace":"6:12","avg_hr":143,"cadence":172,
  "fatigue_label":"괜찮아요","fatigue_num":3,"pain_part":null,"pain_level":0,
  "user_comment":"발목 이상 없음","image_url":null }
```
- **201** `{ "id":12,"session_id":42,"session_status":"완료" }`
- **409 CONFLICT** (Idempotency-Key 재사용 + 본문 상이 시). 자연키 동일 → **200**(upsert, 기존 id).
- 부수효과(트랜잭션): 매칭 `session.status` 갱신(pain_level≥4 → '부분완료'). 파생 이력은 뷰라 쓰기 없음.

#### `POST /api/workout-logs/{id}/review` (M6, SSE)
- **request**: 본문 없음(log_id로 컨텍스트 조립). 선택 `{ "regenerate": true }`.
- **200 `text/event-stream`**
```
event: token
data: "심박이 안정적으로 "

event: token
data: "Zone 2 범위에서 유지됐다. "

event: done
data: {"review_id":5,"recovery":"낮음","strengths":"...","improvements":"...","coach_comment":"..."}
```
- **404** log 없음. **503 AI_UNAVAILABLE** AI 실패(리뷰 미저장, 로그 보존).
- 비스트리밍 폴백: `Accept: application/json` 시 완성 후 단일 JSON 반환.

#### `GET /api/settings` (M1군)
- **200** `{ "weekly_goal_km":45,"pace_unit":"분/km","distance_unit":"km","notify_training":true,"notify_after_workout":true }`

> Phase 2+ 엔드포인트(`POST /weekly-plans`, `/daily-plans`, `/adjust`, `/evaluation`, `PATCH /profile|goal|settings`)는 동일 규약(SSE·실패정책·멱등성)을 따른다. 상세는 Phase 2 착수 시 본 문서에 추가.

---

## 4. 모바일 / PWA 화면 설계

> v1 디자인 자산(`design/project/`, NRC 스타일 iOS UI) 재사용. 모바일 우선, 최대폭 640px.

### 4.1 하단 탭 구조 (고정 탭바)

```
┌──────────────────────────────────┐
│            (화면 컨텐츠)            │
│                                   │
├──────┬──────┬──────┬──────────────┤
│ 오늘  │ 이번주 │ 기록  │   설정        │   ← 4탭 (v1 _TAB_NAMES 동일)
│ 🏃   │ 📅   │ 📊   │   ⚙️          │
└──────┴──────┴──────┴──────────────┘
```
탭은 클라이언트 라우팅(`/today`, `/week`, `/history`, `/settings`). 상태는 URL — 새로고침/딥링크 안전(v1 session_state 핵 제거).

### 4.2 오늘 화면 플로우 (M3·M5·M6 — 상태머신)

```
GET /api/today → state 분기
  S0 NO_PLAN      → "이번 주 계획 없음" + (Phase2: 생성 CTA)
  S1 PRE_WORKOUT  → 오늘 세션 Hero + 당일 카드(워밍업/메인/쿨다운 → 탭하면 모달) + [운동 기록하기]
  S2 POST_WORKOUT → 기록 입력 폼 (M5)
  S3 REVIEWED     → 리뷰 결과 카드 + 회복 뱃지 + 내일 예고
  S4 REST_DAY     → 휴식 안내 + 내일 예고
  S5 WEEK_END     → 주간 요약 진입 유도

[운동 기록하기] 탭
  → 기록 입력 화면 (4.3)
  → 저장(POST /workout-logs) → 즉시 S3 진입(로그 커밋됨)
  → 리뷰 SSE(POST /review) 구독 → 토큰 스트리밍 표시 → done 시 리뷰 카드(4.4)
  → AI 실패 시: "기록 저장됨 · 리뷰 재시도" 인라인 (화면 유지)
```

### 4.3 기록 입력 화면 (M5)

```
종류        [ 쉬운달리기 ▾ ]   ← session.kind 프리필
거리(km)    [ 5.2 ]
시간        [ 32:12 ]
평균 페이스  [ 6:12 ]
평균 심박    [ 143 ]
케이던스     [ 172 ]
피로도       [ 😊 괜찮아요  3/10 슬라이더 ]
불편함/통증  [ 없음 ▾ ] (선택 시 부위+강도)
소감(선택)   [ ............ ]
스크린샷     [ 📷 업로드 ]  ← Garmin/Strava (선택)
            [ 저장하고 리뷰 받기 ]
```
- 클라이언트 검증(거리≥0, 심박 30~250). 통증≥4 선택 시 경고 배너.
- 저장은 낙관적 UI: 즉시 S3 전환 후 리뷰 스트림.

### 4.4 리뷰 결과 화면 (M6)

```
┌ 오늘 훈련 리뷰 ────────────────┐
│ 🟢 회복 양호                    │   ← recovery enum → 뱃지 색(파싱 없음)
│                                │
│ 잘한 점                         │
│   · 심박 Zone 2 안정 유지 ...    │
│ 개선할 점                        │
│   · 후반 케이던스 5spm 하락 ...   │
│ ─────────────                   │
│ 코치 한마디                       │
│   동일 페이스서 평균 심박 ↓ ...    │
└────────────────────────────────┘
[ 이번 주 요약 보기 → ]
```
스트리밍 중에는 coach_comment 영역에 토큰을 실시간 append, done 시 구조화 필드로 재배치.

### 4.5 이번 주 요약 화면 (M4)

```
┌ 진행률 ──────────────────┐
│ 6.2 / 45 km  [▓▓░░░░] 14% │
│ 완료 1/2 세션 · 수행률 50% │   ← done/total 단일정의
└──────────────────────────┘
요일 스트립  월 화 수 ● 목 금 토✓ 일
일정 리스트
  토 ✓ 야외 빠른 걷기+폼 드릴  30분  완료
  일 ○ 트레드밀 복귀 조깅      40분  예정
(Phase2) [ 성장 리포트 ]  [ 계획 조정 ]
```

### 4.6 설정 화면 (Phase 1: 조회 / Phase 3: 편집)

```
프로필   닉네임·키·체중·나이·PB(10k/half/full)
목표     풀마라톤 sub3:30 · 2026-11-01 · D-144
설정     주간 목표 45km · 페이스 단위 · 알림 토글
앱       버전 · 캐시 비우기 · (Phase3) 로그아웃
```
Phase 1은 읽기 전용(편집 버튼 비활성/숨김). Phase 3에서 PATCH 연결.

### 4.7 아이폰 홈 화면 추가 기준 (PWA 설치 가능성)

`manifest.webmanifest` + service worker 필수 요건:

| 요건 | 값 |
|------|-----|
| `name` / `short_name` | "러닝 코치" / "코치" |
| `display` | `standalone` (주소창 숨김) |
| `start_url` | `/today?source=pwa` |
| `theme_color` / `background_color` | `#0088FF` / `#F2F2F7` (v1 토큰) |
| 아이콘 | 180×180(apple-touch-icon), 192/512 maskable |
| `<meta apple-mobile-web-app-capable>` | yes (iOS standalone) |
| service worker | 셸(앱 정적 자산) precache → 오프라인 셸 로드 |
| HTTPS | 필수(설치·SW 동작 조건) |

- iOS Safari는 자동 설치 프롬프트가 없으므로, 첫 방문 시 "홈 화면에 추가하는 법" 안내 시트 1회 노출.
- 오프라인: 셸+마지막 조회 데이터(IndexedDB/Cache) 표시. 쓰기는 Phase 3에서 백그라운드 sync 큐.

---

## 5. Docker Compose 설계

### 5.1 서비스

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: coach
      POSTGRES_USER: coach
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U coach -d coach"]
      interval: 5s
      timeout: 3s
      retries: 5
    # 운영 override에서 ports 제거(외부 비공개)
    ports: ["5432:5432"]

  api:
    build: ./api
    env_file: [.env]
    environment:
      DATABASE_URL: postgresql+asyncpg://coach:${DB_PASSWORD}@db:5432/coach
    depends_on:
      db: {condition: service_healthy}    # ← alembic은 db ready 이후
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000"
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8000/api/health"]
      interval: 10s
      timeout: 3s
      retries: 5
      start_period: 20s     # 마이그레이션 시간 확보
    ports: ["8000:8000"]

  web:
    build: ./web              # multi-stage: node build → nginx
    depends_on:
      api: {condition: service_healthy}
    ports: ["80:80"]

volumes:
  pgdata:
```

### 5.2 env 파일

```bash
# .env  (git ignore. .env.example 만 커밋)
DB_PASSWORD=change-me
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-6
COACH_MOCK=                # 로컬/운영 비움. 테스트·CI에서만 "1"
TZ=Asia/Seoul
```

### 5.3 마이그레이션 실행 순서

```
docker compose up
  └ db 컨테이너 기동 → healthcheck(pg_isready) 통과
      └ api 컨테이너 시작(depends_on healthy)
          └ command: alembic upgrade head   (스키마 보장)
              └ uvicorn 기동 → /api/health
                  └ web 컨테이너(api healthy 후)
```
- alembic은 **api 기동 시 1회** 실행(별도 job 불필요). 멀티 인스턴스 시엔 advisory lock으로 동시 실행 방지(향후).
- 최초 1회: 마이그레이션 직후 `scripts/migrate_v1.py --commit`(데이터 적재) 수동/원샷 job 실행.

---

## 6. GitLab CI/CD 상세

### 6.1 브랜치 전략

| 브랜치 | 역할 | 배포 |
|--------|------|------|
| `feat/*` | 기능 작업 | MR → `dev` |
| `dev` | 통합 | push 시 **dev 환경 자동 배포** |
| `main` | 릴리스 | tag 시 **prod 수동 승인 배포** |

### 6.2 파이프라인

```yaml
stages: [lint, test, build, deploy]

variables:
  POSTGRES_DB: coach
  POSTGRES_USER: coach
  POSTGRES_PASSWORD: ci
  DATABASE_URL: "postgresql+asyncpg://coach:ci@postgres:5432/coach"

# ── LINT ──
lint:api:
  stage: lint
  image: python:3.11-slim
  script: [ "pip install ruff", "ruff check api/" ]
lint:web:
  stage: lint
  image: node:20-alpine
  script: [ "cd web && npm ci && npm run lint" ]

# ── TEST ──
test:api:
  stage: test
  image: python:3.11-slim
  services: ["postgres:16-alpine"]
  variables: { COACH_MOCK: "1" }        # 실 Claude 미호출 → 비용 0
  script:
    - pip install -r api/requirements.txt -r api/requirements-test.txt
    - alembic upgrade head
    - pytest api/tests -q --cov=app --cov-report=term-missing
  coverage: '/TOTAL.*\s(\d+%)$/'

test:web:
  stage: test
  image: node:20-alpine
  script: [ "cd web && npm ci", "npm run test" ]

e2e:
  stage: test
  image: mcr.microsoft.com/playwright:v1.49.0
  services: ["postgres:16-alpine"]
  variables: { COACH_MOCK: "1" }
  script:
    - (cd api && pip install -r requirements.txt && alembic upgrade head &&
       python scripts/seed_e2e.py && uvicorn app.main:app --port 8000 &)
    - cd web && npm ci && npm run build && npm run preview &
    - npx playwright test
  artifacts: { when: on_failure, paths: ["web/playwright-report/"] }

# ── BUILD ──
build:
  stage: build
  image: docker:27
  services: ["docker:27-dind"]
  script:
    - echo "$CI_REGISTRY_PASSWORD" | docker login -u "$CI_REGISTRY_USER" --password-stdin "$CI_REGISTRY"
    - docker build -t $CI_REGISTRY_IMAGE/api:$CI_COMMIT_SHORT_SHA ./api
    - docker build -t $CI_REGISTRY_IMAGE/web:$CI_COMMIT_SHORT_SHA ./web
    - docker push $CI_REGISTRY_IMAGE/api:$CI_COMMIT_SHORT_SHA
    - docker push $CI_REGISTRY_IMAGE/web:$CI_COMMIT_SHORT_SHA
  rules:
    - if: '$CI_COMMIT_BRANCH == "dev" || $CI_COMMIT_TAG'

# ── DEPLOY ──
deploy:dev:
  stage: deploy
  environment: { name: dev }
  script:
    - ssh $DEV_HOST "cd /srv/coach && export TAG=$CI_COMMIT_SHORT_SHA &&
        docker compose -f docker-compose.yml -f docker-compose.dev.yml pull &&
        docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d &&
        docker compose exec -T api alembic upgrade head &&
        curl -fsS http://localhost:8000/api/health"   # smoke
  rules: [ { if: '$CI_COMMIT_BRANCH == "dev"' } ]

deploy:prod:
  stage: deploy
  environment: { name: production }
  when: manual                                          # 수동 승인
  script:
    - ssh $PROD_HOST "cd /srv/coach && export TAG=$CI_COMMIT_TAG &&
        docker compose -f docker-compose.yml -f docker-compose.prod.yml pull &&
        docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d &&
        docker compose exec -T api alembic upgrade head"
  rules: [ { if: '$CI_COMMIT_TAG' } ]
```

### 6.3 필요한 GitLab CI/CD Variables

| Key | Scope | Masked | Protected | 용도 |
|-----|-------|--------|-----------|------|
| `ANTHROPIC_API_KEY` | prod/dev | ✅ | ✅ | 운영 AI 키(CI 테스트는 COACH_MOCK이라 불필요) |
| `DB_PASSWORD` | all env | ✅ | ✅ | DB 비밀번호 |
| `CI_REGISTRY_USER`/`_PASSWORD` | — | ✅ | ✅ | 이미지 레지스트리(기본 제공 가능) |
| `DEV_HOST` / `PROD_HOST` | env별 | | ✅ | 배포 SSH 타깃 |
| `SSH_PRIVATE_KEY` | env별 | ✅ | ✅ | 배포 SSH 키(before_script로 agent 등록) |

### 6.4 롤백 전략

- **이미지 태그 롤백**: 배포는 `:$SHA`/`:$TAG` 불변 태그 사용. 직전 정상 태그로 `TAG=<prev> docker compose up -d` 재실행 → 즉시 복구. `latest` 미사용.
- **DB 마이그레이션 롤백**: 파괴적 변경은 **expand/contract 2단계**(먼저 컬럼 추가·이중쓰기 → 다음 릴리스에서 제거). 단일 릴리스 내 비파괴 변경은 `alembic downgrade -1` 가능. 데이터 변형 마이그레이션은 backfill 스크립트 + 백업(`pg_dump`) 선행.
- **운영 절차**: 배포 전 자동 `pg_dump` 스냅샷 → 실패 시 ① 이미지 태그 롤백 ② 필요 시 `alembic downgrade` ③ 최후 스냅샷 복원.
- **smoke 실패 시**: deploy job이 `curl /health` 실패하면 비정상 종료 → 이전 컨테이너 유지(무중단 롤백). 헬스 통과해야 그린.
