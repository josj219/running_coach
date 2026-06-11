# TEAM FINDINGS

## 발견 사항

### [ux-qa-reviewer] 2026-06-03 — 배포 파일 및 QA 체크리스트 완료

**완료 파일:**
- `webapp/requirements.txt` — streamlit>=1.51.0, anthropic>=0.40.0, python-dateutil, Pillow 포함
- `webapp/Dockerfile` — python:3.11-slim 베이스, /app/workspace 자동 생성, HEALTHCHECK 포함
- `webapp/.streamlit/config.toml` — 오렌지/블루 테마(primaryColor: #FF6B35), maxUploadSize=10, CORS/XSRF 설정
- `webapp/railway.toml` — DOCKERFILE 빌더, `webapp/Dockerfile` 경로, healthcheck 설정
- `webapp/README.md` — 한국어 앱 소개, 로컬 실행, 환경변수, Railway 배포 Step-by-Step, 기능 설명, 파일 저장 구조
- `.kkirikkiri/teams/.../QA_CHECKLIST.md` — 9개 섹션, 5개 스킬 각각 체크리스트, 배포 전 BLOCKER 항목 포함

**주요 결정 사항:**
- Railway 환경에서 `WORKSPACE_PATH=/app/workspace` 권장 (README 및 Dockerfile에 명시)
- Railway 재시작 시 `/app/workspace` 파일 초기화 문제는 현재 MVP에서 허용으로 결정 — QA 체크리스트에 MINOR 이슈로 기록
- `railway.toml`의 `dockerfilePath`는 `webapp/Dockerfile`로 설정 (프로젝트 루트 기준 상대경로)
- 배포 전 BLOCKER: API 키 미설정 크래시 방지, 파일 저장 경로 환경변수 참조 검증

## DEAD_ENDS (하지 말 것)
- 로그인 기능 구현하지 말 것 (요구사항에 없음)
- Garmin/Strava API 직접 연동하지 말 것
- SKILL.md 로직을 재설계하지 말 것 — 기존 입력/출력 구조 그대로 따를 것
- 파일 저장 경로를 임의로 바꾸지 말 것 — 기존 40-training-log/ 구조 유지

## 환경 정보
- Streamlit 1.51.0 설치됨
- Python 3.13.9
- pip 사용
- Railway 배포 타깃
