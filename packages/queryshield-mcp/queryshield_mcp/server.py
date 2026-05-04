"""QueryShield MCP server.

Exposes ``query_database``, ``query_database_sql``, and ``get_audit_log`` tools
that route through the QueryShield REST API. Configuration via environment:

- ``QUERYSHIELD_API_KEY`` — agent API key (required)
- ``QUERYSHIELD_BASE_URL`` — defaults to https://api.queryshield.dev
"""
from __future__ import annotations

import os
from typing import Any

import httpx
from fastmcp import FastMCP

mcp = FastMCP("QueryShield")


def _base_url() -> str:
    return os.environ.get("QUERYSHIELD_BASE_URL", "https://api.queryshield.dev").rstrip("/")


def _api_key() -> str:
    key = os.environ.get("QUERYSHIELD_API_KEY")
    if not key:
        raise RuntimeError("QUERYSHIELD_API_KEY env var is required")
    return key


@mcp.tool()
async def query_database(
    database_alias: str,
    question: str,
    max_rows: int = 100,
) -> dict[str, Any]:
    """Run a natural-language question against a registered database.

    QueryShield translates to safe SQL, applies row-level security, and
    audit-logs the call.

    Args:
        database_alias: alias of a database registered for this tenant.
        question: natural-language question.
        max_rows: cap on returned rows (default 100, hard cap 5000).
    """
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{_base_url()}/v1/query",
            headers={"X-API-Key": _api_key()},
            json={
                "database_alias": database_alias,
                "query": question,
                "mode": "nl",
                "max_rows": max_rows,
            },
        )
        if r.status_code >= 400:
            return {"error": r.text, "status": r.status_code}
        return r.json()


@mcp.tool()
async def query_database_sql(
    database_alias: str,
    sql: str,
    max_rows: int = 100,
) -> dict[str, Any]:
    """Run a structured SELECT statement against a registered database.

    Useful when the agent already knows the schema and wants deterministic
    SQL (no LLM translation step). The same safety + RLS pipeline still
    applies — non-SELECTs are rejected.
    """
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{_base_url()}/v1/query",
            headers={"X-API-Key": _api_key()},
            json={
                "database_alias": database_alias,
                "query": sql,
                "mode": "structured",
                "max_rows": max_rows,
            },
        )
        if r.status_code >= 400:
            return {"error": r.text, "status": r.status_code}
        return r.json()


@mcp.tool()
async def get_audit_log(limit: int = 50) -> dict[str, Any]:
    """Recent audit entries for the calling agent."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{_base_url()}/v1/audit",
            headers={"X-API-Key": _api_key()},
            params={"limit": limit},
        )
        if r.status_code >= 400:
            return {"error": r.text, "status": r.status_code}
        return r.json()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
