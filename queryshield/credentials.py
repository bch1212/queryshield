"""Named credential vault for the QueryShield proxy.

Ported from AgentVault and fitted onto the existing tenant, ``qs_`` agent
key, and ``VAULT_KEY``. Database connection strings stay in ``vault.py``
and are never returned by this module.

Permission patterns are fnmatch globs stored on the agent. An empty list
grants nothing. Audit rows hold metadata only — never the secret.
"""
from __future__ import annotations

import fnmatch
import logging
import math
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select

from queryshield.credential_crypto import decrypt_value, encrypt_value
from queryshield.models import (
    Agent,
    CredentialAccessLog,
    CredentialBudgetUsage,
    SessionLocal,
    StoredCredential,
    Tenant,
    TIER_LIMITS,
)

log = logging.getLogger("queryshield.credentials")

TTL_SECONDS = 300
_MAX_VALUE_CHARS = 100_000
_MAX_DETAILS_CHARS = 8_000


class CredentialError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _permissions(raw: Any) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, str):
        return []
    return [str(p) for p in raw if isinstance(p, str) and p]


def credential_allowed(permissions: Any, credential_name: str) -> bool:
    """True when ``credential_name`` matches a stored fnmatch pattern.

    Empty permissions fail closed. AgentVault treated an empty list as
    "allow all"; that is unsafe once every existing QueryShield agent
    would otherwise inherit every secret.
    """
    patterns = _permissions(permissions)
    if not patterns:
        return False
    return any(fnmatch.fnmatch(credential_name, pattern) for pattern in patterns)


def _public(row: StoredCredential) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "provider": row.provider,
        "rotation_interval_hours": row.rotation_interval_hours,
        "last_rotated": row.last_rotated.isoformat() if row.last_rotated else None,
        "metadata": row.details or {},
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _validate_name(name: str) -> str:
    cleaned = (name or "").strip()
    if not cleaned or len(cleaned) > 255:
        raise CredentialError(400, "credential name must be 1–255 characters")
    if "/" in cleaned or "\\" in cleaned or ".." in cleaned:
        raise CredentialError(400, "credential name cannot contain path characters")
    return cleaned


def _validate_value(value: str) -> str:
    if not isinstance(value, str) or value == "":
        raise CredentialError(400, "credential value is required")
    if len(value) > _MAX_VALUE_CHARS:
        raise CredentialError(400, "credential value is too large")
    return value


def _validate_details(details: Optional[dict]) -> dict:
    import json

    payload = details or {}
    if not isinstance(payload, dict):
        raise CredentialError(400, "metadata must be an object")
    encoded = json.dumps(payload)
    if len(encoded) > _MAX_DETAILS_CHARS:
        raise CredentialError(400, "metadata is too large")
    return payload


def _credential_limit(tenant_id: str, session) -> int:
    tenant = session.get(Tenant, tenant_id)
    tier = tenant.tier if tenant is not None else "starter"
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["starter"])
    return int(limits.get("credentials", 0))


