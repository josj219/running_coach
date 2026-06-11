# V2 데이터 마이그레이션 계획

> 연관: [V2_ARCHITECTURE.md](./V2_ARCHITECTURE.md) (스키마) · [V2_MVP_SCOPE.md](./V2_MVP_SCOPE.md)
> 스크립트: `scripts/migrate_v1.py` · 작성일: 2026-06-10

---

## 0. 원칙

1. **v1 파서 재사용**: v1 `webapp/utils/file_manager.py`·`sync.py`·`app.py`의 검증된 파싱 함수를 그대로 호출해 읽는다(재구현 금지 — 파싱 버그 재유입 방지).
2. **읽기 전용 소스**: 원본 `.md`/`.json`은 변경하지 않는다. 종료 후 `archive/v1-markdown/`로 이동(롤백 안전망).
3. **트랜잭션 단위**: 전체를 단일 트랜잭션으로 — 어느 단계든 실패 시 전부 롤백(부분 적재 금지).
4. **dry-run 우선**: 항상 `--dry-run`으로 적재 건수·검증 결과를 먼저 확인하고 `--commit`.
5. **멱등**: 재실행 시 자연키 upsert — 두 번 돌려도 중복 없음.

---

## 1. md/json 파일 → 대상 테이블 매핑

| v1 소스 | 대상 테이블 | 재사용 파서 | 비고 |
|---------|------------|-------------|------|
| `20-knowledge-base/01_PROFILE.md` | `users`, `user_profiles` | `parse_profile_fields()` | 닉네임·키·체중·나이·PB. 체형/선호/훈련가능시간 → `body_note`(원문 보존) |
| `20-knowledge-base/02_GOAL.md` | `goals` | `parse_goal_fields()` | 활성 목표 1개(`is_active=true`). "sub330"→`target_time='3:30:00'` |
| `20-knowledge-base/app_settings.json` | `app_settings`, `users.nickname` | `json.load` | weekly_goal_km·단위·알림. goal_date는 goals와 교차검증 |
| `40-training-log/weekly/*_plan.md` | `weekly_plans` + `sessions` | `_parse_weekly_rows()`, `_count_*` | 파일명 `2026-W23_plan.md`→iso_year/week. '요일별 계획'표→sessions, '## 훈련 기록'✅/⚠️/❌→status |
| `40-training-log/weekly/*_evaluation.md` | `weekly_evaluations` | `_parse_eval_report()` | best-effort. 없으면 SQL 집계로 재산출 가능 |
| `40-training-log/daily/YYYY-MM-DD.md` | `workout_logs` + `workout_reviews` | `sync._parse_daily_log()` | '## 훈련 내용'→log, '## 훈련 리뷰'→review(🔴/🟡/🟢→recovery enum) |
| `40-training-log/daily/YYYY-MM-DD_plan.md` | `daily_plans` | `_parse_daily_plan_cards()` | `[워밍업]/[메인]/[쿨다운]/[메모]/[상세]`→sections JSONB. `<!-- ADJUSTED -->`→is_adjusted |
| `03_RUNNING_HISTORY.md`, `05_INJURY_HISTORY.md` | (마이그레이션 안 함) | — | workout_logs 파생 뷰로 대체. 단, 로그에 없는 과거 기록만 보강 적재 |
| `04_CURRENT_STATUS.md` | (마이그레이션 안 함) | — | 최신 로그+집계로 실시간 산출 |

### 1.1 값 변환 규칙

| v1 표현 | v2 컬럼·값 | 변환 로직 |
|---------|-----------|----------|
| `✅` / `⚠️` / `❌` / `예정`·빈칸 | `session_status` | 완료 / 부분완료 / 미수행 / 예정 |
| `🔴` / `🟡` / `🟢` | `recovery_level` | 높음 / 보통 / 낮음 |
| 휴식/회복/rest/쉬는 행 | `sessions.is_rest=true` | `fm._row_is_rest()` 재사용 |
| `"70~80분"` | `duration_min=70, duration_min_max=80` | `\d+\s*~\s*\d+` 분해(단일값은 둘 다 동일) |
| `"42분 13초"` (PB) | `INTERVAL '00:42:13'` | 분·초 파싱 |
| `"5.2"` (거리) | `distance_km=5.2` | `fm.parse_km()` |
| `"6:12"` (페이스) | `avg_pace='6:12'` (TEXT) | 그대로 |
| `"😊 괜찮아요 / 3/10"` | `fatigue_label='괜찮아요', fatigue_num=3` | `split('/')` + `\d+/10` |
| `"통increase 없음"` / `"통증 — 왼쪽 무릎 / 3/10"` | `pain_part`, `pain_level` | `sync._parse_daily_log` 정규식 |
| 세션 kind 키워드 | `session_kind` enum | 키워드→enum 매핑표(아래) |

