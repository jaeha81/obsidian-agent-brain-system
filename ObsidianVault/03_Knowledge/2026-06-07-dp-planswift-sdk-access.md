---
title: PlanSwift SDK 접근과 다음 판단
date: 2026-06-07
source: daily-plus/2026-06-07.md (Card 1)
priority: P3
category: knowledge
status: distilled
tags:
- planswift
- sdk
- automation
- takeoff
- api
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# PlanSwift SDK 접근과 다음 판단

> ChatGPT Pulse 2026-06-07 Card 1 증류 (P3 · knowledge-candidate)

## 목적

PlanSwift 자동화 확장 가능성과 현실적인 접근 경로를 파악하고, CSV 우선 파이프라인 전략 채택 여부를 결정한다.

## PlanSwift 현재 상태

- PlanSwift는 전통적인 공개 SDK를 제공하지 않음
- 플러그인 확장 방식이 존재하나 공급업체 승인 필요
- "Takeoff AI" 기능을 통한 AI 연동 확장 가능성이 열려 있음
- API 직접 접근은 현재 공식 지원되지 않음

## SDK 접근 가능 경로

| 경로 | 조건 | 난이도 |
|------|------|--------|
| 공식 플러그인 SDK | 공급업체 파트너십 필요 | 높음 |
| Takeoff AI 연동 | 베타 접근 신청 가능 | 중간 |
| CSV 내보내기 활용 | 즉시 사용 가능 | 낮음 |
| 스크린 스크래핑 | 비공식, 불안정 | 높음 |

## CSV 파이프라인 우선 전략

공식 SDK 접근 대기 중에는 CSV 내보내기를 기반으로 한 파이프라인이 가장 실용적이다:

1. PlanSwift에서 CSV 내보내기
2. 표준 스키마로 정규화 (→ `estimator-csv-standardization-kit`)
3. Google Sheets 또는 ERP로 적재
4. 자동화 레이어 추가

## 다음 판단 기준

- [ ] Takeoff AI 파트너 프로그램 지원 여부 확인
- [ ] CSV 파이프라인 3개월 운영 후 SDK 필요성 재평가
- [ ] PlanSwift 계약 고객 기반 10개 이상이면 공식 파트너십 추진

## 관련 컨텍스트

- [[estimator-csv-standardization-kit]]
- [[cad-estimate-poc-path]]
- APS/ODA 대안과 병행 검토 권장
