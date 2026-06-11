# Running Coach Workspace PRD

## Project Overview

### Project Name
Running Coach Workspace

### Vision

사용자의 일정, 컨디션, 훈련 이력, 성장 데이터, 날씨를 종합적으로 고려하여 지속적으로 학습하고 개선하는 개인 전용 AI 러닝 코치를 구축한다.

본 시스템은 단순 운동 계획 생성기가 아닌, 사용자의 러닝 데이터를 장기적으로 관리하고 성장을 추적하며 최적의 훈련 방향을 제시하는 AI 코치 역할을 수행한다.

---

# Problem Statement

일반적인 러닝 앱 또는 AI는 다음과 같은 한계를 가진다.

- 사용자의 실제 생활 일정을 반영하지 못한다.
- 이전 훈련 결과를 충분히 기억하지 못한다.
- 장기적인 성장 흐름을 추적하지 못한다.
- 컨디션 변화에 따라 훈련을 조정하지 못한다.
- 날씨나 외부 환경을 고려하지 못한다.
- 매번 새로운 대화처럼 동작한다.

본 프로젝트는 위 문제를 해결하는 것을 목표로 한다.

---

# User

## Primary User

조성재

## User Characteristics

- 러닝 성과 향상에 관심이 높음
- 데이터 기반 피드백을 선호함
- 운동 기록을 지속적으로 관리하고 싶어함
- 일정 변화가 자주 발생함
- 장기적인 성장 추적을 중요하게 생각함

---

# Product Goal

## Goal 1

사용 가능한 시간 내에서 가장 효율적인 주간 훈련 계획 생성

## Goal 2

훈련 결과를 분석하여 즉각적인 피드백 제공

## Goal 3

사용자의 장기 성장 추세 추적

## Goal 4

컨디션 및 외부 환경을 반영한 훈련 계획 최적화

## Goal 5

러닝 관련 모든 데이터를 장기적으로 보존 및 활용

---

# Core Principles

## The Coach Must

AI 코치는 반드시 다음 정보를 기억하고 활용해야 한다.

- 사용자 프로필
- 현재 목표
- 러닝 이력
- 주간 훈련 계획
- 주간 훈련 결과
- 장기 성장 추세
- 부상 이력
- 주중 일정
- 날씨 정보

---

## The Coach Must Not

AI 코치는 다음 행동을 해서는 안 된다.

- 목표를 잊는다.
- 이전 훈련 데이터를 무시한다.
- 일정 충돌을 무시한다.
- 근거 없이 훈련 강도를 제안한다.
- 사용자의 현재 컨디션을 무시한다.
- 성장보다 단기 성과를 우선시한다.

---

# Coaching Workflow

## Phase 1. Weekly Planning

### Input

- 이번 주 일정
- 운동 불가 시간
- 현재 컨디션
- 목표
- 최근 훈련 기록

### Output

- 주간 훈련 계획
- 훈련 유형
- 훈련 요일
- 예상 강도
- 주간 목표

---

## Phase 2. Weekly Plan Validation

주간 계획 공유 후 실제 수행 가능 여부를 재확인한다.

### Validation Items

- 일정 충돌 여부
- 훈련 강도 적절성
- 회복 가능 여부

---

## Phase 3. Daily Coaching

당일 훈련 전에 상세 훈련 계획을 생성한다.

### Input

- 주간 계획
- 당일 일정
- 당일 컨디션
- 날씨

### Output

- 훈련 종류
- 거리
- 시간
- 목표 페이스
- 목표 심박
- 목표 케이던스
- 추천 코스
- 워밍업
- 쿨다운

---

## Phase 4. Workout Review

훈련 완료 후 결과를 분석한다.

### Input

- 훈련 기록
- 사용자 소감
- 러닝 데이터

### Output

- 잘된 점
- 개선 포인트
- 성장 분석
- 피로도 평가
- 다음 훈련 권장사항

---

## Phase 5. Adaptive Adjustment

전일 결과와 당일 컨디션을 반영하여 훈련 계획을 미세 조정한다.

### Adjustment Scope

- 훈련 강도
- 거리
- 시간
- 회복 훈련 전환
- 휴식일 변경

주간 계획의 큰 틀은 유지하되 필요 시 주간 계획 자체를 수정할 수 있다.

---

# Required Data Sources

## User Profile

- 나이
- 키
- 체중
- 러닝 경력
- 부상 이력

---

## Running Goals

- 현재 목표
- 목표 기록
- 목표 일정

---

## Weekly Schedule

- 업무 일정
- 개인 일정
- 운동 가능 시간

---

## Training History

- 날짜
- 훈련 종류
- 거리
- 시간
- 페이스
- 심박
- 케이던스
- 보폭
- 고도
- 주관적 피로도

---

## Weather Data

- 기온
- 강수 여부
- 습도
- 풍속

---

# Outputs

## Before Workout

### Weekly Plan

- 주간 계획
- 주간 목표
- 예상 훈련 강도

### Daily Training Plan

- 거리
- 시간
- 페이스
- 심박
- 케이던스
- 추천 코스
- 주의사항

---

## After Workout

### Workout Feedback

- 훈련 평가
- 강점
- 약점
- 개선 포인트

### Growth Analysis

- 최근 성장 추세
- 목표 대비 진행률
- 향후 예상 성장 방향

### Next Action

- 다음 훈련 추천
- 회복 가이드
- 주간 계획 수정 사항

---

# Success Metrics

## Coaching Quality

- 일정 충돌 없는 훈련 계획 비율
- 훈련 수행률
- 주간 목표 달성률

## Running Performance

- 페이스 향상
- 심박 효율 향상
- 거리 증가
- 부상 발생 감소

## User Experience

- 계획 신뢰도
- 피드백 만족도
- 장기 사용 지속률

---

# Future Scope

향후 추가 기능

- Garmin 연동
- Strava 연동
- 자동 날씨 조회
- 러닝 코스 추천 엔진
- 레이스 목표 관리
- 부상 위험 예측
- AI 기반 시즌 훈련 계획 생성
- 주간/월간 성장 리포트 자동 생성