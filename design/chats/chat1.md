# 러닝 퍼포먼스 코치

_Started 2026-06-05 14:06 UTC_

---

## User

러닝 퍼포먼스 코치 어플이야. 

주의 첫 시작에는 지난 주 훈련 데이터를 확인한 후에 주간 훈련을 만들어주고, 주간 훈련표가 만들어 지고 나면 해당 주차에는 각 일별 훈련 상세 추천해줘. 그래서 훈련표를 보면 내가 상세하게 훈련할 내용을 알려주고, 내가 훈련을 끝마치고 나면 내가 훈련 결과와 느낀점 (운동 기록에 대한 가민 데이터 또는 스트라바 캡처사진 - 추후 api연동) 을 기록하면 해당 훈련에 대한 평가를 해주고 주간 계획을 (수정이 필요하다면) 조정하거나 하는 어플이야. 주간 훈련 결과도 나타나고. 

기존에 구상한 흐름은 아래와 같아 그런데 전체적으로 해당 흐름을 따라갈 필요 없고 기존 구상한 것보다 더 직관적으로 디자인 해줘.



*상태별 화면 정의
S0 — 주간 계획 없음 NO_PLAN

[Hero] 이번 주 계획이 없어요
       서브: D-{N}일 남았어요

[컨텍스트] 지난 주 거리/수행률 (있으면)
CTA	타입	액션
이번 주 계획 세우기 →	Primary	이번 주 탭 > 계획 폼으로 이동
S1 — 훈련 전 PRE_WORKOUT

[Hero] 오늘: {훈련 종류} — {예상 시간}

[직전 유사 훈련 카드] (접힌 상태)
[오전 9시+ 배너] "방금 뛰고 오셨나요?" (V2 추가 예정)
CTA	타입	액션
오늘 훈련 계획 보기 →	Primary	AI 당일 계획 생성
다녀왔어요 (기록 입력)	Secondary	S2 진입
계획 조정이 필요해요	Ghost	AI 계획 조정 생성
휴식일 Variant:


[Hero] 오늘은 쉬는 날이에요 / 이번 주 N km
CTA	타입
주간 계획 보기	Ghost
S2 — 훈련 수행 후 POST_WORKOUT

[Hero] 수고했어요 💪 / 기록을 남기면 다음 훈련이 더 정확해져요.

[기록 폼]
  거리(km) / 시간(분) / 페이스(/km)
  평균심박 / 최대심박 / 케이던스
  📸 Garmin/Strava 이미지 업로드
  몸 상태 라디오 (😰 / 😐 / 😊 / 💪)
  불편한 곳 체크박스 → 부위 + 슬라이더(1~10)
  한 줄 소감 텍스트
CTA	타입	액션
기록 저장하기 →	Primary	AI 리뷰 생성 + daily log 저장 + sync
저장 시 자동 실행 (sync.py):


save_daily_log()
    └── sync_after_save()
            ├── weekly plan 훈련 기록 표 해당 날짜 행 기입
            ├── 04_CURRENT_STATUS.md 덮어쓰기
            ├── 05_INJURY_HISTORY.md 행 추가 (통증 > 0)
            └── 03_RUNNING_HISTORY.md 행 추가 (거리 > 0)
S3 — 훈련 리뷰 후 REVIEWED

[Hero] ✅ 오늘 완료 / {km}km · {페이스}/km
       회복 필요도 배지 (🔴/🟡/🟢)

[메트릭 행] 페이스 / 평균 심박 / 케이던스

[코치 분석 한줄]

[내일 예고 카드]
  [세션 상세 expander]
  [직전 유사 훈련 기록 expander]
CTA (평일)	타입	액션
코치 분석 전체 보기	Ghost	expander 오픈
계획 조정이 필요해요	Ghost	AI 계획 조정 생성
CTA (주간 종료 조건)	타입	액션
이번 주 성장 리포트 만들기 →	Primary	이번 주 탭으로 이동 안내
S4 (현재 S5) — 주간 종료 WEEK_END

[Hero 큰 수치] {week_km} km / {done_count}/{total_count} 세션

[수행률 배지] {completion_rate}%

[이번 주 방향 인용문]

[이번 주 집계 통계]
  총 거리 / 완료 회수 / 수행률

[주간 성장 리포트 생성 버튼]
[리포트 결과 expander + 저장 버튼]
CTA	타입	액션
이번 주 성장 리포트 만들기 →	Primary	AI 주간 평가 생성
다음 주 계획 세우기	Secondary	→ 이번 주 탭

## Assistant

_[tool: questions_v2]_

러닝 퍼포먼스 코치 앱이네요! 흐름을 잘 정리해주셔서 핵심은 명확합니다. iOS 26 디자인 시스템을 기반으로 만들 거예요. 본격적으로 디자인하기 전에 방향을 맞추기 위해 몇 가지 여쭤볼게요.

## User

