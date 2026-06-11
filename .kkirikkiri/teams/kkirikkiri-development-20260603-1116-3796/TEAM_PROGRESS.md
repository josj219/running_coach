# TEAM PROGRESS

## 현재 단계
- [x] 기존 파일 읽기 (CLAUDE.md, PRD.md, SKILL.md 5개)
- [x] 아키텍처 설계 확정
- [x] webapp/ 디렉토리 구조 생성
- [x] utils/ 구현 (claude_client.py, file_manager.py, prompts.py, page_common.py)
- [x] app.py 구현 (홈 화면)
- [x] pages/1_주간_계획.py 구현
- [x] pages/2_오늘_계획.py 구현
- [x] pages/3_훈련_리뷰.py 구현
- [x] pages/4_계획_조정.py 구현
- [x] pages/5_주간_평가.py 구현
- [x] requirements.txt + Dockerfile + railway.toml (docs-writer)
- [x] README.md (docs-writer)
- [x] UX/QA 검수 (QA_CHECKLIST.md 작성, BLOCKER 2개 확인 → 코드에서 이미 처리됨)
- [x] 최종 검증 (py_compile ALL PASS, HTTP 200 확인, Dockerfile 경로 버그 수정)

## 진행 로그
- [streamlit-developer] utils 4종 구현 완료 (file_manager / claude_client / prompts / page_common)
  - BASE_DIR: WORKSPACE_PATH 환경변수 또는 webapp 부모(프로젝트 루트)
  - 모델 claude-sonnet-4-6, max_tokens 4096, vision(이미지) 지원
  - 시스템 프롬프트 = CLAUDE.md 원문 + 스킬별 프롬프트 결합
- [streamlit-developer] app.py(홈) + pages 5종 구현 완료
  - 각 페이지가 대응 SKILL.md 입력/출력 구조를 폼으로 변환
  - 파일 저장 경로: 40-training-log/weekly/YYYY-WNN_plan.md, weekly/..._evaluation.md, daily/YYYY-MM-DD.md
- [streamlit-developer] 검증: 전체 py_compile 통과 / file_manager 실데이터 스모크 테스트 통과
  (2026-W23_plan.md 오늘 세션 추출 정상) / streamlit run 부팅 HTTP 200 확인
- [streamlit-developer] .streamlit/config.toml의 enableCORS=false 라인 제거
  (enableXsrfProtection=true와 충돌 경고 해소)
