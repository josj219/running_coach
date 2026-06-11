# AI 러닝 코치 웹앱

고고조 전용 AI 러닝 코치를 Streamlit 웹 인터페이스로 구현한 앱입니다.  
주간 훈련 계획부터 당일 훈련, 결과 분석, 계획 조정, 주간 평가까지 한 곳에서 관리합니다.

---

## 주요 기능

| 메뉴 | 설명 |
|------|------|
| 주간 계획 | 이번 주 일정을 입력하면 맞춤 주간 훈련 계획을 생성합니다 |
| 오늘 계획 | 당일 컨디션·날씨를 반영한 상세 훈련 계획을 제안합니다 |
| 훈련 리뷰 | 완료한 훈련 결과를 입력하고 코치 피드백을 받습니다 |
| 계획 조정 | 피로·부상·일정 변경 시 남은 주간 계획을 보수적으로 조정합니다 |
| 주간 평가 | 한 주 훈련을 종합 평가하고 다음 주 방향성을 수립합니다 |

---

## 파일 저장 구조

```
workspace/
├── 40-training-log/
│   ├── daily/          # 당일 훈련 계획 및 결과 (YYYY-MM-DD.md)
│   └── weekly/         # 주간 훈련 계획 (YYYY-WNN.md)
└── 50-outputs/         # 주간 평가 리포트
```

---

## 로컬 실행 방법

### 1. 의존성 설치

```bash
cd webapp
pip install -r requirements.txt
```

### 2. 환경변수 설정

**.env 파일 생성 (권장):**

```bash
# webapp/.env
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx
WORKSPACE_PATH=/절대경로/performance-coach
```

**또는 터미널에서 직접 설정:**

```bash
export ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx
export WORKSPACE_PATH=/절대경로/performance-coach
```

> `WORKSPACE_PATH`를 설정하지 않으면 자동으로 `webapp/../` (프로젝트 루트)를 사용합니다.

### 3. 앱 실행

```bash
# webapp/ 디렉토리에서 실행
streamlit run app.py

# 또는 프로젝트 루트에서 실행
streamlit run webapp/app.py
```

브라우저에서 `http://localhost:8501` 접속

---

## Railway 배포 방법

### Step 1: Railway 계정 및 프로젝트 준비

1. [railway.app](https://railway.app) 접속 후 로그인
2. **New Project** 클릭
3. **Deploy from GitHub repo** 선택
4. 이 저장소를 연결

### Step 2: 환경변수 설정

Railway 대시보드 → **Variables** 탭에서 아래 환경변수를 추가합니다:

| 변수명 | 값 | 설명 |
|--------|----|------|
| `ANTHROPIC_API_KEY` | `sk-ant-xxxxx` | Anthropic API 키 (필수) |
| `WORKSPACE_PATH` | `/app/workspace` | 파일 저장 경로 (Railway 권장값) |

> **주의:** `ANTHROPIC_API_KEY`가 없으면 앱이 실행되더라도 AI 기능이 동작하지 않습니다.

### Step 3: 빌드 설정 확인

Railway가 `railway.toml`을 자동으로 감지하여 Dockerfile로 빌드합니다.  
`webapp/Dockerfile`을 기준으로 빌드되도록 `dockerfilePath`가 이미 설정되어 있습니다.

### Step 4: 배포

Railway가 자동으로 빌드 및 배포를 시작합니다.  
배포 완료 후 Railway가 제공하는 URL로 접속합니다.

### Step 5: 도메인 설정 (선택)

Railway 대시보드 → **Settings** → **Networking** → **Generate Domain**으로 공개 URL을 생성합니다.

---

## 환경변수 참조

| 변수명 | 필수 여부 | 기본값 | 설명 |
|--------|----------|--------|------|
| `ANTHROPIC_API_KEY` | 필수 | 없음 | Anthropic Claude API 인증 키 |
| `WORKSPACE_PATH` | 선택 | `webapp/../` | 훈련 로그 파일 저장 루트 경로 |

---

## 기술 스택

- **프론트엔드/백엔드:** Streamlit 1.51+
- **AI:** Anthropic Claude API (claude-opus-4-5 / claude-sonnet-4-5)
- **배포:** Railway (Docker 기반)
- **데이터 저장:** 로컬 마크다운 파일

---

## 문의

이 앱은 고고조 전용으로 제작된 개인 AI 러닝 코치입니다.
