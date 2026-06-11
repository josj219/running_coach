---
name: weekly-evaluation
description: This skill should be used when the user asks to "이번 주 어땠어", "주간 평가 해줘", "weekly evaluation", "이번 주 정리해줘", "주간 리포트", "이번 주 얼마나 달렸어", "성장하고 있어", "이번 주 총정리". 하루 단위 기록(daily log, workout-review, 훈련 기록 표)을 집계해 주 단위 성장 분석 리포트를 생성하고 knowledge-base를 업데이트한다 — 일별 훈련을 성장 곡선으로 전환해 다음 주 계획의 근거를 만들기 위해. Use this skill whenever the user wants a weekly summary or asks about their progress.
---

# /weekly-evaluation — 주간 훈련 평가

> 이번 주 기록을 집계하고 성장 추세를 분석한다. 집계기가 아닌 코치 판단을 출력한다.

---

## 핵심 원칙

- 새로운 코칭 철학을 만들지 않는다. 기존 daily log, workout-review, 주간 계획 데이터를 읽어 집계한다.
- 달리기 0km인 주도 의미 있는 평가를 생성한다. 수치보다 맥락이 중요하다.
- 수정된 계획(plan-adjustment 이력)과 원계획을 구분해서 수행률을 이중 표기한다.
- 이 스킬은 knowledge-base 3개 파일(`03/04/05`)의 업데이트 책임자다.

---

## 프로젝트 경로

```
WEEKLY_LOG_DIR  = 40-training-log/weekly/
DAILY_LOG_DIR   = 40-training-log/daily/
PROFILE_FILE    = 20-knowledge-base/01_PROFILE.md
RUNNING_HISTORY = 20-knowledge-base/03_RUNNING_HISTORY.md
CURRENT_STATUS  = 20-knowledge-base/04_CURRENT_STATUS.md
INJURY_HISTORY  = 20-knowledge-base/05_INJURY_HISTORY.md
```

---

## 워크플로우

### Step 0: 실행 시점 가드 [script]

```python
import datetime
today = datetime.date.today()
iso = today.isocalendar()
# 이번 주 일요일 계산
week_end = today + datetime.timedelta(days=(6 - today.weekday()))
```

오늘이 이번 주 일요일 이전이면:

```
⚠️ 이번 주가 아직 끝나지 않았습니다. (오늘: M/D, 이번 주 종료: M/D)
남은 세션이 있으면 집계에서 제외되어 수행률이 낮게 표시됩니다.
```

AskUserQuestion으로 분기:
- **"주 종료 후 다시 실행할게요"** → 종료
- **"지금까지 기록으로 중간 평가할게요"** → 계속 진행 (출력에 "부분 평가" 표시)

이미 `YYYY-WNN_evaluation.md`가 존재하면:

```
이번 주 평가 파일이 이미 있습니다. 재평가하시겠습니까?
```

AskUserQuestion으로 분기:
- **"기존 평가 보여줘"** → 파일 내용 출력 후 종료
- **"재평가할게요"** → 계속 진행 (기존 파일 덮어쓰기)

---

### Step 1: 컨텍스트 로드 [rag]

**읽어야 할 파일:**

1. `YYYY-WNN_plan.md` 전체
   - `## 요일별 계획` 표 (계획 세션 목록, 조정 이력 여부)
   - `## 훈련 기록` 표 (✅/⚠️/❌/— 상태)
   - `## 조정 이력` 섹션 (plan-adjustment 실행 이력, 없으면 건너뜀)

2. 이번 주 daily log 파일 (날짜 범위 필터 필수)
   - **범위**: 이번 주 월요일 ~ 오늘(또는 일요일)의 `YYYY-MM-DD.md`만 읽는다
   - 각 파일에서 추출: 거리(km), 시간(분), 페이스, 평균심박, 최대심박, 케이던스, 피로도, 통증
   - `## 훈련 리뷰` 섹션 있으면: 회복 필요도(🔴/🟡/🟢), 코칭 피드백 요약도 추출

3. 최근 3주치 `YYYY-WNN_plan.md` (성장 추세용)
   - `## 훈련 기록` 표의 ✅/⚠️/❌ 집계치만 파싱

4. `PROFILE_FILE` — 부상 이력, 목표, 현재 PB 확인

---

### Step 2: 집계 계산 [script]

**수행률 계산:**

```
✅ 완료       = 1.0점
⚠️ 부분 완료 = 0.5점
❌ 미수행     = 0.0점
— (미완료)   = 오늘 이전 날짜면 ❌ 처리, 오늘 이후면 제외
```

- **원계획 수행률** = (완료 합산점 / 원래 계획 세션 수) × 100
- **조정 후 수행률** = (완료 합산점 / 조정 후 계획 세션 수) × 100
- plan-adjustment 이력이 없으면 단일 수행률만 표시

**거리 집계:**
daily log에서 아래 순서로 거리 추출:
1. `## 훈련 내용`의 "거리: N km" 패턴
2. `## 분석`의 계획 vs 실제 표 "실제" 컬럼
3. `## 훈련 리뷰`의 계획 대비 수행 표

