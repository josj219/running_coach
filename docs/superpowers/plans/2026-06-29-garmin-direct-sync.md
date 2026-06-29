# Garmin Connect 직접 동기화 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 구독 없이 Garmin Connect에서 직접 러닝 데이터를 가져와 기록 입력 자동채움에 쓴다.

**Architecture:** 기존 Strava 연동(`services/strava.py` + `routers/integrations.py`)을 미러링한다. 비공식 `python-garminconnect`로 사용자 대신 로그인하고, **모든 라이브러리 호출은 `services/garmin.py` 안의 작은 헬퍼에 격리**한다. 라우터·프론트는 라이브러리가 아니라 우리가 정의한 안정적 인터페이스(`begin_login`/`complete_mfa`/`sync_activities`)에만 의존한다. 동기화는 앱 열 때(활동 조회 시) 자동 + 수동 버튼.

**Tech Stack:** Python 3.12, FastAPI(async), SQLAlchemy 2.0(async), `python-garminconnect`, React(Vite), 기존 sqlite(dev)/postgres(prod).

## Global Constraints

- 제공자 문자열은 `"garmin"` (소문자), 기존 `Integration`/`ExternalActivity` 테이블 재사용.
- **케이던스는 ×2 하지 않는다** — Garmin `averageRunningCadenceInStepsPerMinute`는 이미 양발 기준 spm. (Strava는 한 발 기준이라 ×2 했음.)
- **원시 비밀번호 미저장** — 로그인 1회에만 사용, 토큰 블롭(base64 문자열)만 `Integration.auth_blob`에 저장.
- 새 환경변수/시크릿 없음. 사용자가 UI에서 로그인.
- 동기 라이브러리 호출은 `asyncio.to_thread(...)`로 감싼다.
- 백엔드 테스트는 네트워크/실제 가민 호출 없이 — 라이브러리 경계를 monkeypatch.
- UI 카피는 한국어, 기존 Strava 카드 스타일 재사용.
- 라이브러리 import 실패가 전체 앱을 깨지 않도록, `garminconnect`는 `requirements.txt`에 추가하고 Task 2에서 설치한다.

---

### Task 1: DB — `Integration.auth_blob` 컬럼 추가

**Files:**
- Modify: `api/app/db.py:221-234` (Integration 모델), `api/app/db.py:265-269` (`_ADDED_COLUMNS`)
- Test: `api/tests/test_garmin.py` (신규)

**Interfaces:**
- Produces: `Integration.auth_blob: str | None` (가민 토큰 블롭 저장용)

- [ ] **Step 1: 실패하는 테스트 작성** — `api/tests/test_garmin.py`

```python
import pytest
from sqlalchemy import select
from app.db import Integration


@pytest.mark.asyncio
async def test_integration_has_auth_blob(db_session):
    integ = Integration(user_id=1, provider="garmin", auth_blob="abc123")
    db_session.add(integ)
    await db_session.commit()
    got = (await db_session.execute(
        select(Integration).where(Integration.provider == "garmin"))).scalar_one()
    assert got.auth_blob == "abc123"
```

- [ ] **Step 2: conftest에 `db_session` fixture가 있는지 확인** — 없으면 추가

Run: `grep -n "db_session\|async def db\|SessionLocal" api/tests/conftest.py`
없으면 `api/tests/conftest.py`에 추가 (기존 엔진/세션 재사용):

```python
import pytest_asyncio
from app.db import SessionLocal, init_db

@pytest_asyncio.fixture
async def db_session():
    await init_db()
    async with SessionLocal() as s:
        yield s
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd api && python -m pytest tests/test_garmin.py::test_integration_has_auth_blob -v`
Expected: FAIL — `TypeError: 'auth_blob' is an invalid keyword argument` 또는 컬럼 없음.

- [ ] **Step 4: 모델에 컬럼 추가** — `api/app/db.py` Integration 클래스, `last_sync_at` 다음 줄에:

```python
    auth_blob: Mapped[str | None] = mapped_column(Text)  # Garmin 토큰 블롭(base64)
```

(`Text`는 이미 `api/app/db.py:13`에서 import됨.)

- [ ] **Step 5: 경량 마이그레이션 등록** — `_ADDED_COLUMNS` 리스트에 추가:

```python
    ("integrations", "auth_blob", "TEXT"),
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `cd api && python -m pytest tests/test_garmin.py::test_integration_has_auth_blob -v`
Expected: PASS

- [ ] **Step 7: 커밋**

```bash
git add api/app/db.py api/tests/test_garmin.py api/tests/conftest.py
git commit -m "feat(garmin): add Integration.auth_blob column for token storage"
```

---

### Task 2: `garmin.py` — 순수 매핑 헬퍼

**Files:**
- Create: `api/app/services/garmin.py`
- Modify: `api/requirements.txt`
- Test: `api/tests/test_garmin.py`

**Interfaces:**
- Produces:
  - `class GarminError(Exception)`
  - `is_running(a: dict) -> bool`
  - `map_activity(a: dict) -> dict` — 키: `external_id, name, sport_type, start_date, distance_km, duration_sec, avg_pace, avg_hr, max_hr, cadence, elevation_m`
  - `_pace_str(distance_m: float, moving_sec: int) -> str | None`

- [ ] **Step 1: 의존성 추가 + 설치** — `api/requirements.txt` 끝에 한 줄 추가:

```
garminconnect>=0.3.6
```

Run: `cd api && pip install -r requirements.txt`
Expected: `garminconnect`, `curl_cffi` 등 설치 성공.

- [ ] **Step 2: 실패하는 테스트 작성** — `api/tests/test_garmin.py`에 추가

```python
from app.services import garmin


