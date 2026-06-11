# V2 MVP 범위 & 개발 작업 분해

> 연관 문서: [V2_ARCHITECTURE.md](./V2_ARCHITECTURE.md) · [V2_MIGRATION_PLAN.md](./V2_MIGRATION_PLAN.md) · [V2_TEST_STRATEGY.md](./V2_TEST_STRATEGY.md)
> 작성일: 2026-06-10 · 대상: 고고조 AI 러닝 코치 v2

---

## 1. MVP 범위 재정의

### 1.1 핵심 전략: "읽기 위주 + 쓰기 2개" 수직 슬라이스

v1 F01~F12를 한 번에 옮기지 않는다. **Phase 1은 가장 위험한 부분(AI 생성·SSE·파서)을 빼고**, 마이그레이션된 데이터를 읽고 핵심 쓰기 2개만 구현해 전체 스택(DB→API→PWA)을 관통시킨다.

> 핵심 결정: **Phase 1의 주간/당일 계획은 "생성"하지 않는다. v1에서 마이그레이션한 계획을 읽기만 한다.** 따라서 Phase 1의 유일한 AI 호출은 "운동 리뷰 생성" 1개다. 이로써 AI 스트리밍·JSON 파서·프롬프트 5종을 Phase 2로 미루고, Phase 1에서 DB·API·PWA·CI/CD·마이그레이션 기반을 먼저 안정화한다.

### 1.2 Phase 1 IN — MVP에 포함

| # | 기능 | 종류 | v1 매핑 | AI 호출 |
|---|------|------|---------|---------|
| M1 | 프로필 조회 | READ | F11 | — |
| M2 | 목표 조회 (D-day 포함) | READ | F11 | — |
| M3 | 오늘 계획 조회 (당일 카드 + 오늘 세션) | READ | F01·F03 | — |
| M4 | 이번 주 요약 조회 (세션 리스트 + 진행률) | READ | F06 | — |
| M5 | 운동 기록 저장 | WRITE | F04·F05 | — |
| M6 | AI 리뷰 생성·저장 | WRITE | F04 | ✅ (유일) |
| M7 | 기록 목록 조회 | READ | F10 | — |

**Phase 1 완료 기준 (Definition of Done)**: 아이폰 PWA에서 — ① 홈 화면 추가 → ② 오늘 탭에서 마이그레이션된 오늘 계획 확인 → ③ 운동 기록 입력·저장 → ④ AI 리뷰 표시·저장 → ⑤ 이번 주 탭에서 수행률 갱신 확인. 이 플로우가 새로고침/재접속 후에도 일관되게 동작.

### 1.3 Phase 1 OUT — 명시적 제외 (→ Phase 2+)

| 제외 기능 | v1 | 이유 / 이관 |
|-----------|----|----|
| 주간 계획 **AI 생성** | F07 | 마이그레이션 데이터로 대체. Phase 2 |
| 당일 계획 **AI 생성** | F02 | 마이그레이션 데이터로 대체. Phase 2 |
| 계획 조정 (당일/주간) | F09 | Phase 2 (adjust 엔드포인트 + SSE) |
| 주간 성장 리포트 | F08 | 카드 숫자(SQL)는 가능하나 AI 서술은 Phase 2 |
| 설정 **변경**(PATCH) | F11 | Phase 1은 조회만. 편집은 Phase 3 |
| 설정 변경 → 계획 갱신 | F12 | Phase 3 (F11 PATCH 의존) |
| 멀티유저 인증 | — | v2.0 전체에서 제외. `user_id=1` 고정 |
| Garmin/Strava·날씨 자동연동 | Future | v2.1+ |
| 푸시 알림 | — | Phase 3 (PWA 마감 시) |

> Phase 1의 AI 호출은 M6(리뷰) 단 1개. 따라서 SSE 스트리밍은 Phase 1에서 "리뷰 생성"에만 적용하고, 나머지 AI 생성 엔드포인트는 Phase 2에서 같은 SSE 패턴을 재사용한다.

### 1.4 전체 로드맵 (Phase 0~4)

