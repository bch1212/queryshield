"""Streamable-HTTP MCP transport for hosted agent platforms.

This is the same toolset as ``queryshield.mcp_server`` (and the standalone
``queryshield-mcp`` PyPI package), but mounted as a sub-app at ``/mcp`` of
the FastAPI process so platforms that can't fork stdio (Vercel AI,
LangGraph Cloud, Cloudflare Agents, etc.) can connect over HTTP.

The agent identifies via ``X-API-Key`` (or an MCP authorization header on
the request); we decode that header inside each tool and route to the same
proxy code path the REST endpoint uses.
"""
from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any

from fastmcp import FastMCP
from sqlalchemy import select

from queryshield.audit import get_agent_logs
from queryshield.billing import check_quota, increment_quota
from queryshield.models import Agent, QueryRequest, SessionLocal, hash_api_key
from queryshield.proxy import execute_query

log = logging.getLogger("queryshield.mcp_http")

# Per-request agent context — populated by the auth dependency below.
_AGENT: ContextVar[Agent | None] = ContextVar("queryshield_agent", default=None)


def _resolve_policy_for(agent: Agent, database_alias: str):
    from queryshield.models import RLSPolicy, RLSPolicyRow

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


def _load_agent(api_key: str) -> Agent | None:
    digest = hash_api_key(api_key)
    with SessionLocal() as session:
        return session.execute(
            select(Agent).where(Agent.api_key_hash == digest, Agent.active.is_(True))
        ).scalar_one_or_none()


def _agent_or_raise() -> Agent:
    agent = _AGENT.get()
    if agent is None:
        raise PermissionError(
            "missing API key — pass it as `X-API-Key` header on the MCP request"
        )
    return agent


def build_mcp_app():  # type: ignore[no-untyped-def]
    """Build a Starlette ASGI app exposing QueryShield tools over MCP HTTP."""
    mcp = FastMCP("QueryShield")

    @mcp.tool()
    async def query_database(
        database_alias: str, question: str, max_rows: int = 100
    ) -> dict[str, Any]:
        """Run a natural-language question against a registered database."""
        agent = _agent_or_raise()
        allowed, info = await check_quota(agent.tenant_id)
        if not allowed:
            return {"error": "quota exceeded", "detail": info}
        policy = _resolve_policy_for(agent, database_alias)
        try:
            result = await execute_query(
                QueryRequest(
                    database_alias=database_alias,
                    query=question,
                    mode="nl",
                    max_rows=max_rows,
                ),
                policy,
                agent,
            )
        except (PermissionError, ValueError, KeyError) as e:
            return {"error": str(e)}
        increment_quota(agent.tenant_id, by=1)
        return result.model_dump(mode="json")

    @mcp.tool()
    async def query_database_sql(
        database_alias: str, sql: str, max_rows: int = 100
    ) -> dict[str, Any]:
        """Run a structured SELECT against a registered database."""
        agent = _agent_or_raise()
        allowed, info = await check_quota(agent.tenant_id)
        if not allowed:
            return {"error": "quota exceeded", "detail": info}
        policy = _resolve_policy_for(agent, database_alias)
        try:
            result = await execute_query(
                QueryRequest(
                    database_alias=database_alias,
                    query=sql,
                    mode="structured",
                    max_rows=max_rows,
                ),
                policy,
                agent,
            )
        except (PermissionError, ValueError, KeyError) as e:
            return {"error": str(e)}
        increment_quota(agent.tenant_id, by=1)
        return result.model_dump(mode="json")

    @mcp.tool()
    async def get_audit_log(limit: int = 50) -> dict[str, Any]:
        """Return recent audit entries for the calling agent."""
        agent = _agent_or_raise()
        rows = await get_agent_logs(agent.tenant_id, agent.id, limit)
        return {"entries": [r.model_dump(mode="json") for r in rows]}

    # Build a Starlette ASGI app from FastMCP and wrap it with our auth
    # middleware so we can bind the agent into a ContextVar.
    # FastMCP 3.x renamed `streamable_http_app()` -> `http_app(transport=...)`.
    if hasattr(mcp, "http_app"):
        asgi_app = mcp.http_app(transport="streamable-http")
    else:
        asgi_app = mcp.streamable_http_app()  # type: ignore[attr-defined]

    async def auth_middleware(scope, receive, send):  # type: ignore[no-untyped-def]
        if scope.get("type") != "http":
            return await asgi_app(scope, receive, send)
        headers = {
            k.decode("latin-1").lower(): v.decode("latin-1")
            for k, v in scope.get("headers", [])
        }
        key = headers.get("x-api-key") or _bearer(headers.get("authorization", ""))
        token = _AGENT.set(_load_agent(key) if key else None)
        try:
            return await asgi_app(scope, receive, send)
        finally:
            _AGENT.reset(token)

    return auth_middleware


def _bearer(auth_header: str) -> str | None:
    if not auth_header:
        return None
    parts = auth_header.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None
