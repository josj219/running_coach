# Garmin Connect 직접 동기화 — 설계

- 날짜: 2026-06-29
- 상태: 합의 완료, 구현 대기
- 관련 코드: `api/app/services/strava.py`, `api/app/routers/integrations.py`(미러링 대상)

## 배경 / 동기

Strava 연동은 코드가 완성돼 있으나, 2026-06-01부터 Strava가 **REST API와 MCP를 모두 구독($11.99/월) 뒤로 옮겼다**. 공식 문서: "A Strava subscription is a prerequisite for creating an app." 사용자는 구독을 원하지 않는다.

사용자 데이터의 실제 원천은 **Garmin 시계**다(Garmin → Strava 자동 업로드를 써왔을 뿐). 따라서 Strava를 거치지 않고 **Garmin Connect에서 직접 러닝 데이터를 무료로 자동 수집**한다.

## 핵심 제약과 위험 (정직한 평가)

- Garmin은 개인에게 공식 OAuth를 제공하지 않는다(Health API는 기업 파트너 승인 필요). 따라서 **비공식 라이브러리로 사용자 대신 로그인**하는 방식이 유일한 자동 경로다.
- `garth`(종전 표준)는 2026-03-28 폐기됨 — Garmin이 인증 흐름을 바꿔 신규 로그인이 깨졌다.
- **후속 라이브러리 `python-garminconnect`(≥0.3.6, 2026-06-14 릴리스)** 는 garth 의존성을 끊고 자체 다중 인증 전략(mobile / SSO widget / web portal × TLS 위장) + MFA + 토큰 자동저장/자동갱신/자가복구를 지원한다. 현재 작동.
- **위험**: 비공식(리버스 엔지니어링) API이므로 Garmin이 또 인증을 바꾸면 깨질 수 있다. 1인 셀프호스팅 개인 앱이라 감수하기로 합의. 공식 보장은 없음.

## 합의된 결정

| 항목 | 결정 |
|---|---|
| 라이브러리 | `python-garminconnect` (≥0.3.6) |
| 인증 | 이메일+비밀번호(+MFA 코드), 2단계 플로우. **비밀번호 미저장 — 토큰 블롭만 저장** |
| 동기화 시점 | **앱 열 때 / 기록할 때** (활동 조회 시 자동 동기화 + 수동 버튼). 백그라운드 cron 없음 |
| DB | 기존 `Integration`/`ExternalActivity` 재사용. `Integration.auth_blob TEXT` 컬럼 추가 |
| 구조 | 기존 Strava 연동을 그대로 미러링 |

## 아키텍처

### 백엔드

#### `api/app/services/garmin.py` (신규, `strava.py` 대칭)
- `class GarminError(Exception)`.
- 라이브러리가 동기(sync)이므로 모든 호출을 `asyncio.to_thread(...)`로 감싼다.
- **로그인 (MFA 2단계)**: `python-garminconnect`의 문서화된 MFA 플로우 사용 — `Garmin(email, password, return_on_mfa=True)` → `login()`이 MFA 필요 시 중간 상태(client state)를 반환 → `resume_login(state, code)`. 정확한 메서드 시그니처는 설치된 버전에 맞춰 구현 단계에서 확정한다.
- 성공 시 **base64 토큰 블롭**을 직렬화해 반환(예: `garth.dumps()` 류). 이 블롭만 DB에 저장한다.
- **블롭에서 클라이언트 복원**: 저장된 블롭으로 로그인(`tokenstore_base64=...`) → 만료 임박 시 라이브러리가 자동 갱신.
- `sync_activities(db, integ, user_id, limit=10)`:
  1. 블롭으로 클라이언트 복원
  2. `get_activities(0, limit)` 호출
  3. 러닝 타입만 필터(typeKey가 running 계열: `running`, `trail_running`, `treadmill_running`, `virtual_run`, `track_running`, `indoor_running` 등 — "running" 포함 또는 화이트리스트)
  4. `ExternalActivity(provider="garmin", external_id=activityId)` upsert(중복 스킵)
  5. 갱신된 토큰 블롭을 `integ.auth_blob`에 다시 저장, `last_sync_at` 갱신
  6. 새로 추가된 수 반환
- **필드 매핑** (Garmin → ExternalActivity):
  - `distance`(m) → `distance_km` = round(m/1000, 2)
  - `duration`/`movingDuration`(s) → `duration_sec`
  - `averageSpeed`(m/s) 또는 distance/duration → `avg_pace`("M:SS", `_pace_str` 재사용)
  - `averageHR` → `avg_hr`, `maxHR` → `max_hr`
  - `averageRunningCadenceInStepsPerMinute` → `cadence` **(×2 안 함 — Garmin은 이미 양발 기준 spm. Strava는 한 발 기준이라 ×2 했던 것과 다름)**
  - `elevationGain` → `elevation_m`
  - `startTimeGMT`/`startTimeLocal` → `start_date`(UTC aware)
  - `activityName` → `name`, `activityType.typeKey` → `sport_type`
  - `raw`: 원본 핵심 필드 일부 저장

#### DB (`api/app/db.py`)
- `Integration` 모델에 `auth_blob: Mapped[str | None] = mapped_column(Text)` 추가.
- 경량 마이그레이션 목록 `_ADDED_COLUMNS`에 `("integrations", "auth_blob", "TEXT")` 추가(기존 패턴).
- 새 테이블 없음.
- `athlete_name`은 Garmin 프로필의 표시 이름으로 채운다.

