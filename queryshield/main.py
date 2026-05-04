"""FastAPI application — wires the API surface together.

Routes:
- POST /v1/query                  — the proxy endpoint (NL or structured)
- GET  /v1/audit                  — recent audit log for the calling agent
- POST /v1/agents                 — create an agent + API key (tenant-scoped)
- POST /v1/databases              — register a database for the tenant
- GET  /v1/databases              — list registered databases (no creds)
- POST /v1/policies               — set/replace an RLS policy for an agent
- POST /v1/billing/checkout       — Stripe Checkout link
- POST /v1/billing/webhook        — Stripe webhook
- GET  /health, /ready            — liveness + readiness
- GET  /                          — landing page

Auth model:
- ``X-API-Key`` carries an Agent API key. The agent's tenant is derived.
- Tenant-admin endpoints (registering DBs, creating agents) authenticate via
  ``X-Admin-Key`` which is the FIRST agent issued to a tenant — there is no
  second auth tier in v1; we tag a single agent as the admin at provisioning
  time. (See provision_admin().)
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Cookie, Depends, FastAPI, Form, Header, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select

from queryshield import auth as qs_auth

from queryshield import __version__
from queryshield.audit import get_agent_logs, get_tenant_logs
from queryshield.billing import (
    check_quota,
    create_checkout_session,
    handle_webhook,
    increment_quota,
)
from queryshield.config import get_settings
from queryshield.models import (
    Agent,
    AgentRegistration,
    AgentRegistrationResult,
    DatabaseRegistration,
    QueryRequest,
    QueryResult,
    RLSPolicy,
    SessionLocal,
    Tenant,
    Tier,
    generate_api_key,
    hash_api_key,
    init_db,
)
from queryshield.network_safety import UnsafeDatabaseHost, assert_safe_database_url
from queryshield.notifications import discord_alert
from queryshield.proxy import execute_query
from queryshield.rate_limit import check as rl_check, client_ip
from queryshield.rls import upsert_policy
from queryshield.vault import (
    delete_database,
    list_databases,
    store_connection,
)

logging.basicConfig(
    level=get_settings().log_level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("queryshield.main")


def _validate_production_config() -> None:
    settings = get_settings()
    if not settings.is_production:
        return
    required = {
        "ANTHROPIC_API_KEY": settings.anthropic_api_key,
        "DATABASE_URL": settings.database_url,
        "VAULT_KEY": settings.vault_key,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        msg = f"Refusing to start in production — missing: {missing}"
        log.error(msg)
        raise RuntimeError(msg)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_production_config()
    settings = get_settings()
    log.info("QueryShield starting (env=%s, version=%s)", settings.env, __version__)
    try:
        init_db()
        log.info("DB schema initialized")
    except Exception as e:  # noqa: BLE001
        log.exception("init_db failed at startup: %s", e)
    if settings.is_production:
        discord_alert("QueryShield boot", f"v{__version__} — env={settings.env}", "info")
    try:
        yield
    finally:
        log.info("QueryShield shutting down")


app = FastAPI(
    title="QueryShield",
    version=__version__,
    description=(
        "Secure SQL proxy between AI agents and enterprise databases. "
        "Validate intent, translate NL → SQL, enforce row-level security per "
        "agent identity, and audit-log every query."
    ),
    lifespan=lifespan,
)


# --- Streamable-HTTP MCP transport ------------------------------------
# Hosted agent platforms (Vercel AI, LangGraph Cloud, Cloudflare Agents, etc.)
# can't shell out to the stdio MCP, so we also expose the same tools over
# HTTP at /mcp. Auth: agents send their normal X-API-Key header, which the
# MCP tools read from the request context (forwarded as bearer to /v1/query).
try:
    from queryshield.mcp_http import build_mcp_app

    app.mount("/mcp", build_mcp_app())
except Exception as _mcp_exc:  # noqa: BLE001
    log.warning("MCP HTTP transport not mounted: %s", _mcp_exc)


# --- Auth dependencies -------------------------------------------------

async def _agent_from_key(x_api_key: str) -> Agent:
    digest = hash_api_key(x_api_key)
    with SessionLocal() as session:
        agent = session.execute(
            select(Agent).where(Agent.api_key_hash == digest, Agent.active.is_(True))
        ).scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=401, detail="invalid or inactive API key")
    return agent


async def require_agent(x_api_key: str = Header(..., alias="X-API-Key")) -> Agent:
    return await _agent_from_key(x_api_key)


async def require_admin(x_admin_key: str = Header(..., alias="X-Admin-Key")) -> Agent:
    """Admin = the first agent provisioned for a tenant (name == '__admin__')."""
    import secrets as _secrets

    agent = await _agent_from_key(x_admin_key)
    # Constant-time comparison so attackers can't time-side-channel the
    # difference between "valid key, not admin" and "valid key, is admin".
    if not _secrets.compare_digest(agent.name or "", "__admin__"):
        raise HTTPException(status_code=403, detail="admin key required for this endpoint")
    return agent


# --- Health ------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "queryshield", "version": __version__}


@app.get("/ready")
def ready() -> JSONResponse:
    from sqlalchemy import text

    from queryshield.models import ENGINE

    checks = {"db": "unknown"}
    healthy = True
    try:
        with ENGINE.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as e:  # noqa: BLE001
        checks["db"] = f"error: {type(e).__name__}: {e}"[:200]
        healthy = False
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ready" if healthy else "degraded", "checks": checks},
    )


# --- Query proxy -------------------------------------------------------

@app.post("/v1/query", response_model=QueryResult)
async def query_endpoint(
    request: QueryRequest,
    http_request: Request,
    agent: Agent = Depends(require_agent),
):
    ip = client_ip(http_request)
    allowed, retry = rl_check(ip, "query", limit=120, window_sec=60)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={"reason": "ip rate limit", "retry_after_sec": retry},
            headers={"Retry-After": str(retry)},
        )
    allowed, info = await check_quota(agent.tenant_id)
    if not allowed:
        raise HTTPException(status_code=429, detail=info)

    # The dependency already validated the key; resolve the policy keyed by
    # the authenticated agent + alias.
    policy = _resolve_policy_for(agent, request.database_alias)
    try:
        result = await execute_query(request, policy, agent)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    increment_quota(agent.tenant_id, by=1)
    return result


def _resolve_policy_for(agent: Agent, database_alias: str) -> RLSPolicy:
    """Build the policy directly from the authenticated agent + alias."""
    from queryshield.models import RLSPolicyRow

    with SessionLocal() as session:
        row = session.execute(
            select(RLSPolicyRow).where(
                RLSPolicyRow.agent_id == agent.id,
                RLSPolicyRow.database_alias == database_alias,
            )
        ).scalar_one_or_none()

    if row is None:
        return RLSPolicy(agent_id=agent.id, database_alias=database_alias)
    return RLSPolicy(
        agent_id=agent.id,
        database_alias=database_alias,
        allowed_schemas=[s.lower() for s in (row.allowed_schemas or [])],
        allowed_tables=[t.lower() for t in (row.allowed_tables or [])],
        row_filters={k.lower(): v for k, v in (row.row_filters or {}).items()},
        read_only=row.read_only,
    )


# --- Audit -------------------------------------------------------------

@app.get("/v1/audit")
async def audit_endpoint(limit: int = 100, agent: Agent = Depends(require_agent)):
    rows = await get_agent_logs(agent.tenant_id, agent.id, limit)
    return {"agent_id": agent.id, "tenant_id": agent.tenant_id, "entries": [r.model_dump() for r in rows]}


@app.get("/v1/audit/tenant")
async def audit_tenant_endpoint(limit: int = 200, agent: Agent = Depends(require_admin)):
    rows = await get_tenant_logs(agent.tenant_id, limit)
    return {"tenant_id": agent.tenant_id, "entries": [r.model_dump() for r in rows]}


# --- Agent / DB / policy management ------------------------------------

@app.post("/v1/tenants", response_model=AgentRegistrationResult)
async def create_tenant(request: Request, name: str):
    """Boot a fresh tenant + admin agent. Open in v1 — Stripe controls cost.

    The returned admin key is the only key that can register databases /
    create more agents for this tenant.
    """
    ip = client_ip(request)
    allowed, retry = rl_check(ip, "tenants_create", limit=5, window_sec=600)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={"reason": "ip rate limit on tenant creation", "retry_after_sec": retry},
            headers={"Retry-After": str(retry)},
        )
    raw, prefix, digest = generate_api_key()
    with SessionLocal() as session:
        tenant = Tenant(name=name, tier="starter")
        session.add(tenant)
        session.flush()
        agent = Agent(
            tenant_id=tenant.id,
            name="__admin__",
            api_key_hash=digest,
            api_key_prefix=prefix,
        )
        session.add(agent)
        session.commit()
        return AgentRegistrationResult(
            agent_id=agent.id,
            api_key=raw,
            tenant_id=tenant.id,
            tier=Tier.starter,
        )


@app.post("/v1/agents", response_model=AgentRegistrationResult)
async def create_agent(reg: AgentRegistration, admin: Agent = Depends(require_admin)):
    if reg.tenant_id != admin.tenant_id:
        raise HTTPException(status_code=403, detail="tenant mismatch")
    raw, prefix, digest = generate_api_key()
    with SessionLocal() as session:
        agent = Agent(
            tenant_id=reg.tenant_id,
            name=reg.name,
            api_key_hash=digest,
            api_key_prefix=prefix,
        )
        session.add(agent)
        session.commit()
        return AgentRegistrationResult(
            agent_id=agent.id,
            api_key=raw,
            tenant_id=reg.tenant_id,
            tier=reg.tier,
        )


@app.post("/v1/databases")
async def register_database(reg: DatabaseRegistration, admin: Agent = Depends(require_admin)):
    try:
        assert_safe_database_url(reg.connection_string, reg.db_type)
    except UnsafeDatabaseHost as e:
        raise HTTPException(status_code=400, detail=f"unsafe database host: {e}")
    store_connection(
        tenant_id=admin.tenant_id,
        alias=reg.alias,
        db_type=reg.db_type,
        connection_string=reg.connection_string,
    )
    # If the admin sent any default policy fields, apply them as the admin
    # agent's own RLS policy on this DB. Other agents need explicit policies.
    if reg.allowed_schemas or reg.allowed_tables or reg.row_filters:
        upsert_policy(
            agent_id=admin.id,
            database_alias=reg.alias,
            allowed_schemas=reg.allowed_schemas,
            allowed_tables=reg.allowed_tables,
            row_filters=reg.row_filters,
        )
    return {"alias": reg.alias, "ok": True}


@app.get("/v1/databases")
async def list_dbs(admin: Agent = Depends(require_admin)):
    return {"databases": list_databases(admin.tenant_id)}


@app.delete("/v1/databases/{alias}")
async def delete_db(alias: str, admin: Agent = Depends(require_admin)):
    ok = delete_database(admin.tenant_id, alias)
    if not ok:
        raise HTTPException(status_code=404, detail="database alias not found")
    return {"alias": alias, "deleted": True}


class PolicyPayload(BaseModel):
    """Inline pydantic model — kept here to avoid a roundtrip through models.py."""
    agent_id: str
    database_alias: str
    allowed_schemas: list[str] = []
    allowed_tables: list[str] = []
    row_filters: dict[str, str] = {}
    read_only: bool = True


@app.post("/v1/policies")
async def upsert_policy_endpoint(p: PolicyPayload, admin: Agent = Depends(require_admin)):
    # Verify the target agent belongs to this tenant.
    with SessionLocal() as session:
        target = session.get(Agent, p.agent_id)
    if target is None or target.tenant_id != admin.tenant_id:
        raise HTTPException(status_code=404, detail="agent not in this tenant")
    upsert_policy(
        agent_id=p.agent_id,
        database_alias=p.database_alias,
        allowed_schemas=p.allowed_schemas,
        allowed_tables=p.allowed_tables,
        row_filters=p.row_filters,
        read_only=p.read_only,
    )
    return {"ok": True}


# --- Billing -----------------------------------------------------------

@app.post("/v1/billing/checkout")
async def billing_checkout(tier: str, success_url: str, cancel_url: str, admin: Agent = Depends(require_admin)):
    try:
        url = create_checkout_session(admin.tenant_id, tier, success_url, cancel_url)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))
    return {"checkout_url": url}


@app.post("/v1/billing/webhook")
async def billing_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    try:
        return handle_webhook(payload, sig)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"webhook error: {e}")


# --- Self-serve signup + dashboard ------------------------------------

from queryshield.web import (
    DASHBOARD_HTML,
    LANDING_HTML,
    LOGIN_HTML,
    SIGNUP_RESULT_HTML,
    VERIFY_FAILED_HTML,
)


@app.get("/", response_class=HTMLResponse)
def landing() -> str:
    return LANDING_HTML.replace("__BASE__", get_settings().public_base_url)


@app.post("/signup", response_class=HTMLResponse)
async def signup_handler(request: Request, email: str = Form(...), workspace: str = Form("")):
    ip = client_ip(request)
    allowed, retry = rl_check(ip, "signup", limit=5, window_sec=600)
    if not allowed:
        return HTMLResponse(
            LOGIN_HTML.replace(
                "__ERROR__",
                f"Too many signups from your network. Try again in {retry}s.",
            ),
            status_code=429,
            headers={"Retry-After": str(retry)},
        )
    try:
        tenant_id, _agent_id, api_key, token = qs_auth.signup(email, workspace or None)
    except ValueError as e:
        return HTMLResponse(LOGIN_HTML.replace("__ERROR__", str(e)), status_code=400)

    base = get_settings().public_base_url.rstrip("/")
    is_new = api_key.startswith("qs_")  # signup() returns "(unchanged…)" if pre-existing
    qs_auth.send_magic_link_email(email, token, is_new_signup=is_new, api_key=api_key if is_new else None)

    if is_new:
        body = (
            SIGNUP_RESULT_HTML
            .replace("__EMAIL__", email)
            .replace("__API_KEY__", api_key)
            .replace("__BASE__", base)
        )
        return HTMLResponse(body)
    return HTMLResponse(
        LOGIN_HTML.replace(
            "__ERROR__",
            "Welcome back — we sent you a fresh magic link. Check your inbox.",
        )
    )


@app.get("/login", response_class=HTMLResponse)
def login_form() -> str:
    return LOGIN_HTML.replace("__ERROR__", "")


@app.post("/login", response_class=HTMLResponse)
async def login_handler(request: Request, email: str = Form(...)):
    """Send a magic link to an existing tenant owner. Silent for unknown emails
    so we don't leak which addresses have accounts."""
    ip = client_ip(request)
    allowed, retry = rl_check(ip, "login", limit=10, window_sec=600)
    if not allowed:
        return HTMLResponse(
            LOGIN_HTML.replace("__ERROR__", f"Too many requests. Try again in {retry}s."),
            status_code=429,
            headers={"Retry-After": str(retry)},
        )
    email = email.lower().strip()
    if qs_auth._looks_like_email(email):
        with SessionLocal() as session:
            tenant = session.execute(
                select(Tenant).where(Tenant.owner_email == email)
            ).scalar_one_or_none()
        if tenant is not None:
            token = qs_auth.issue_magic_link(email, tenant.id)
            qs_auth.send_magic_link_email(email, token, is_new_signup=False)
    # Always succeed — no enumeration of registered emails.
    return HTMLResponse(
        LOGIN_HTML.replace(
            "__ERROR__", "If that email has an account, we just sent you a link."
        )
    )


