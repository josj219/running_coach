# 팀 작업 계획

- 팀명: kkirikkiri-analysis-20260606-1432-6cdc
- 목표: AI 러닝 코치 Streamlit 앱 전체 점검 — 구조/아키텍처·코드 품질·사용성/UX 3개 관점의 이슈 리포트
- 생성 시각: 2026-06-06T14:32

## 팀 구성
| 이름 | 역할 | archetype | 모델 | 담당 업무 |
|------|------|-----------|------|----------|
| analysis-lead | 팀장 | Leader | Opus | 탐색 계획 수립, 역할 배분, 결과 통합, 리포트 작성 |
| structure-explorer | 구조 분석가 | Analyst | Opus | 파일 구조·모듈 의존성·스킬-워크플로우-webapp 연결 상태 |
| code-reviewer | 코드 리뷰어 | Critic | Opus | 코드 품질·중복·버그 가능성·패턴 일관성·보안 |
| ux-auditor | UX 검증자 | Designer | Opus | Streamlit UI 흐름·디자인 체계 일관성·사용성 |

## 탐색 대상
- webapp/app.py — 메인 Streamlit 앱
- webapp/utils/ — 유틸리티 모듈 (file_manager, page_common, sync 등)
- .claude/agents/ 및 스킬 파일들 (있으면)
- 40-training-log/, 20-knowledge-base/ — 데이터 구조
- CLAUDE.md — 코치 정체성/워크플로우
- 40-training-log/weekly/ 주간 계획 파일들
- webapp/requirements.txt

## 태스크 목록
- [ ] 태스크 1: 전체 파일 구조 + 모듈 의존성 맵핑 → structure-explorer
- [ ] 태스크 2: 코드 품질 점검 (app.py + utils/) → code-reviewer
- [ ] 태스크 3: UX/UI 흐름 + 디자인 체계 점검 → ux-auditor
- [ ] 태스크 4: 결과 통합 + 이슈 리포트 생성 → analysis-lead

## 주요 결정사항
- 분석 범위: webapp 전체 + 데이터 구조 + 스킬/워크플로우
- 결과물: 중요도 순 이슈 리포트 (구조/코드/UX 파트 각각)
- 외부 CLI 없음 → 전원 Claude Opus