```
Phase 0  기반 구축        (모노레포·DB·CI 골격·coach 서비스)          ~1주
Phase 1  MVP 수직 슬라이스 (마이그레이션 + 읽기 + 기록/리뷰 쓰기)      ~2주   ← 본 MVP
Phase 2  AI 생성 경로      (주간/당일 계획 생성·조정·리포트 + SSE)     ~2주
Phase 3  설정·PWA 마감     (PATCH·F12·푸시·오프라인)                  ~1주
Phase 4  검증·컷오버       (F01~F12 회귀·병렬운영·v1 디코미션)         ~1주
```

---

## 2. 개발 작업 분해 (GitLab Issue 단위)

> 라벨 규칙: `phase::N`, `area::{api,web,db,infra,migration,test}`, `feat::{M1..M7}`
> 각 이슈는 **완료 조건(DoD)** 과 **산출물**을 가진다. 브랜치: `feat/<issue-id>-<slug>` → MR → `dev`.

### Phase 0 — 기반 구축

#### P0-1 모노레포 스캐폴딩 · Compose 골격
- **작업**: `api/`, `web/`, `scripts/`, `docker-compose.yml`, `.env.example` 생성. db+api 컨테이너 기동.
- **DoD**: `docker compose up` → `GET /api/health` 200 응답. db healthcheck 통과.
- **산출물**: 디렉토리 구조, `docker-compose.yml`, `api/app/main.py`(health만).

#### P0-2 DB 모델 · Alembic 초기 마이그레이션
- **작업**: SQLAlchemy 2.0 ORM 모델 + enum + Alembic `0001_init`. (스키마는 ARCHITECTURE §2)
- **DoD**: `alembic upgrade head` 성공, 전 테이블·enum·인덱스 생성. `alembic downgrade base` 도 성공.
- **산출물**: `api/app/db/models.py`, `api/alembic/versions/0001_init.py`.

#### P0-3 coach 서비스 (async) + COACH_MOCK
- **작업**: v1 `claude_client`/`page_common.run_coach` async 이식. `CLAUDE.md` 시스템 프롬프트 로드. `COACH_MOCK` 분기.
- **DoD**: 유닛 테스트 — `COACH_MOCK=1` 시 모의 응답, `__ERROR__` 시 에러 경로. 실 API 미호출.
- **산출물**: `api/app/services/coach.py`, `api/app/prompts/`(리뷰 프롬프트만 우선).

#### P0-4 context 직렬화 (DB → Markdown)
- **작업**: DB 조회 → v1과 **동일한 Markdown** 컨텍스트 생성(`render_review_context()`).
- **DoD**: 골든 테스트 — 마이그레이션된 데이터로 만든 MD가 v1 파일 컨텍스트와 의미 동등(핵심 필드 일치).
- **산출물**: `api/app/services/context.py`.

#### P0-5 GitLab CI 골격
- **작업**: `.gitlab-ci.yml` — lint/test/build stage. postgres service. `COACH_MOCK=1`.
- **DoD**: MR 시 lint+test 자동 실행. (CI/CD 상세는 ARCHITECTURE §7)
- **산출물**: `.gitlab-ci.yml`.

### Phase 1 — MVP 수직 슬라이스

#### P1-1 v1 마이그레이션 스크립트 (dry-run)
- **작업**: `scripts/migrate_v1.py` — md/json → 테이블. dry-run 모드. (상세 MIGRATION_PLAN)
- **DoD**: `--dry-run` 시 쓰기 없이 적재 건수·검증 리포트 출력. `--commit` 시 트랜잭션 적재 후 검증 쿼리 통과.
- **산출물**: `scripts/migrate_v1.py`, 검증 리포트 샘플.

#### P1-2 읽기 API: 프로필·목표·설정 (M1·M2)
- **작업**: `GET /api/profile`, `GET /api/goal`, `GET /api/settings`. D-day 계산.
- **DoD**: API 테스트 — 마이그레이션 데이터로 닉네임/PB/목표일/D-day 정확. 목표 없으면 `dday=null`.
- **산출물**: `routers/profile.py`, 응답 스키마, 테스트.

#### P1-3 읽기 API: 오늘 (M3)
- **작업**: `GET /api/today` — state(S0~S5) SQL 판정 + 오늘 세션 + 당일 카드.
- **DoD**: API 테스트 — 6개 상태 분기(BUG-06 회귀 포함: 첫 기록 후 S5 오판정 안 됨).
- **산출물**: `routers/today.py`, `services/state_machine.py`, 테스트.