### 1.2 session_kind 매핑

```
인터벌/스피드/파틀렉 → 인터벌      롱런/장거리 → 롱런
템포/임계          → 템포         페이스런 → 페이스런
회복 조깅          → 회복조깅      쉬운 달리기/이지/기초 → 쉬운달리기
근력/보강          → 근력         헬스 → 헬스
드릴/폼/교정 드릴   → 드릴         코어 → 코어
가동성/스트레칭     → 가동성       휴식/rest → 휴식
(매칭 실패)        → 기타
```

---

## 2. Import 순서 (FK 의존성)

```
1. users               (email='josj219@gmail.com', nickname)
2. user_profiles       (FK→users)
3. app_settings        (FK→users)
4. goals               (FK→users, is_active=true 1개)
5. weekly_plans        (FK→users)         ← 파일명 정렬 오름차순(과거→현재)
6. sessions            (FK→weekly_plans)  ← 각 plan의 '요일별 계획'행
7. daily_plans         (FK→sessions via session_id, nullable)
8. workout_logs        (FK→sessions via session_id, nullable)
9. workout_reviews     (FK→workout_logs)
10. weekly_evaluations (FK→weekly_plans)
11. (보강) 03/05 .md 중 로그에 없는 과거 행 → workout_logs backfill
```

- **session_id 연결**: workout_logs/daily_plans는 `(user_id, date)`로 같은 날 `sessions.session_date` 매칭해 `session_id` 채움. 매칭 없으면 NULL(즉흥 운동 허용).
- 5~6단계는 파일명 **오름차순**(2026-W22 → W23 → W24)으로 처리해 `weekly_plans.id` 시간순 정렬.

---

## 3. 검증 쿼리 (마이그레이션 후 자동 실행)

스크립트가 적재 후 아래를 실행, **하나라도 불일치면 트랜잭션 롤백**.

```sql
-- V1: 프로필 핵심 필드 존재
SELECT count(*)=1 FROM user_profiles WHERE user_id=1 AND height_cm IS NOT NULL;

-- V2: 활성 목표 정확히 1개 + 목표일 일치
SELECT count(*)=1 FROM goals WHERE user_id=1 AND is_active
  AND target_date = DATE '2026-11-01';

-- V3: 주간 계획 수 = *_plan.md 파일 수
SELECT count(*) FROM weekly_plans;          -- expect: glob('weekly/*_plan.md') 개수

-- V4: 세션 수 정합 (v1 count_sessions와 대조) — 주별
SELECT wp.iso_week,
       count(*) FILTER (WHERE NOT s.is_rest)              AS total_sessions,
       count(*) FILTER (WHERE s.status IN ('완료','부분완료')) AS done_sessions
FROM weekly_plans wp JOIN sessions s ON s.plan_id=wp.id
GROUP BY wp.iso_week;
-- expect: 각 주 (done,total)이 v1 fm.count_sessions(plan_md)와 동일

-- V5: 일별 로그 수 = daily/YYYY-MM-DD.md 파일 수(‗_plan.md 제외)
SELECT count(*) FROM workout_logs;          -- expect: glob('daily/[0-9]*.md') 개수

-- V6: 거리 합 정합 (주별 km)
SELECT date_trunc('week', log_date) AS wk, sum(distance_km)
FROM workout_logs GROUP BY 1;
-- expect: v1 get_week_daily_logs + parse_km 합과 일치

-- V7: 리뷰 있는 로그는 recovery enum 채워짐(또는 명시적 NULL 허용)
SELECT count(*) FROM workout_reviews WHERE recovery IS NULL AND raw_md LIKE '%🟢%';
-- expect: 0  (🟢 있는데 enum 누락이면 파싱 실패 → 조사)

-- V8: 고아 FK 없음
SELECT count(*) FROM sessions s LEFT JOIN weekly_plans p ON s.plan_id=p.id WHERE p.id IS NULL;
-- expect: 0
```

