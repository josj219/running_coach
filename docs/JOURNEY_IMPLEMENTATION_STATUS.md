# 사용자 여정 구현·배포 진행 상태

기준: `USER_JOURNEY_REVIEW_2026-09-13.md` J01~J10. 기존 기준 커밋: `bc41359`.
기존 미커밋 대시보드·기록 추가·계획 병합 변경을 보존하고 통합한다.
원래 추적 파일 변경 백업: `/private/tmp/coach-before-journey.patch` (커밋 제외).

## 진행 순서

- [x] J01 데이터 충분성 기준·PB 참고 상태, J05 러닝 종목·입력 적합성 검증
- [x] J03 독립 운동 ID·명시적 수정·리뷰 갱신·기존 데이터 마이그레이션
- [x] J02 외부 활동 확인 후 가져오기·중복 방지·동기화 상태
- [x] J06 참여와 계획 이행 분리·승인된 계획 변경 보존
- [x] J04 당시 평가·PB 날짜/수정 이력·목표 버전 보존
- [x] J10 기간 선택·실제 관측값과 당시 평가 비교
- [x] J07 입력 변화 원인·계획 사건·조건부 전망/체크포인트
- [x] J08 근거가 있는 코칭 과제 → 다음 계획 → 수행 재평가
- [x] J09 생성 후 컨디션 변경·변경 전후 확인 및 적용
- [x] Expo API 계약 영향 처리
- [x] 회귀 테스트·프런트 빌드·주요 브라우저 여정 검증 (CI journey-checks 통과, 2026-09-16)
- [x] 운영 백업·복원 리허설·마이그레이션 검증 (deploy run 35103715293, 2026-09-16)
- [x] 커밋·푸시·운영 배포·배포 환경 핵심 동작 검증 (revision 8c52ae7, 2026-09-16)

## 결정

- 현재 기록의 거리 환산값과 목표일까지의 전망을 분리한다. 검증되지 않은 달성 확률/범위는 제공하지 않는다.
- 데이터 충분성은 명시적 제품 기준이며 예측 정확도의 검증을 의미하지 않는다.
- POST는 새 운동, PATCH는 특정 운동 수정. 외부 ID/명시적 요청 ID로 재시도 중복을 막는다.
- 운영은 `.github/workflows/deploy.yml` → self-hosted Linux runner → Docker Compose + PostgreSQL 16 + Cloudflare Tunnel.
- DB·캐시·비밀값은 커밋에서 제외한다. 기존 추적 중인 생성물도 로컬 파일을 보존하며 추적 해제한다.

## 확인 기록

- 2026-09-13: 우선 문서 4개 및 기존 변경/배포 구성 확인. 기존 운영 배포 `34001710564` 성공, 커밋 `bc41359b5ce7eb82296938e5ac3abb3988aee7fe`.
- 구현/테스트/새 운영 배포는 아직 미완료.

## 재개 지점

J01~J10 구현을 로컬 검증했다. 다음 단계는 최신 수정의 전체 테스트/빌드 → 검증 브랜치 푸시 → PostgreSQL 16 CI 및 브라우저 → main 배포 → 운영 확인이다.

## 2026-09-13 구현 중간 기록

- J01~J10 DB/API/PWA 기본 구현을 연결했다. `api/tests/test_journey.py` 11개 수용 시나리오가 1차 통과했다.
- 전체 API 회귀는 102개 중 99개 통과 후, 완료 세션 당일 재생성의 기존 기대값 3개를 새 보존 계약으로 수정 중이다.
- 프런트 Vite 빌드 성공 (`/private/tmp/coach-journey-dist`, 1589 modules). 후속 수정 이후 최종 빌드 재실행 필요.
- 실제 SQLite 이전 제약 → 새 스키마 + 복구 리허설 테스트 및 `app.verify_migration` 추가. 현재 전체 테스트 재실행 중.
- Expo 인증 헤더/로그인, ID 수정, 재시도 요청 ID, 외부 활동 ID, 복수 기록 조회/수정 UI 변경. Native 실기기는 아직 검증하지 않음.
- 로컬 API `127.0.0.1:8013`, PWA `127.0.0.1:5173` 시작. DB는 `/private/tmp/coach-journey-browser.db` (격리 모의 데이터).
- 운영 주소 확인: `https://coach.gogojo.cloud` (`docs/setting_manual.md`). 새 운영 배포는 아직 하지 않음.
- 루트 `pytest`는 구형 Streamlit 전용 테스트이며 현재 API venv에서 streamlit/playwright 의존성 부족으로 수집 실패. 현재 운영 대상인 `api/` 테스트는 별도 실행한다.

## 로컬 검증 통과 및 운영 준비

