---
title: 구매대행 대시보드 핵심 점검
date: 2026-06-05
source: daily-plus/2026-06-05.md (Card 12)
priority: P1
category: knowledge
status: distilled
tags:
- sniper-dashboard
- audit
- data-freshness
- cs
- supplier
- daily-plus
- knowledge
- source/today_plus
- type/reference
graph_cluster: daily-practice
---

# 구매대행 대시보드 핵심 점검

> ChatGPT Pulse 2026-06-05 Card 12 증류 (P1 · knowledge-candidate)

## 목적

sniper-buying-dashboard 개선을 위한 초경량 감사 결과. 데이터 신선도, 구매 실패 대응, 정산/조정 UI 3축을 잡으면 CS가 줄고 공급처 신뢰도 향상.

## 3축 점검 항목

### 축 1 — 데이터 신선도 (Data Freshness)

현재 대시보드의 데이터 갱신 주기와 실시간성 점검:

| 항목 | 현재 상태 | 목표 |
|-----|---------|-----|
| 재고 정보 갱신 | 수동/일 1회 | 1시간 자동 갱신 |
| 가격 변동 반영 | 지연 | 실시간 or 30분 |
| 주문 상태 동기화 | 수동 확인 | 웹훅 자동 수신 |
| 배송 추적 | 링크만 제공 | 인라인 상태 표시 |

**즉시 적용 가능**:
- `Last updated: 00분 전` 타임스탬프 표시
- 30분 이상 미갱신 시 경고 배지 표시

### 축 2 — 구매 실패 대응 (Purchase Failure)

| 실패 유형 | 현재 처리 | 개선안 |
|---------|---------|------|
| 재고 소진 | 수동 CS | 자동 대체 상품 제안 |
| 가격 초과 | 수동 확인 | 임계값 설정 + 자동 알림 |
| 배송 지연 | 고객 문의 | 예상 지연 사전 알림 |
| 공급처 오류 | 미파악 | 오류 분류 + 대응 매뉴얼 |

### 축 3 — 정산/조정 UI (Settlement)

- 수수료 계산 투명성 (공급가 vs 판매가 diff 표시)
- 반품/환불 조정 이력
- 공급처별 정산 현황 요약

## KPI 임계값

| KPI | 경보 기준 | 위험 기준 |
|-----|---------|---------|
| CS 문의 비율 | > 3% | > 7% |
| 구매 실패율 | > 2% | > 5% |
| 데이터 갱신 지연 | > 60분 | > 3시간 |
| 정산 오류 건수 | > 1건/주 | > 3건/주 |

## 즉시 적용 체크리스트

단기 (1~2일 내 적용 가능):
- [ ] 데이터 갱신 타임스탬프 표시 추가
- [ ] 재고 부족 항목 빨간색 하이라이트
- [ ] 구매 실패 건 필터링 뷰 추가

중기 (1주 내):
- [ ] 자동 갱신 폴링 또는 웹훅 연동
- [ ] 공급처별 오류율 집계 차트
- [ ] 정산 조정 이력 페이지

## 관련 컨텍스트

- sniper-buying-dashboard: Vercel 배포 완료 (T014)
- [[sniper-buying-dashboard]], [[stripe-webhook-metadata]]
