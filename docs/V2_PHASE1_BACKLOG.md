# V2 Phase 1 MVP — Issue Backlog

> 대상: **Phase 1 MVP만** (M1~M7 — 프로필/목표 조회, 오늘 계획 조회, 운동 기록 저장, AI 리뷰 저장, 이번 주 요약 조회)
> 연관: [V2_MVP_SCOPE.md](./V2_MVP_SCOPE.md) · [V2_ARCHITECTURE.md](./V2_ARCHITECTURE.md) · [V2_MIGRATION_PLAN.md](./V2_MIGRATION_PLAN.md) · [V2_TEST_STRATEGY.md](./V2_TEST_STRATEGY.md)
> 작성일: 2026-06-10

## 범례

- **크기**: `S`=0.5일, `M`=1일
- **의존**: 시작 전 완료돼야 하는 선행 이슈. `—`=없음(병렬 가능)
- **DoD**: 완료 조건(이게 충족돼야 MR 머지). **산출물**: 생성/변경 파일
- MVP에 필요한 최소 기반(Phase 0)도 본 백로그에 포함(없으면 MVP가 못 뜸)
- 라벨: `area::{infra,db,api,web,migration,test}` · `feat::{M1..M7}`

## 작업 그룹 & 권장 순서

```
A. 스캐폴딩 (001–004)     ─┐
B. DB·모델 (005–011)      ─┼─► D. 마이그레이션 (017–023)
C. coach·context (012–016)┘        │
                                   ▼
                          E. 읽기 API (024–033) ─► G. PWA (037–047)
                          F. 쓰기 API (034–036) ─┘        │
                                                          ▼
                                         H. E2E·배포 (048–054)
```

크리티컬 패스: `001→002→003→005→006/007→010 → 017…022 → 024 → 029/031 → 035→037 → 042/044 → 048/049`

---

## A. 스캐폴딩 & 기반

### P1-001 · 모노레포 구조 + .env.example · `S` · infra
- **의존**: —
- **DoD**: `api/`,`web/`,`scripts/`,`docs/` 레이아웃 생성. `.env.example`에 DB_PASSWORD/ANTHROPIC_API_KEY/CLAUDE_MODEL/COACH_MOCK/TZ 키. `.env`·`backups/`·`archive/` gitignore. README에 부트스트랩 절차.
- **산출물**: 디렉토리 트리, `.env.example`, `.gitignore`, `README.md`

### P1-002 · docker-compose(db+api) 골격 + healthcheck · `M` · infra
- **의존**: P1-001
- **DoD**: `docker compose up` → postgres16 기동 + `pg_isready` healthcheck 통과. api 컨테이너 `depends_on: db healthy`. pgdata 볼륨 영속.
- **산출물**: `docker-compose.yml`, `api/Dockerfile`

### P1-003 · FastAPI 스켈레톤 + config + /api/health · `S` · api
- **의존**: P1-002
- **DoD**: `GET /api/health`→`{"status":"ok"}` 200. `pydantic-settings`로 env 로드(DATABASE_URL 등). `X-Request-Id` 미들웨어. uvicorn 기동.
- **산출물**: `api/app/main.py`, `api/app/config.py`, `api/requirements.txt`

### P1-004 · web Vite+React 스켈레톤 + nginx + compose web · `M` · web
- **의존**: P1-003
- **DoD**: multi-stage(node build→nginx) 이미지. nginx가 `/api`→api 프록시, 그 외 SPA fallback. `docker compose up`로 web:80 접속 → 빈 셸 렌더.
- **산출물**: `web/`(Vite 초기), `web/Dockerfile`, `web/nginx.conf`, compose `web` 서비스

---

## B. DB · 모델 · 마이그레이션 기반

### P1-005 · SQLAlchemy 2.0 async 엔진 + 세션 의존성 · `S` · db
- **의존**: P1-003
- **DoD**: asyncpg 엔진, `get_session` FastAPI 의존성(요청당 세션·자동 close). 헬스에서 `SELECT 1` 연결 확인.
- **산출물**: `api/app/db/session.py`, `api/app/db/base.py`

### P1-006 · ORM 모델: 사용자/프로필/설정/목표 + enum · `M` · db
- **의존**: P1-005
- **DoD**: `users`,`user_profiles`,`app_settings`,`goals` 모델 + `recovery_level` 외 공용 enum 선언. 컬럼/타입/null/default/PK/FK/UNIQUE가 ARCHITECTURE §2와 일치. `goals` 활성 1개 부분유니크 인덱스.
- **산출물**: `api/app/db/models/user.py`, `.../goal.py`, `.../enums.py`