#### `api/app/routers/integrations.py` (확장)
- `POST /api/integrations/garmin/connect` (auth 필요) — body `{email, password}`
  - 로그인 성공 → 블롭 저장, `{connected: true, athlete_name}`
  - MFA 필요 → 중간 상태를 **서버 메모리 캐시**에 랜덤 `mfa_token` 키로 보관(TTL 5분, 만료분 정리) → `{mfa_required: true, mfa_token}`
  - 자격증명 오류 → 401, 친절한 메시지
- `POST /api/integrations/garmin/mfa` (auth 필요) — body `{mfa_token, code}`
  - 캐시에서 상태 복원 → `resume_login` → 블롭 저장 → `{connected: true, athlete_name}`
  - 잘못된 코드/만료 → 401, 재시도 안내
- `POST /api/integrations/garmin/sync` — Strava `strava_sync`와 동일 패턴
- `GET /api/integrations/garmin/activities?limit=5` — 조회 시 자동 동기화 1회 시도 후 캐시 반환(`strava_activities` 패턴)
- `DELETE /api/integrations/garmin` — 연결 해제(Integration 삭제)
- `list_integrations(GET "")`의 garmin 블록 갱신: `available: true`, `connected` = (integ 존재 && auth_blob 있음), `athlete_name`, `last_sync_at` 반환. 미연결 시 기존 안내 note는 보조로 유지 가능.

### 프론트엔드

#### `web/src/api.js`
- 추가: `garminConnect({email, password})`, `garminMfa({mfa_token, code})`, `garminSync()`, `garminActivities(limit)`, `garminDisconnect()`.

#### `web/src/tabs/Settings.jsx`
- "데이터 연동" 섹션의 Garmin 카드를 정적 안내문에서 **인터랙티브 연결 플로우**로 교체:
  - 미연결: "연결" 버튼 → 이메일/비밀번호 입력 폼 → 제출
  - MFA 필요 응답 시: 코드 입력 필드 표시 → 제출
  - 연결됨: `연결됨 · {이름}` + "해제" 버튼
  - 성공/실패 배너(기존 `notice`/`Banner` 재사용)
- 기존 Strava 카드 스타일/행 레이아웃 재사용.

#### `web/src/components/RecordSheet.jsx`
- 현재 `StravaImport`(=`api.stravaActivities`)를, 연결된 제공자(가민 포함)의 활동을 가져오도록 일반화.
  - 단순안: 가민 활동도 가져와 합쳐 보여주기. 각 활동은 이미 `provider` 필드를 가짐.
  - 라벨을 제공자에 맞게(예: "Garmin에서 가져오기" / "연동에서 가져오기").
  - `pickActivity` 선택 로직은 유지(거리·시간·페이스·심박·케이던스 폼 채움).

### 운영 / 배포
- `api/requirements.txt`에 `garminconnect` 추가 → 기존 배포 워크플로(`docker compose ... up -d --build`)로 반영.
- **새 시크릿/환경변수 없음** — 사용자가 UI에서 로그인.
- 빌드 시 `curl_cffi` 등 의존성 설치 확인(보통 manylinux wheel로 자동, Dockerfile 변경 불필요 예상).

### 보안 / 프라이버시
- **원시 비밀번호 미저장** — connect 요청 처리 중 메모리에서만 사용, 토큰 교환 후 폐기.
- 토큰 블롭은 본인 서버 Postgres에 저장(기존 Strava 토큰과 동일 신뢰 수준).
- (선택적 강화) `JWT_SECRET` 파생 키로 Fernet 암호화 — 1인 셀프호스팅에선 기존 평문 토큰과 동등하므로 MVP에서는 생략 가능, 후속 과제로 표기.
- connect/mfa/sync 엔드포인트는 모두 `get_current_user` 인증 필수.

### 실패 처리
- 로그인 실패(잘못된 자격증명) → 401 + 메시지.
- MFA 코드 오류/만료 → 401 + 재시도.
- 토큰 블롭 만료·폐기로 동기화 실패 → `GarminError` → 엔드포인트가 409/502 + "가민 재로그인 필요"; UI는 재연결 유도 배너.
- 라이브러리 인증 전략 깨짐(Garmin이 또 변경) → `GarminError` 로깅 + "가민 연동 일시 불가" 안내.
- Garmin 429(Too Many Requests) → 메시지 + 잠시 후 재시도 안내. 동기화 limit 작게(10), 온디맨드만으로 호출 빈도 최소화.

## 테스트
- 매핑 로직 단위테스트(네트워크 없이): `_pace_str`, 케이던스 ×2 미적용, 러닝 타입 필터, distance/duration→필드 변환.
- `sync_activities`는 Garmin 클라이언트를 monkeypatch로 가짜 응답 주입해 upsert/중복스킵/필드 검증.
- 기존 Strava 테스트 패턴(있다면 `coach_mock` 류) 참고해 동일 스타일 유지.

## 범위에서 제외 (YAGNI)
- 백그라운드 cron 동기화(사용자 선택대로 제외).
- Garmin 공식 Health API(파트너 승인 필요).
- 활동에서 `workout_log` 자동 생성(기존 수동 기록 플로우 유지).
- 토큰 블롭 암호화(후속 과제로만 표기).

## 사용자 경험 (완성 후)
폰에서 **설정 → Garmin → 이메일/비밀번호(+MFA 코드) 1회 입력** → 이후 기록 화면을 열 때마다 최근 러닝이 자동으로 채워진다. 구독 비용 0.
