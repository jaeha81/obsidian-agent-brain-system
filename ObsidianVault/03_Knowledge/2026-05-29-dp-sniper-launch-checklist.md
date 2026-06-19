---
title: JH 구매대행 출시 점검표
date: 2026-05-29
source: daily-plus/2026-05-29.md (Card 8)
priority: P1
category: knowledge
status: distilled
tags:
- sniper-dashboard
- launch
- checklist
- stripe
- deployment
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# JH 구매대행 출시 점검표

> ChatGPT Pulse 2026-05-29 Card 8 증류 (P1 · knowledge)

## 목적
출시 직전 점검을 한눈에 끝내는 프리런치 런북. 스테이징 100% 통과 후 48시간 안정성 게이트를 거쳐 프로덕션 승격. 지표/웹훅/결제 실패율 점검. sniper-buying-dashboard 프로덕션 출시 전 반드시 완료해야 할 검증 목록.

## 핵심 내용
- **게이트 기준값**:
  - 스테이징 테스트: 전체 케이스 100% 통과
  - 48시간 안정성: 오류율 < 0.1%, p99 응답시간 < 2초
  - Stripe 결제 성공률: 스테이징 > 99%
  - 웹훅 전달 성공률: > 99.5%
- **Stripe 검증 항목**:
  - [ ] Stripe Webhook 서명 검증 정상 작동
  - [ ] 결제 성공/실패/환불 이벤트 핸들러 테스트
  - [ ] 테스트 카드 번호로 전체 결제 플로우 완주
  - [ ] Stripe 대시보드 로그 이상 없음 확인
- **48시간 모니터링 지표**:
  - 주문 생성 성공률
  - 결제 → 완료 전환율
  - 에러 로그 발생 빈도
  - DB 연결 오류 횟수
- **프로덕션 승격 순서**: Vercel Preview → 스테이징 48h → 프로덕션 10% 트래픽 → 100%

## 구현 체크리스트
- [ ] 스테이징 환경 전체 테스트 실행 및 100% 통과 확인
- [ ] Stripe Webhook 엔드포인트 검증 (서명, 이벤트 타입)
- [ ] 48시간 모니터링 대시보드 설정
- [ ] 롤백 절차 문서화 (Vercel instant rollback)
- [ ] 출시 당일 on-call 담당자 지정

## 관련 컨텍스트
- sniper-buying-dashboard 상태: Vault Memory `project_sniper_buying_dashboard.md`
- AgentDispatcher 상태 오판 금지: Vault Memory `feedback_agent_dispatcher_status.md`
- 배포 전 1분 검증 체크: `2026-05-27-dp-deploy-1min-verify.md`

## 관련 노트
- [[hubs/JH System]]