### P1-007 · ORM 모델: 주간계획/세션/당일계획/기록/리뷰/평가 · `M` · db
- **의존**: P1-006
- **DoD**: `weekly_plans`,`sessions`,`daily_plans`,`workout_logs`,`workout_reviews`,`weekly_evaluations` 모델. `session_kind`/`session_status`/`gen_status` enum. 관계(plan→sessions, session→log/daily_plan, log→review) + UNIQUE/인덱스 ARCHITECTURE 일치.
- **산출물**: `api/app/db/models/plan.py`, `.../log.py`, `.../review.py`

### P1-008 · Alembic 초기화 + 0001_init · `M` · db
- **의존**: P1-007
- **DoD**: `alembic upgrade head`로 전 테이블·enum·인덱스 생성. `alembic downgrade base` 도 깨끗이 되돌림. api 컨테이너 command에 `alembic upgrade head` 선행.
- **산출물**: `api/alembic.ini`, `api/alembic/env.py`, `api/alembic/versions/0001_init.py`

### P1-009 · 파생 뷰 v_running_history / v_injury_history · `S` · db
- **의존**: P1-008
- **DoD**: 두 뷰 마이그레이션(logs WHERE distance_km>0 / pain_level>0). `SELECT * FROM v_*` 동작. v1 03/05 .md를 별도 테이블 없이 대체함을 주석화.
- **산출물**: `api/alembic/versions/0002_views.py`

### P1-010 · 기본 사용자 시드(user_id=1) · `S` · db
- **의존**: P1-008
- **DoD**: 멱등 시드(`scripts/seed_base.py`) — email=josj219@gmail.com 사용자 + 기본 settings 행. 2회 실행해도 행 1개.
- **산출물**: `scripts/seed_base.py`

### P1-011 · 트랜잭션 롤백 테스트 픽스처 · `S` · test
- **의존**: P1-008
- **DoD**: pytest fixture — 테스트별 SAVEPOINT 감싸 종료 시 롤백. 테스트 DB url env 격리. `test_imports.py`(전 모듈 import 성공, BUG-01 방지) 통과.
- **산출물**: `api/tests/conftest.py`, `api/tests/test_imports.py`

---

## C. coach 서비스 & context

### P1-012 · coach 서비스 async + COACH_MOCK + AIUnavailable · `M` · api
- **의존**: P1-003
- **DoD**: `coach.stream()` async generator. `COACH_MOCK` 미설정→실 호출, `=1`→모의 토큰, `=__ERROR__`→`AIUnavailable`. 유닛 테스트 3분기. 실 API 미호출 확인.
- **산출물**: `api/app/services/coach.py`, `api/tests/test_coach_mock.py`

### P1-013 · CLAUDE.md 시스템 프롬프트 로더 · `S` · api
- **의존**: P1-012
- **DoD**: 루트 `CLAUDE.md` 읽어 시스템 프롬프트로. 파일 없으면 요약 폴백. v1 `get_coaching_system_prompt` 동작 동등.
- **산출물**: `api/app/services/prompt_loader.py`

### P1-014 · 리뷰 프롬프트 모듈 이식 · `S` · api
- **의존**: P1-013
- **DoD**: v1 `_WORKOUT_REVIEW_FALLBACK` 이식 + 회복도(낮음/보통/높음) enum 출력 지시. 리뷰 1종만(나머지 프롬프트는 Phase 2).
- **산출물**: `api/app/prompts/review.py`

### P1-015 · context 직렬화(DB→MD) for 리뷰 · `M` · api
- **의존**: P1-007, P1-014
- **DoD**: `render_review_context(log_id)` — 프로필·목표·해당 세션 계획·로그 수치를 v1과 의미 동등한 MD로 조립. 골든 테스트(핵심 필드 포함) 통과.
- **산출물**: `api/app/services/context.py`, `api/tests/test_context.py`

### P1-016 · 값 변환 유틸 + 단위 테스트 · `S` · migration
- **의존**: P1-006
- **DoD**: 변환 함수 — "70~80분"→(70,80) [BUG-15], "😊 괜찮아요 /3/10"→(괜찮아요,3), 🟢/🟡/🔴→enum [BUG-13], ✅/⚠️/❌→status, "42분 13초"→INTERVAL, session_kind 키워드 매핑. 각 케이스 유닛 테스트.
- **산출물**: `scripts/transforms.py`, `api/tests/test_transforms.py`

