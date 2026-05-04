"""Passwordless auth — magic links + HMAC-signed session cookies.

The model:
- Anyone can sign up by handing us an email. We mint a tenant + admin
  agent for them on the spot, return the API key once, and email a magic
  link they can use to access the dashboard later.
- Subsequent logins: enter email → receive magic link → click → cookie set.
- Sessions are HMAC-signed cookies (no DB hit per request). 30-day TTL.

Token format:
- Magic link: opaque random string. We store sha256(token) in `magic_links`,
  the user gets the cleartext in the URL.
- Session cookie: `tenant_id|expires_iso|hmac` separated by '|'. HMAC keyed
  by SESSION_KEY (derived from VAULT_KEY if not set explicitly).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select

from queryshield.config import get_settings
from queryshield.models import (
    Agent,
    MagicLink,
    SessionLocal,
    Tenant,
    generate_api_key,
)
from queryshield.notifications import send_email

log = logging.getLogger("queryshield.auth")

SESSION_COOKIE = "qs_session"
SESSION_TTL_DAYS = 30
MAGIC_LINK_TTL_MIN = 30


# --- Session cookies ---------------------------------------------------

def _session_key() -> bytes:
    """Derive a stable HMAC key. Falls back to VAULT_KEY if SESSION_KEY unset."""
    s = get_settings()
    key = getattr(s, "session_key", None) or s.vault_key or "dev-only-fallback-session-key"
    return hashlib.sha256(key.encode("utf-8") if isinstance(key, str) else key).digest()


def issue_session(tenant_id: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
    payload = f"{tenant_id}|{expires.isoformat()}"
    sig = hmac.new(_session_key(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}|{sig}"


def verify_session(cookie: Optional[str]) -> Optional[str]:
    """Return tenant_id if cookie is valid; otherwise None."""
    if not cookie:
        return None
    try:
        tenant_id, expires_iso, sig = cookie.rsplit("|", 2)
    except ValueError:
        return None
    expected = hmac.new(_session_key(), f"{tenant_id}|{expires_iso}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        expires = datetime.fromisoformat(expires_iso)
    except ValueError:
        return None
    if expires < datetime.now(timezone.utc):
        return None
    return tenant_id


# --- Magic links -------------------------------------------------------

def issue_magic_link(email: str, tenant_id: str) -> str:
    """Mint a token, persist its hash, return the cleartext."""
    token = secrets.token_urlsafe(32)
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires = datetime.now(timezone.utc) + timedelta(minutes=MAGIC_LINK_TTL_MIN)
    with SessionLocal() as session:
        session.add(
            MagicLink(
                email=email.lower().strip(),
                token_hash=digest,
                tenant_id=tenant_id,
                expires_at=expires,
            )
        )
        session.commit()
    return token


def consume_magic_link(token: str) -> Optional[str]:
    """Verify + mark consumed. Returns the tenant_id, or None on failure."""
    if not token:
        return None
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with SessionLocal() as session:
        link = session.execute(
            select(MagicLink).where(MagicLink.token_hash == digest)
        ).scalar_one_or_none()
        if link is None:
            return None
        if link.consumed_at is not None:
            log.warning("auth: replay attempt on consumed magic link for %s", link.email)
            return None
        # SQLite returns naive datetimes; normalize.
        expires = link.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            return None
        link.consumed_at = datetime.now(timezone.utc)
        session.commit()
        return link.tenant_id


# --- Signup ------------------------------------------------------------

def signup(email: str, workspace_name: Optional[str] = None) -> tuple[str, str, str, str]:
    """Provision a fresh tenant + admin agent for an email.

    Returns ``(tenant_id, agent_id, api_key, magic_token)``. The API key is
    shown once at signup; the magic_token is also emailed for later access.

    If the email already owns a tenant, we re-use it and only mint a new
    magic link (we don't issue a new API key — they keep the old one).
    """
    email = email.lower().strip()
    if not _looks_like_email(email):
        raise ValueError("invalid email")

    with SessionLocal() as session:
        existing = session.execute(
            select(Tenant).where(Tenant.owner_email == email)
        ).scalar_one_or_none()
        if existing is not None:
            agent = session.execute(
                select(Agent).where(
                    Agent.tenant_id == existing.id, Agent.name == "__admin__"
                )
            ).scalar_one()
            token = issue_magic_link(email, existing.id)
            return existing.id, agent.id, "(unchanged — see your prior signup email)", token

        tenant = Tenant(
            name=workspace_name or email.split("@", 1)[0],
            owner_email=email,
            tier="starter",
        )
        session.add(tenant)
        session.flush()
        raw, prefix, digest = generate_api_key()
        agent = Agent(
            tenant_id=tenant.id,
            name="__admin__",
            api_key_hash=digest,
            api_key_prefix=prefix,
        )
        session.add(agent)
        session.commit()
        token = issue_magic_link(email, tenant.id)
        return tenant.id, agent.id, raw, token


def _looks_like_email(s: str) -> bool:
    if not s or "@" not in s or len(s) > 320:
        return False
    local, _, domain = s.partition("@")
    return bool(local) and "." in domain and " " not in s


# --- Email helpers -----------------------------------------------------

def send_magic_link_email(email: str, token: str, *, is_new_signup: bool, api_key: Optional[str] = None) -> bool:
    base = get_settings().public_base_url.rstrip("/")
    link = f"{base}/auth/verify?token={token}"
    if is_new_signup and api_key:
        subject = "Welcome to QueryShield — your API key + dashboard link"
        body = (
            f"Welcome to QueryShield.\n\n"
            f"Your API key (save this now — it won't be shown again):\n\n  {api_key}\n\n"
            f"Open your dashboard:\n  {link}\n\n"
            f"Quickstart:\n"
            f"  curl -X POST {base}/v1/databases \\\n"
            f"    -H 'X-Admin-Key: {api_key}' \\\n"
            f"    -H 'Content-Type: application/json' \\\n"
            f"    -d '{{\"alias\":\"prod\",\"db_type\":\"postgresql\",\"connection_string\":\"postgresql://...\"}}'\n\n"
            f"  curl -X POST {base}/v1/query \\\n"
            f"    -H 'X-API-Key: {api_key}' \\\n"
            f"    -H 'Content-Type: application/json' \\\n"
            f"    -d '{{\"database_alias\":\"prod\",\"query\":\"how many users signed up last week\",\"mode\":\"nl\"}}'\n\n"
            f"This link expires in {MAGIC_LINK_TTL_MIN} minutes.\n"
        )
    else:
        subject = "Your QueryShield dashboard link"
        body = (
            f"Click to sign in to your QueryShield dashboard:\n\n  {link}\n\n"
            f"Link expires in {MAGIC_LINK_TTL_MIN} minutes.\n"
        )
    return send_email(email, subject, body)
