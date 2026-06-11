---
title: 익스프레스 모크업 즉시 실행 매니페스트
date: 2026-06-01
source: daily-plus/2026-06-01.md (Card 1)
priority: P2
category: knowledge
status: distilled
tags:
  - mockup
  - stripe
  - obsidian
  - bucky
  - manifest
  - daily-plus
  - knowledge
---

# 익스프레스 모크업 즉시 실행 매니페스트

> Daily Plus Pulse 2026-06-01 Card 1 증류 (P2 · knowledge-candidate)

## 목적

Express Mockup 파일럿을 48-96시간 안에 돌리는 실행 아티팩트. Stripe Payment Link로 결제, 결제 성공 시 Bucky에 알림, Obsidian에 기록, 텔레메트리까지 한 번에 연결한다.

## Stripe Payment Link 설정

| 항목 | 값 |
|------|---|
| 상품명 | Express Mockup Pilot |
| 가격 유형 | 1회성 (one-time) |
| 성공 URL | `https://<your-domain>/success?session_id={CHECKOUT_SESSION_ID}` |
| 웹훅 이벤트 | `checkout.session.completed` |
| 메타데이터 키 | `pilot_id`, `customer_email`, `mockup_type` |

```
POST /webhook/stripe
Content-Type: application/json
Stripe-Signature: <sig>

{
  "type": "checkout.session.completed",
  "data": {
    "object": {
      "id": "cs_xxx",
      "metadata": { "pilot_id": "EP-001", "mockup_type": "interior" }
    }
  }
}
```

## Bucky 트리거 형식

```json
{
  "trigger": "stripe_payment_success",
  "source": "express-mockup-pilot",
  "pilot_id": "EP-001",
  "amount": 49000,
  "currency": "KRW",
  "customer_email": "user@example.com",
  "mockup_type": "interior",
  "ts": "2026-06-01T10:00:00Z",
  "action": "notify_and_record"
}
```

Bucky 수신 채널: `#jh-수익알림` Discord → 즉시 Obsidian 기록 트리거

## Obsidian 기록 포맷

```yaml
---
type: payment-event
pilot: express-mockup
payment_id: cs_xxx
amount: 49000
currency: KRW
mockup_type: interior
recorded_at: 2026-06-01T10:00:00Z
---
```

파일 경로: `ObsidianVault/05_Revenue/payments/2026-06-01-ep-<pilot_id>.md`

## 텔레메트리 이벤트

| 이벤트명 | 발생 시점 | 필드 |
|---------|--------|------|
| `mockup_page_view` | 랜딩 방문 | `ts`, `referrer`, `utm_source` |
| `mockup_preview_click` | 미리보기 클릭 | `ts`, `mockup_type`, `session_id` |
| `mockup_checkout_start` | 결제 시작 | `ts`, `pilot_id`, `amount` |
| `mockup_payment_success` | 결제 완료 | `ts`, `pilot_id`, `payment_id`, `amount` |

```js
// 최소 텔레메트리 코드
window.track = (event, props) => {
  fetch('/api/telemetry', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ event, ts: Date.now(), ...props })
  });
};
```

## 실행 체크리스트

- [ ] Stripe Payment Link 생성 및 웹훅 등록
- [ ] Bucky 트리거 엔드포인트 연결
- [ ] Obsidian 기록 스크립트 배포
- [ ] 텔레메트리 이벤트 4종 연결
- [ ] 48시간 파일럿 런 실행

## 관련 컨텍스트

- Express Mockup 파일럿 전체 흐름과 연동
- [[단일-HTML-랜딩과-추적-연결]], [[가격-AB-결정-매니페스트]]