def test_pace_str():
    assert garmin._pace_str(5000, 1500) == "5:00"   # 5km / 25min
    assert garmin._pace_str(0, 100) is None
    assert garmin._pace_str(5000, 0) is None


def test_is_running():
    assert garmin.is_running({"activityType": {"typeKey": "running"}}) is True
    assert garmin.is_running({"activityType": {"typeKey": "trail_running"}}) is True
    assert garmin.is_running({"activityType": {"typeKey": "cycling"}}) is False
    assert garmin.is_running({}) is False


def test_map_activity_cadence_not_doubled():
    a = {
        "activityId": 12345,
        "activityName": "아침 러닝",
        "activityType": {"typeKey": "running"},
        "startTimeGMT": "2026-06-28 21:00:00",
        "distance": 10000.0,
        "duration": 3000.0,
        "averageHR": 150.4,
        "maxHR": 172.0,
        "averageRunningCadenceInStepsPerMinute": 178.0,
        "elevationGain": 42.0,
    }
    m = garmin.map_activity(a)
    assert m["external_id"] == "12345"
    assert m["distance_km"] == 10.0
    assert m["duration_sec"] == 3000
    assert m["avg_pace"] == "5:00"
    assert m["avg_hr"] == 150
    assert m["max_hr"] == 172
    assert m["cadence"] == 178       # ×2 하지 않음
    assert m["elevation_m"] == 42
    assert m["start_date"].year == 2026
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd api && python -m pytest tests/test_garmin.py -k "pace or running or cadence" -v`
Expected: FAIL — `AttributeError: module ... has no attribute '_pace_str'`

- [ ] **Step 4: `garmin.py` 작성** (순수 헬퍼만)

```python
"""Garmin Connect 직접 동기화 (비공식 python-garminconnect 기반).

Garmin은 개인에게 공식 OAuth를 제공하지 않아, 사용자 대신 로그인한다.
모든 라이브러리 호출은 이 모듈의 헬퍼에 격리한다.
"""

from datetime import datetime, timezone

RUN_KEYS = {"running", "trail_running", "treadmill_running", "virtual_run",
            "track_running", "indoor_running", "ultra_run", "obstacle_run"}


class GarminError(Exception):
    pass


def _pace_str(distance_m: float, moving_sec: int) -> str | None:
    if not distance_m or not moving_sec:
        return None
    sec_per_km = moving_sec / (distance_m / 1000)
    return f"{int(sec_per_km // 60)}:{int(sec_per_km % 60):02d}"


def is_running(a: dict) -> bool:
    key = ((a.get("activityType") or {}).get("typeKey") or "").lower()
    return key in RUN_KEYS or "running" in key


