"""Functional tests for billing webhook — mocks Stripe SDK calls.

Tests:
  1. checkout.session.completed  → user upgraded to pro
  2. customer.subscription.deleted → user downgraded to free
  3. Invalid signature            → 400 response
"""
from __future__ import annotations

import json
import os
import sys
import types
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers: build a minimal fake Stripe event dict
# ---------------------------------------------------------------------------

def _make_event(event_type: str, data_object: dict) -> dict:
    return {
        "type": event_type,
        "data": {"object": data_object},
    }


# ---------------------------------------------------------------------------
# Fixture: reset DB between tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Point auth.models.DB_PATH at a temp file for each test."""
    import auth.models as m
    monkeypatch.setattr(m, "DB_PATH", tmp_path / "test.db")
    m.init_db()
    yield


@pytest.fixture()
def client():
    import app as application
    return TestClient(application.app, raise_server_exceptions=True)


@pytest.fixture()
def test_user(isolated_db):
    """Create a free user and return the dict."""
    from auth.models import create_user
    u = create_user("test@example.com", "hashed_pw")
    return u


# ---------------------------------------------------------------------------
# Utility: call POST /billing/webhook with a pre-built event, bypassing sig
# ---------------------------------------------------------------------------

def _post_webhook(client, event: dict, env_vars: dict | None = None):
    env = {"STRIPE_SECRET_KEY": "sk_test_fake", **(env_vars or {})}
    with patch.dict(os.environ, env, clear=False):
        # No STRIPE_WEBHOOK_SECRET → dev-mode path (no sig check)
        os.environ.pop("STRIPE_WEBHOOK_SECRET", None)

        # Patch stripe.Event.construct_from to return the event dict-like object
        fake_event = MagicMock()
        fake_event.__getitem__ = lambda self, k: event[k]
        fake_event.get = event.get

        with patch("stripe.Event.construct_from", return_value=fake_event):
            return client.post(
                "/billing/webhook",
                content=json.dumps(event).encode(),
                headers={"content-type": "application/json"},
            )


# ---------------------------------------------------------------------------
# Test 1: checkout.session.completed → plan becomes pro
# ---------------------------------------------------------------------------

def test_checkout_completed_upgrades_user(client, test_user):
    event = _make_event(
        "checkout.session.completed",
        {
            "metadata": {"user_id": test_user["id"]},
            "customer": "cus_testABC",
        },
    )
    resp = _post_webhook(client, event)
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    from auth.models import get_user_by_id
    updated = get_user_by_id(test_user["id"])
    assert updated["plan"] == "pro"
    assert updated["stripe_customer_id"] == "cus_testABC"


# ---------------------------------------------------------------------------
# Test 2: customer.subscription.deleted → plan becomes free
# ---------------------------------------------------------------------------

def test_subscription_deleted_downgrades_user(client, test_user):
    # First set the user to pro with a Stripe customer ID
    from auth.models import set_user_plan
    set_user_plan(test_user["id"], "pro", stripe_customer_id="cus_testDEF")

    event = _make_event(
        "customer.subscription.deleted",
        {"customer": "cus_testDEF"},
    )
    resp = _post_webhook(client, event)
    assert resp.status_code == 200

    from auth.models import get_user_by_id
    updated = get_user_by_id(test_user["id"])
    assert updated["plan"] == "free"
    assert updated["stripe_customer_id"] == "cus_testDEF"


# ---------------------------------------------------------------------------
# Test 3: invalid Stripe signature → 400
# ---------------------------------------------------------------------------

def test_invalid_signature_returns_400(client):
    with patch.dict(
        os.environ,
        {"STRIPE_SECRET_KEY": "sk_test_fake", "STRIPE_WEBHOOK_SECRET": "whsec_test"},
        clear=False,
    ):
        import stripe as _stripe
        with patch.object(
            _stripe.Webhook,
            "construct_event",
            side_effect=_stripe.error.SignatureVerificationError("bad sig", "sig_header"),
        ):
            resp = client.post(
                "/billing/webhook",
                content=b"{}",
                headers={
                    "content-type": "application/json",
                    "stripe-signature": "t=bad,v1=bad",
                },
            )
    assert resp.status_code == 400
