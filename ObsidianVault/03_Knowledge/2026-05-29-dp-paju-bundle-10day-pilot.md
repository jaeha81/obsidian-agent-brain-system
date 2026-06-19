---
title: 파주권 번들 10일 파일럿
date: 2026-05-29
source: daily-plus/2026-05-29.md (Card 11)
priority: P1
category: knowledge
status: distilled
tags:
- upsell
- pilot
- revenue
- payment
- pazhou
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 파주권 번들 10일 파일럿

> ChatGPT Pulse 2026-05-29 Card 11 증류 (P1 · knowledge)

## 목적
메인 결제 흐름을 건드리지 않고 결제 완료 화면+주문 확인 메일에서만 추가 구매를 받는 10일 파일럿. 파주/수도권 구매자 대상, 200건 또는 10일 기준. 기존 결제 안정성을 유지하면서 업셀을 통한 추가 수익을 검증하는 최소 실험.

## 핵심 내용
- **업셀 부착 위치**:
  1. 결제 완료 화면 하단 (주문 감사 메시지 아래)
  2. 주문 확인 이메일 내 추가 섹션
  - 메인 결제 UI는 절대 변경하지 않음
- **파일럿 대상 조건**:
  - 파주/고양/수도권 배송지 구매자
  - 기간: 10일 또는 200건 도달 시 종료
- **성공 기준**:
  - 업셀 전환율 목표: 5% 이상
  - 추가 마진: 건당 최소 5,000원
  - 결제 에러율: 0% (기존 대비 증가 없음)
- **롤백 조건**:
  - 결제 에러율 0.1% 이상 증가
  - 메인 전환율 1% 이상 하락
  - 고객 불만 3건 이상
- **업셀 상품 예시**: 파주 지역 추가 서비스, 빠른 배송, 패키지 확장

## 구현 체크리스트
- [ ] 결제 완료 화면에 업셀 컴포넌트 추가 (별도 feature flag)
- [ ] 주문 확인 이메일 템플릿 업셀 섹션 추가
- [ ] 파주/수도권 배송지 필터 로직 구현
- [ ] 파일럿 종료 조건 모니터링 (200건 카운터, 10일 타이머)
- [ ] 롤백 절차 준비 (feature flag 즉시 off)

## 관련 컨텍스트
- JH 구매대행 출시 점검표: `2026-05-29-dp-sniper-launch-checklist.md`
- 묶음 상품으로 ARPU 키우기: `2026-05-28-dp-bundle-arpu-growth.md`
- sniper-buying-dashboard 상태: Vault Memory `project_sniper_buying_dashboard.md`