---

## D. v1 마이그레이션

### P1-017 · 마이그레이션 CLI 골격 + dry-run 트랜잭션 래퍼 · `M` · migration
- **의존**: P1-008, P1-016
- **DoD**: `migrate_v1.py` — `--dry-run`(기본, BEGIN→적재→검증→ROLLBACK)/`--commit`/`--only`/`--workspace`/`--archive`. `--commit` 전 `pg_dump` 스냅샷. v1 파서 import 경로 연결.
- **산출물**: `scripts/migrate_v1.py`(골격)

### P1-018 · 마이그레이션: 프로필/목표/설정 · `M` · migration
- **의존**: P1-017
- **DoD**: `parse_profile_fields`/`parse_goal_fields` 재사용 → users/user_profiles/goals/app_settings. 체형·선호·훈련가능시간→`body_note`. "sub330"→target_time. 빈 필드→null(BUG-05 방지). goal_date↔settings 교차검증.
- **산출물**: `scripts/migrate_v1.py`(profiles/goals)

### P1-019 · 마이그레이션: 주간계획 + 세션 · `M` · migration
- **의존**: P1-017
- **DoD**: 파일명→iso_year/week. `_parse_weekly_rows`→sessions(kind/title/duration 범위/pace/is_rest). '## 훈련 기록' ✅/⚠️/❌→status. 파일 오름차순 처리. UNIQUE(plan,date) 보장.
- **산출물**: `scripts/migrate_v1.py`(weekly/sessions)

### P1-020 · 마이그레이션: 일별 로그 + 리뷰 · `M` · migration
- **의존**: P1-019
- **DoD**: `sync._parse_daily_log` 재사용 → workout_logs. '## 훈련 리뷰'→workout_reviews(recovery enum). 같은 날 sessions와 `session_id` 매칭(없으면 NULL). UNIQUE(user,date).
- **산출물**: `scripts/migrate_v1.py`(daily logs/reviews)

### P1-021 · 마이그레이션: 당일계획(JSONB) + 평가 · `S` · migration
- **의존**: P1-020
- **DoD**: `_parse_daily_plan_cards`→`daily_plans.sections` JSONB. `<!-- ADJUSTED -->`→is_adjusted(BUG-11). `*_evaluation.md`→weekly_evaluations(best-effort, 없으면 스킵).
- **산출물**: `scripts/migrate_v1.py`(daily_plans/eval)

### P1-022 · 마이그레이션: 검증쿼리 V1~V8 + 리포트 · `M` · migration
- **의존**: P1-018, P1-019, P1-020, P1-021
- **DoD**: V1~V8(MIGRATION_PLAN §3) 실행, 하나라도 실패 시 ROLLBACK+종료(코드 3). dry-run 리포트 출력(건수+OK/FAIL). 세션수/거리합이 v1 `count_sessions`/`parse_km`와 일치.
- **산출물**: `scripts/migrate_v1.py`(validate), 리포트 샘플

### P1-023 · 마이그레이션 테스트(dry-run·멱등·검증) · `M` · test
- **의존**: P1-022
- **DoD**: v1 픽스처로 — dry-run 시 행 0(쓰기 없음), `--commit` 2회→행 동일(멱등), V1~V8 통과, 깨진 형식→ROLLBACK. 빈 03/05 .md 케이스 처리.
- **산출물**: `api/tests/test_migration.py`, `api/tests/fixtures/`

---

## E. 읽기 API

### P1-024 · 공용 pydantic 응답 스키마 · `S` · api
- **의존**: P1-007
- **DoD**: Profile/Goal/Today/WeekSummary/WorkoutLog/Review 응답 모델. ISO 날짜/시간 직렬화. enum→문자열.
- **산출물**: `api/app/schemas/*.py`

### P1-025 · GET /api/profile (M1) · `S` · api · feat::M1
- **의존**: P1-024
- **DoD**: 닉네임/키/체중/나이/PB/career/body_note 반환. 빈 필드→null. API 테스트(마이그레이션 데이터로 값 정확).
- **산출물**: `api/app/routers/profile.py`(profile), `api/tests/test_profile.py`

### P1-026 · GET /api/goal + D-day (M2) · `S` · api · feat::M2
- **의존**: P1-024
- **DoD**: race_type/target_time/target_date/description + `dday`(target_date−today). 목표 없으면 dday=null. 음수 dday 처리 규칙. 테스트.
- **산출물**: `routers/profile.py`(goal), `test_goal.py`

