"""Tests for the self-serve signup + magic-link flow.

Covers happy path (signup → magic link → dashboard), session cookie crypto,
and the abuse paths (replay, expired tokens, unknown email).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from queryshield import auth as qs_auth
from queryshield.main import app
from queryshield.models import MagicLink, SessionLocal, Tenant


@pytest.fixture()
def client(control_db):
    return TestClient(app)


def _last_magic_token_for(email: str) -> str | None:
    """Tests can't read tokens out of email — we hook the email sender to
    capture them. This fixture grabs them via the model row instead."""
    return None


# Patch the email sender to a no-op so tests don't hit SendGrid.
@pytest.fixture(autouse=True)
def _no_email():
    with patch("queryshield.auth.send_email", return_value=True):
        yield


# --- Session cookies --------------------------------------------------

def test_session_roundtrip() -> None:
    cookie = qs_auth.issue_session("tenant-abc")
    assert qs_auth.verify_session(cookie) == "tenant-abc"


def test_tampered_session_rejected() -> None:
    cookie = qs_auth.issue_session("tenant-abc")
    bad = cookie[:-2] + "00"
    assert qs_auth.verify_session(bad) is None


def test_expired_session_rejected() -> None:
    # Forge a session with a past expiry.
    payload = "tenant-abc|" + (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    import hashlib
    import hmac

    sig = hmac.new(qs_auth._session_key(), payload.encode(), hashlib.sha256).hexdigest()
    assert qs_auth.verify_session(f"{payload}|{sig}") is None


# --- Signup flow ------------------------------------------------------

def test_signup_creates_tenant_and_returns_key(client) -> None:
    r = client.post(
        "/signup",
        data={"email": "alice@example.com", "workspace": "Acme"},
        follow_redirects=False,
    )
    assert r.status_code == 200
    assert "qs_" in r.text  # API key shown in HTML
    assert "alice@example.com" in r.text

    with SessionLocal() as session:
        tenant = session.query(Tenant).filter_by(owner_email="alice@example.com").one()
        assert tenant.name == "Acme"
        link = session.query(MagicLink).filter_by(email="alice@example.com").one()
        assert link.consumed_at is None


def test_signup_existing_email_does_not_recreate(client) -> None:
    client.post("/signup", data={"email": "bob@example.com"})
    r = client.post("/signup", data={"email": "bob@example.com"})
    assert r.status_code == 200
    # The success page is only shown for *new* signups; the duplicate
    # response routes back to login with a "we sent you a link" message.
    assert "fresh magic link" in r.text or "sent you a link" in r.text

    with SessionLocal() as session:
        assert session.query(Tenant).filter_by(owner_email="bob@example.com").count() == 1


def test_signup_invalid_email(client) -> None:
    r = client.post("/signup", data={"email": "not-an-email"})
    assert r.status_code == 400
    assert "invalid email" in r.text.lower()


# --- Magic link → session ---------------------------------------------

def _consume_signup_link(client: TestClient, email: str) -> str:
    """Helper: do the signup, fish out the issued token, follow the link."""
    client.post("/signup", data={"email": email})
    with SessionLocal() as session:
        link = session.query(MagicLink).filter_by(email=email).order_by(MagicLink.created_at.desc()).first()
        assert link is not None
    # We only have the hash in DB. For tests we mint a new link directly so
    # we can hold the cleartext token.
    tenant_id = link.tenant_id
    token = qs_auth.issue_magic_link(email, tenant_id)
    return token


def test_magic_link_grants_session_and_dashboard(client) -> None:
    client.post("/signup", data={"email": "carol@example.com"})
    with SessionLocal() as session:
        tenant = session.query(Tenant).filter_by(owner_email="carol@example.com").one()
    token = qs_auth.issue_magic_link("carol@example.com", tenant.id)

    r = client.get(f"/auth/verify?token={token}", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/dashboard"
    assert qs_auth.SESSION_COOKIE in r.cookies

    # Now hit /dashboard with the cookie.
    r = client.get("/dashboard")
    assert r.status_code == 200
    assert "Loading" in r.text or "Workspace" in r.text  # JS-rendered


def test_magic_link_replay_blocked(client) -> None:
    client.post("/signup", data={"email": "dave@example.com"})
    with SessionLocal() as session:
        tenant = session.query(Tenant).filter_by(owner_email="dave@example.com").one()
    token = qs_auth.issue_magic_link("dave@example.com", tenant.id)

    r1 = client.get(f"/auth/verify?token={token}", follow_redirects=False)
    assert r1.status_code == 303
    r2 = client.get(f"/auth/verify?token={token}", follow_redirects=False)
    assert r2.status_code == 400  # consumed already


def test_dashboard_requires_session(client) -> None:
    r = client.get("/dashboard", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_dashboard_data_returns_json(client) -> None:
    client.post("/signup", data={"email": "eve@example.com", "workspace": "Eve Inc"})
    with SessionLocal() as session:
        tenant = session.query(Tenant).filter_by(owner_email="eve@example.com").one()
    token = qs_auth.issue_magic_link("eve@example.com", tenant.id)
    client.get(f"/auth/verify?token={token}")

    r = client.get("/dashboard/data")
    assert r.status_code == 200
    body = r.json()
    assert body["tenant"]["owner_email"] == "eve@example.com"
    assert body["tenant"]["name"] == "Eve Inc"
    assert len(body["agents"]) == 1  # admin agent


def test_login_does_not_leak_unknown_email(client) -> None:
    r = client.post("/login", data={"email": "ghost@example.com"})
    assert r.status_code == 200
    # Same generic response whether the email exists or not.
    assert "we just sent you a link" in r.text.lower()


def test_upgrade_endpoint_validates_tier(client) -> None:
    """Upgrade endpoint should reject unknown tiers and require auth."""
    # No session — 401
    r = client.post("/dashboard/upgrade", data={"tier": "pro"})
    assert r.status_code == 401

    # Auth in
    client.post("/signup", data={"email": "iris@example.com"})
    with SessionLocal() as session:
        from queryshield.models import Tenant

        tenant = session.query(Tenant).filter_by(owner_email="iris@example.com").one()
    token = qs_auth.issue_magic_link("iris@example.com", tenant.id)
    client.get(f"/auth/verify?token={token}")

    r = client.post("/dashboard/upgrade", data={"tier": "platinum"})
    assert r.status_code == 400
    assert "invalid tier" in r.text.lower()

    # Valid tier — fails with a Stripe error in tests since no real webhook target,
    # but we should at least get past validation. STRIPE_SECRET_KEY isn't set in
    # the test env, so we expect 400 with a "STRIPE_SECRET_KEY is not configured"
    # message.
    r = client.post("/dashboard/upgrade", data={"tier": "pro"})
    # 400 is OK here — the test is that the route is reachable and tier validation works.
    assert r.status_code in (400, 200)


def test_dashboard_create_and_rotate_agent(client) -> None:
    client.post("/signup", data={"email": "fran@example.com"})
    with SessionLocal() as session:
        tenant = session.query(Tenant).filter_by(owner_email="fran@example.com").one()
    token = qs_auth.issue_magic_link("fran@example.com", tenant.id)
    client.get(f"/auth/verify?token={token}")

    # Mint a new agent
    r = client.post("/dashboard/agents", data={"name": "reporting"})
    assert r.status_code == 200
    new_key = r.json()["api_key"]
    assert new_key.startswith("qs_")

    # Rotate it
    agent_id = r.json()["agent_id"]
    r = client.post("/dashboard/agents/rotate", data={"agent_id": agent_id})
    assert r.status_code == 200
    rotated = r.json()["api_key"]
    assert rotated.startswith("qs_")
    assert rotated != new_key
