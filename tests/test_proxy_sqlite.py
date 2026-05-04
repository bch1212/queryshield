"""End-to-end exercise of the proxy against a SQLite "customer DB".

We bypass the NL→SQL step (mode='structured') so the test doesn't need a
real Anthropic key. The whole rest of the pipeline — vault decrypt, schema,
safety, RLS, cache, audit — runs for real.
"""
from __future__ import annotations

import asyncio

import pytest

from queryshield.audit import get_agent_logs
from queryshield.models import (
    Agent,
    QueryRequest,
    SessionLocal,
    Tenant,
    generate_api_key,
)
from queryshield.proxy import execute_query
from queryshield.rls import upsert_policy
from queryshield.vault import store_connection


def _provision(sample_db_path: str) -> tuple[Tenant, Agent]:
    raw, prefix, digest = generate_api_key()
    with SessionLocal() as session:
        tenant = Tenant(name="acme", tier="starter")
        session.add(tenant)
        session.flush()
        agent = Agent(
            tenant_id=tenant.id,
            name="reporting-agent",
            api_key_hash=digest,
            api_key_prefix=prefix,
        )
        session.add(agent)
        session.commit()
        # Detached copies safe to use after the session closes.
        return Tenant(id=tenant.id, name=tenant.name, tier=tenant.tier), Agent(
            id=agent.id,
            tenant_id=agent.tenant_id,
            name=agent.name,
            api_key_hash=agent.api_key_hash,
            api_key_prefix=agent.api_key_prefix,
            active=True,
        )


def test_structured_select_runs(control_db, sample_customer_db) -> None:
    tenant, agent = _provision(sample_customer_db)
    store_connection(tenant.id, "prod", "sqlite", sample_customer_db)

    from queryshield.models import RLSPolicy

    policy = RLSPolicy(
        agent_id=agent.id, database_alias="prod",
        allowed_tables=["users", "orders"],
    )

    request = QueryRequest(
        database_alias="prod",
        query="SELECT id, name FROM users LIMIT 10",
        mode="structured",
        max_rows=10,
    )
    result = asyncio.run(execute_query(request, policy, agent))
    assert result.row_count == 3
    assert {r["name"] for r in result.rows} == {"alice", "bob", "carol"}


def test_dml_blocked(control_db, sample_customer_db) -> None:
    tenant, agent = _provision(sample_customer_db)
    store_connection(tenant.id, "prod", "sqlite", sample_customer_db)

    from queryshield.models import RLSPolicy

    policy = RLSPolicy(agent_id=agent.id, database_alias="prod")

    request = QueryRequest(
        database_alias="prod",
        query="DELETE FROM users",
        mode="structured",
        max_rows=10,
    )
    with pytest.raises(ValueError):
        asyncio.run(execute_query(request, policy, agent))

    # Audit log must capture the block reason.
    rows = asyncio.run(get_agent_logs(tenant.id, agent.id))
    assert any("safety" in (r.blocked_reason or "") for r in rows)


def test_rls_filter_applied(control_db, sample_customer_db) -> None:
    tenant, agent = _provision(sample_customer_db)
    store_connection(tenant.id, "prod", "sqlite", sample_customer_db)
    upsert_policy(
        agent_id=agent.id,
        database_alias="prod",
        allowed_schemas=[],
        allowed_tables=["users", "orders"],
        row_filters={"users": "tenant_id = 't1'"},
    )

    # Resolve the policy the way the API endpoint does.
    from queryshield.main import _resolve_policy_for

    policy = _resolve_policy_for(agent, "prod")

    request = QueryRequest(
        database_alias="prod",
        query="SELECT id, name FROM users LIMIT 10",
        mode="structured",
        max_rows=10,
    )
    result = asyncio.run(execute_query(request, policy, agent))
    # tenant_id='t2' rows must be filtered out.
    assert {r["name"] for r in result.rows} == {"alice", "carol"}
    assert "tenant_id" in result.sql_executed


def test_table_whitelist_blocks(control_db, sample_customer_db) -> None:
    tenant, agent = _provision(sample_customer_db)
    store_connection(tenant.id, "prod", "sqlite", sample_customer_db)
    upsert_policy(
        agent_id=agent.id,
        database_alias="prod",
        allowed_schemas=[],
        allowed_tables=["users"],  # orders not allowed
        row_filters={},
    )

    from queryshield.main import _resolve_policy_for

    policy = _resolve_policy_for(agent, "prod")
    request = QueryRequest(
        database_alias="prod",
        query="SELECT id FROM orders LIMIT 10",
        mode="structured",
        max_rows=10,
    )
    with pytest.raises(PermissionError):
        asyncio.run(execute_query(request, policy, agent))


def test_cache_hit_on_repeat(control_db, sample_customer_db) -> None:
    tenant, agent = _provision(sample_customer_db)
    store_connection(tenant.id, "prod", "sqlite", sample_customer_db)

    from queryshield.models import RLSPolicy

    policy = RLSPolicy(agent_id=agent.id, database_alias="prod")
    request = QueryRequest(
        database_alias="prod",
        query="SELECT id, name FROM users LIMIT 10",
        mode="structured",
        max_rows=10,
    )
    first = asyncio.run(execute_query(request, policy, agent))
    second = asyncio.run(execute_query(request, policy, agent))
    assert first.cached is False
    assert second.cached is True
    assert first.row_count == second.row_count