### P1-027 · GET /api/settings · `S` · api · feat::M1
- **의존**: P1-024
- **DoD**: weekly_goal_km/단위/알림 반환. 행 없으면 기본값. 테스트.
- **산출물**: `routers/profile.py`(settings)

### P1-028 · state_machine 서비스(S0~S5) + 유닛 · `M` · api · feat::M3
- **의존**: P1-007
- **DoD**: SQL 기반 `detect_state(user,date)` — 우선순위 week_end>no_plan>reviewed>post_workout>rest>pre_workout. **첫 기록 후 S3(S5 아님, BUG-06)** 단위 테스트. `_is_week_end` A/B/C, `_is_rest` 동등.
- **산출물**: `api/app/services/state_machine.py`, `api/tests/test_state_machine.py`

### P1-029 · GET /api/today (M3) · `M` · api · feat::M3
- **의존**: P1-028, P1-024
- **DoD**: state+session+daily_plan(sections)+week_progress 반환. daily_plan 없으면 null. dday 포함. API 테스트 6상태 분기.
- **산출물**: `api/app/routers/today.py`, `api/tests/test_today.py`

### P1-030 · 주간 집계 서비스(수행률·km) + 유닛 · `S` · api · feat::M4
- **의존**: P1-007
- **DoD**: `week_progress(user,iso_week)` — done/total(휴식 제외 분모, BUG-16 단일정의), week_km=SUM(distance_km), goal_km(plan 없으면 settings 폴백, BUG-14). 단위 테스트.
- **산출물**: `api/app/services/aggregate.py`, `api/tests/test_aggregate.py`

### P1-031 · GET /api/weeks/{iso_week} (M4) · `M` · api · feat::M4
- **의존**: P1-030, P1-024
- **DoD**: plan+direction+goal_km+progress+sessions[] 반환. 404 미존재 주. 범위 `~`(6:20~6:40) 보존(BUG-15). 테스트.
- **산출물**: `api/app/routers/weeks.py`, `api/tests/test_weeks.py`

### P1-032 · GET /api/workout-logs (M7, 목록) · `S` · api · feat::M7
- **의존**: P1-024
- **DoD**: `?from&to&limit` 페이지네이션. 각 항목에 review 요약(recovery enum). 날짜 내림차순. 테스트.
- **산출물**: `api/app/routers/workout_logs.py`(list), `api/tests/test_logs_list.py`

### P1-033 · GET /api/stats/weekly · `S` · api · feat::M4
- **의존**: P1-030
- **DoD**: `?weeks=4` 최근 N주 [{iso_week, km, completion_rate}]. 빈 주 0 처리. 테스트.
- **산출물**: `routers/stats.py`, `test_stats.py`

---

## F. 쓰기 API

### P1-034 · 에러 핸들링 + 실패 응답 포맷 · `S` · api
- **의존**: P1-003
- **DoD**: 전역 예외 핸들러 — VALIDATION_ERROR(422)/NOT_FOUND(404)/CONFLICT(409)/AI_UNAVAILABLE(503)/INTERNAL(500) → 공통 `{error:{code,message,details}}`(ARCHITECTURE §3.1). 테스트.
- **산출물**: `api/app/errors.py`, `api/tests/test_errors.py`

### P1-035 · POST /api/workout-logs (M5, upsert+트랜잭션) · `M` · api · feat::M5
- **의존**: P1-007, P1-034
- **DoD**: 트랜잭션 — log upsert(UNIQUE user,date → ON CONFLICT UPDATE, BUG-03) + 매칭 session.status 갱신(pain≥4→부분완료). 파생이력 별도쓰기 없음(뷰, BUG-18). 201/200. 테스트(신규·재요청 행1개·부분완료).
- **산출물**: `routers/workout_logs.py`(create), `test_workout_logs.py`

### P1-036 · Idempotency-Key 처리 · `S` · api
- **의존**: P1-035
- **DoD**: `Idempotency-Key` 헤더 24h 저장. 동일 키+동일 본문→최초 결과 재반환, 동일 키+상이 본문→409. 미전달→자연키 정책. 테스트.
- **산출물**: `api/app/services/idempotency.py`, 테스트

