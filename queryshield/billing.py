"""Stripe-backed billing & quota enforcement.

Three jobs:

1. Hand a tenant a Stripe Checkout link for a tier (or upgrade their existing
   subscription).
2. On Stripe webhook, update the tenant row to reflect tier changes / lapses.
3. Enforce per-tenant per-period quotas before letting a query run.

The proxy calls ``check_quota`` on every request; we increment in-memory
on success and persist via the audit log so usage is reconstructable from
either source. The DB-side counter is the source of truth at period boundaries.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select

from queryshield.config import get_settings
from queryshield.models import (
    SessionLocal,
    Tenant,
    TIER_LIMITS,
    Tier,
)

log = logging.getLogger("queryshield.billing")


def _stripe():  # type: ignore[no-untyped-def]
    import stripe  # type: ignore

    settings = get_settings()
    if not settings.stripe_secret_key:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")
    stripe.api_key = settings.stripe_secret_key
    return stripe


def _price_for_tier(tier: str) -> Optional[str]:
    s = get_settings()
    return {
        "starter": s.stripe_price_starter,
        "pro": s.stripe_price_pro,
        "enterprise": s.stripe_price_enterprise,
    }.get(tier)


# --- Quota enforcement -------------------------------------------------

async def check_quota(tenant_id: str) -> tuple[bool, dict]:
    """Returns (allowed, info). Resets the counter on a 30-day rollover."""
    with SessionLocal() as session:
        tenant = session.get(Tenant, tenant_id)
        if tenant is None:
            return False, {"reason": "unknown tenant"}
        limits = TIER_LIMITS.get(tenant.tier, TIER_LIMITS["starter"])

        # 30-day rolling reset. SQLite drops timezone info, so normalize
        # both sides to UTC-naive before subtracting.
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        period_start = tenant.period_started_at
        if period_start is not None and period_start.tzinfo is not None:
            period_start = period_start.astimezone(timezone.utc).replace(tzinfo=None)
        if period_start and (now - period_start) > timedelta(days=30):
            tenant.queries_used_period = 0
            tenant.period_started_at = datetime.now(timezone.utc)
            session.commit()

        if tenant.queries_used_period >= limits["queries_per_month"]:
            return False, {
                "reason": "monthly quota exceeded",
                "tier": tenant.tier,
                "used": tenant.queries_used_period,
                "limit": limits["queries_per_month"],
            }
        return True, {
            "tier": tenant.tier,
            "used": tenant.queries_used_period,
            "limit": limits["queries_per_month"],
        }


def increment_quota(tenant_id: str, by: int = 1) -> None:
    with SessionLocal() as session:
        tenant = session.get(Tenant, tenant_id)
        if tenant is None:
            return
        tenant.queries_used_period = (tenant.queries_used_period or 0) + by
        session.commit()


# --- Subscription lifecycle -------------------------------------------

def create_checkout_session(tenant_id: str, tier: str, success_url: str, cancel_url: str) -> str:
    """Returns a Stripe Checkout URL the tenant can redirect to."""
    stripe = _stripe()
    price_id = _price_for_tier(tier)
    if not price_id:
        raise ValueError(f"no Stripe price configured for tier '{tier}'")

    with SessionLocal() as session:
        tenant = session.get(Tenant, tenant_id)
        if tenant is None:
            raise KeyError(f"unknown tenant {tenant_id}")
        customer_id = tenant.stripe_customer_id
        if customer_id is None:
            customer = stripe.Customer.create(metadata={"tenant_id": tenant_id})
            tenant.stripe_customer_id = customer.id
            session.commit()
            customer_id = customer.id

    session_obj = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"tenant_id": tenant_id, "tier": tier},
    )
    return session_obj.url


def handle_webhook(payload: bytes, signature: str) -> dict:
    """Process a Stripe webhook event. Returns a small status dict."""
    stripe = _stripe()
    secret = get_settings().stripe_webhook_secret
    try:
        event = stripe.Webhook.construct_event(payload, signature, secret)
    except Exception as e:  # noqa: BLE001
        log.warning("billing: webhook signature failed: %s", e)
        raise

    etype = event["type"]
    obj = event["data"]["object"]
    tenant_id = (obj.get("metadata") or {}).get("tenant_id") if isinstance(obj, dict) else None

    if etype == "checkout.session.completed":
        tier = (obj.get("metadata") or {}).get("tier", "starter")
        if tenant_id:
            _set_tenant_subscription(tenant_id, tier=tier, subscription_id=obj.get("subscription"))
            log.info("billing: tenant %s upgraded to %s", tenant_id, tier)

    elif etype in {"customer.subscription.deleted", "customer.subscription.updated"}:
        # Subscription ended or downgraded — drop to starter on cancel.
        cancel_at_period_end = obj.get("cancel_at_period_end")
        status = obj.get("status")
        if status in {"canceled", "incomplete_expired", "unpaid"}:
            if tenant_id:
                _set_tenant_subscription(tenant_id, tier="starter")
        elif cancel_at_period_end:
            log.info("billing: subscription marked to cancel at period end (%s)", tenant_id)

    return {"received": True, "type": etype}


def _set_tenant_subscription(
    tenant_id: str,
    tier: str = "starter",
    subscription_id: Optional[str] = None,
) -> None:
    with SessionLocal() as session:
        tenant = session.get(Tenant, tenant_id)
        if tenant is None:
            log.warning("billing: webhook for unknown tenant %s", tenant_id)
            return
        tenant.tier = tier
        if subscription_id:
            tenant.stripe_subscription_id = subscription_id
        session.commit()
