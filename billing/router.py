"""Stripe billing router for ConvertFlow.

Routes
------
GET  /pricing              → pricing page (Free vs Pro)
POST /billing/checkout     → create Stripe Checkout Session, redirect
POST /billing/portal       → create Stripe Customer Portal session, redirect
POST /billing/webhook      → handle checkout.session.completed + customer.subscription.deleted
GET  /billing/success      → post-payment confirmation page
GET  /billing/cancel       → page shown when user abandons checkout
"""
from __future__ import annotations

import os

import stripe
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from auth.quota import get_current_user
from auth.models import set_user_plan, set_plan_by_stripe_customer

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()

# ── Stripe config ─────────────────────────────────────────────────────────────

def _stripe_secret() -> str:
    key = os.getenv("STRIPE_SECRET_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="Stripe is not configured.")
    return key


def _webhook_secret() -> str:
    return os.getenv("STRIPE_WEBHOOK_SECRET", "")


def _pro_price_id() -> str:
    price_id = os.getenv("STRIPE_PRO_PRICE_ID", "")
    if not price_id:
        raise HTTPException(status_code=503, detail="Stripe price is not configured.")
    return price_id


def _app_url() -> str:
    return os.getenv("APP_URL", "http://localhost:8080").rstrip("/")


# ── Pages ─────────────────────────────────────────────────────────────────────

@router.get("/pricing", response_class=HTMLResponse)
async def pricing_page(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(
        request,
        "pricing.html",
        {"request": request, "user": user},
    )


@router.get("/billing/success", response_class=HTMLResponse)
async def billing_success(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(
        request,
        "billing/success.html",
        {"request": request, "user": user},
    )


@router.get("/billing/cancel", response_class=HTMLResponse)
async def billing_cancel(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(
        request,
        "billing/cancel.html",
        {"request": request, "user": user},
    )


# ── Stripe flows ──────────────────────────────────────────────────────────────

@router.post("/billing/checkout")
async def create_checkout(request: Request):
    """Create a Stripe Checkout Session and redirect the user to Stripe."""
    user = get_current_user(request)
    if user is None:
        # Not logged in — send to login page
        return RedirectResponse("/auth/login?next=/billing/checkout", status_code=303)

    stripe.api_key = _stripe_secret()
    app_url = _app_url()

    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": _pro_price_id(), "quantity": 1}],
        metadata={"user_id": user["id"]},
        customer_email=user["email"],
        success_url=f"{app_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{app_url}/billing/cancel",
    )

    return RedirectResponse(session.url, status_code=303)


@router.post("/billing/portal")
async def create_portal(request: Request):
    """Create a Stripe Customer Portal session and redirect the user."""
    user = get_current_user(request)
    if user is None:
        return RedirectResponse("/auth/login", status_code=303)

    # Fetch fresh user row to get stripe_customer_id
    from auth.models import get_user_by_id
    full_user = get_user_by_id(user["id"])
    customer_id = full_user.get("stripe_customer_id") if full_user else None

    if not customer_id:
        # No subscription yet — send to checkout instead
        return RedirectResponse("/billing/checkout", status_code=303)

    stripe.api_key = _stripe_secret()
    app_url = _app_url()

    portal = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{app_url}/dashboard",
    )

    return RedirectResponse(portal.url, status_code=303)


# ── Webhook ───────────────────────────────────────────────────────────────────

@router.post("/billing/webhook")
async def stripe_webhook(request: Request):
    """Verify Stripe signature and handle subscription lifecycle events."""
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    webhook_secret = _webhook_secret()

    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

    if webhook_secret:
        try:
            event = stripe.Webhook.construct_event(payload, sig, webhook_secret)
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid Stripe signature.")
    else:
        # Dev mode: no signature check (only allow when secret not set)
        import json
        event = stripe.Event.construct_from(
            json.loads(payload), stripe.api_key
        )

    event_type = event["type"]

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = (session.get("metadata") or {}).get("user_id")
        customer_id = session.get("customer")
        if user_id and customer_id:
            set_user_plan(user_id, "pro", stripe_customer_id=customer_id)

    elif event_type == "customer.subscription.deleted":
        customer_id = event["data"]["object"].get("customer")
        if customer_id:
            set_plan_by_stripe_customer(customer_id, "free")

    return {"ok": True}
