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

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import select

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
from queryshield.notifications import discord_alert
from queryshield.proxy import execute_query
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
    agent = await _agent_from_key(x_admin_key)
    if agent.name != "__admin__":
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
    agent: Agent = Depends(require_agent),
):
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
async def create_tenant(name: str):
    """Boot a fresh tenant + admin agent. Open in v1 — Stripe controls cost.

    The returned admin key is the only key that can register databases /
    create more agents for this tenant.
    """
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


# --- Landing page -----------------------------------------------------

LANDING_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>QueryShield — secure SQL proxy for AI agents</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root { --fg: #111; --bg: #fafafa; --accent: #2563eb; }
        * { box-sizing: border-box; }
        body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
                color: var(--fg); background: var(--bg); line-height: 1.55; }
        .wrap { max-width: 760px; margin: 0 auto; padding: 56px 24px; }
        h1 { font-size: 38px; margin: 0 0 8px; letter-spacing: -0.5px; }
        .tag { color: #555; margin: 0 0 32px; font-size: 18px; }
        h2 { font-size: 22px; margin: 36px 0 8px; }
        code, pre { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 14px; }
        pre { background: #111; color: #eee; padding: 14px 16px; border-radius: 8px; overflow-x: auto; }
        a { color: var(--accent); text-decoration: none; }
        a:hover { text-decoration: underline; }
        .pill { display: inline-block; background: #eef2ff; color: var(--accent);
                padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; margin-right: 6px; }
    </style>
</head>
<body>
<div class="wrap">
    <h1>QueryShield</h1>
    <p class="tag">A secure proxy between your AI agents and your databases. Agents send natural language; we validate, translate, enforce row-level security, and audit every call.</p>

    <p>
        <span class="pill">SELECT-only AST validator</span>
        <span class="pill">Per-agent RLS</span>
        <span class="pill">Append-only audit</span>
        <span class="pill">MCP-native</span>
    </p>

    <h2>Quickstart</h2>
    <pre><code>curl -X POST __BASE__/v1/tenants?name=Acme

# response → { agent_id, api_key (admin), tenant_id }

curl -X POST __BASE__/v1/databases \\
  -H 'X-Admin-Key: qs_...' \\
  -H 'Content-Type: application/json' \\
  -d '{"alias":"prod","db_type":"postgresql","connection_string":"postgresql://..."}'

curl -X POST __BASE__/v1/query \\
  -H 'X-API-Key: qs_...' \\
  -H 'Content-Type: application/json' \\
  -d '{"database_alias":"prod","query":"how many users signed up last week","mode":"nl","max_rows":10}'</code></pre>

    <h2>Connect via MCP</h2>
    <p>Add to your Claude Desktop / Cursor / agent config:</p>
    <pre><code>{
  "queryshield": {
    "command": "python",
    "args": ["-m", "queryshield.mcp_server"],
    "env": { "QUERYSHIELD_API_KEY": "qs_..." }
  }
}</code></pre>

    <p style="margin-top: 48px; color: #888; font-size: 13px;">
        Docs at <a href="/docs">/docs</a> · Health at <a href="/health">/health</a>
    </p>
</div>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def landing() -> str:
    return LANDING_HTML_TEMPLATE.replace("__BASE__", get_settings().public_base_url)
