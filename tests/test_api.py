"""HTTP-level integration tests via FastAPI's TestClient.

Walks the same flow a customer would: create tenant -> register DB ->
register agent -> set policy -> query.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from queryshield.main import app


@pytest.fixture()
def client(control_db, sample_customer_db):
    return TestClient(app)


def _create_tenant_and_db(client: TestClient, sample_customer_db: str):
    r = client.post("/v1/tenants", params={"name": "Acme"})
    assert r.status_code == 200, r.text
    admin = r.json()
    admin_key = admin["api_key"]
    tenant_id = admin["tenant_id"]

    r = client.post(
        "/v1/databases",
        headers={"X-Admin-Key": admin_key},
        json={
            "alias": "prod",
            "db_type": "sqlite",
            "connection_string": sample_customer_db,
            "allowed_tables": ["users", "orders"],
        },
    )
    assert r.status_code == 200, r.text
    return admin_key, tenant_id


def test_landing_page(client) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "QueryShield" in r.text


def test_health(client) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_admin_can_query(client, sample_customer_db) -> None:
    admin_key, _ = _create_tenant_and_db(client, sample_customer_db)
    r = client.post(
        "/v1/query",
        headers={"X-API-Key": admin_key},
        json={
            "database_alias": "prod",
            "query": "SELECT id, name FROM users LIMIT 10",
            "mode": "structured",
            "max_rows": 10,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["row_count"] == 3
    assert body["cached"] is False


def test_dml_via_api_blocked(client, sample_customer_db) -> None:
    admin_key, _ = _create_tenant_and_db(client, sample_customer_db)
    r = client.post(
        "/v1/query",
        headers={"X-API-Key": admin_key},
        json={
            "database_alias": "prod",
            "query": "DROP TABLE users",
            "mode": "structured",
            "max_rows": 10,
        },
    )
    assert r.status_code == 400
    assert "safety" in r.text.lower() or "select" in r.text.lower()


def test_unknown_db_alias_returns_404(client, sample_customer_db) -> None:
    admin_key, _ = _create_tenant_and_db(client, sample_customer_db)
    r = client.post(
        "/v1/query",
        headers={"X-API-Key": admin_key},
        json={
            "database_alias": "doesnotexist",
            "query": "SELECT 1 LIMIT 1",
            "mode": "structured",
            "max_rows": 1,
        },
    )
    assert r.status_code in (403, 404), r.text


def test_invalid_api_key(client) -> None:
    r = client.post(
        "/v1/query",
        headers={"X-API-Key": "qs_not_real"},
        json={
            "database_alias": "prod",
            "query": "SELECT 1 LIMIT 1",
            "mode": "structured",
            "max_rows": 1,
        },
    )
    assert r.status_code == 401


def test_register_secondary_agent_and_query(client, sample_customer_db) -> None:
    admin_key, tenant_id = _create_tenant_and_db(client, sample_customer_db)

    # Provision a non-admin agent.
    r = client.post(
        "/v1/agents",
        headers={"X-Admin-Key": admin_key},
        json={"name": "reporting", "tenant_id": tenant_id, "tier": "starter"},
    )
    assert r.status_code == 200, r.text
    new = r.json()
    new_key = new["api_key"]

    # Apply a row filter limiting them to tenant_id='t1'.
    r = client.post(
        "/v1/policies",
        headers={"X-Admin-Key": admin_key},
        json={
            "agent_id": new["agent_id"],
            "database_alias": "prod",
            "allowed_schemas": [],
            "allowed_tables": ["users", "orders"],
            "row_filters": {"users": "tenant_id = 't1'"},
        },
    )
    assert r.status_code == 200, r.text

    # The new agent only sees the t1 rows.
    r = client.post(
        "/v1/query",
        headers={"X-API-Key": new_key},
        json={
            "database_alias": "prod",
            "query": "SELECT id, name FROM users LIMIT 10",
            "mode": "structured",
            "max_rows": 10,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["row_count"] == 2
    assert "tenant_id" in body["sql_executed"]