def map_activity(a: dict) -> dict:
    dist_m = a.get("distance") or 0
    dur = a.get("duration") or a.get("movingDuration") or 0
    start = None
    if a.get("startTimeGMT"):
        # Garmin GMT 포맷: "2026-06-28 21:00:00"
        start = datetime.strptime(a["startTimeGMT"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    cad = a.get("averageRunningCadenceInStepsPerMinute")
    return {
        "external_id": str(a["activityId"]),
        "name": a.get("activityName"),
        "sport_type": (a.get("activityType") or {}).get("typeKey"),
        "start_date": start,
        "distance_km": round(dist_m / 1000, 2) if dist_m else None,
        "duration_sec": int(dur) if dur else None,
        "avg_pace": _pace_str(dist_m, dur),
        "avg_hr": round(a["averageHR"]) if a.get("averageHR") else None,
        "max_hr": round(a["maxHR"]) if a.get("maxHR") else None,
        "cadence": round(cad) if cad else None,   # 양발 spm — ×2 하지 않음
        "elevation_m": round(a["elevationGain"]) if a.get("elevationGain") else None,
    }
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd api && python -m pytest tests/test_garmin.py -k "pace or running or cadence" -v`
Expected: PASS (3 passed)

- [ ] **Step 6: 커밋**

```bash
git add api/requirements.txt api/app/services/garmin.py api/tests/test_garmin.py
git commit -m "feat(garmin): add garmin service mapping helpers + dependency"
```

---

### Task 3: `garmin.py` — 활동 동기화 (`sync_activities`)

**Files:**
- Modify: `api/app/services/garmin.py`
- Test: `api/tests/test_garmin.py`

**Interfaces:**
- Consumes: `is_running`, `map_activity` (Task 2)
- Produces:
  - `fetch_recent(blob: str, limit: int = 10) -> tuple[list[dict], str]` — (활동 원본 리스트, 갱신된 토큰 블롭). 라이브러리 경계.
  - `async sync_activities(db, integ: Integration, user_id: int, limit: int = 10) -> int` — 새로 추가된 활동 수

- [ ] **Step 1: 실패하는 테스트 작성** — `api/tests/test_garmin.py`에 추가

```python
import pytest
from sqlalchemy import select
from app.db import ExternalActivity, Integration


@pytest.mark.asyncio
async def test_sync_activities_upserts_running_only(db_session, monkeypatch):
    fake = [
        {"activityId": 1, "activityName": "런", "activityType": {"typeKey": "running"},
         "startTimeGMT": "2026-06-28 21:00:00", "distance": 5000.0, "duration": 1500.0,
         "averageRunningCadenceInStepsPerMinute": 176.0},
        {"activityId": 2, "activityName": "자전거", "activityType": {"typeKey": "cycling"},
         "startTimeGMT": "2026-06-27 21:00:00", "distance": 20000.0, "duration": 3600.0},
    ]
    monkeypatch.setattr(garmin, "fetch_recent", lambda blob, limit=10: (fake, "newblob"))

    integ = Integration(user_id=1, provider="garmin", auth_blob="oldblob")
    db_session.add(integ)
    await db_session.commit()

    added = await garmin.sync_activities(db_session, integ, user_id=1)
    assert added == 1                      # 러닝만
    assert integ.auth_blob == "newblob"    # 갱신된 토큰 저장
    assert integ.last_sync_at is not None

    rows = (await db_session.execute(select(ExternalActivity).where(
        ExternalActivity.provider == "garmin"))).scalars().all()
    assert len(rows) == 1
    assert rows[0].cadence == 176

    # 재동기화 시 중복 추가 안 함
    added2 = await garmin.sync_activities(db_session, integ, user_id=1)
    assert added2 == 0
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd api && python -m pytest tests/test_garmin.py::test_sync_activities_upserts_running_only -v`
Expected: FAIL — `AttributeError: ... 'fetch_recent'` / `'sync_activities'`

- [ ] **Step 3: `garmin.py`에 동기화 구현 추가**

상단 import에 추가:

```python
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import ExternalActivity, Integration
```

함수 추가:

```python
def _load_client(blob: str):
    """토큰 블롭으로 로그인된 Garmin 클라이언트 복원. (라이브러리 경계)"""
    from garminconnect import Garmin
    client = Garmin()
    client.garth.loads(blob)   # garth base64 토큰 복원
    return client


def _dump_blob(client) -> str:
    """클라이언트의 (갱신될 수 있는) 토큰을 base64 블롭으로 직렬화. (라이브러리 경계)"""
    return client.garth.dumps()


def fetch_recent(blob: str, limit: int = 10) -> tuple[list[dict], str]:
    """최근 활동 원본 리스트 + 갱신된 토큰 블롭. (블로킹 — to_thread로 호출)"""
    client = _load_client(blob)
    activities = client.get_activities(0, limit)
    return activities, _dump_blob(client)


async def sync_activities(db: AsyncSession, integ: Integration, user_id: int, limit: int = 10) -> int:
    if not integ.auth_blob:
        raise GarminError("가민이 연결되어 있지 않습니다.")
    try:
        acts, new_blob = await asyncio.to_thread(fetch_recent, integ.auth_blob, limit)
    except GarminError:
        raise
    except Exception as e:
        raise GarminError(f"가민 활동 조회 실패: {e}") from e

    added = 0
    for a in acts:
        if not is_running(a):
            continue
        m = map_activity(a)
        existing = (await db.execute(select(ExternalActivity).where(
            ExternalActivity.provider == "garmin",
            ExternalActivity.external_id == m["external_id"],
        ))).scalar_one_or_none()
        if existing:
            continue
        db.add(ExternalActivity(
            user_id=user_id, provider="garmin",
            raw={k: a.get(k) for k in ("activityId", "activityName", "activityType",
                                       "startTimeGMT", "distance", "duration")},
            **m,
        ))
        added += 1
    integ.auth_blob = new_blob
    integ.last_sync_at = datetime.now(timezone.utc)
    await db.commit()
    return added
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd api && python -m pytest tests/test_garmin.py::test_sync_activities_upserts_running_only -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add api/app/services/garmin.py api/tests/test_garmin.py
git commit -m "feat(garmin): sync_activities — fetch + filter + upsert"
```

---

### Task 4: `garmin.py` — 로그인 / MFA

**Files:**
- Modify: `api/app/services/garmin.py`
- Test: `api/tests/test_garmin.py`

**Interfaces:**
- Produces:
  - `begin_login(email: str, password: str) -> dict` — `{"status":"ok","blob":str,"athlete_name":str|None}` 또는 `{"status":"mfa","mfa_token":str}`
  - `complete_mfa(mfa_token: str, code: str) -> dict` — `{"status":"ok","blob":str,"athlete_name":str|None}`
  - 두 함수 모두 실패 시 `GarminError`

- [ ] **Step 1: 실패하는 테스트 작성** — `api/tests/test_garmin.py`에 추가

```python
class _FakeClient:
    def __init__(self, *a, needs_mfa=False, **kw):
        self._needs_mfa = needs_mfa
        self.garth = self
    def login(self):
        if self._needs_mfa:
            return ("needs_mfa", {"state": "x"})
        return ("ok", None)
    def resume_login(self, state, code):
        if code != "123456":
            raise ValueError("bad code")
        return ("ok", None)
    def dumps(self):
        return "BLOB"
    def get_full_name(self):
        return "고고조"


def test_begin_login_ok(monkeypatch):
    monkeypatch.setattr(garmin, "Garmin", lambda **kw: _FakeClient(**kw))
    res = garmin.begin_login("a@b.com", "pw")
    assert res["status"] == "ok"
    assert res["blob"] == "BLOB"
    assert res["athlete_name"] == "고고조"


def test_begin_login_mfa_then_complete(monkeypatch):
    monkeypatch.setattr(garmin, "Garmin", lambda **kw: _FakeClient(needs_mfa=True, **kw))
    res = garmin.begin_login("a@b.com", "pw")
    assert res["status"] == "mfa"
    tok = res["mfa_token"]
    ok = garmin.complete_mfa(tok, "123456")
    assert ok["status"] == "ok"
    assert ok["blob"] == "BLOB"


def test_complete_mfa_wrong_code(monkeypatch):
    monkeypatch.setattr(garmin, "Garmin", lambda **kw: _FakeClient(needs_mfa=True, **kw))
    tok = garmin.begin_login("a@b.com", "pw")["mfa_token"]
    with pytest.raises(garmin.GarminError):
        garmin.complete_mfa(tok, "000000")
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd api && python -m pytest tests/test_garmin.py -k "login or mfa" -v`
Expected: FAIL — `AttributeError: ... 'Garmin'` / `'begin_login'`

- [ ] **Step 3: 구현 추가** — `garmin.py` 상단에 모듈 레벨 import + 캐시:

```python
import secrets
import time

from garminconnect import Garmin   # 테스트에서 monkeypatch 가능하도록 모듈 레벨 import

_PENDING: dict[str, tuple] = {}   # mfa_token -> (client, state, expires)
_MFA_TTL = 300
```

함수 추가:

```python
def _athlete_name(client) -> str | None:
    try:
        return client.get_full_name()
    except Exception:
        return None


def _prune_pending() -> None:
    now = time.time()
    for k in [k for k, (_, _, exp) in _PENDING.items() if exp < now]:
        _PENDING.pop(k, None)


def begin_login(email: str, password: str) -> dict:
    """1단계 로그인. MFA 필요 시 중간 클라이언트를 메모리에 보관하고 토큰 반환."""
    try:
        client = Garmin(email=email, password=password, return_on_mfa=True)
        res = client.login()
    except Exception as e:
        raise GarminError("가민 로그인 실패: 이메일/비밀번호를 확인해 주세요.") from e
    if isinstance(res, tuple) and res[0] == "needs_mfa":
        _prune_pending()
        tok = secrets.token_urlsafe(16)
        _PENDING[tok] = (client, res[1], time.time() + _MFA_TTL)
        return {"status": "mfa", "mfa_token": tok}
    return {"status": "ok", "blob": _dump_blob(client), "athlete_name": _athlete_name(client)}


def complete_mfa(mfa_token: str, code: str) -> dict:
    """2단계: 보관된 클라이언트로 MFA 코드 제출."""
    _prune_pending()
    entry = _PENDING.pop(mfa_token, None)
    if not entry:
        raise GarminError("MFA 세션이 만료됐어요. 다시 연결해 주세요.")
    client, state, _ = entry
    try:
        client.resume_login(state, code)
    except Exception as e:
        raise GarminError("MFA 코드가 올바르지 않아요.") from e
    return {"status": "ok", "blob": _dump_blob(client), "athlete_name": _athlete_name(client)}
```

> **라이브러리 경계 주의:** `_load_client`/`_dump_blob`(Task 3)와 `begin_login`의 `return_on_mfa`/`resume_login`은 설치된 `garminconnect` 버전에 맞춰 시그니처를 확인해야 한다. 단위테스트는 `_FakeClient`로 통과하므로, **Task 9의 실기기 스모크 테스트에서 실제 로그인으로 검증**한다. `client.garth.dumps()/loads()`가 없으면 파일 토큰스토어(`client.garth.dump(dir)`)로 폴백한다.

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd api && python -m pytest tests/test_garmin.py -k "login or mfa" -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 전체 garmin 테스트 확인**

Run: `cd api && python -m pytest tests/test_garmin.py -v`
Expected: 모두 PASS

- [ ] **Step 6: 커밋**

```bash
git add api/app/services/garmin.py api/tests/test_garmin.py
git commit -m "feat(garmin): email/password + MFA two-step login"
```

---

### Task 5: 라우터 — Garmin 엔드포인트 + 상태

**Files:**
- Modify: `api/app/routers/integrations.py` (상단 import; `list_integrations` garmin 블록; 파일 끝에 엔드포인트 추가)
- Test: `api/tests/test_scenarios.py:315-329` (test_23 수정), `api/tests/test_garmin.py` (라우터 테스트 추가)

**Interfaces:**
- Consumes: `garmin.begin_login`, `garmin.complete_mfa`, `garmin.sync_activities`, `garmin.GarminError` (Task 3·4)
- Produces (HTTP):
  - `POST /api/integrations/garmin/connect` {email,password} → `{connected:true,athlete_name}` 또는 `{mfa_required:true,mfa_token}`
  - `POST /api/integrations/garmin/mfa` {mfa_token,code} → `{connected:true,athlete_name}`
  - `POST /api/integrations/garmin/sync` → `{added:int}`
  - `GET /api/integrations/garmin/activities?limit=5` → `{items:[...]}`
  - `DELETE /api/integrations/garmin` → `{disconnected:true}`

- [ ] **Step 1: 기존 상태 테스트(test_23) 수정** — `api/tests/test_scenarios.py:315-319`

```python
async def test_23_integrations_status(client):
    body = (await client.get("/api/integrations")).json()
    assert body["strava"]["available"] is False   # 키 미설정
    assert body["strava"]["connected"] is False
    assert body["garmin"]["available"] is True     # 가민은 UI 로그인 — 항상 가능
    assert body["garmin"]["connected"] is False
```

- [ ] **Step 2: 라우터 테스트 추가** — `api/tests/test_garmin.py`에 추가

```python
@pytest.mark.asyncio
async def test_garmin_sync_requires_connection(client):
    r = await client.post("/api/integrations/garmin/sync")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_garmin_connect_ok(client, monkeypatch):
    monkeypatch.setattr(garmin, "begin_login",
                        lambda email, password: {"status": "ok", "blob": "B", "athlete_name": "고고조"})
    r = await client.post("/api/integrations/garmin/connect",
                          json={"email": "a@b.com", "password": "pw"})
    assert r.status_code == 200
    assert r.json()["connected"] is True
    status = (await client.get("/api/integrations")).json()
    assert status["garmin"]["connected"] is True


@pytest.mark.asyncio
async def test_garmin_connect_mfa(client, monkeypatch):
    monkeypatch.setattr(garmin, "begin_login",
                        lambda email, password: {"status": "mfa", "mfa_token": "T"})
    r = await client.post("/api/integrations/garmin/connect",
                          json={"email": "a@b.com", "password": "pw"})
    assert r.json()["mfa_required"] is True
```

> `client` fixture는 인증된 사용자로 동작해야 한다. `test_scenarios.py`의 `client` fixture 패턴을 그대로 사용한다 (`grep -n "def client" api/tests/conftest.py api/tests/test_scenarios.py`로 확인 후 동일 import).

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd api && python -m pytest tests/test_garmin.py -k garmin_ -v tests/test_scenarios.py::test_23_integrations_status`
Expected: FAIL (404 아님 / connect 404 / garmin.available False)

- [ ] **Step 4: 라우터 상단 import 추가** — `api/app/routers/integrations.py:9-18` 영역

```python
import asyncio

from ..services import garmin
```

(`from ..services import strava` 옆에 `garmin` 추가, `import asyncio`는 파일 상단.)

- [ ] **Step 5: `list_integrations`의 garmin 블록 교체** — `api/app/routers/integrations.py:41-47`

```python
        "garmin": {
            "available": True,
            "connected": ga is not None and ga.auth_blob is not None,
            "athlete_name": ga.athlete_name if ga else None,
            "last_sync_at": ga.last_sync_at.isoformat() if ga and ga.last_sync_at else None,
            "note": "가민 커넥트 이메일/비밀번호로 직접 연결합니다. 비밀번호는 저장하지 않아요.",
        },
```

- [ ] **Step 6: 엔드포인트 추가** — `api/app/routers/integrations.py` 파일 끝에

```python
class GarminConnectBody(BaseModel):
    email: str
    password: str


class GarminMfaBody(BaseModel):
    mfa_token: str
    code: str


async def _store_garmin(db: AsyncSession, user_id: int, res: dict) -> None:
    integ = await _get_integration(db, "garmin", user_id) \
        or Integration(user_id=user_id, provider="garmin")
    integ.auth_blob = res["blob"]
    integ.athlete_name = res.get("athlete_name")
    db.add(integ)
    await db.commit()


@router.post("/garmin/connect")
async def garmin_connect(body: GarminConnectBody, user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    try:
        res = await asyncio.to_thread(garmin.begin_login, body.email, body.password)
    except garmin.GarminError as e:
        raise HTTPException(401, {"code": "GARMIN_AUTH", "message": str(e)})
    if res["status"] == "mfa":
        return {"mfa_required": True, "mfa_token": res["mfa_token"]}
    await _store_garmin(db, user.id, res)
    return {"connected": True, "athlete_name": res.get("athlete_name")}


@router.post("/garmin/mfa")
async def garmin_mfa(body: GarminMfaBody, user: User = Depends(get_current_user),
                     db: AsyncSession = Depends(get_db)):
    try:
        res = await asyncio.to_thread(garmin.complete_mfa, body.mfa_token, body.code)
    except garmin.GarminError as e:
        raise HTTPException(401, {"code": "GARMIN_MFA", "message": str(e)})
    await _store_garmin(db, user.id, res)
    return {"connected": True, "athlete_name": res.get("athlete_name")}


@router.post("/garmin/sync")
async def garmin_sync(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    integ = await _get_integration(db, "garmin", user.id)
    if integ is None or not integ.auth_blob:
        raise HTTPException(404, {"code": "NOT_CONNECTED", "message": "가민이 연결되어 있지 않습니다."})
    try:
        added = await garmin.sync_activities(db, integ, user.id)
    except garmin.GarminError as e:
        raise HTTPException(502, {"code": "INTEGRATION_ERROR", "message": str(e)})
    return {"added": added}


@router.get("/garmin/activities")
async def garmin_activities(limit: int = 5, user: User = Depends(get_current_user),
                            db: AsyncSession = Depends(get_db)):
    integ = await _get_integration(db, "garmin", user.id)
    if integ and integ.auth_blob:
        try:
            await garmin.sync_activities(db, integ, user.id)
        except garmin.GarminError:
            pass  # 캐시로 응답
    res = await db.execute(select(ExternalActivity).where(
        ExternalActivity.user_id == user.id, ExternalActivity.provider == "garmin",
    ).order_by(ExternalActivity.start_date.desc()).limit(limit))
    return {"items": [_activity_dict(a) for a in res.scalars()]}


@router.delete("/garmin")
async def garmin_disconnect(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    integ = await _get_integration(db, "garmin", user.id)
    if integ:
        await db.delete(integ)
        await db.commit()
    return {"disconnected": True}
```

- [ ] **Step 7: 테스트 통과 확인**

Run: `cd api && python -m pytest tests/test_garmin.py tests/test_scenarios.py::test_23_integrations_status -v`
Expected: 모두 PASS

- [ ] **Step 8: 전체 백엔드 회귀 확인**

Run: `cd api && python -m pytest -q`
Expected: 전체 PASS (기존 테스트 깨지지 않음)

- [ ] **Step 9: 커밋**

```bash
git add api/app/routers/integrations.py api/tests/test_garmin.py api/tests/test_scenarios.py
git commit -m "feat(garmin): connect/mfa/sync/activities/disconnect endpoints"
```

---

### Task 6: 프론트 — `api.js` 메서드

**Files:**
- Modify: `web/src/api.js:68-71` (integration 메서드 옆)

**Interfaces:**
- Produces: `api.garminConnect`, `api.garminMfa`, `api.garminSync`, `api.garminActivities`, `api.garminDisconnect`

- [ ] **Step 1: 메서드 추가** — `web/src/api.js`의 `stravaDisconnect` 줄(71) 다음에

```javascript
  garminConnect: (body) => request('/api/integrations/garmin/connect', { method: 'POST', body: JSON.stringify(body) }),
  garminMfa: (body) => request('/api/integrations/garmin/mfa', { method: 'POST', body: JSON.stringify(body) }),
  garminSync: () => request('/api/integrations/garmin/sync', { method: 'POST' }),
  garminActivities: (limit = 5) => request(`/api/integrations/garmin/activities?limit=${limit}`),
  garminDisconnect: () => request('/api/integrations/garmin', { method: 'DELETE' }),
```

- [ ] **Step 2: 빌드 확인**

Run: `cd web && npm run build`
Expected: 빌드 성공 (문법 오류 없음)

- [ ] **Step 3: 커밋**

```bash
git add web/src/api.js
git commit -m "feat(garmin): api client methods"
```

---

### Task 7: 프론트 — 설정 탭 Garmin 연결 UI

**Files:**
- Modify: `web/src/tabs/Settings.jsx:400-410` (Garmin 카드 영역), 그리고 새 컴포넌트 `GarminCard` 추가(같은 파일 상단 부근)

**Interfaces:**
- Consumes: `api.garminConnect`, `api.garminMfa`, `api.garminDisconnect`, `integ.garmin` (Task 5·6)

- [ ] **Step 1: `GarminCard` 컴포넌트 추가** — `Settings.jsx`의 `Row` 함수 위(약 195행 부근)에 삽입

```javascript
// 가민 연결: 이메일/비번 → (필요시) MFA 코드 → 연결됨/해제
function GarminCard({ garmin, onChanged }) {
  const [mode, setMode] = useState('idle');        // idle | form | mfa | busy
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mfaToken, setMfaToken] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState(null);

  const inputS = { width: '100%', border: 'none', outline: 'none', background: 'var(--fill-tertiary)',
    borderRadius: 11, padding: '11px 13px', fontSize: 15, color: 'var(--label-primary)', marginBottom: 8 };

  const connect = async () => {
    setError(null); setMode('busy');
    try {
      const r = await api.garminConnect({ email, password });
      setPassword('');
      if (r.mfa_required) { setMfaToken(r.mfa_token); setMode('mfa'); return; }
      onChanged();
    } catch (e) { setError(e.message || '연결 실패'); setMode('form'); }
  };
  const submitMfa = async () => {
    setError(null); setMode('busy');
    try { await api.garminMfa({ mfa_token: mfaToken, code }); setCode(''); onChanged(); }
    catch (e) { setError(e.message || 'MFA 실패'); setMode('mfa'); }
  };

  return (
    <div style={{ borderTop: '0.5px solid var(--separator-non-opaque)', display: 'flex', gap: 12,
      padding: '14px 16px', alignItems: 'flex-start' }}>
      <span style={{ width: 34, height: 34, borderRadius: 10, background: '#11A9ED', display: 'grid',
        placeItems: 'center', flex: 'none' }}><Icon name="Watch" size={18} color="#fff" /></span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ fontSize: 16, fontWeight: 600, flex: 1 }}>Garmin</div>
          {garmin?.connected ? (
            <button onClick={async () => { await api.garminDisconnect(); onChanged(); }}
              style={{ border: 'none', background: 'var(--fill-tertiary)', color: 'var(--accent-red)',
                fontWeight: 600, fontSize: 13.5, borderRadius: 999, padding: '7px 13px', cursor: 'pointer' }}>해제</button>
          ) : mode === 'idle' ? (
            <button onClick={() => setMode('form')}
              style={{ border: 'none', background: '#11A9ED', color: '#fff', fontWeight: 700, fontSize: 13.5,
                borderRadius: 999, padding: '7px 14px', cursor: 'pointer' }}>연결</button>
          ) : null}
        </div>
        <div style={{ fontSize: 13, color: 'var(--label-secondary)', marginTop: 2 }}>
          {garmin?.connected
            ? `연결됨${garmin.athlete_name ? ` · ${garmin.athlete_name}` : ''}`
            : '가민 커넥트 로그인 · 비밀번호는 저장하지 않아요'}
        </div>

        {mode === 'form' && (
          <div style={{ marginTop: 10 }} className="anim-in">
            <input style={inputS} placeholder="가민 커넥트 이메일" value={email}
              onChange={(e) => setEmail(e.target.value)} inputMode="email" />
            <input style={inputS} placeholder="비밀번호" type="password" value={password}
              onChange={(e) => setPassword(e.target.value)} />
            {error && <div style={{ marginBottom: 8 }}><Banner tone="error">{error}</Banner></div>}
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={() => { setMode('idle'); setError(null); }}
                style={{ flex: 1, padding: '10px 0', borderRadius: 11, border: 'none', cursor: 'pointer',
                  background: 'var(--fill-tertiary)', color: 'var(--label-secondary)', fontWeight: 600 }}>취소</button>
              <button onClick={connect} disabled={!email || !password}
                style={{ flex: 1, padding: '10px 0', borderRadius: 11, border: 'none', cursor: 'pointer',
                  background: '#11A9ED', color: '#fff', fontWeight: 700 }}>연결</button>
            </div>
          </div>
        )}
        {mode === 'mfa' && (
          <div style={{ marginTop: 10 }} className="anim-in">
            <input style={inputS} placeholder="2단계 인증 코드" value={code} inputMode="numeric"
              onChange={(e) => setCode(e.target.value)} />
            {error && <div style={{ marginBottom: 8 }}><Banner tone="error">{error}</Banner></div>}
            <button onClick={submitMfa} disabled={!code}
              style={{ width: '100%', padding: '10px 0', borderRadius: 11, border: 'none', cursor: 'pointer',
                background: '#11A9ED', color: '#fff', fontWeight: 700 }}>코드 확인</button>
          </div>
        )}
        {mode === 'busy' && <div style={{ fontSize: 13, color: 'var(--label-secondary)', marginTop: 8 }}>처리 중…</div>}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 기존 Garmin 정적 블록을 컴포넌트로 교체** — `Settings.jsx:400-410`의 `<div style={{ borderTop... Garmin ...}}>...</div>` 전체를:

```javascript
            <GarminCard garmin={integ?.garmin} onChanged={load} />
```

- [ ] **Step 3: 빌드 확인**

Run: `cd web && npm run build`
Expected: 빌드 성공

- [ ] **Step 4: 커밋**

```bash
git add web/src/tabs/Settings.jsx
git commit -m "feat(garmin): settings connect UI (email/password + MFA)"
```

---

### Task 8: 프론트 — 기록 입력 자동채움에 Garmin 포함

**Files:**
- Modify: `web/src/components/RecordSheet.jsx:128-181` (`StravaImport`), `:220-229` (`pickActivity`), `:378` (호출부)

**Interfaces:**
- Consumes: `api.integrations`, `api.stravaActivities`, `api.garminActivities` (Task 6)

- [ ] **Step 1: `StravaImport`을 다중 제공자로 일반화** — 함수 본문의 `load`를 교체

```javascript
  const load = async () => {
    setState('loading');
    try {
      const integ = await api.integrations();
      const calls = [];
      if (integ.strava?.connected) calls.push(api.stravaActivities(5));
      if (integ.garmin?.connected) calls.push(api.garminActivities(5));
      if (!calls.length) { setState('off'); return; }
      const results = await Promise.all(calls);
      const merged = results.flatMap((r) => r.items)
        .sort((a, b) => (b.start_date || '').localeCompare(a.start_date || ''))
        .slice(0, 5);
      if (!merged.length) { setState('empty'); return; }
      setItems(merged);
      setState('list');
    } catch { setState('empty'); }
  };
```

- [ ] **Step 2: 라벨/안내 문구를 제공자 중립으로** — `idle` 버튼 텍스트(152행)와 `off` 배너(160행)

```javascript
          <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--label-primary)' }}>연동에서 가져오기</div>
```

```javascript
  if (state === 'off') return <Banner tone="info">설정 탭에서 Strava·가민을 연결하면 기록이 자동으로 채워져요.</Banner>;
```

- [ ] **Step 3: `pickActivity`의 source를 활동 제공자로** — `:226`

```javascript
    setSource(a.provider || 'strava');
```

- [ ] **Step 4: 빌드 확인**

Run: `cd web && npm run build`
Expected: 빌드 성공

- [ ] **Step 5: 커밋**

```bash
git add web/src/components/RecordSheet.jsx
git commit -m "feat(garmin): record autofill pulls garmin activities too"
```

---

### Task 9: 통합 검증 (로컬 + 실기기 스모크)

**Files:** 없음 (검증 전용)

- [ ] **Step 1: 백엔드 전체 테스트**

Run: `cd api && python -m pytest -q`
Expected: 전체 PASS

- [ ] **Step 2: 로컬 기동** — api + web

Run: `cd api && (uvicorn app.main:app --reload &) && cd ../web && npm run dev`
브라우저로 dev URL 접속.

- [ ] **Step 3: 실제 가민 로그인 스모크 (라이브러리 경계 검증)**

설정 → Garmin → 연결 → 실제 가민 이메일/비번 입력.
- MFA 켜진 계정이면 코드 입력 화면 → 코드 입력.
- 기대: "연결됨 · {이름}" 표시.
- **만약 `client.garth.dumps()/loads()` 또는 `return_on_mfa`에서 에러** → Task 3·4의 라이브러리 경계 헬퍼를 설치된 버전 API에 맞게 수정(파일 토큰스토어 폴백). 단위테스트는 그대로 통과해야 함.

- [ ] **Step 4: 자동채움 확인**

이번 주 탭 → 세션 기록 → "연동에서 가져오기" → 최근 가민 러닝이 뜨고, "채우기" 시 거리·페이스·심박·케이던스가 폼에 채워지는지 확인. (케이던스가 2배로 뻥튀기되지 않았는지 특히 확인.)

- [ ] **Step 5: 해제 확인**

설정 → Garmin → 해제 → `connected:false`로 돌아오는지.

- [ ] **Step 6: 배포 노트**

`main` 머지 시 기존 배포 워크플로가 `--build`로 `garminconnect`를 설치한다. 별도 시크릿/환경변수 불필요. 빌드 로그에서 `garminconnect`/`curl_cffi` 설치 성공 확인.

---

## Self-Review

**1. Spec coverage:**
- garmin 서비스(로그인·MFA·동기화·매핑) → Task 2·3·4 ✓
- DB auth_blob → Task 1 ✓
- 라우터 5개 엔드포인트 + 상태 → Task 5 ✓
- api.js → Task 6 ✓
- 설정 연결 UI → Task 7 ✓
- RecordSheet 일반화 → Task 8 ✓
- 케이던스 ×2 미적용 → Task 2 테스트로 고정 ✓
- 비밀번호 미저장(토큰만) → Task 4 설계 ✓
- 앱 열 때 동기화(cron 없음) → Task 5 `garmin_activities` 자동 sync ✓
- 운영/배포(시크릿 0) → Task 9 Step 6 ✓
- 실패 처리(미연결 404, 인증 401, 동기화 502) → Task 5 ✓
- 범위 제외(cron/공식 API/자동 log 생성/암호화) → 계획에 미포함 ✓

**2. Placeholder scan:** 모든 코드 스텝에 실제 코드 포함. 라이브러리 경계의 "버전 확인" 노트는 의도적 검증 단계(Task 9)로 구체화됨 — vague placeholder 아님.

**3. Type consistency:** `begin_login`/`complete_mfa` 반환 `{"status","blob","athlete_name","mfa_token"}` ↔ Task 5 라우터 사용 일치. `fetch_recent -> (list, blob)` ↔ `sync_activities` 사용 일치. `map_activity` 키 ↔ `ExternalActivity` 컬럼 일치. `integ.auth_blob` Task 1~5 일관.

**미해결 가정(구현 중 확인):** `conftest.py`의 `client`/`db_session` fixture 정확한 이름·시그니처는 Task 1 Step 2 / Task 5 Step 2에서 기존 파일을 grep해 맞춘다.
