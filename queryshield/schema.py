"""Database schema introspection.

We hand the schema to the NL→SQL agent so it can ground generated SQL in
real columns. Two design points:

1. We cache aggressively (TTL per registered DB) — schema rarely changes
   between requests, and we don't want to hit the customer's DB every
   call. The cache is in-process by default; Redis is used if configured.

2. We never store the schema persistently in our own DB. If a row's name is
   sensitive, the customer can suppress it via the RLS allowed_tables list,
   and that filter happens on lookup.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, Optional

from queryshield.cache import cache_get_json, cache_set_json
from queryshield.vault import find_database_metadata, get_connection_string

log = logging.getLogger("queryshield.schema")

_PROCESS_CACHE: Dict[str, tuple[float, Dict[str, Any]]] = {}


async def get_schema(tenant_id: str, alias: str) -> Dict[str, Any]:
    """Returns ``{table_name: {"columns": [{"name": ..., "type": ...}, ...]}}``."""
    meta = find_database_metadata(tenant_id, alias)
    if meta is None:
        raise KeyError(f"unknown database alias: {alias}")
    ttl = meta.schema_cache_ttl or 3600

    cache_key = f"qs:schema:{tenant_id}:{alias}"

    # In-process L1
    entry = _PROCESS_CACHE.get(cache_key)
    if entry and entry[0] > time.time():
        return entry[1]

    # Shared cache L2 (Redis if configured)
    cached = await cache_get_json(cache_key)
    if cached:
        _PROCESS_CACHE[cache_key] = (time.time() + ttl, cached)
        return cached

    # Cold path — go to the source.
    conn_info = await get_connection_string(tenant_id, alias)
    schema = await _introspect(conn_info)

    _PROCESS_CACHE[cache_key] = (time.time() + ttl, schema)
    await cache_set_json(cache_key, schema, ttl=ttl)
    return schema


def invalidate_schema(tenant_id: str, alias: str) -> None:
    _PROCESS_CACHE.pop(f"qs:schema:{tenant_id}:{alias}", None)


# --- Per-engine introspection -----------------------------------------

async def _introspect(conn_info: dict) -> Dict[str, Any]:
    db_type = conn_info["type"]
    if db_type == "postgresql":
        return await _introspect_postgres(conn_info["url"])
    if db_type == "mysql":
        return await _introspect_mysql(conn_info["url"])
    if db_type == "mssql":
        return await _introspect_mssql(conn_info["dsn"])
    if db_type == "sqlite":
        return await _introspect_sqlite(conn_info["path"])
    raise ValueError(f"introspection not implemented for {db_type}")


async def _introspect_sqlite(path: str) -> Dict[str, Any]:
    def _sync() -> Dict[str, Any]:
        import sqlite3

        c = sqlite3.connect(path)
        try:
            cur = c.cursor()
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = [row[0] for row in cur.fetchall()]
            out: Dict[str, Any] = {}
            for t in tables:
                cur.execute(f"PRAGMA table_info({t})")
                cols = [{"name": r[1], "type": r[2]} for r in cur.fetchall()]
                out[t] = {"columns": cols}
            return out
        finally:
            c.close()

    return await asyncio.get_event_loop().run_in_executor(None, _sync)


async def _introspect_postgres(url: str) -> Dict[str, Any]:
    import asyncpg  # type: ignore

    conn = await asyncpg.connect(url)
    try:
        rows = await conn.fetch(
            """
            SELECT table_schema, table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema NOT IN ('pg_catalog','information_schema')
            ORDER BY table_schema, table_name, ordinal_position
            """
        )
    finally:
        await conn.close()
    return _group_columns(rows)


async def _introspect_mysql(url: str) -> Dict[str, Any]:
    # Run pymysql in a thread to keep the API uniformly async.
    def _sync() -> list:
        import pymysql
        from urllib.parse import urlparse

        u = urlparse(url)
        c = pymysql.connect(
            host=u.hostname,
            port=u.port or 3306,
            user=u.username,
            password=u.password,
            database=(u.path or "/").lstrip("/"),
        )
        try:
            cur = c.cursor()
            cur.execute(
                """
                SELECT table_schema, table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema NOT IN ('mysql','sys','performance_schema','information_schema')
                ORDER BY table_schema, table_name, ordinal_position
                """
            )
            return [
                {"table_schema": r[0], "table_name": r[1], "column_name": r[2], "data_type": r[3]}
                for r in cur.fetchall()
            ]
        finally:
            c.close()

    rows = await asyncio.get_event_loop().run_in_executor(None, _sync)
    return _group_columns(rows)


async def _introspect_mssql(dsn: str) -> Dict[str, Any]:
    def _sync() -> list:
        import pyodbc

        c = pyodbc.connect(dsn, timeout=10)
        try:
            cur = c.cursor()
            cur.execute(
                """
                SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE
                FROM INFORMATION_SCHEMA.COLUMNS
                ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
                """
            )
            return [
                {"table_schema": r[0], "table_name": r[1], "column_name": r[2], "data_type": r[3]}
                for r in cur.fetchall()
            ]
        finally:
            c.close()

    rows = await asyncio.get_event_loop().run_in_executor(None, _sync)
    return _group_columns(rows)


def _group_columns(rows) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for r in rows:
        # asyncpg returns Records (mapping-like), pymysql/pyodbc return dicts.
        schema = r["table_schema"]
        table = r["table_name"]
        key = f"{schema}.{table}" if schema and schema != "public" else table
        bucket = out.setdefault(key, {"columns": []})
        bucket["columns"].append(
            {"name": r["column_name"], "type": str(r["data_type"])}
        )
    return out
