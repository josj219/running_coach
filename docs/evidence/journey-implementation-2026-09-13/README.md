# 구현 검증 증거

로컬 COACH_MOCK=1, 임시 SQLite, 별도 합성 계정으로 수행한 Playwright Chrome 결과입니다. 사용자 실측 기록·운영 계정·인증 토큰은 포함하지 않습니다.

`results.json`은 주요 여정 8개의 자동 검증 결과입니다. PNG는 모바일/데스크톱 화면 증거입니다. 페이지 내부 스크롤 때문에 일부 화면은 현재 보이는 구간을 담습니다.

API 수용 테스트는 `api/tests/test_journey.py`, 마이그레이션/복구는 `api/tests/test_migration.py`, Expo HTTP/JSX 계약은 `web/e2e/mobile-contract.mjs`입니다. 운영 배포와 PostgreSQL 검증은 별도 GitHub Actions 결과를 [진행 기록](../../JOURNEY_IMPLEMENTATION_STATUS.md)에 남깁니다. 이 디렉터리의 로컬 결과만으로 운영 성공이나 실제 LLM/외부 동기화 품질을 주장하지 않습니다.