### P1-037 · POST /api/workout-logs/{id}/review (M6, SSE) · `M` · api · feat::M6
- **의존**: P1-015, P1-035
- **DoD**: SSE `token…`→`done{review_id,recovery,...}`. coach 호출→workout_reviews upsert(UNIQUE log_id 덮어쓰기). `Accept: application/json` 폴백. COACH_MOCK 정상저장. 테스트.
- **산출물**: `routers/workout_logs.py`(review), `test_review.py`

### P1-038 · 리뷰 AI 실패 경로(503·로그 보존) 테스트 · `S` · test · feat::M6
- **의존**: P1-037
- **DoD**: `COACH_MOCK=__ERROR__`→503 AI_UNAVAILABLE, **workout_logs 보존·review 미생성**(BUG-04 정신). 재요청 성공 시 review 생성. 회귀 고정.
- **산출물**: `api/tests/test_review_fail.py`

---

## G. PWA 프론트엔드

### P1-039 · PWA 셸: 라우팅 + 하단 4탭 + testid 레지스트리 · `M` · web
- **의존**: P1-004
- **DoD**: `/today`,`/week`,`/history`,`/settings` 라우팅. 고정 하단 탭바(오늘/이번주/기록/설정). 새로고침·딥링크 시 탭 유지(BUG-08 방지). 모든 핵심 요소 `data-testid`(BUG-02), `testids.ts` 단일출처.
- **산출물**: `web/src/App.tsx`, `web/src/components/TabBar.tsx`, `web/src/testids.ts`

### P1-040 · manifest + service worker(설치형·오프라인 셸) · `M` · web
- **의존**: P1-039
- **DoD**: `manifest.webmanifest`(standalone, start_url=/today, theme/bg, 180/192/512 아이콘). SW 셸 precache→오프라인 셸 렌더. iOS apple-touch 메타. "홈 화면 추가" 안내 시트 1회.
- **산출물**: `web/public/manifest.webmanifest`, `web/src/sw.ts`, 아이콘 세트

### P1-041 · API/SSE 클라이언트 + 에러 토스트 · `S` · web
- **의존**: P1-039
- **DoD**: fetch 래퍼(공통 에러포맷 파싱→토스트), SSE 구독 유틸(token/done/에러). 로딩/실패 상태 훅.
- **산출물**: `web/src/lib/api.ts`, `web/src/lib/sse.ts`

### P1-042 · 오늘 화면: 상태머신 렌더 + 당일카드 모달 (M3) · `M` · web · feat::M3
- **의존**: P1-041, P1-029
- **DoD**: `GET /today` state별 렌더(S0~S5). S1 Hero+세션. 당일카드 워밍업/메인/쿨다운→탭 시 모달(상세). dday 칩. testid 부여.
- **산출물**: `web/src/screens/Today.tsx`, `web/src/components/DailyPlanCard.tsx`

### P1-043 · 기록 입력 화면 (M5) · `M` · web · feat::M5
- **의존**: P1-041, P1-035
- **DoD**: 종류(세션 프리필)/거리/시간/페이스/심박/케이던스/피로도 슬라이더/통증/소감/스크린샷. 클라 검증(거리≥0, 심박30~250). 통증≥4 경고. 저장→낙관적 S3 전환.
- **산출물**: `web/src/screens/LogForm.tsx`

### P1-044 · 리뷰 결과 화면: SSE 스트리밍 + 회복 뱃지 (M6) · `M` · web · feat::M6
- **의존**: P1-043, P1-037
- **DoD**: 저장 후 `/review` SSE 구독→coach_comment 실시간 append, done 시 잘한점/개선점/회복뱃지(enum→색) 재배치. **AI 실패 시 "기록 저장됨·재시도" 인라인, 화면 유지**(BUG-04).
- **산출물**: `web/src/screens/ReviewResult.tsx`, `web/src/components/RecoveryBadge.tsx`

### P1-045 · 이번 주 요약 화면 (M4) · `M` · web · feat::M4
- **의존**: P1-041, P1-031
- **DoD**: 진행률 바(km/goal), done/total·수행률, 요일 스트립, 세션 리스트(상태 아이콘). 화면 수치=API와 일치(BUG-16).
- **산출물**: `web/src/screens/Week.tsx`

### P1-046 · 기록 목록 화면 (M7) · `S` · web · feat::M7
- **의존**: P1-041, P1-032
- **DoD**: 최근 로그 카드 리스트(날짜/종류/거리/회복뱃지). 탭 시 상세. 빈 상태 처리.
- **산출물**: `web/src/screens/History.tsx`