검증 리포트 출력 예:
```
[migrate_v1] DRY-RUN
  users:1  profiles:1  settings:1  goals:1
  weekly_plans:3  sessions:17 (rest:4)  daily_plans:4
  workout_logs:2  reviews:1  evaluations:1
  V1 profile........ OK
  V2 active goal.... OK (target_date=2026-11-01)
  V3 plan count..... OK (3 == 3 files)
  V4 session parity. OK (W22 1/3, W23 1/2, W24 0/5)
  V5 log count...... OK (2 == 2 files)
  V6 km parity...... OK (W23 6.2km)
  V7 recovery enum.. OK (0 mismatch)
  V8 orphan FK...... OK (0)
  → DRY-RUN, no rows written. Re-run with --commit.
```

---

## 4. dry-run 모드 & CLI

```bash
# 1) 미리보기 (쓰기 없음, 검증만)
python scripts/migrate_v1.py --workspace . --database-url $DATABASE_URL --dry-run

# 2) 실제 적재 (단일 트랜잭션, 검증 통과 시에만 commit)
python scripts/migrate_v1.py --workspace . --database-url $DATABASE_URL --commit

# 3) 특정 범위만 (디버깅)
python scripts/migrate_v1.py --only profiles,goals --dry-run
```

| 플래그 | 동작 |
|--------|------|
| `--dry-run` (기본) | 트랜잭션 BEGIN → 적재 → 검증 출력 → **ROLLBACK**. 쓰기 없음 |
| `--commit` | 트랜잭션 BEGIN → 적재 → 검증 → 통과 시 COMMIT, 실패 시 ROLLBACK+비정상종료 |
| `--only <tables>` | 지정 단계만 |
| `--workspace <path>` | v1 워크스페이스 루트(기본 `.`) |
| `--archive` | commit 성공 후 `.md`를 `archive/v1-markdown/`로 이동 |

### 4.1 dry-run 내부 동작

dry-run도 **실제 INSERT를 트랜잭션 안에서 수행**해 FK·UNIQUE·검증 쿼리를 진짜로 돌린 뒤 ROLLBACK한다. "파싱만"이 아니라 "적재 가능성"까지 확인 → commit 시 놀람 없음.

---

## 5. 실패 시 롤백 방식

| 실패 지점 | 동작 |
|-----------|------|
| 파싱 오류(예상 못한 형식) | 해당 파일 경로·라인 로그 → 트랜잭션 ROLLBACK → 비정상 종료(코드 2). 부분 적재 없음 |
| FK/UNIQUE 위반 | DB가 예외 → ROLLBACK → 로그 |
| 검증 쿼리 불일치(V1~V8) | 어떤 검증이 깨졌는지 출력 → ROLLBACK → 종료(코드 3) |
| `--commit` 중 DB 끊김 | 트랜잭션 미완 → DB가 자동 ROLLBACK. 재실행(멱등) |
| commit 후 데이터 이상 발견 | ① `archive/`의 원본 `.md` 복원 ② `TRUNCATE ... CASCADE` 또는 `pg_dump` 스냅샷 복원 ③ 파서 수정 후 재실행 |

- **안전망**: `--commit`은 실행 전 `pg_dump`로 빈/기존 상태 스냅샷을 `backups/pre_migrate_<ts>.sql`에 남긴다.
- **재실행 안전**: 자연키 upsert라 `--commit` 재실행해도 행 증가 없음(검증 V3/V5 동일).

---

## 6. 컷오버 절차 (Phase 4)

```
1. v1 운영 동결(읽기 전용 안내) 또는 마지막 기록까지 입력 완료
2. pg_dump 백업
3. migrate_v1.py --commit --archive  (검증 통과 → 적재 + .md 아카이브)
4. v2 dev/prod에서 GET /api/today, /weeks/* 시각 대조(v1 화면 vs v2)
5. 1~2일 병렬 운영(v2에 신규 기록, v1은 참조용)
6. 이상 없으면 v1 Streamlit/Railway 디코미션
7. archive/v1-markdown/ 는 영구 보관(롤백 최후 수단)
```
