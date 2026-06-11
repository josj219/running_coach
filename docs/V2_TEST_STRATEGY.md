# V2 테스트 전략

> 연관: [V2_ARCHITECTURE.md](./V2_ARCHITECTURE.md) · [V2_MVP_SCOPE.md](./V2_MVP_SCOPE.md)
> 작성일: 2026-06-10

---

## 1. 테스트 피라미드

```
        ╱ E2E (Playwright, PWA) ╲          소수 · 해피패스 + 핵심 회귀     (~5)
      ╱─── API 통합 (httpx+DB) ───╲        엔드포인트 계약·트랜잭션·실패   (~30)
    ╱──────── 유닛 (pytest/vitest) ──────╲  파서·집계·상태머신·변환        (~60)
```

| 층 | 도구 | 대상 | DB | AI |
|----|------|------|----|----|
| Unit (api) | pytest | services(state_machine, context, plan_parser), 변환 함수 | 없음(순수) 또는 in-memory | 미호출 |
| Unit (web) | vitest | 컴포넌트 로직, enum→뱃지 매핑, 폼 검증 | — | — |
| API 통합 | pytest + httpx + 테스트 PostgreSQL | 라우터 계약·트랜잭션·멱등·실패응답 | 실 PG(테스트 DB, 트랜잭션 롤백 fixture) | `COACH_MOCK=1` |
| E2E | Playwright | PWA 사용자 플로우 | 실 PG(시드) + 실 api | `COACH_MOCK=1` |
| Migration | pytest | 검증쿼리 V1~V8, dry-run, 멱등 | 실 PG | — |

- **API 통합 fixture**: 각 테스트를 SAVEPOINT로 감싸 종료 시 롤백 → 테스트 간 격리·고속.
- **모든 CI에서 `COACH_MOCK=1`** → 실 Claude 비용 0(v1에서 검증된 방식 계승).

---

## 2. v1 버그(BUG-01~06)를 막는 테스트 매핑

v1은 동일 클래스 버그가 반복됐다(파싱·forward reference·상태 오판정). v2는 **구조로 제거 + 회귀 테스트로 고정**한다.

| v1 BUG | 원인 | v2 구조적 제거 | 회귀 테스트 (반드시 존재) |
|--------|------|----------------|---------------------------|
| **BUG-01** `_daily_section_dialog` NameError (forward reference, F03) | 단일 거대 모듈의 정의/호출 순서 | 모듈 분리 + import 시점 정적 검증 | `test_imports.py`: 모든 라우터/서비스 import 성공. `ruff`(F821 미정의 참조) CI lint |
| **BUG-02** CSS `:has()` Playwright count=0 (F10 테스트) | DOM 구조 의존 셀렉터 | 테스트는 `data-testid` 로만 선택(셀렉터 계약 고정) | `test_e2e_selectors`: 핵심 요소에 `data-testid` 존재 단언. 컴포넌트에 testid 누락 시 vitest 실패 |
| **BUG-03** `_update_weekly_plan_record` UPSERT 누락 (날짜행 없으면 미삽입, F05) | 수동 표 행 조작 | DB UNIQUE + `ON CONFLICT DO UPDATE`(자연키 upsert) | `test_workout_log_upsert`: 신규 날짜 insert + 동일 날짜 재요청 시 행 1개 유지·값 갱신 |
| **BUG-04** 프롬프트/파서 포맷 불일치 → 빈 카드 (F02/F03) | AI 출력 텍스트를 regex 파싱 | AI **JSON 출력** + pydantic 검증 + 실패 시 재요청 | `test_plan_parser`: 정상 JSON→sections 채워짐, 깨진 JSON→재요청/에러(빈 카드 금지). `test_review_ai_fail`: 503이어도 **로그 보존**·화면 유지 |
| **BUG-05** `parse_profile_fields` `\s`가 개행 흡수 (빈 필드→다음 줄 캡처, F11) | Markdown regex 파싱 | 정형 컬럼 직접 저장(파싱 없음) | `test_profile_read`: 빈 필드 → `null`(다음 섹션 흡수 안 함). 마이그레이션 단위로 v1 빈필드 케이스 커버 |
| **BUG-06** `count_sessions` total을 빈 기록표로 산출 → 첫 기록 후 S5 오판정 (F01/F04/F05) | total/done을 같은 표에서 파싱 | total=`sessions WHERE NOT is_rest`(계획), done=완료 status. **분모/분자 소스 분리** | `test_state_machine_s5`: 첫 기록 저장 후 `state==REVIEWED`(S3), **S5 아님**. `test_completion_rate`: 휴식 제외 분모, 단일 정의 |

> 추가 회귀(BUG-07~19)도 Phase 4에서 같은 표 형식으로 이식. 특히 BUG-13(회복 이모지 오판→enum), BUG-15(범위 `~` 분해→2컬럼), BUG-16(수행률 단일정의), BUG-18(완료기록 소실→뷰), BUG-19(캐시 stale→당일 1행 UNIQUE)는 **스키마로 이미 제거**되므로 "구조 단언" 테스트로 고정.

### 2.1 회귀 방지의 핵심 원칙

1. **파싱을 테스트하지 말고, 파싱을 없앤다.** v1 버그 다수가 regex였다 → v2는 정형 컬럼/JSONB/enum. 테스트는 "파서 정확성"이 아니라 "구조 제약(UNIQUE/FK/enum)"을 검증.
2. **AI 출력은 계약(JSON 스키마)으로 받는다.** 자유 텍스트 파싱 금지 → BUG-04류 원천 차단.
3. **사용자 데이터와 AI 산출을 분리 커밋.** 리뷰 실패가 기록을 날리지 않음(BUG-04 정신의 일반화).

