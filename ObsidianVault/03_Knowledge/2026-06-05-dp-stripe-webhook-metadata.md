---
title: Stripe 웹훅 메타데이터 연결
date: 2026-06-05
source: daily-plus/2026-06-05.md (Card 10)
priority: P1
category: knowledge
status: distilled
tags:
  - stripe
  - webhook
  - metadata
  - idempotency
  - payment
  - daily-plus
  - knowledge
---

# Stripe 웹훅 메타데이터 연결

> ChatGPT Pulse 2026-06-05 Card 10 증류 (P1 · knowledge-candidate)

## 목적

Stripe webhook 처리에서 원자적 주문 노트와 텔레메트리를 안정적으로 받는 설계 패턴. Checkout Sessions 생성 시 metadata 설정, 서명 검증, idempotency 보장.

## metadata 필드 설계

Stripe Checkout Session 생성 시 metadata에 포함할 핵심 필드:

```python
import stripe

session = stripe.checkout.Session.create(
    payment_method_types=["card"],
    line_items=[...],
    mode="payment",
    metadata={
        # 내부 추적
        "order_id": "ORD-2026-001234",
        "user_id": "USR-5678",
        "project_id": "PROJ-견적-001",
        # 비즈니스 컨텍스트
        "service_type": "interior_estimate",
        "source": "wishket_dashboard",
        # 텔레메트리
        "session_id": "sess_abc123",
        "created_at": "2026-06-05T09:00:00Z",
    },
    success_url="https://example.com/success?session_id={CHECKOUT_SESSION_ID}",
    cancel_url="https://example.com/cancel",
)
```

**제약 사항**:
- 최대 50개 키
- 키/값 각각 최대 500자
- 중첩 객체 불가 (문자열만)

## 서명 검증 코드

```python
import stripe
from fastapi import Request, HTTPException

STRIPE_WEBHOOK_SECRET = os.environ["STRIPE_WEBHOOK_SECRET"]

@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 이벤트 처리
    await handle_stripe_event(event)
    return {"status": "ok"}
```

**중요**: `stripe.Webhook.construct_event()`는 내부적으로 HMAC-SHA256 서명 검증 + 타임스탬프 5분 윈도우 적용.

## idempotency_key 처리

Stripe는 결제 재시도 시 중복 처리를 막는 idempotency_key를 지원한다:

```python
# 결제 생성 시 idempotency_key 사용
payment_intent = stripe.PaymentIntent.create(
    amount=1000,
    currency="krw",
    idempotency_key=f"pi_{order_id}_{timestamp}"
)

# 웹훅 중복 처리 방지 (자체 구현)
async def handle_stripe_event(event: dict):
    event_id = event["id"]

    # Redis로 중복 확인
    if await redis.exists(f"stripe:event:{event_id}"):
        return  # 이미 처리됨

    await process_event(event)
    await redis.setex(f"stripe:event:{event_id}", 86400, "processed")
```

## 이벤트 처리 순서

권장 이벤트 처리 우선순위:

```
1. checkout.session.completed
   → 주문 생성, metadata에서 order_id 추출
   → DB 상태 업데이트: pending → paid

2. payment_intent.succeeded
   → 결제 확정 알림 발송 (이메일/Discord)
   → 텔레메트리 로그 기록

3. payment_intent.payment_failed
   → 결제 실패 알림 발송
   → 재시도 링크 생성

4. customer.subscription.updated / deleted
   → 구독 상태 동기화
   → 기능 플래그 업데이트
```

## 안전한 설계 원칙

- [ ] 웹훅 엔드포인트는 HTTPS 전용
- [ ] `stripe-signature` 헤더 검증 필수
- [ ] Raw body 사용 (JSON 파싱 전 원본 바이트)
- [ ] 이벤트 idempotency 처리 (Redis TTL 24시간)
- [ ] 실패 시 `200 OK` 반환 후 재시도 허용 (5xx는 Stripe가 재전송)
- [ ] metadata에 PII 저장 금지

## 관련 컨텍스트

- [[hmac-idempotency-human-checklist]]
- Wishket 결제 파이프라인, sniper-buying-dashboard 연동 가능
