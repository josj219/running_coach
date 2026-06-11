# 러닝 코치 v2 — FastAPI + PostgreSQL + React PWA + Expo

고고조 전용 AI 러닝 코치. v1(Streamlit 로컬)을 아이폰에서 쓰는 실제 앱 형태로 재구축한 버전.

```
┌─────────────┐  ┌──────────────┐   HTTP/SSE   ┌──────────────────┐  asyncpg  ┌────────────┐
│  PWA (web)  │  │ Expo(mobile) │ ───────────► │  FastAPI (api)   │ ────────► │ PostgreSQL │
│ React+Vite  │  │ React Native │ ◄─────────── │  AI 코치 서비스    │           │  (db)      │
└─────────────┘  └──────────────┘              └────────┬─────────┘           └────────────┘
                                                        ├── Anthropic API (Claude)
                                                        └── Strava API (OAuth2, Garmin 경유 포함)
```

## 디렉토리

| 경로 | 내용 |
|------|------|
| `api/` | FastAPI 백엔드 — 코치 AI(SSE 스트리밍), 주간/당일 계획, 기록/리뷰, Strava OAuth |
| `web/` | React PWA — 아이폰 홈 화면 추가 지원, 다크 기본, iOS 26 디자인 토큰 |
| `mobile/` | Expo(React Native) 앱 — 동일 API, 동일 디자인 언어 |
| `docker-compose.yml` | db + api + web 풀스택 구동 |

## 빠른 시작

### Docker (전체 스택)
```bash
cp .env.example .env   # ANTHROPIC_API_KEY 등 입력
docker compose up --build
# 웹: http://localhost  ·  API: http://localhost:8000/api/health
```

### 로컬 개발
```bash
# API (sqlite 폴백으로 DB 없이도 동작)
cd api && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
COACH_MOCK=1 .venv/bin/uvicorn app.main:app --reload --port 8000

# 웹 (Vite dev — /api는 :8000으로 프록시)
cd web && npm install && npm run dev   # http://localhost:5173

# 모바일 (Expo)
cd mobile && npm install && npx expo start
# 실기기 테스트: app.json → extra.apiBaseUrl 을 맥의 LAN IP로 변경
```

`COACH_MOCK=1`이면 Claude를 호출하지 않고 모의 응답을 사용한다(개발/테스트/CI).

## 아이폰 설치 (PWA)

1. 배포된 주소(HTTPS 필요)를 사파리로 열기
2. 공유 → **홈 화면에 추가**
3. 주소창 없는 standalone 앱으로 실행됨 (오프라인 셸 지원)

## Strava / Garmin 연동

1. https://www.strava.com/settings/api 에서 앱 등록 → Client ID/Secret 발급
2. Authorization Callback Domain에 API 도메인 등록 (로컬은 `localhost`)
3. `.env`에 `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET` 입력
4. 앱 설정 탭 → Strava **연결** → 승인하면 끝
5. 이후 기록 입력 시 **"Strava에서 가져오기"** 한 번으로 거리·시간·페이스·심박·케이던스 자동 입력

**Garmin 사용자**: Garmin Health API는 파트너 승인이 필요해 개인 발급이 불가합니다.
Garmin Connect 앱 → 설정 → 연결된 앱 → **Strava 자동 업로드**를 켜면
시계로 잰 모든 러닝이 Strava를 거쳐 자동으로 들어옵니다(추가 작업 불필요).

## API 요약

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /api/today` | 오늘 상태머신(S0~S5) + 세션 + 당일 카드 + 주간 진행 |
| `POST /api/workout-logs` | 기록 저장 (AI와 독립 — 항상 즉시 커밋, 같은 날 upsert) |
| `POST /api/workout-logs/{id}/review` | AI 리뷰 — SSE 스트리밍(`Accept: text/event-stream`) 또는 JSON |
| `POST /api/weekly-plans` | 주간 계획 AI 생성 (완료 세션은 보존) |
| `POST /api/weeks/current/adjust` | 남은 세션만 보수적 조정 |
| `POST /api/weeks/current/evaluation` | 주간 성장 리포트 (숫자는 SQL, 서술만 AI) |
| `POST /api/daily-plans` | 당일 카드 생성 (컨디션·날씨 반영) |
| `GET·PUT /api/availability` | 정기 훈련 가능 시간(기본 시간표) — 요일 멀티선택 슬롯, PUT 전체 교체 |
| `GET /api/integrations` · `/strava/*` | Strava OAuth · 활동 동기화 · 자동 채움 |

핵심 불변식: **사용자 기록은 AI와 독립적으로 먼저 커밋**된다. AI 실패 시 503을 반환하지만 기록은 보존되고, 화면에는 "기록 저장됨 · 리뷰 재시도"가 표시된다.

## 훈련 가능 시간 & 주간 계획 플로우

- **설정 탭 → 훈련 가능 시간**: 요일별 기본 루틴(예: 평일 점심 헬스장 45분, 화·목 퇴근런)을 슬롯 단위로 등록/편집. 주간·당일 계획 AI가 이 시간표 안에서만 세션을 배치한다.
- **주의 첫 실행(계획 없음)**: 주간 계획 생성 시트가 자동으로 열린다 — 기본 시간표를 보여주고 **"이번 주 특이 일정"**(회식·출장 등 다른 점만)을 입력받아, AI가 가능 시간을 검토한 뒤 7일 계획을 생성한다. 닫으면 그 주에는 다시 뜨지 않는다.

## 테스트

```bash
cd api && COACH_MOCK=1 .venv/bin/python -m pytest tests -q
```