---

## 3. COACH_MOCK 유지 방식

v1 `page_common.run_coach`의 `COACH_MOCK` 시드를 v2 `services/coach.py`로 계승.

```python
# services/coach.py
async def stream(system: str, user: str, *, image=None):
    mock = os.environ.get("COACH_MOCK")
    if mock is not None:
        if mock == "__ERROR__":
            raise AIUnavailable("테스트 모의 오류")     # → 503 경로
        for tok in _chunk(mock):                       # 모의 토큰 스트림
            yield tok
        return
    async for tok in _anthropic_stream(system, user, image):
        yield tok
```

- **CI/E2E/Migration**: `COACH_MOCK=1`(또는 시나리오별 모의 텍스트) → 실 API 미호출, 결정적·무비용.
- **에러 경로**: `COACH_MOCK=__ERROR__` → `AI_UNAVAILABLE` 503. 리뷰 실패 시 로그 보존·재시도 UI를 테스트.
- **운영/로컬 실호출**: 변수 비움. 프로덕션 무영향(v1과 동일 계약).
- **시나리오 모의**: 특정 테스트는 `COACH_MOCK` 에 고정 JSON/MD를 주입해 파서·렌더 결정적 검증.

---

## 4. 대표 테스트 케이스 (Phase 1 = M1~M7)

### 4.1 API 통합 (pytest + httpx)

```
test_profile.py
  GET /profile → 닉네임/PB/D-day 정확, 빈 필드 null (BUG-05 방지)
test_today.py
  S0~S5 6분기. 첫 기록 후 S3(S5 아님, BUG-06)
test_weeks.py
  수행률 done/total 휴식 제외(BUG-16), week_km=SUM, 404 미존재 주
test_workout_logs.py
  POST 201 + session.status 갱신 / 동일날짜 재POST→200 upsert 행1개(BUG-03)
  pain_level>=4 → session '부분완료'
  Idempotency-Key 재사용+본문상이 → 409
test_review.py
  COACH_MOCK 정상→review 저장, recovery enum
  COACH_MOCK=__ERROR__ → 503, 로그 보존, review 미생성 (BUG-04)
  재요청 → 기존 review update (UNIQUE log_id)
test_migration.py
  dry-run 쓰기없음, 검증 V1~V8, --commit 멱등(2회→행 동일)
```

### 4.2 유닛

```
test_state_machine.py   detect_state 우선순위(week_end > no_plan > reviewed > ...)
test_context.py         DB→MD 직렬화 골든(v1 컨텍스트 의미 동등)
test_plan_parser.py     AI JSON→sessions/sections, 깨진 JSON 처리 (BUG-04)
test_transforms.py      "70~80분"→(70,80) BUG-15, "😊 .. /3/10"→(괜찮아요,3),
                        🟢/🟡/🔴→enum BUG-13, ✅/⚠️/❌→status
web: settings.test.ts   enum→뱃지색 매핑, 폼검증(거리≥0·심박범위)
```

---

## 5. Playwright PWA E2E 범위

> 소수 정예. 해피패스 + 핵심 회귀만. `COACH_MOCK=1`, 시드 DB(`scripts/seed_e2e.py`).

| ID | 시나리오 | 검증 | 막는 버그 |
|----|----------|------|-----------|
| E1 | MVP 핵심 플로우 | 오늘(S1)→기록입력(M5)→저장→S3→리뷰 스트리밍 표시→이번주 수행률 갱신 | 통합 회귀 |
| E2 | 리뷰 AI 실패 | `COACH_MOCK=__ERROR__` → "기록 저장됨·리뷰 재시도" 표시, **빈 화면 아님** | BUG-04 |
| E3 | 상태머신 첫 기록 | 첫 기록 후 화면이 S3(리뷰)지 S5(주간종료) 아님 | BUG-06 |
| E4 | 탭 네비/딥링크 | 4탭 이동, 새로고침 후 같은 탭 유지(URL 라우팅) | BUG-08(v1 탭전환 실패) |
| E5 | PWA 설치성 | manifest 로드, SW 등록, 오프라인 시 셸 렌더 | PWA 요건 |

- **셀렉터 계약**: 모든 E2E는 `data-testid` 사용(BUG-02 — DOM 구조 의존 `:has()` 금지). testid 목록은 `web/src/testids.ts` 단일 출처.
- **결정성**: AI 모의·시드 DB·고정 `TEST_TODAY`(서버 env)로 시간 의존 제거.
- **아티팩트**: 실패 시 trace+screenshot 업로드(CI `artifacts`).

---

## 6. 커버리지 / 게이트

| 게이트 | 기준 |
|--------|------|
| CI lint | `ruff`(F821 등 미정의 참조 차단 — BUG-01류), web `eslint` |
| api 커버리지 | services·routers 라인 ≥ 80% (MR 차단) |
| 회귀 필수 | BUG-01~06 매핑 테스트는 **삭제/skip 금지**(CI에서 존재 단언) |
| E2E | dev 배포 전 E1~E3 green 필수 |
| migration | `--dry-run` 검증 V1~V8 전부 OK 아니면 배포 불가 |

---

## 7. 테스트 데이터

- **시드 스크립트** `scripts/seed_e2e.py`: 결정적 최소 데이터(1 user, W23 plan+2 sessions, 1 log). E2E·로컬 공용.
- **픽스처 재사용**: v1 `tests/fixtures/daily_log_fixture.md` 등을 마이그레이션 입력 픽스처로 전환 → "v1 실제 포맷"을 회귀로 고정.
- **금지**: 테스트가 운영 DB/실 API 키를 건드리지 않음(env 격리, `COACH_MOCK` 강제).
