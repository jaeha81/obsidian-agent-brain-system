#!/usr/bin/env python3
"""
Stripe + Toss Payments 결제 서버 보일러플레이트
FastAPI 기반 — 구독/일회성 결제 + 웹훅 처리

사용법:
    1. .env 설정 (STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, TOSS_SECRET_KEY)
    2. pip install fastapi uvicorn stripe python-dotenv
    3. uvicorn server:app --reload

Stripe 설정:
    - Dashboard → Products → 가격 ID 복사 → .env STRIPE_PRICE_ID 설정
    - Dashboard → Webhooks → 엔드포인트 추가: /webhook/stripe
"""
import hashlib
import hmac
import json
import os
import time
from pathlib import Path

import stripe
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

# ── 환경변수 ────────────────────────────────────────────────────────────────
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "")  # price_xxx 형식

TOSS_CLIENT_KEY = os.getenv("TOSS_CLIENT_KEY", "")
TOSS_SECRET_KEY = os.getenv("TOSS_SECRET_KEY", "")

PRODUCT_NAME = os.getenv("PRODUCT_NAME", "Bucky Pro")
PRODUCT_PRICE = int(os.getenv("PRODUCT_PRICE", "29000"))  # KRW 원화
DOMAIN = os.getenv("DOMAIN", "http://localhost:8000")

stripe.api_key = STRIPE_SECRET_KEY

app = FastAPI(title=f"{PRODUCT_NAME} Payment Server")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Stripe 결제 세션 생성 ────────────────────────────────────────────────────

@app.post("/api/stripe/checkout")
async def create_checkout_session(request: Request):
    """Stripe Checkout 세션 생성 → 결제 페이지 URL 반환."""
    body = await request.json()
    customer_email = body.get("email", "")
    mode = body.get("mode", "subscription")  # subscription | payment

    try:
        params = {
            "payment_method_types": ["card"],
            "line_items": [{
                "price": STRIPE_PRICE_ID,
                "quantity": 1,
            }] if STRIPE_PRICE_ID else [{
                "price_data": {
                    "currency": "krw",
                    "unit_amount": PRODUCT_PRICE,
                    "product_data": {"name": PRODUCT_NAME},
                    **({"recurring": {"interval": "month"}} if mode == "subscription" else {}),
                },
                "quantity": 1,
            }],
            "mode": mode,
            "success_url": f"{DOMAIN}/success?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{DOMAIN}/cancel",
        }
        if customer_email:
            params["customer_email"] = customer_email

        session = stripe.checkout.Session.create(**params)
        return JSONResponse({"url": session.url, "session_id": session.id})

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/stripe/session/{session_id}")
async def get_session(session_id: str):
    """결제 완료 후 세션 상태 확인."""
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return JSONResponse({
            "status": session.payment_status,
            "customer_email": session.customer_details.email if session.customer_details else "",
            "amount_total": session.amount_total,
        })
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Stripe 웹훅 ──────────────────────────────────────────────────────────────

@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Stripe 이벤트 웹훅 처리."""
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        _handle_payment_success(session)

    elif event_type == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        _handle_subscription_cancelled(subscription)

    elif event_type == "invoice.payment_failed":
        invoice = event["data"]["object"]
        _handle_payment_failed(invoice)

    return Response(status_code=200)


def _handle_payment_success(session: dict) -> None:
    """결제 완료 처리 — DB 업데이트, 이메일 발송 등."""
    email = session.get("customer_details", {}).get("email", "")
    amount = session.get("amount_total", 0)
    print(f"[Payment] ✅ 결제 완료 — {email} / ₩{amount:,}")
    # TODO: DB에 구독 상태 저장, 환영 이메일 발송


def _handle_subscription_cancelled(subscription: dict) -> None:
    customer_id = subscription.get("customer", "")
    print(f"[Payment] ❌ 구독 취소 — {customer_id}")
    # TODO: 구독 만료 처리


def _handle_payment_failed(invoice: dict) -> None:
    email = invoice.get("customer_email", "")
    print(f"[Payment] ⚠️ 결제 실패 — {email}")
    # TODO: 재결제 안내 이메일


# ── Toss Payments (한국 결제) ────────────────────────────────────────────────

@app.post("/api/toss/confirm")
async def toss_confirm(request: Request):
    """Toss Payments 결제 승인 — 프론트에서 paymentKey, orderId, amount 전송."""
    import base64
    import urllib.request

    body = await request.json()
    payment_key = body.get("paymentKey", "")
    order_id = body.get("orderId", "")
    amount = body.get("amount", 0)

    if not all([payment_key, order_id, amount]):
        raise HTTPException(status_code=400, detail="paymentKey, orderId, amount 필수")

    # Toss API 호출
    credentials = base64.b64encode(f"{TOSS_SECRET_KEY}:".encode()).decode()
    payload = json.dumps({"paymentKey": payment_key, "orderId": order_id, "amount": amount}).encode()

    req = urllib.request.Request(
        "https://api.tosspayments.com/v1/payments/confirm",
        data=payload,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            print(f"[Toss] ✅ 결제 승인 — {data.get('orderId')} / ₩{data.get('totalAmount', 0):,}")
            return JSONResponse({"success": True, "data": data})
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Toss 결제 실패: {e}")


# ── 성공/취소 페이지 ─────────────────────────────────────────────────────────

@app.get("/success", response_class=HTMLResponse)
async def success_page(session_id: str = ""):
    return HTMLResponse(f"""
<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">
<title>결제 완료</title>
<style>body{{font-family:sans-serif;text-align:center;padding:60px;background:#0f172a;color:#e2e8f0}}
h1{{color:#22c55e;font-size:3rem}}p{{font-size:1.2rem;color:#94a3b8}}</style></head>
<body><h1>✅ 결제 완료!</h1>
<p>{PRODUCT_NAME}에 오신 것을 환영합니다.</p>
<p style="font-size:.9rem;color:#64748b">세션 ID: {session_id[:20]}...</p>
<a href="/" style="color:#3b82f6">홈으로 돌아가기</a></body></html>
""")


@app.get("/cancel", response_class=HTMLResponse)
async def cancel_page():
    return HTMLResponse(f"""
<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">
<title>결제 취소</title>
<style>body{{font-family:sans-serif;text-align:center;padding:60px;background:#0f172a;color:#e2e8f0}}
h1{{color:#ef4444;font-size:2.5rem}}</style></head>
<body><h1>결제가 취소되었습니다</h1>
<a href="/" style="color:#3b82f6">다시 시도하기</a></body></html>
""")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