수치 없는 세션은 `km = 0`으로 처리, 세션 수 카운트에는 포함.

**최근 4주 추세 테이블:**
```
| 주차 | 총 거리 | 세션 수 | 수행률 | 비고 |
|------|---------|---------|--------|------|
| W20  | 30km    | 4/4     | 100%   | 정상 |
| W21  | 28km    | 4/5     | 80%    | 야근 1회 |
| W22  | 0km     | 0/0     | —      | 안와골절 휴식 |
| W23  | ?km     | ?       | ?%     | 이번 주 |
```

---

### Step 3: 주간 평가 리포트 생성 [generate]

**출력 형식 (대화창 — 간결 버전):**

```
## 이번 주 요약 — W23 (6/1 ~ 6/7)

### 핵심 수치
| 항목 | 이번 주 |
|------|---------|
| 총 거리 | N km |
| 총 세션 | N회 완료 / N회 계획 |
| 수행률 | N% (원계획) / N% (조정 후) |
| 총 훈련 시간 | N분 |

### 최근 4주 성장 추세
{Step 2의 추세 테이블}

### 코치 판단
- **이번 주 총평**: {데이터 기반 한 줄 — 성장/유지/후퇴 판단}
- **잘한 점**: ...
- **개선할 점**: ...
- **다음 주 방향**: {구체적인 한 줄 — "/weekly-plan 실행 시 이것을 고려할 것"}

### 회복/부상 신호
{이번 주 통증 기록 요약, 없으면 "이상 없음"}

### sub 3:30 목표 진척도
- 남은 기간: N주 / 현재 추정 준비도: {상/중/하 + 근거 한 줄}
```

**달리기 0km 주 특별 처리:**
수치 집계 대신 "왜 이 주가 필요했는가 + 목표 타임라인에서의 위치"를 코치 판단으로 설명한다.

---

### Step 4: 사용자 확인 [review]

AskUserQuestion:
```json
{
  "questions": [{
    "question": "주간 평가를 저장할까요?",
    "header": "저장",
    "options": [
      {"label": "저장 (추천)", "description": "evaluation.md 생성 + plan.md 업데이트 + knowledge-base 갱신"},
      {"label": "저장 안 함", "description": "평가 결과는 대화에만 남깁니다."}
    ],
    "multiSelect": false
  }]
}
```

---

### Step 5: 파일 저장 및 knowledge-base 업데이트 [script]

저장 위치 3곳. 순서대로 실행.

**1. `YYYY-WNN_evaluation.md` 신규 생성:**

```markdown
# 주간 훈련 평가 — YYYY년 NN주차 (M/D ~ M/D)

## 훈련 요약
{Step 3 핵심 수치 표}

## 성장 추세
{최근 4주 추세 테이블}

## 코치 판단
{잘한 점 / 개선할 점 / 다음 주 방향}

## 회복/부상 신호
{통증 기록 요약}

## 평가 메타
- 평가 시점: YYYY-MM-DD
- 수행률 기준: 원계획 N세션 / 조정 후 N세션
- 부분 평가 여부: 예/아니오
```

**2. `YYYY-WNN_plan.md`의 `## 주간 평가` 섹션 채우기:**

`_미작성_`을 평가 요약으로 교체. Edit 도구 사용.

**3. `03_RUNNING_HISTORY.md` append:**

중복 방지: 해당 주차(`W23:`) 키워드가 이미 있으면 스킵.

```markdown
| W23 | 0km | 1/4세션 | 25%(원)/100%(조정) | 복귀 준비 주, 교정 드릴 집중 |
```

파일 내 활성 데이터가 8주를 초과하면: "오래된 기록은 아카이브하고 최근 8주만 유지하시겠습니까?" 안내.

**4. `04_CURRENT_STATUS.md` overwrite:**

```markdown
# 현재 상태 — YYYY-MM-DD 기준

## 체력 수준
{이번 주 수치 기반 추정}

## 최근 페이스 추이
{최근 3-4주 평균 페이스 변화}

## 피로/회복 상태
{이번 주 피로도 평균 + 회복 필요도}

## sub 3:30 준비도
{N주 남음 / 현재 위치 / 조정 필요 사항}
```

**5. `05_INJURY_HISTORY.md` append (통증 신호 있을 때만):**

이번 주 1/10 이상 통증 기록이 있으면:
```markdown
- W23 (2026-06-01~07): {부위} / 수준 {N}/10 / {발생 맥락} / 상태: {지속/해소}
```

저장 완료 후: "📅 이번 주 평가 완료. `/weekly-plan`으로 다음 주 계획을 수립하세요." 안내.

---

## 폴백 처리

| 상황 | 처리 |
|------|------|
| 주간 계획 파일 없음 | daily log만으로 집계, "계획 없음" 명시 |
| daily log 전부 없음 | plan.md 훈련 기록 표만으로 집계, 수치 N/A |
| 달리기 0km 주 | 비러닝 세션 수/종류로 대체 집계, 맥락 해석 필수 |
| 최근 4주 이력 부족 | 있는 주차만으로 추세 표 작성 |
| knowledge-base 파일 없음 | 파일 신규 생성 후 기록 |
