# TEAM PLAN — kkirikkiri-development-20260603-1116-3796

## 팀 목표
AI Running Coach Workspace의 5개 스킬(weekly-training-plan, daily-training-plan, workout-review, plan-adjustment, weekly-evaluation)을 Streamlit 웹앱 UI로 감싸는 MVP 구현. Railway 배포 가능하고 약간 다듬은 UI.

## 제약 조건
- 로그인 없음, Garmin/Strava API 연동 없음
- 입력: Streamlit 폼 / 출력: 마크다운 파일로 저장
- ANTHROPIC_API_KEY 환경변수 필요
- Python + Streamlit 기반
- Railway 배포 타깃

## 기존 파일 참조 (반드시 읽을 것)
- /Users/sungjae/study/AI/performance-coach/CLAUDE.md — 코칭 철학
- /Users/sungjae/study/AI/performance-coach/10-planning/PRD.md — 제품 요구사항
- /Users/sungjae/study/AI/performance-coach/20-knowledge-base/*.md — 프로필/목표
- /Users/sungjae/study/AI/performance-coach/.claude/skills/weekly-training-plan/SKILL.md
- /Users/sungjae/study/AI/performance-coach/.claude/skills/daily-training-plan/SKILL.md
- /Users/sungjae/study/AI/performance-coach/.claude/skills/workout-review/SKILL.md
- /Users/sungjae/study/AI/performance-coach/.claude/skills/plan-adjustment/SKILL.md
- /Users/sungjae/study/AI/performance-coach/.claude/skills/weekly-evaluation/SKILL.md

## 생성할 파일 목록

### 앱 코어
- /Users/sungjae/study/AI/performance-coach/webapp/app.py — 메인 앱
- /Users/sungjae/study/AI/performance-coach/webapp/pages/1_주간_계획.py
- /Users/sungjae/study/AI/performance-coach/webapp/pages/2_오늘_계획.py
- /Users/sungjae/study/AI/performance-coach/webapp/pages/3_훈련_리뷰.py
- /Users/sungjae/study/AI/performance-coach/webapp/pages/4_계획_조정.py
- /Users/sungjae/study/AI/performance-coach/webapp/pages/5_주간_평가.py
- /Users/sungjae/study/AI/performance-coach/webapp/utils/claude_client.py — Anthropic API 유틸
- /Users/sungjae/study/AI/performance-coach/webapp/utils/file_manager.py — 파일 읽기/쓰기 유틸
- /Users/sungjae/study/AI/performance-coach/webapp/utils/prompts.py — 스킬별 시스템 프롬프트

### 배포
- /Users/sungjae/study/AI/performance-coach/webapp/requirements.txt
- /Users/sungjae/study/AI/performance-coach/webapp/Dockerfile
- /Users/sungjae/study/AI/performance-coach/webapp/.streamlit/config.toml
- /Users/sungjae/study/AI/performance-coach/webapp/railway.toml

### 문서
- /Users/sungjae/study/AI/performance-coach/webapp/README.md

## 팀 역할 분배
| 역할 | 담당 |
|------|------|
| 팀장 (lead-coach-webapp) | 아키텍처 설계, 코드 리뷰, 최종 검증 |
| 풀스택 개발자 (streamlit-developer) | app.py, pages/*.py, utils/*.py 전체 구현 |
| UX/QA 검증자 (ux-qa-reviewer) | 첫 화면 UX, 모바일, 배포 체크리스트 |
| 문서 작성자 (docs-writer) | requirements.txt, Dockerfile, railway.toml, README.md |

## 아키텍처 설계 원칙
1. 각 페이지는 대응하는 SKILL.md의 입력/출력 구조를 따른다
2. Claude API 호출 시 CLAUDE.md 코칭 철학을 시스템 프롬프트에 포함
3. 파일 I/O는 기존 40-training-log/ 구조를 그대로 사용
4. BASE_DIR은 환경변수 또는 webapp/../ 으로 설정 (프로젝트 루트)