#### P1-4 읽기 API: 이번 주 요약 (M4·M7)
- **작업**: `GET /api/weeks/{iso_week}`, `GET /api/workout-logs`, `GET /api/stats/weekly`.
- **DoD**: 수행률 = `done/total`(휴식 제외 분모, BUG-16 단일정의). km 합 = SUM. 화면 간 수치 일치.
- **산출물**: `routers/weekly_plans.py`(read), `routers/stats.py`, 테스트.

#### P1-5 쓰기 API: 운동 기록 저장 (M5)
- **작업**: `POST /api/workout-logs` — 트랜잭션: log insert + session.status update. idempotency.
- **DoD**: 같은 `(user, date)` 재요청 시 중복 행 없음(upsert). pain_level≥4 → session.status='부분완료'. running/injury는 뷰라 별도 쓰기 없음(BUG-18 불가능 검증).
- **산출물**: `routers/workout_logs.py`(create), 테스트(중복 정책 포함).

#### P1-6 쓰기 API: AI 리뷰 생성·저장 (M6)
- **작업**: `POST /api/workout-logs/{id}/review` (SSE) — coach 호출 → `workout_reviews` insert. 회복=enum.
- **DoD**: `COACH_MOCK` 시 모의 리뷰 저장. **AI 실패 시 로그는 보존되고 리뷰만 미생성**(에러 응답, 빈 화면 X — BUG-04 정신). 재요청 시 기존 리뷰 덮어쓰기(UNIQUE log_id).
- **산출물**: `routers/workout_logs.py`(review), 테스트(성공/실패/재생성).

#### P1-7 PWA 셸 + 4탭 + MVP 화면
- **작업**: Vite+React PWA. 하단 4탭. 오늘/이번주/기록/설정 화면. manifest + 기본 service worker.
- **DoD**: 아이폰 Safari "홈 화면 추가" 가능. M1~M7 플로우 동작. 오프라인 시 셸 로드(데이터는 캐시 표시).
- **산출물**: `web/` 전체, `manifest.webmanifest`, `sw.js`.

#### P1-8 PWA E2E (Playwright)
- **작업**: M3→M5→M6→M4 해피패스 E2E. `COACH_MOCK`.
- **DoD**: 기록 입력→리뷰→주간 수행률 갱신 E2E 통과. (TEST_STRATEGY §5)
- **산출물**: `web/e2e/mvp_flow.spec.ts`.

#### P1-9 배포 파이프라인 (dev 환경)
- **작업**: CI build+push 이미지, dev 서버 배포 job, alembic 자동 upgrade.
- **DoD**: `dev` 브랜치 머지 → dev 환경 자동 배포 → smoke test(health+today) 통과.
- **산출물**: `.gitlab-ci.yml` deploy:dev, `docker-compose.prod.yml`.

### Phase 2 — AI 생성 경로 (요약)
- P2-1 `POST /api/weekly-plans`(F07) + JSON 파서 → sessions
- P2-2 `POST /api/daily-plans`(F02·F03) SSE
- P2-3 `POST .../adjust`(F09) 잔여 세션 update
- P2-4 `POST /api/weeks/{week}/evaluation`(F08) 카드=SQL·서술=AI

### Phase 3 — 설정·PWA 마감 (요약)
- P3-1 `PATCH /api/profile|goal|settings`(F11)
- P3-2 `plan_refresh_suggested`(F12)
- P3-3 푸시 알림 + 오프라인 쓰기 큐 + 프로필 이미지 업로드

### Phase 4 — 검증·컷오버 (요약)
- P4-1 F01~F12 + BUG-01~19 회귀 통합 테스트 이식
- P4-2 v1 병렬 운영 → 재마이그레이션 → 컷오버
- P4-3 v1 Streamlit/Railway 디코미션, `.md` 아카이브

---

## 3. MVP 비기능 요구사항

| 항목 | 기준 |
|------|------|
| 응답시간 | 읽기 API p95 < 300ms (단일 사용자, 로컬 DB) |
| AI 리뷰 | 스트리밍 첫 토큰 < 3s, COACH_MOCK 시 < 100ms |
| 가용성 | 단일 사용자 — 무중단 불필요. 배포 시 짧은 다운타임 허용 |
| 데이터 정합성 | 마이그레이션 후 v1 대비 손실 0 (검증 쿼리 통과) |
| 보안 | API 키 서버 전용. v2.0 인증 없음(사설망/단일 사용자 전제) |