@app.get("/auth/verify")
async def auth_verify(token: str = ""):
    tenant_id = qs_auth.consume_magic_link(token)
    if tenant_id is None:
        return HTMLResponse(VERIFY_FAILED_HTML, status_code=400)
    cookie = qs_auth.issue_session(tenant_id)
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        qs_auth.SESSION_COOKIE,
        cookie,
        max_age=qs_auth.SESSION_TTL_DAYS * 86400,
        httponly=True,
        secure=get_settings().is_production,
        samesite="lax",
    )
    return response


@app.get("/auth/logout")
async def auth_logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(qs_auth.SESSION_COOKIE)
    return response


def _require_session(qs_session: str | None = Cookie(default=None, alias=qs_auth.SESSION_COOKIE)) -> str:
    tenant_id = qs_auth.verify_session(qs_session)
    if tenant_id is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    return tenant_id


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(qs_session: str | None = Cookie(default=None, alias=qs_auth.SESSION_COOKIE)):
    tenant_id = qs_auth.verify_session(qs_session)
    if tenant_id is None:
        return RedirectResponse(url="/login", status_code=303)
    return HTMLResponse(DASHBOARD_HTML)


@app.get("/dashboard/data")
async def dashboard_data(tenant_id: str = Depends(_require_session)):
    """JSON snapshot for the dashboard page."""
    from queryshield.audit import get_tenant_logs as _get_logs
    from queryshield.billing import TIER_LIMITS

    with SessionLocal() as session:
        tenant = session.get(Tenant, tenant_id)
        if tenant is None:
            raise HTTPException(status_code=404)
        agents = session.execute(
            select(Agent).where(Agent.tenant_id == tenant_id)
        ).scalars().all()
        agents_data = [
            {
                "id": a.id,
                "name": a.name,
                "key_prefix": a.api_key_prefix,
                "active": a.active,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in agents
        ]
        tier = tenant.tier or "starter"
        limits = TIER_LIMITS.get(tier, TIER_LIMITS["starter"])

    databases = list_databases(tenant_id)
    logs = await _get_logs(tenant_id, limit=25)
    return {
        "tenant": {
            "id": tenant_id,
            "name": tenant.name,
            "owner_email": tenant.owner_email,
            "tier": tier,
            "queries_used": tenant.queries_used_period,
            "queries_limit": limits["queries_per_month"],
            "databases_limit": limits["databases"],
        },
        "agents": agents_data,
        "databases": databases,
        "audit": [r.model_dump(mode="json") for r in logs],
    }


@app.post("/dashboard/agents/rotate")
async def dashboard_rotate(agent_id: str = Form(...), tenant_id: str = Depends(_require_session)):
    """Rotate an agent's API key. Returns the cleartext once."""
    raw, prefix, digest = generate_api_key()
    with SessionLocal() as session:
        agent = session.get(Agent, agent_id)
        if agent is None or agent.tenant_id != tenant_id:
            raise HTTPException(status_code=404)
        agent.api_key_hash = digest
        agent.api_key_prefix = prefix
        session.commit()
    return {"agent_id": agent_id, "api_key": raw}


@app.post("/dashboard/agents")
async def dashboard_create_agent(name: str = Form(...), tenant_id: str = Depends(_require_session)):
    raw, prefix, digest = generate_api_key()
    with SessionLocal() as session:
        agent = Agent(
            tenant_id=tenant_id,
            name=name or "agent",
            api_key_hash=digest,
            api_key_prefix=prefix,
        )
        session.add(agent)
        session.commit()
        return {"agent_id": agent.id, "api_key": raw, "name": agent.name}


@app.post("/dashboard/databases")
async def dashboard_register_database(
    alias: str = Form(...),
    db_type: str = Form(...),
    connection_string: str = Form(...),
    tenant_id: str = Depends(_require_session),
):
    try:
        assert_safe_database_url(connection_string, db_type)
    except UnsafeDatabaseHost as e:
        raise HTTPException(status_code=400, detail=f"unsafe database host: {e}")
    try:
        store_connection(
            tenant_id=tenant_id,
            alias=alias,
            db_type=db_type,
            connection_string=connection_string,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"alias": alias, "ok": True}


@app.delete("/dashboard/databases/{alias}")
async def dashboard_delete_database(alias: str, tenant_id: str = Depends(_require_session)):
    if not delete_database(tenant_id, alias):
        raise HTTPException(status_code=404)
    return {"alias": alias, "deleted": True}
