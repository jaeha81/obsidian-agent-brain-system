#!/usr/bin/env python3
"""Stripe 결제 서버 보일러플레이트 — FastAPI 기반

랜딩 페이지와 연동되는 결제 백엔드.
PaymentIntent 생성, Webhook 처리, 구독 관리.

사용법:
    pip install fastapi uvicorn stripe python-dotenv
    python scripts/stripe_payment_server.py

환경변수 (.env):
    STRIPE_SECRET_KEY=sk_test_...
    STRIPE_PUBLISHABLE_KEY=pk_test_...
    STRIPE_WEBHOOK_SECRET=whsec_...
    PRICE_MONTHLY_ID=price_...    # Stripe 대시보드에서 생성한 가격 ID
    PRICE_YEARLY_ID=price_...
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", encoding="utf-8")

import stripe

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
PRICE_IDS = {
    "month": os.getenv("PRICE_MONTHLY_ID", ""),
    "year":  os.getenv("PRICE_YEARLY_ID", ""),
}

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse
    import uvicorn
    from pydantic import BaseModel, EmailStr
except ImportError:
    print("설치 필요: pip install fastapi uvicorn stripe python-dotenv pydantic[email]")
    sys.exit(1)

app = FastAPI(title="Bucky Payment Server", docs_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# 정적 파일 (랜딩 페이지 HTML)
TEMPLATES_DIR = ROOT / "templates"
if TEMPLATES_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(TEMPLATES_DIR)), name="static")


# ── 요청 모델 ─────────────────────────────────────────────────────────────────

class PaymentIntentRequest(BaseModel):
    email: str
    plan: str = "month"  # "month" | "year"


class SubscriptionRequest(BaseModel):
    email: str
    plan: str = "month"
    payment_method_id: str


# ── 엔드포인트 ────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    """랜딩 페이지 서빙."""
    landing = TEMPLATES_DIR / "landing_page_template.html"
    if landing.exists():
        return landing.read_text(encoding="utf-8")
    return "<h1>Bucky Payment Server Running</h1>"


@app.get("/pay", response_class=HTMLResponse)
async def payment_page():
    """결제 페이지."""
    page = TEMPLATES_DIR / "stripe_payment_template.html"
    if page.exists():
        content = page.read_text(encoding="utf-8")
        content = content.replace(
            "{{STRIPE_PUBLISHABLE_KEY}}",
            os.getenv("STRIPE_PUBLISHABLE_KEY", "")
        )
        return content
    raise HTTPException(404, "결제 페이지 템플릿을 찾을 수 없습니다.")


@app.post("/api/create-payment-intent")
async def create_payment_intent(req: PaymentIntentRequest):
    """PaymentIntent 생성 (일회성 결제)."""
    if not stripe.api_key:
        raise HTTPException(500, "Stripe API 키가 설정되지 않았습니다.")

    PRICES = {"month": 29000, "year": 290000}
    amount = PRICES.get(req.plan, 29000)

    try:
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency="krw",
            receipt_email=req.email,
            metadata={"plan": req.plan, "email": req.email},
        )
        return {"clientSecret": intent.client_secret}
    except stripe.error.StripeError as e:
        raise HTTPException(400, str(e.user_message))


@app.post("/api/create-subscription")
async def create_subscription(req: SubscriptionRequest):
    """Stripe 구독 생성."""
    if not stripe.api_key:
        raise HTTPException(500, "Stripe API 키가 설정되지 않았습니다.")

    price_id = PRICE_IDS.get(req.plan, "")
    if not price_id:
        raise HTTPException(400, f"유효하지 않은 플랜: {req.plan}")

    try:
        # 고객 생성 또는 조회
        customers = stripe.Customer.list(email=req.email, limit=1)
        if customers.data:
            customer = customers.data[0]
        else:
            customer = stripe.Customer.create(email=req.email)

        # 결제 수단 연결
        stripe.PaymentMethod.attach(req.payment_method_id, customer=customer.id)
        stripe.Customer.modify(
            customer.id,
            invoice_settings={"default_payment_method": req.payment_method_id},
        )

        # 구독 생성
        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{"price": price_id}],
            expand=["latest_invoice.payment_intent"],
        )

        latest_invoice = subscription.latest_invoice
        payment_intent = latest_invoice.payment_intent if latest_invoice else None

        return {
            "subscriptionId": subscription.id,
            "clientSecret": payment_intent.client_secret if payment_intent else None,
            "status": subscription.status,
        }
    except stripe.error.StripeError as e:
        raise HTTPException(400, str(e.user_message))


@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Stripe Webhook 처리."""
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(400, "Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")

    event_type = event["type"]

    if event_type == "payment_intent.succeeded":
        pi = event["data"]["object"]
        print(f"✅ 결제 성공: {pi['id']} ({pi['amount']}원) — {pi.get('receipt_email', '')}")
        _on_payment_success(pi)

    elif event_type == "customer.subscription.created":
        sub = event["data"]["object"]
        print(f"🆕 구독 시작: {sub['id']} — {sub['customer']}")

    elif event_type == "customer.subscription.deleted":
        sub = event["data"]["object"]
        print(f"❌ 구독 취소: {sub['id']} — {sub['customer']}")

    elif event_type == "invoice.payment_failed":
        inv = event["data"]["object"]
        print(f"⚠️ 결제 실패: {inv['customer_email']}")

    return {"status": "ok"}


def _on_payment_success(payment_intent: dict) -> None:
    """결제 성공 후 처리 — Obsidian에 기록."""
    try:
        vault = ROOT / "ObsidianVault" / "00_System" / "payment_log.md"
        from datetime import datetime
        entry = (
            f"\n| {datetime.now().strftime('%Y-%m-%d %H:%M')} "
            f"| {payment_intent.get('receipt_email', 'unknown')} "
            f"| {payment_intent.get('amount', 0):,}원 "
            f"| {payment_intent['id']} |"
        )
        with open(vault, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as e:
        print(f"결제 로그 저장 실패: {e}")


# ── 실행 ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    print(f"💳 Bucky 결제 서버 시작 — http://localhost:{port}")
    print(f"   Stripe 키: {'설정됨' if stripe.api_key else '❌ 미설정'}")
    uvicorn.run("stripe_payment_server:app", host="0.0.0.0", port=port, reload=True)
