"""Named credential vault — AgentVault flows on the QueryShield API.

Adapted from AgentVault's tests/test_api.py. Users, Clerk, avk_ keys, and
a second Stripe catalog are not part of this suite, so those cases are
expressed with a tenant admin key and a qs_ agent key.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from queryshield.main import app

# Obviously fake. Not a provider key.
_SECRET = "dummy_credential_value"
_OTHER = "dummy_other_credential_value"


@pytest.fixture()
def client(control_db):
    return TestClient(app)


def _tenant(client: TestClient) -> tuple[str, str]:
    r = client.post("/v1/tenants", params={"name": "Acme"})
    assert r.status_code == 200, r.text
    body = r.json()
    return body["api_key"], body["tenant_id"]


def _store(client: TestClient, admin_key: str, name: str, value: str, provider: str = "example") -> dict:
    r = client.post(
        "/v1/credentials",
        headers={"X-Admin-Key": admin_key},
        json={"name": name, "provider": provider, "value": value},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _agent(
    client: TestClient,
    admin_key: str,
    tenant_id: str,
    *,
    name: str = "worker",
    permissions: list[str] | None = None,
    budget_daily: float | None = None,
    budget_monthly: float | None = None,
) -> str:
    payload: dict = {
        "name": name,
        "tenant_id": tenant_id,
        "credential_permissions": ["*"] if permissions is None else permissions,
    }
    if budget_daily is not None:
        payload["budget_daily"] = budget_daily
    if budget_monthly is not None:
        payload["budget_monthly"] = budget_monthly
    r = client.post("/v1/agents", headers={"X-Admin-Key": admin_key}, json=payload)
    assert r.status_code == 200, r.text
    return r.json()["api_key"]


def test_suite_page_links_injectshield(client) -> None:
    r = client.get("/suite")
    assert r.status_code == 200
    assert "InjectShield" in r.text
    assert "https://github.com/bch1212/injectshield" in r.text
    assert "https://injectshield.dev" in r.text
    assert "credential" in r.text.lower()


def test_landing_mentions_suite(client) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "InjectShield" in r.text
    assert "Credential vault" in r.text


def test_create_credential_hides_value(client) -> None:
    admin, _tenant_id = _tenant(client)
    body = _store(client, admin, "openai_key", _SECRET, provider="openai")
    assert body["name"] == "openai_key"
    assert body["provider"] == "openai"
    assert "value" not in body
    assert _SECRET not in str(body)


def test_duplicate_credential_name(client) -> None:
    admin, _tenant_id = _tenant(client)
    _store(client, admin, "dup_key", _SECRET)
    r = client.post(
        "/v1/credentials",
        headers={"X-Admin-Key": admin},
        json={"name": "dup_key", "value": _OTHER},
    )
    assert r.status_code == 409


def test_credential_plan_limit(client, monkeypatch) -> None:
    from queryshield.models import TIER_LIMITS

    monkeypatch.setitem(TIER_LIMITS["starter"], "credentials", 2)
    admin, _tenant_id = _tenant(client)
    _store(client, admin, "key_0", _SECRET)
    _store(client, admin, "key_1", _OTHER)
    r = client.post(
        "/v1/credentials",
        headers={"X-Admin-Key": admin},
        json={"name": "key_2", "value": "dummy_third"},
    )
    assert r.status_code == 403
    assert "limit" in r.text.lower()


def test_list_and_update_credential(client) -> None:
    admin, _tenant_id = _tenant(client)
    created = _store(client, admin, "update_me", _SECRET)
    listed = client.get("/v1/credentials", headers={"X-Admin-Key": admin})
    assert listed.status_code == 200
    assert len(listed.json()["credentials"]) == 1
    assert _SECRET not in listed.text

    renamed = client.patch(
        f"/v1/credentials/{created['id']}",
        headers={"X-Admin-Key": admin},
        json={"name": "updated_name"},
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["name"] == "updated_name"
    assert "value" not in renamed.json()


def test_get_credential_via_vault(client) -> None:
    admin, tenant_id = _tenant(client)
    _store(client, admin, "stripe_key", _SECRET, provider="example")
    _store(client, admin, "openai_key", _OTHER, provider="example")
    _store(client, admin, "twilio_sid", "dummy_twilio_value", provider="example")
    key = _agent(
        client,
        admin,
        tenant_id,
        permissions=["stripe_*", "openai_key"],
    )
    r = client.post("/v1/vault/get/stripe_key", headers={"X-API-Key": key})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["value"] == _SECRET
    assert body["name"] == "stripe_key"
    assert body["ttl_seconds"] == 300


def test_permission_denied(client) -> None:
    admin, tenant_id = _tenant(client)
    _store(client, admin, "twilio_sid", "dummy_twilio_value")
    key = _agent(client, admin, tenant_id, permissions=["stripe_*", "openai_key"])
    r = client.post("/v1/vault/get/twilio_sid", headers={"X-API-Key": key})
    assert r.status_code == 403


def test_empty_permissions_fail_closed(client) -> None:
    admin, tenant_id = _tenant(client)
    _store(client, admin, "test_key", _SECRET)
    key = _agent(client, admin, tenant_id, permissions=[])
    r = client.post("/v1/vault/get/test_key", headers={"X-API-Key": key})
    assert r.status_code == 403


def test_credential_not_found(client) -> None:
    admin, tenant_id = _tenant(client)
    key = _agent(client, admin, tenant_id, permissions=["stripe_*"])
    r = client.post("/v1/vault/get/stripe_nonexistent", headers={"X-API-Key": key})
    assert r.status_code == 404


def test_invalid_agent_key(client) -> None:
    r = client.post(
        "/v1/vault/get/stripe_key",
        headers={"X-API-Key": "qs_not_a_real_agent_key"},
    )
    assert r.status_code == 401


def test_list_available_credentials(client) -> None:
    admin, tenant_id = _tenant(client)
    _store(client, admin, "stripe_key", _SECRET)
    _store(client, admin, "openai_key", _OTHER)
    _store(client, admin, "twilio_sid", "dummy_twilio_value")
    key = _agent(client, admin, tenant_id, permissions=["stripe_*", "openai_key"])
    r = client.get("/v1/vault/credentials", headers={"X-API-Key": key})
    assert r.status_code == 200, r.text
    names = r.json()["credentials"]
    assert "stripe_key" in names
    assert "openai_key" in names
    assert "twilio_sid" not in names


def test_database_connection_is_not_a_vault_credential(client, sample_customer_db) -> None:
    admin, tenant_id = _tenant(client)
    r = client.post(
        "/v1/databases",
        headers={"X-Admin-Key": admin},
        json={
            "alias": "prod",
            "db_type": "sqlite",
            "connection_string": sample_customer_db,
        },
    )
    assert r.status_code == 200, r.text
    key = _agent(client, admin, tenant_id, permissions=["*"])
    revealed = client.post("/v1/vault/get/prod", headers={"X-API-Key": key})
    assert revealed.status_code == 404
    assert sample_customer_db not in revealed.text
    listed = client.get("/v1/databases", headers={"X-Admin-Key": admin})
    assert sample_customer_db not in listed.text
    named = client.get("/v1/credentials", headers={"X-Admin-Key": admin})
    assert named.json()["credentials"] == []


def test_budget_enforcement_blocks_overspend(client) -> None:
    admin, tenant_id = _tenant(client)
    _store(client, admin, "test_key", _SECRET)
    key = _agent(
        client,
        admin,
        tenant_id,
        permissions=["test_key"],
        budget_daily=1.00,
        budget_monthly=10.00,
    )
    ok = client.post(
        "/v1/vault/get/test_key",
        headers={"X-API-Key": key},
        params={"cost": 0.80},
    )
    assert ok.status_code == 200, ok.text
    blocked = client.post(
        "/v1/vault/get/test_key",
        headers={"X-API-Key": key},
        params={"cost": 0.30},
    )
    assert blocked.status_code == 429
    assert "budget" in blocked.json()["detail"].lower()
    assert _SECRET not in blocked.text


def test_zero_cost_always_allowed(client) -> None:
    admin, tenant_id = _tenant(client)
    _store(client, admin, "test_key", _SECRET)
    key = _agent(
        client,
        admin,
        tenant_id,
        permissions=["*"],
        budget_daily=1.00,
    )
    for _ in range(5):
        r = client.post(
            "/v1/vault/get/test_key",
            headers={"X-API-Key": key},
            params={"cost": 0.0},
        )
        assert r.status_code == 200, r.text


def test_access_log_omits_secret(client) -> None:
    admin, tenant_id = _tenant(client)
    _store(client, admin, "openai_key", _SECRET)
    key = _agent(client, admin, tenant_id, permissions=["openai_key"])
    assert client.post("/v1/vault/get/openai_key", headers={"X-API-Key": key}).status_code == 200
    log = client.get("/v1/credentials/access-log", headers={"X-Admin-Key": admin})
    assert log.status_code == 200, log.text
    assert log.json()["entries"][0]["success"] is True
    assert _SECRET not in log.text


def test_vault_with_cost_tracking(client) -> None:
    admin, tenant_id = _tenant(client)
    _store(client, admin, "stripe_key", _SECRET)
    key = _agent(client, admin, tenant_id, permissions=["stripe_*"])
    r = client.post(
        "/v1/vault/get/stripe_key",
        headers={"X-API-Key": key},
        params={"cost": 0.50},
    )
    assert r.status_code == 200, r.text


def test_cross_tenant_isolation(client) -> None:
    admin_a, tenant_a = _tenant(client)
    admin_b, tenant_b = _tenant(client)
    created = _store(client, admin_a, "openai_key", _SECRET)
    missing = client.get(
        f"/v1/credentials/{created['id']}",
        headers={"X-Admin-Key": admin_b},
    )
    assert missing.status_code == 404
    key_b = _agent(client, admin_b, tenant_b, permissions=["*"])
    revealed = client.post("/v1/vault/get/openai_key", headers={"X-API-Key": key_b})
    assert revealed.status_code == 404
    assert _SECRET not in revealed.text
    key_a = _agent(client, admin_a, tenant_a, permissions=["openai_key"])
    ok = client.post("/v1/vault/get/openai_key", headers={"X-API-Key": key_a})
    assert ok.status_code == 200
    assert ok.json()["value"] == _SECRET


def test_dashboard_store_does_not_echo_value(client) -> None:
    from queryshield import auth as qs_auth
    from queryshield.models import SessionLocal, Tenant

    client.post("/signup", data={"email": "vault@example.com", "workspace": "Vault"})
    with SessionLocal() as session:
        tenant = session.query(Tenant).filter_by(owner_email="vault@example.com").one()
        tenant_id = tenant.id
    token = qs_auth.issue_magic_link("vault@example.com", tenant_id)
    assert client.get(f"/auth/verify?token={token}", follow_redirects=False).status_code == 303

    stored = client.post(
        "/dashboard/credentials",
        data={"name": "openai_key", "provider": "openai", "value": _SECRET},
    )
    assert stored.status_code == 200, stored.text
    assert stored.json()["name"] == "openai_key"
    assert _SECRET not in stored.text

    page = client.get("/dashboard")
    assert page.status_code == 200
    assert "Credential vault" in page.text
    assert _SECRET not in page.text

    data = client.get("/dashboard/data")
    assert data.status_code == 200
    assert data.json()["credentials"][0]["name"] == "openai_key"
    assert _SECRET not in data.text


def test_negative_cost_rejected(client) -> None:
    admin, tenant_id = _tenant(client)
    _store(client, admin, "test_key", _SECRET)
    key = _agent(client, admin, tenant_id, permissions=["*"])
    r = client.post(
        "/v1/vault/get/test_key",
        headers={"X-API-Key": key},
        params={"cost": -1},
    )
    assert r.status_code == 400
    assert _SECRET not in r.text


def test_existing_database_gains_vault_columns(control_db) -> None:
    """create_all does not add columns to a table that already exists."""
    from sqlalchemy import text

    from queryshield.models import ENGINE, init_db

    with ENGINE.begin() as conn:
        conn.execute(text("ALTER TABLE agents DROP COLUMN credential_permissions"))
        conn.execute(text("ALTER TABLE agents DROP COLUMN budget_daily"))
        conn.execute(text("ALTER TABLE agents DROP COLUMN budget_monthly"))
    init_db()
    with ENGINE.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(agents)"))}
    assert "credential_permissions" in cols
    assert "budget_daily" in cols
    assert "budget_monthly" in cols


def test_credential_allowed_patterns() -> None:
    from queryshield.credentials import credential_allowed

    assert credential_allowed([], "openai_key") is False
    assert credential_allowed(["openai_*"], "openai_key") is True
    assert credential_allowed(["stripe_*"], "openai_key") is False
    assert credential_allowed(["*"], "anything") is True
