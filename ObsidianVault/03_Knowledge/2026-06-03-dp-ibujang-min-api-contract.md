---
type: knowledge-note
date: 2026-06-03
source: daily-plus
category: knowledge-candidate
tags:
  - "#area/ai_automation"
  - "#status/active"
summary: 이부장 최소 API 계약 — 핸드오프 API 계약 스펙: 필수 헤더 4종, 페이로드 예시 3개, HMAC 스모크 테스트, 커밋/롤백 레시피
status: applied
applied_at: 2026-06-11
---

# 이부장 최소 API 계약 (Min API Contract)

## 목적

이부장 시스템 핸드오프 시 혼란을 줄이기 위한 최소 API 계약 명세.
4개 필수 헤더, 3개 페이로드 예시, HMAC 스모크 테스트, 커밋/롤백 레시피 포함.

## 필수 헤더 4종

| 헤더 | 값 형식 | 설명 |
|------|---------|------|
| `X-Ibujang-Timestamp` | ISO8601 | 요청 생성 시각 |
| `X-Ibujang-Signature` | HMAC-SHA256 hex | 페이로드 서명 |
| `X-Ibujang-Idempotency-Key` | UUID v4 | 중복 방지 키 |
| `Content-Type` | `application/json` | 페이로드 형식 |

## 페이로드 예시 3종

### 예시 1: 신규 주문 접수

```json
{
  "event": "order.created",
  "order_id": "ord_abc123",
  "customer_email": "test@example.com",
  "amount": 29000,
  "currency": "KRW",
  "items": [{"sku": "ibujang-basic", "qty": 1}],
  "created_at": "2026-06-03T09:00:00+09:00"
}
```

### 예시 2: 결제 확정

```json
{
  "event": "payment.confirmed",
  "order_id": "ord_abc123",
  "payment_intent_id": "pi_xyz789",
  "amount_received": 29000,
  "confirmed_at": "2026-06-03T09:01:30+09:00"
}
```

### 예시 3: 주문 취소

```json
{
  "event": "order.cancelled",
  "order_id": "ord_abc123",
  "reason": "customer_request",
  "cancelled_at": "2026-06-03T10:00:00+09:00",
  "refund_required": true
}
```

## HMAC 서명 스모크 테스트

```python
import hmac
import hashlib
import json

IBUJANG_SECRET = os.getenv("IBUJANG_WEBHOOK_SECRET")

def sign_payload(payload: dict, timestamp: str) -> str:
    message = f"{timestamp}.{json.dumps(payload, separators=(',', ':'))}"
    return hmac.new(
        IBUJANG_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

def verify_signature(payload: dict, timestamp: str, received_sig: str) -> bool:
    expected = sign_payload(payload, timestamp)
    return hmac.compare_digest(expected, received_sig)

# 스모크 테스트
def smoke_test():
    test_payload = {"event": "test", "ts": "2026-06-03T09:00:00"}
    ts = "2026-06-03T09:00:00+09:00"
    sig = sign_payload(test_payload, ts)
    assert verify_signature(test_payload, ts, sig), "HMAC smoke test FAILED"
    print("HMAC smoke test PASSED")
```

## 커밋/롤백 레시피

### 커밋 (주문 확정)

```python
def commit_order(order_id: str, idempotency_key: str):
    if is_key_used(idempotency_key):
        return {"status": "already_committed"}
    
    save_order_to_obsidian(order_id)
    mark_key_used(idempotency_key)
    return {"status": "committed", "order_id": order_id}
```

### 롤백 (주문 취소/환불)

```python
def rollback_order(order_id: str, reason: str):
    order = get_order(order_id)
    if not order:
        return {"status": "not_found"}
    
    update_order_status(order_id, "cancelled", reason)
    update_obsidian_note(order_id, status="cancelled")
    return {"status": "rolled_back", "order_id": order_id}
```

## 관련 노트

- [[2026-06-03-dp-ibujang-stripe-webhook]]
- [[2026-06-03-dp-verified-handoff-flow]]
