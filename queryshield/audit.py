"""Append-only audit log.

The contract:
- We log metadata for every query attempt: query_id, agent_id, tenant_id,
  database_alias, executed SQL (post-RLS), cached/uncached, row_count,
  execution_ms, optional blocked_reason.
- We NEVER log result rows. The whole point of a security proxy is that
  the proxy itself doesn't become a data exfiltration vector.
- The table is append-only. UPDATE / DELETE on audit_log isn't exposed
  through any code path.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import desc, select

from queryshield.models import AuditEntry, AuditLog, SessionLocal

log = logging.getLogger("queryshield.audit")


async def log_query(
    *,
    query_id: str,
    agent_id: str,
    tenant_id: str,
    database_alias: str,
    sql_executed: str,
    nl_query: Optional[str] = None,
    cached: bool = False,
    row_count: int = 0,
    execution_ms: int = 0,
    blocked_reason: Optional[str] = None,
) -> None:
    entry = AuditLog(
        query_id=query_id,
        agent_id=agent_id,
        tenant_id=tenant_id,
        database_alias=database_alias,
        sql_executed=sql_executed,
        nl_query=nl_query,
        cached=cached,
        row_count=row_count,
        execution_ms=execution_ms,
        blocked_reason=blocked_reason,
        created_at=datetime.now(timezone.utc),
    )
    try:
        with SessionLocal() as session:
            session.add(entry)
            session.commit()
    except Exception as e:  # noqa: BLE001
        # Never let audit-write failure break the user request — but do
        # surface it loudly in logs so we notice.
        log.exception("audit: failed to write log entry: %s", e)


async def get_agent_logs(
    tenant_id: str, agent_id: str, limit: int = 100
) -> List[AuditEntry]:
    """Recent audit entries scoped to one agent.

    The ``tenant_id`` filter is mandatory — never serve logs from another
    tenant even if the agent_id is right (defense-in-depth).
    """
    limit = min(max(int(limit), 1), 1000)
    with SessionLocal() as session:
        rows = session.execute(
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id, AuditLog.agent_id == agent_id)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        ).scalars().all()
    return [
        AuditEntry(
            query_id=r.query_id,
            agent_id=r.agent_id,
            tenant_id=r.tenant_id,
            database_alias=r.database_alias,
            sql_executed=r.sql_executed,
            cached=r.cached,
            row_count=r.row_count,
            execution_ms=r.execution_ms,
            blocked_reason=r.blocked_reason,
            created_at=r.created_at,
        )
        for r in rows
    ]


async def get_tenant_logs(tenant_id: str, limit: int = 200) -> List[AuditEntry]:
    limit = min(max(int(limit), 1), 1000)
    with SessionLocal() as session:
        rows = session.execute(
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        ).scalars().all()
    return [
        AuditEntry(
            query_id=r.query_id,
            agent_id=r.agent_id,
            tenant_id=r.tenant_id,
            database_alias=r.database_alias,
            sql_executed=r.sql_executed,
            cached=r.cached,
            row_count=r.row_count,
            execution_ms=r.execution_ms,
            blocked_reason=r.blocked_reason,
            created_at=r.created_at,
        )
        for r in rows
    ]
