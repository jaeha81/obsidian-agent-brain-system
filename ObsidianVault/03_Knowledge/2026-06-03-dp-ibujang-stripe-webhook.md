---
type: knowledge-note
date: 2026-06-03
source: daily-plus
category: implementation-candidate
tags:
- '#area/ai_automation'
- '#status/active'
summary: 이부장 Stripe 웹훅 무결성 처리 — 서명 검증, 멱등성 키 저장, Obsidian 주문 기록, 중복 200 응답 패턴
status: applied
applied_at: 2026-06-11
graph_cluster: daily-practice
---

# 이부장 Stripe 웹훅 무결성 처리

## 핵심 4원칙

1. **서명 검증 먼저** — `STRIPE_WEBHOOK_SECRET`으로 페이로드 서명 검증
2. **멱등성 키 저장** — 동일 이벤트 중복 처리 방지
3. **Obsidian 주문 기록** — 결제 확정 시 자동 노트 생성
4. **중복 200 응답** — 이미 처리된 이벤트도 200 반환 (Stripe 재전송 방지)

## 서명 검증 패턴

```python
import stripe
from fastapi import Request, HTTPException

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

@app.post("/stripe-webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    return await handle_event(event)
```

## 멱등성 키 저장

```python
PROCESSED_EVENTS_PATH = "data/stripe_processed_events.json"

def is_already_processed(event_id: str) -> bool:
    processed = load_json(PROCESSED_EVENTS_PATH)
    return event_id in processed

def mark_as_processed(event_id: str):
    processed = load_json(PROCESSED_EVENTS_PATH)
    processed[event_id] = {
        "processed_at": datetime.now().isoformat(),
        "type": "stripe_event"
    }
    save_json(PROCESSED_EVENTS_PATH, processed)
```

## 중복 200 응답 핸들러 패턴

```python
async def handle_event(event):
    event_id = event["id"]

    # 이미 처리된 이벤트 — 200 반환 (Stripe 재전송 방지)
    if is_already_processed(event_id):
        return {"status": "already_processed", "event_id": event_id}

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        await process_successful_payment(session)
        mark_as_processed(event_id)

    return {"status": "ok"}
```

## Obsidian 주문 기록 자동 생성

```python
ORDERS_PATH = "ObsidianVault/05_Orders/"

async def create_order_note(session):
    order_id = session["id"]
    customer_email = session.get("customer_details", {}).get("email", "unknown")
    amount = session["amount_total"] / 100  # cents → 원

    content = f"""---
type: order-record
order_id: {order_id}
date: {datetime.now().strftime('%Y-%m-%d')}
customer: {customer_email}
amount: {amount}
status: confirmed
---

# 주문 #{order_id}

- 고객: {customer_email}
- 금액: {amount:,.0f}원
- 확정: {datetime.now().isoformat()}
"""
    file_path = f"{ORDERS_PATH}{datetime.now().strftime('%Y-%m-%d')}-order-{order_id[:8]}.md"
    write_file(file_path, content)
```

## 보안 체크리스트

- [ ] `STRIPE_WEBHOOK_SECRET` 환경변수 주입 (코드 하드코딩 금지)
- [ ] 서명 검증 실패 시 400 반환
- [ ] 멱등성 키 파일 `.gitignore` 등록
- [ ] 주문 기록 파일에 PII 최소화 (이메일만, 카드 정보 없음)

## 관련 노트

- [[2026-06-03-dp-ibujang-oneclick-pilot]]
- [[2026-06-03-dp-verified-handoff-flow]]
- [[2026-06-03-dp-webhook-vault-write-pattern]]
