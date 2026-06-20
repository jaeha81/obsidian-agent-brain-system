---
title: One-Page Demo and Onboarding Design
date: 2026-06-11
source: daily-plus/2026-06-10.md (Card 7)
priority: P3
category: knowledge
status: distilled
tags:
- demo
- onboarding
- voice-pipeline
- toss-payments
- stt
- daily-plus
- knowledge
- source/today_plus
- type/reference
graph_cluster: daily-practice
---

# One-Page Demo and Onboarding Design

> ChatGPT Pulse 2026-06-10 Card 7 증류 (P3 · voice-pipeline)

## 목적

JH AI 시스템의 핵심 기능을 한 페이지에서 보여주는 데모 + 신규 사용자 온보딩 플로우 설계.

## 데모 구성 요소 (3개 핵심 모듈)

### 1. PlanSwift CSV 내보내기 데모
- Excel/CSV 직접 내보내기 시연
- 커뮤니티 플러그인 활용 방법
- 파이프라인: DXF → CSV → Estimator

### 2. Toss Payments 샌드박스 데모
```
test_sk_* 키 사용 → 실제 금액 차감 없음
결제 플로우 테스트 가능
```
- 결제 버튼 클릭 → 샌드박스 처리 → 완료 확인
- 실제 배포 전 전체 플로우 검증

### 3. STT 옵션 선택 데모
| 옵션 | 특징 |
|-----|-----|
| VOSK (온디바이스, ~50MB) | 오프라인, 개인정보 보호 |
| Whisper (오픈소스, 다국어) | 높은 정확도 |
| CLOVA Speech (클라우드 API) | 한국어 특화 |

## 온보딩 플로우

```
1. 랜딩 페이지 (시스템 소개 30초)
   ↓
2. SKU 선택 (Beginner/Intermediate/Advanced)
   ↓
3. 설치 가이드 (원클릭 설치)
   ↓
4. 샘플 데이터로 첫 실행
   ↓
5. 대시보드 확인
```

## 원 페이지 레이아웃

```
[Hero: 핵심 가치 1줄]
[Feature 1] [Feature 2] [Feature 3]
[Demo 실행 버튼]
[빠른 시작 3단계]
[FAQ]
```

## 구현 우선순위

- [ ] Toss Payments 샌드박스 연동 테스트
- [ ] VOSK 빠른 데모 환경
- [ ] 온보딩 체크리스트 UI

## 관련 컨텍스트

- [[JH AI SKU Blueprint]] 패키지 연동
- [[jh-ai-sku-blueprint]] 스타터 키트 기반