### P1-047 · 설정 화면(읽기 전용) (M1) · `S` · web · feat::M1
- **의존**: P1-041, P1-025, P1-026, P1-027
- **DoD**: 프로필/목표(D-day)/설정 표시. 편집 버튼 비활성·숨김(Phase 3 안내). 버전·캐시 비우기.
- **산출물**: `web/src/screens/Settings.tsx`

---

## H. E2E · CI/CD · 인수

### P1-048 · E2E 시드 + Playwright 설정 · `S` · test
- **의존**: P1-010
- **DoD**: `seed_e2e.py`(결정적 최소: user1, W23 plan+2세션, 1로그). Playwright config + `TEST_TODAY` 고정 + COACH_MOCK. testid 셀렉터만 사용.
- **산출물**: `scripts/seed_e2e.py`, `web/playwright.config.ts`

### P1-049 · E2E E1 해피패스 · `M` · test
- **의존**: P1-048, P1-042, P1-043, P1-044, P1-045
- **DoD**: 오늘(S1)→기록입력→저장→S3→리뷰 스트리밍→이번주 수행률 갱신. green.
- **산출물**: `web/e2e/e1_happy.spec.ts`

### P1-050 · E2E E2/E3/E4 회귀 · `M` · test
- **의존**: P1-049
- **DoD**: E2(리뷰 AI실패→재시도·빈화면X, BUG-04) / E3(첫 기록 후 S3 아닌 S5 아님, BUG-06) / E4(탭 딥링크 유지, BUG-08). 3건 green.
- **산출물**: `web/e2e/e2_e3_e4.spec.ts`

### P1-051 · CI: lint+test+e2e job 연결 · `M` · infra
- **의존**: P1-023, P1-038, P1-050
- **DoD**: `.gitlab-ci.yml` lint(ruff/eslint)+test:api(COACH_MOCK=1, postgres svc, 커버리지≥80%)+test:web+e2e. MR에서 자동 실행·차단. BUG-01~06 매핑 테스트 존재 단언.
- **산출물**: `.gitlab-ci.yml`(lint/test/e2e)

### P1-052 · CD: 이미지 build/push + deploy:dev + smoke · `M` · infra
- **의존**: P1-051
- **DoD**: dev 브랜치 머지→api/web 이미지 `:$SHA` push→dev 서버 compose up→`alembic upgrade head`→`/api/health` smoke. 실패 시 비정상종료(이전 컨테이너 유지).
- **산출물**: `.gitlab-ci.yml`(build/deploy), `docker-compose.dev.yml`

### P1-053 · 운영 override + 마이그레이션 순서 문서화 · `S` · infra
- **의존**: P1-052
- **DoD**: `docker-compose.prod.yml`(db 포트 비공개, 리소스 제한, start_period). 배포 절차서(pg_dump→up→alembic→smoke→롤백) README 반영.
- **산출물**: `docker-compose.prod.yml`, README 배포 섹션

### P1-054 · Phase 1 인수: 아이폰 단말 워크스루 · `M` · test
- **의존**: P1-052, P1-040, P1-046, P1-047
- **DoD**: 실 아이폰 — 홈화면 추가→오늘 계획 확인→기록 입력·저장→리뷰 표시→주간 수행률 갱신→재접속 일관성. MVP DoD(MVP_SCOPE §1.2) 전 항목 ✅. 발견 결함 이슈화.
- **산출물**: 인수 체크리스트 결과, 데모 캡처

---

## 요약

| 그룹 | 이슈 | 합계(일) |
|------|------|----------|
| A 스캐폴딩 | 001–004 | 3.0 |
| B DB·모델 | 005–011 | 5.0 |
| C coach·context | 012–016 | 3.5 |
| D 마이그레이션 | 017–023 | 6.5 |
| E 읽기 API | 024–033 | 6.5 |
| F 쓰기 API | 034–038 | 3.5 |
| G PWA | 039–047 | 8.0 |
| H E2E·배포 | 048–054 | 6.0 |
| **총 54 이슈** | | **≈42일(1인)** |

> 병렬화: C(coach)·D(마이그레이션)는 B 완료 후 E/F와 부분 병렬 가능. 2인 작업 시 백엔드(B~F)·프론트(G) 분담으로 ~3주.
> 권장 마일스톤: **MS1**=001–023(기반+마이그레이션 검증), **MS2**=024–038(API green), **MS3**=039–054(PWA+E2E+dev배포+인수).