def create_credential(
    tenant_id: str,
    name: str,
    value: str,
    provider: Optional[str] = None,
    rotation_interval_hours: Optional[int] = None,
    metadata: Optional[dict] = None,
) -> dict:
    name = _validate_name(name)
    value = _validate_value(value)
    details = _validate_details(metadata)
    if provider is not None and len(provider) > 100:
        raise CredentialError(400, "provider name is too long")
    if rotation_interval_hours is not None and rotation_interval_hours < 1:
        raise CredentialError(400, "rotation_interval_hours must be positive")

    try:
        token = encrypt_value(value)
    except RuntimeError as e:
        raise CredentialError(500, str(e)) from e

    with SessionLocal() as session:
        limit = _credential_limit(tenant_id, session)
        count = session.execute(
            select(func.count()).select_from(StoredCredential).where(
                StoredCredential.tenant_id == tenant_id
            )
        ).scalar_one()
        if limit > 0 and count >= limit:
            raise CredentialError(
                403,
                f"Credential limit reached ({limit}). Upgrade your plan for more.",
            )
        existing = session.execute(
            select(StoredCredential).where(
                StoredCredential.tenant_id == tenant_id,
                StoredCredential.name == name,
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise CredentialError(409, f"Credential '{name}' already exists")
        row = StoredCredential(
            tenant_id=tenant_id,
            name=name,
            provider=provider,
            encrypted_value=token,
            rotation_interval_hours=rotation_interval_hours,
            details=details,
        )
        session.add(row)
        session.commit()
        log.info("credentials: stored %s/%s", tenant_id, name)
        return _public(row)


def list_credentials(tenant_id: str) -> list[dict]:
    with SessionLocal() as session:
        rows = session.execute(
            select(StoredCredential)
            .where(StoredCredential.tenant_id == tenant_id)
            .order_by(StoredCredential.created_at.desc())
        ).scalars().all()
        return [_public(r) for r in rows]


def get_credential(tenant_id: str, credential_id: str) -> dict:
    with SessionLocal() as session:
        row = session.get(StoredCredential, credential_id)
        if row is None or row.tenant_id != tenant_id:
            raise CredentialError(404, "Credential not found")
        return _public(row)


def update_credential(
    tenant_id: str,
    credential_id: str,
    *,
    name: Optional[str] = None,
    provider: Optional[str] = None,
    value: Optional[str] = None,
    rotation_interval_hours: Optional[int] = None,
    metadata: Optional[dict] = None,
    fields_set: Optional[set[str]] = None,
) -> dict:
    fields_set = fields_set or set()
    with SessionLocal() as session:
        row = session.get(StoredCredential, credential_id)
        if row is None or row.tenant_id != tenant_id:
            raise CredentialError(404, "Credential not found")
        if "name" in fields_set and name is not None:
            cleaned = _validate_name(name)
            clash = session.execute(
                select(StoredCredential).where(
                    StoredCredential.tenant_id == tenant_id,
                    StoredCredential.name == cleaned,
                    StoredCredential.id != row.id,
                )
            ).scalar_one_or_none()
            if clash is not None:
                raise CredentialError(409, f"Credential '{cleaned}' already exists")
            row.name = cleaned
        if "provider" in fields_set:
            if provider is not None and len(provider) > 100:
                raise CredentialError(400, "provider name is too long")
            row.provider = provider
        if "value" in fields_set and value is not None:
            try:
                row.encrypted_value = encrypt_value(_validate_value(value))
            except RuntimeError as e:
                raise CredentialError(500, str(e)) from e
            row.last_rotated = _utcnow()
        if "rotation_interval_hours" in fields_set:
            if rotation_interval_hours is not None and rotation_interval_hours < 1:
                raise CredentialError(400, "rotation_interval_hours must be positive")
            row.rotation_interval_hours = rotation_interval_hours
        if "metadata" in fields_set and metadata is not None:
            row.details = _validate_details(metadata)
        row.updated_at = _utcnow()
        session.commit()
        log.info("credentials: updated %s/%s", tenant_id, row.name)
        return _public(row)


def delete_credential(tenant_id: str, credential_id: str) -> None:
    with SessionLocal() as session:
        row = session.get(StoredCredential, credential_id)
        if row is None or row.tenant_id != tenant_id:
            raise CredentialError(404, "Credential not found")
        session.delete(row)
        session.commit()
        log.info("credentials: deleted %s/%s", tenant_id, row.name)


def _period_key(kind: str, now: Optional[datetime] = None) -> str:
    now = now or _utcnow()
    if kind == "daily":
        return now.strftime("daily:%Y-%m-%d")
    return now.strftime("monthly:%Y-%m")


def _usage(session, agent_id: str, kind: str, limit_amount: float) -> CredentialBudgetUsage:
    key = _period_key(kind)
    row = session.execute(
        select(CredentialBudgetUsage).where(
            CredentialBudgetUsage.agent_id == agent_id,
            CredentialBudgetUsage.period_key == key,
        )
    ).scalar_one_or_none()
    if row is not None:
        row.limit_amount = limit_amount
        return row
    row = CredentialBudgetUsage(
        agent_id=agent_id,
        period_key=key,
        amount_used=0.0,
        limit_amount=limit_amount,
    )
    session.add(row)
    session.flush()
    return row


def _check_budget(session, agent: Agent, cost: float) -> tuple[bool, str]:
    if cost <= 0:
        return True, "ok"
    if agent.budget_daily is not None:
        daily = _usage(session, agent.id, "daily", agent.budget_daily)
        if daily.amount_used + cost > daily.limit_amount:
            return False, (
                f"Daily budget exceeded: ${daily.amount_used:.2f} used of "
                f"${daily.limit_amount:.2f} limit"
            )
    if agent.budget_monthly is not None:
        monthly = _usage(session, agent.id, "monthly", agent.budget_monthly)
        if monthly.amount_used + cost > monthly.limit_amount:
            return False, (
                f"Monthly budget exceeded: ${monthly.amount_used:.2f} used of "
                f"${monthly.limit_amount:.2f} limit"
            )
    return True, "ok"


def _record_spend(session, agent: Agent, cost: float) -> None:
    if cost <= 0:
        return
    if agent.budget_daily is not None:
        daily = _usage(session, agent.id, "daily", agent.budget_daily)
        daily.amount_used = round(daily.amount_used + cost, 6)
    if agent.budget_monthly is not None:
        monthly = _usage(session, agent.id, "monthly", agent.budget_monthly)
        monthly.amount_used = round(monthly.amount_used + cost, 6)


def _log_access(
    session,
    *,
    tenant_id: str,
    agent_id: str,
    credential_id: str,
    success: bool,
    error_message: Optional[str],
    ip_address: Optional[str],
    user_agent: Optional[str],
) -> None:
    session.add(
        CredentialAccessLog(
            tenant_id=tenant_id,
            agent_id=agent_id,
            credential_id=credential_id,
            action="read",
            success=success,
            error_message=error_message[:512] if error_message else None,
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
        )
    )


def reveal_credential(
    agent_id: str,
    credential_name: str,
    cost: float = 0.0,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> dict:
    """Return a decrypted credential for an agent, or raise CredentialError.

    The plaintext is the response body only. It is not written to the audit
    log or the application log.
    """
    if not math.isfinite(cost) or cost < 0:
        raise CredentialError(400, "cost must be a finite number >= 0")
    name = _validate_name(credential_name)

    with SessionLocal() as session:
        agent = session.get(Agent, agent_id)
        if agent is None or not agent.active:
            raise CredentialError(401, "invalid or inactive API key")

        row = session.execute(
            select(StoredCredential).where(
                StoredCredential.tenant_id == agent.tenant_id,
                StoredCredential.name == name,
            )
        ).scalar_one_or_none()

        if not credential_allowed(agent.credential_permissions, name):
            if row is not None:
                _log_access(
                    session,
                    tenant_id=agent.tenant_id,
                    agent_id=agent.id,
                    credential_id=row.id,
                    success=False,
                    error_message="Permission denied",
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                session.commit()
            raise CredentialError(
                403, f"Agent does not have permission to access '{name}'"
            )

        if row is None:
            raise CredentialError(404, f"Credential '{name}' not found")

        allowed, reason = _check_budget(session, agent, cost)
        if not allowed:
            _log_access(
                session,
                tenant_id=agent.tenant_id,
                agent_id=agent.id,
                credential_id=row.id,
                success=False,
                error_message=reason,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            session.commit()
            raise CredentialError(429, reason)

        try:
            value = decrypt_value(row.encrypted_value)
        except (ValueError, RuntimeError) as e:
            _log_access(
                session,
                tenant_id=agent.tenant_id,
                agent_id=agent.id,
                credential_id=row.id,
                success=False,
                error_message="Failed to decrypt credential",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            session.commit()
            log.warning("credentials: decrypt failed for %s/%s", agent.tenant_id, name)
            raise CredentialError(500, "Failed to decrypt credential") from e

        _record_spend(session, agent, cost)
        _log_access(
            session,
            tenant_id=agent.tenant_id,
            agent_id=agent.id,
            credential_id=row.id,
            success=True,
            error_message=None,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        session.commit()
        return {
            "credential_id": row.id,
            "name": row.name,
            "provider": row.provider,
            "value": value,
            "ttl_seconds": TTL_SECONDS,
        }


def list_available_names(agent_id: str) -> list[str]:
    with SessionLocal() as session:
        agent = session.get(Agent, agent_id)
        if agent is None or not agent.active:
            raise CredentialError(401, "invalid or inactive API key")
        rows = session.execute(
            select(StoredCredential.name).where(
                StoredCredential.tenant_id == agent.tenant_id
            )
        ).all()
        names = [r[0] for r in rows]
        return [n for n in names if credential_allowed(agent.credential_permissions, n)]


def list_access_log(tenant_id: str, limit: int = 100) -> list[dict]:
    limit = max(1, min(limit, 1000))
    with SessionLocal() as session:
        rows = session.execute(
            select(CredentialAccessLog)
            .where(CredentialAccessLog.tenant_id == tenant_id)
            .order_by(CredentialAccessLog.created_at.desc())
            .limit(limit)
        ).scalars().all()
        return [
            {
                "id": r.id,
                "agent_id": r.agent_id,
                "credential_id": r.credential_id,
                "action": r.action,
                "ip_address": r.ip_address,
                "success": r.success,
                "error_message": r.error_message,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]


def budget_summary(tenant_id: str, agent_id: str) -> dict:
    with SessionLocal() as session:
        agent = session.get(Agent, agent_id)
        if agent is None or agent.tenant_id != tenant_id:
            raise CredentialError(404, "agent not in this tenant")
        summary: dict[str, Any] = {
            "agent_id": agent.id,
            "agent_name": agent.name,
            "daily_limit": agent.budget_daily,
            "monthly_limit": agent.budget_monthly,
            "daily_used": 0.0,
            "monthly_used": 0.0,
        }
        if agent.budget_daily is not None:
            daily = _usage(session, agent.id, "daily", agent.budget_daily)
            summary["daily_used"] = daily.amount_used
            session.commit()
        if agent.budget_monthly is not None:
            monthly = _usage(session, agent.id, "monthly", agent.budget_monthly)
            summary["monthly_used"] = monthly.amount_used
            session.commit()
        return summary


def update_agent_vault(
    tenant_id: str,
    agent_id: str,
    *,
    name: Optional[str] = None,
    credential_permissions: Optional[list[str]] = None,
    budget_daily: Optional[float] = None,
    budget_monthly: Optional[float] = None,
    active: Optional[bool] = None,
    fields_set: Optional[set[str]] = None,
) -> dict:
    fields_set = fields_set or set()
    with SessionLocal() as session:
        agent = session.get(Agent, agent_id)
        if agent is None or agent.tenant_id != tenant_id:
            raise CredentialError(404, "agent not in this tenant")
        if "name" in fields_set and name is not None:
            if not name.strip():
                raise CredentialError(400, "name is required")
            agent.name = name.strip()[:255]
        if "credential_permissions" in fields_set and credential_permissions is not None:
            if not isinstance(credential_permissions, list) or any(
                not isinstance(p, str) or not p or len(p) > 255 for p in credential_permissions
            ):
                raise CredentialError(400, "credential_permissions must be a list of patterns")
            agent.credential_permissions = list(credential_permissions)
        for field, value in (("budget_daily", budget_daily), ("budget_monthly", budget_monthly)):
            if field in fields_set:
                if value is not None and (not math.isfinite(value) or value < 0):
                    raise CredentialError(400, f"{field} must be >= 0")
                setattr(agent, field, value)
        if "active" in fields_set and active is not None:
            if agent.name == "__admin__" and active is False:
                raise CredentialError(400, "the admin agent cannot be deactivated")
            agent.active = active
        session.commit()
        return {
            "id": agent.id,
            "name": agent.name,
            "api_key_prefix": agent.api_key_prefix,
            "credential_permissions": _permissions(agent.credential_permissions),
            "budget_daily": agent.budget_daily,
            "budget_monthly": agent.budget_monthly,
            "active": agent.active,
        }