Questions answered:
- ui_language: 한국어
- core_flow: 주간 계획 없음 → 지난 주 데이터 확인 → 주간 훈련 생성, 오늘의 훈련 상세 추천, 훈련 후 기록 입력 (페이스/심박/사진/몸상태), AI 코치 리뷰 + 계획 조정, 주간 훈련표(달력/리스트) 화면, 주간 종료 성장 리포트
- nav_model: 오늘 · 이번 주 · 기록 · 설정 (4탭)
- tone: 차분하고 데이터 중심 (애플 기본 톤)
- visual_energy: 스포티/대담 — 강한 컬러 액센트, 큰 수치 타이포
- accent_color: 1
- data_richness: + 심박·케이던스
- workout_types: 이지 런 / 회복주, 인터벌 / 스피드, 템포 / 임계주, 롱런, 휴식일, 근력/보강 운동
- dark_mode: 라이트 모드 위주
- tweaks: 코치 톤 (문구 변화), 강조 색상, 주간 진행 상태 (S0~S4 시뮬레이션), 데이터 표시 밀도
- extra: 나이키 런클럽, 가민 어플의 상세 데이터

## Assistant

_[tool: update_todos]_

좋습니다! 방향이 명확해졌어요. iOS 26 시스템 룩을 기반으로, 스포티하고 대담한 컬러·타이포를 입힌 4탭 러닝 코치 앱을 만들겠습니다. 먼저 디자인 시스템과 iPhone UI 키트를 살펴볼게요.

_[tool: list_files]_

_[tool: read_file]_

Now let me explore the iPhone UI kit and icons.

_[tool: list_files]_

_[tool: read_file]_

_[tool: read_file]_

_[tool: read_file]_

_[tool: read_file]_

Let me read the chrome (status bar / frame), tabbar, and the main index to understand the kit structure.

_[tool: read_file]_

_[tool: read_file]_

Let me read controls and list to grab reusable primitives, then I'll have all I need.

_[tool: copy_files]_

_[tool: copy_starter_component]_

I have everything I need. Let me set up the project: copy the design system base files and the tweaks panel starter.

_[tool: str_replace_edit]_

Now let me extend the icon set with running-specific glyphs (Lucide paths matching the SF Symbols substitution).

_[tool: write_file]_

Now the data layer — workout types, weekly plan, last-week data, daily detail, coach-tone copy, and the state model. Let me write it.

_[tool: write_file]_

Now a shared "sporty" UI layer — big-number metrics, workout badges, glass hero cards, charts, recovery badges.

_[tool: write_file]_

Now the centerpiece — the **오늘 (Today)** tab with all four lifecycle states (S0/S1/S3/S4).

## User

하던거 마무리해줘

## Assistant

_[tool: update_todos]_

_[tool: write_file]_

이번 주 탭부터 이어갑니다.

_[tool: write_file]_

기록 입력 폼 + AI 리뷰 시트를 씁니다.

_[tool: write_file]_

기록 탭과 설정 탭을 씁니다.

_[tool: write_file]_

설정 탭, 그 다음 앱 루트, 마지막으로 HTML 진입점 순서로 씁니다.

_[tool: write_file]_

app.jsx를 씁니다.

_[tool: write_file]_

마지막으로 메인 HTML 진입점을 씁니다.

_[tool: done]_

_[tool: save_screenshot]_

_[tool: multi_screenshot]_

좋아 보입니다. 나머지 탭들도 확인해볼게요.

_[tool: multi_screenshot]_

모든 탭이 깔끔하게 렌더링됩니다. 나머지 상태들도 트위크 패널로 확인합니다.

_[tool: update_todos]_

localStorage 조작은 같은 탭에서 storage 이벤트를 발생시키지 않아서 전환이 안 됩니다 — 트위크 패널 UI로 직접 조작하면 됩니다. 앱 자체는 모든 탭이 잘 동작하고 있어요.

_[tool: fork_verifier_agent]_

프로토타입 완성입니다! 구현 내용을 정리할게요:

---

## 러닝 퍼포먼스 코치 — 완성

**구현된 화면**

| 탭 | 내용 |
|---|---|
| **오늘** | S0(무계획) / S1(훈련 전, AI 설계) / S3(리뷰 완료) / S4(주간 종료) 4가지 상태 |
| **이번 주** | 7일 훈련표 + 수행률 링 + 세션 상세 시트 + AI 계획 생성 로딩 + 성장 리포트 |
| **기록** | 최근 러닝 카드 + 4주 트렌드 바 + 주간 통계 토글 |
| **설정** | 러너 프로필 + 훈련 설정 + 데이터 연동(예정) |
| **기록 입력** | 거리/시간/심박/케이던스/사진/몸 상태/통증 부위 슬라이더 + AI 리뷰 |

**트위크 패널** (우측 상단 슬라이더 버튼)
- `주간 상태` → S0 / S1 / S3 / S4 시뮬레이션
- `코치 톤` → calm / warm / strict (문구 변화)
- `강조 색상` → 5가지 색상 스와치
- `데이터 밀도` → core / full

---

**다음 단계로 고려할 것들**
- 가민/스트라바 API 실제 연동 시 사진 업로드 플로우 교체
- 주간 계획 폼 (목표 거리, 레이스 거리, 부상 여부 입력 → AI 프롬프트 구성)
- 온보딩 (첫 실행 시 러너 프로필 설정)
- HR 존 색상 시각화 (Zone 1–5 구간 표시)
- 페이스 트렌드 라인 차트 (기록 탭 확장)

## User

Verifier agent check completed

## Assistant

검증 통과입니다! 모든 탭, 트위크 패널, 기록 시트가 정상 동작 확인되었어요.

수정이 필요한 부분이나 추가하고 싶은 기능이 있으면 알려주세요.

