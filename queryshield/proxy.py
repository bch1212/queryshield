"""The QueryShield engine.

A single ``execute_query`` orchestrates the full flow:

  1. Load the DB schema (cached).
  2. Translate NL → SQL via Claude (or pass through if mode='structured').
  3. Validate the SQL with safety.py — block on first violation.
  4. Apply RLS — schema/table whitelist + WHERE injection.
  5. Re-validate the rewritten SQL (defense in depth).
  6. Look up the result cache.
  7. On cache miss, execute against the customer DB with strict row caps.
  8. Audit-log every attempt, including blocked/errored ones.

Every branch writes to the audit log before returning or raising. The only
data we hand back is the rows + metadata; the original connection string
never leaves vault.py.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import uuid
from typing import Any, List, Optional

from queryshield.audit import log_query
from queryshield.cache import cache_get_json, cache_set_json
from queryshield.config import get_settings
from queryshield.models import (
    Agent,
    QueryRequest,
    QueryResult,
    RLSPolicy,
)
from queryshield.nl_to_sql import translate_nl_to_sql
from queryshield.rls import apply_rls
from queryshield.safety import validate_sql
from queryshield.schema import get_schema
from queryshield.vault import find_database_metadata, get_connection_string

log = logging.getLogger("queryshield.proxy")


async def execute_query(
    request: QueryRequest,
    policy: RLSPolicy,
    agent: Agent,
) -> QueryResult:
    settings = get_settings()
    query_id = uuid.uuid4().hex
    started = time.time()

    # Hard cap regardless of what the user asks for.
    request.max_rows = min(int(request.max_rows or 1000), settings.max_rows_hard_limit)

    # Make sure the database is registered before doing anything else.
    db_meta = find_database_metadata(agent.tenant_id, request.database_alias)
    if db_meta is None:
        await log_query(
            query_id=query_id, agent_id=agent.id, tenant_id=agent.tenant_id,
            database_alias=request.database_alias, sql_executed="",
            blocked_reason="unknown database alias",
        )
        raise PermissionError(f"unknown database alias '{request.database_alias}'")

    nl_query = request.query if request.mode == "nl" else None

    try:
        # 1) Schema (cached)
        schema = await get_schema(agent.tenant_id, request.database_alias)

        # 2) NL → SQL or pass-through
        sql = (
            await translate_nl_to_sql(request, schema)
            if request.mode == "nl"
            else request.query
        )

        # 3) Pre-RLS safety check
        ok, reason = validate_sql(sql)
        if not ok:
            await log_query(
                query_id=query_id, agent_id=agent.id, tenant_id=agent.tenant_id,
                database_alias=request.database_alias, sql_executed=sql,
                nl_query=nl_query, blocked_reason=f"safety: {reason}",
            )
            raise ValueError(f"query blocked by safety: {reason}")

        # 4) RLS rewrite
        try:
            sql_after_rls, _modified = apply_rls(sql, policy)
        except PermissionError as e:
            await log_query(
                query_id=query_id, agent_id=agent.id, tenant_id=agent.tenant_id,
                database_alias=request.database_alias, sql_executed=sql,
                nl_query=nl_query, blocked_reason=f"rls: {e}",
            )
            raise

        # 5) Defence-in-depth: re-validate after rewriting.
        ok, reason = validate_sql(sql_after_rls)
        if not ok:
            await log_query(
                query_id=query_id, agent_id=agent.id, tenant_id=agent.tenant_id,
                database_alias=request.database_alias, sql_executed=sql_after_rls,
                nl_query=nl_query, blocked_reason=f"safety_post_rls: {reason}",
            )
            raise ValueError(f"post-RLS safety check failed: {reason}")

        # 6) Cache
        cache_key = _cache_key(agent.tenant_id, request.database_alias, sql_after_rls)
        cached_rows = await cache_get_json(cache_key)
        if cached_rows is not None:
            execution_ms = int((time.time() - started) * 1000)
            await log_query(
                query_id=query_id, agent_id=agent.id, tenant_id=agent.tenant_id,
                database_alias=request.database_alias, sql_executed=sql_after_rls,
                nl_query=nl_query, cached=True, row_count=len(cached_rows),
                execution_ms=execution_ms,
            )
            return QueryResult(
                query_id=query_id,
                sql_executed=sql_after_rls,
                rows=cached_rows[: request.max_rows],
                row_count=min(len(cached_rows), request.max_rows),
                cached=True,
                execution_time_ms=execution_ms,
            )

        # 7) Execute on the customer DB
        conn_info = await get_connection_string(agent.tenant_id, request.database_alias)
        rows = await _execute_db_query(conn_info, sql_after_rls, request.max_rows)

        # 8) Cache + audit
        await cache_set_json(cache_key, rows, ttl=300)
        execution_ms = int((time.time() - started) * 1000)
        await log_query(
            query_id=query_id, agent_id=agent.id, tenant_id=agent.tenant_id,
            database_alias=request.database_alias, sql_executed=sql_after_rls,
            nl_query=nl_query, cached=False, row_count=len(rows),
            execution_ms=execution_ms,
        )

        return QueryResult(
            query_id=query_id,
            sql_executed=sql_after_rls,
            rows=rows,
            row_count=len(rows),
            cached=False,
            execution_time_ms=execution_ms,
        )

    except (PermissionError, ValueError):
        # Already logged at the point of failure.
        raise
    except Exception as e:  # noqa: BLE001
        # Unexpected — log the failure shape, but don't leak DB details.
        log.exception("proxy: unexpected error: %s", e)
        await log_query(
            query_id=query_id, agent_id=agent.id, tenant_id=agent.tenant_id,
            database_alias=request.database_alias, sql_executed="",
            nl_query=nl_query, blocked_reason=f"internal_error: {type(e).__name__}",
        )
        raise


# --- Engine-specific execution ----------------------------------------

async def _execute_db_query(conn_info: dict, sql: str, max_rows: int) -> List[dict]:
    db_type = conn_info["type"]
    if db_type == "postgresql":
        return await _exec_postgres(conn_info["url"], sql, max_rows)
    if db_type == "mysql":
        return await _exec_mysql(conn_info["url"], sql, max_rows)
    if db_type == "mssql":
        return await _exec_mssql(conn_info["dsn"], sql, max_rows)
    if db_type == "sqlite":
        return await _exec_sqlite(conn_info["path"], sql, max_rows)
    raise ValueError(f"unsupported db_type: {db_type}")


async def _exec_sqlite(path: str, sql: str, max_rows: int) -> List[dict]:
    def _sync() -> List[dict]:
        import sqlite3

        c = sqlite3.connect(path)
        try:
            c.row_factory = sqlite3.Row
            cur = c.cursor()
            cur.execute(sql)
            return [dict(row) for row in cur.fetchmany(max_rows)]
        finally:
            c.close()

    return await asyncio.get_event_loop().run_in_executor(None, _sync)


async def _exec_postgres(url: str, sql: str, max_rows: int) -> List[dict]:
    import asyncpg  # type: ignore

    conn = await asyncpg.connect(url)
    try:
        records = await conn.fetch(sql)
        return [dict(r) for r in records[:max_rows]]
    finally:
        await conn.close()


async def _exec_mysql(url: str, sql: str, max_rows: int) -> List[dict]:
    def _sync() -> list[dict]:
        import pymysql
        from urllib.parse import urlparse

        u = urlparse(url)
        c = pymysql.connect(
            host=u.hostname,
            port=u.port or 3306,
            user=u.username,
            password=u.password,
            database=(u.path or "/").lstrip("/"),
            cursorclass=pymysql.cursors.DictCursor,
        )
        try:
            cur = c.cursor()
            cur.execute(sql)
            return list(cur.fetchmany(max_rows))
        finally:
            c.close()

    return await asyncio.get_event_loop().run_in_executor(None, _sync)


async def _exec_mssql(dsn: str, sql: str, max_rows: int) -> List[dict]:
    def _sync() -> list[dict]:
        import pyodbc

        c = pyodbc.connect(dsn, timeout=10)
        try:
            cur = c.cursor()
            cur.execute(sql)
            cols = [col[0] for col in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchmany(max_rows)]
        finally:
            c.close()

    return await asyncio.get_event_loop().run_in_executor(None, _sync)


def _cache_key(tenant_id: str, alias: str, sql: str) -> str:
    digest = hashlib.sha256(sql.encode("utf-8")).hexdigest()[:32]
    return f"qs:result:{tenant_id}:{alias}:{digest}"
