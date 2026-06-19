---
type: knowledge-note
date: 2026-06-03
source: daily-plus
category: implementation-candidate
tags:
- '#area/ai_automation'
- '#status/active'
summary: 이부장 원클릭 파일럿 런칭 — 단일 파일 랜딩 + Stripe 결제 + 텔레메트리 24~72시간 내 시험
status: applied
applied_at: 2026-06-11
graph_cluster: daily-practice
---

# 이부장 원클릭 파일럿 런칭

## 목적

이부장(이부장닷컴) 수익화 파이프라인의 첫 번째 구현 후보.
단일 파일 랜딩 페이지 + Stripe 결제 + 텔레메트리를 최소 구성으로 통합하여 24~72시간 내 시험 가능한 파일럿 구축.

## 구성 요소

### 1. 단일 파일 랜딩 페이지

- 파일 하나(`index.html`)로 전체 랜딩 구성
- 외부 의존성 최소화 (CDN CSS/JS만 허용)
- CTA 버튼 → Stripe Checkout 직접 연결

### 2. Stripe 결제 통합

```
흐름:
사용자 클릭
  → Stripe Checkout Session 생성 (백엔드 API 1개)
  → Stripe 결제 페이지 리디렉션
  → 성공/취소 콜백 URL 처리
  → 웹훅으로 주문 확정
```

필요한 Stripe 설정:
- `STRIPE_SECRET_KEY` (서버 전용)
- `STRIPE_WEBHOOK_SECRET` (웹훅 서명 검증용)
- Product ID + Price ID (대시보드에서 사전 생성)

### 3. 텔레메트리 통합

추적 이벤트:
- `page_view` — 랜딩 페이지 방문
- `cta_click` — 구매 버튼 클릭
- `checkout_start` — Stripe Checkout 시작
- `purchase_complete` — 결제 완료 (웹훅 확정 후)

### 4. Obsidian 주문 기록

결제 완료 시 자동 노트 생성:
```
ObsidianVault/05_Orders/2026-06-03-order-{order_id}.md
```

## 파일럿 런칭 체크리스트

- [ ] `index.html` 단일 랜딩 파일 작성
- [ ] Stripe Product/Price 생성 (대시보드)
- [ ] 백엔드 API 1개: `/create-checkout-session`
- [ ] 웹훅 엔드포인트: `/stripe-webhook`
- [ ] 텔레메트리 이벤트 4종 연결
- [ ] Obsidian 주문 기록 자동 생성
- [ ] 24시간 내 첫 구매 시뮬레이션 테스트

## 72시간 성공 기준

| 지표 | 목표 |
|------|------|
| 랜딩 페이지 방문 | > 10 |
| CTA 클릭률 | > 20% |
| 결제 완료 | >= 1 |
| 주문 기록 자동 생성 | 100% |

## 관련 노트

- [[2026-06-03-dp-ibujang-stripe-webhook]]
- [[2026-06-03-dp-ibujang-min-api-contract]]