- 전체 API 테스트 **103개 통과** (SQLite, 1차 완료). 후속 소유권/동기화 실패/PG 동시성 테스트를 추가했으므로 최종 수치는 다음 실행에서 갱신한다.
- 실제 Chrome 주요 사용자 여정 **8개 통과**: PB-only, 당일 제안 확인·적용, 부분 수행·과제 선택, 하루 2운동 추가·ID 수정, 주간 평가, 외부 3건→2운동 중복 처리, 월/당시 평가 조회, 모바일·데스크톱 무오류.
- Expo 인증 헤더·POST/PATCH·revision·외부 ID·JSON 리뷰·전체 JSX 구문 검사 통과.
- 로컬 이전 API가 8013을 사용 중이었다. 이를 보존하고 **18113 API / 15173 PWA**로 검증 완료했다. 8013/5173을 새 구현 검증에 사용하지 않는다.
- 증거: `docs/evidence/journey-implementation-2026-09-13/`. 프런트 빌드 1차 성공, 최신 수정의 최종 빌드/CI 필요.
- 배포 자동화는 테스트 게이트와 백업/복원본 검증/실제 DB 비교/임시 계정 스모크를 포함한다. 실행·복구: `docs/JOURNEY_OPERATIONS.md`.
- 남은 검증: PostgreSQL 16 CI, 최종 빌드/브라우저, 운영 백업·마이그레이션·배포·공개 URL 확인. 실제 Garmin/Strava 로그인·LLM 품질·Expo 실기기는 아직 확인하지 않았다.

## 최종 로컬 회귀 및 CI 진입

- 시간대가 있는/없는 DB 시각을 UTC로 통일해 마지막 반영 시각 비교 오류를 수정했다.
- 전체 API 회귀 106개 통과, PostgreSQL 전용 동시성 1개는 SQLite에서 제외. 이후 추가한 리뷰 생성 중 수정/외부 자전거 오분류 방지 2개를 포함한 J 수용 테스트 16개 통과, PG 전용 1개 제외.
- 최신 PWA 빌드 성공: 1589 modules, JS 311.10 kB (gzip 91.65 kB).
- 운영 스모크 스크립트의 임시 계정 생성→로그인→기록·목표·가져오기→성장→정리 흐름을 로컬에서 실행해 통과했다. 실제 nginx/PostgreSQL 운영 검증은 배포 단계에서 별도 수행한다.
- 기존 DB·캐시·빌드 생성물 67개는 로컬에 보존하고 Git 추적만 해제했다.
- 다음: journey-implementation 브랜치의 CI → 통과 후 main으로 반영 → 백업·복원 리허설·운영 배포.

## 2026-09-16 재개: 커밋·CI 통과

- 9/13 세션은 `git commit`/`git push` 승인 대기에서 종료되어 148개 변경이 스테이징만 된 상태였다. 이를 이어받아 커밋했다.
- 로컬 재검증에서 `test_32`/`test_34`가 실패했다. 고정 "수요일" 타깃이 실제 오늘(수요일)과 겹쳐 앞선 테스트의 기록으로 세션이 `planned`가 아니게 되는 요일 의존 문제였다. 오늘이 아닌 미수행 세션을 고르도록 수정.
- 1차 CI(run 35102416025)는 PostgreSQL 16 단계에서 53 failed/19 errors. 원인은 pytest-asyncio의 테스트별 이벤트 루프와 전역 asyncpg 풀 충돌("attached to a different loop") 및 `test_garmin`의 존재하지 않는 user_id FK 위반. `pytest.ini` loop scope를 session으로 고정하고 테스트가 실제 User 행을 만들도록 수정. 로컬 PostgreSQL 16.2에서 109 passed, SQLite 108 passed/1 skipped.
- 2차 CI(run 35103001605) 전체 통과: SQLite·PostgreSQL 16 회귀, PWA 빌드, Expo 계약, Chrome 여정.
- 커밋: `521eb68`(구현 통합), `d62dc57`(CI 수정). 브랜치 `journey-implementation` 원격 푸시 완료. self-hosted runner 온라인 확인.
- 다음: main 병합 → deploy 워크플로우(checks 재실행 → 백업·복원 리허설·마이그레이션 검증·스모크) → `https://coach.gogojo.cloud/api/health`의 `revision` 확인.

## 2026-09-16 운영 배포 완료

- main fast-forward(`bc41359` → `8c52ae7`) 푸시 → deploy run `35103715293` 성공 (checks 재통과 후 self-hosted runner 실행).
- 복원 리허설·실제 마이그레이션 검증 모두 `passed`, idempotent. 기존 행 보존 확인: users 1, weekly_plans 6, sessions 43, daily_plans 15, workout_logs 9, workout_reviews 9, external_activities 13, integrations 1, goals 1, availability_slots 3.
- 운영 스모크 `passed`: nginx-to-api, login, PB-only, same-day-add, edit, partial, goal-history, cross-provider-import, import-idempotency, growth. 임시 계정·기록 제거 확인.
- 공개 URL: `https://coach.gogojo.cloud/api/health` → `{"status":"ok","revision":"8c52ae7…"}`, 웹 루트 HTTP 200.
- 복구 자료: 서버 `/home/ubuntu/coach-backups/deploy-20260916T134521Z` (coach.dump + sha256, images.txt, 검증 JSON).
- 미검증(사용자 실사용으로 확인 필요): 실제 Garmin/Strava 로그인·동기화, 실제 LLM 응답 품질, Expo 실기기.
