"""Tests for the production hardening pass: SSRF defenses + rate limiting."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from queryshield.main import app
from queryshield.network_safety import UnsafeDatabaseHost, assert_safe_database_url
from queryshield.rate_limit import _BUCKETS, check as rl_check


@pytest.fixture(autouse=True)
def _no_email():
    with patch("queryshield.auth.send_email", return_value=True):
        yield


@pytest.fixture()
def client(control_db):
    return TestClient(app)


# --- SSRF ---------------------------------------------------------------

@pytest.mark.parametrize(
    "url",
    [
        "postgresql://user:pw@localhost:5432/db",
        "postgresql://user:pw@127.0.0.1:5432/db",
        "postgresql://user:pw@10.0.0.5:5432/db",
        "postgresql://user:pw@192.168.1.1:5432/db",
        "postgresql://user:pw@169.254.169.254:5432/db",  # AWS/Azure/GCP metadata
        "mysql://user:pw@127.0.0.1:3306/db",
    ],
)
def test_private_hosts_blocked(url: str) -> None:
    with pytest.raises(UnsafeDatabaseHost):
        assert_safe_database_url(url, "postgresql" if url.startswith("postgresql") else "mysql")


def test_sqlite_path_passes_through() -> None:
    # SQLite uses local file paths; SSRF is a no-op concern.
    assert_safe_database_url("/tmp/x.db", "sqlite")


def test_register_db_with_private_host_returns_400(client) -> None:
    r = client.post("/v1/tenants", params={"name": "T"})
    admin_key = r.json()["api_key"]
    r = client.post(
        "/v1/databases",
        headers={"X-Admin-Key": admin_key},
        json={
            "alias": "evil",
            "db_type": "postgresql",
            "connection_string": "postgresql://user:pw@127.0.0.1:5432/db",
        },
    )
    assert r.status_code == 400
    assert "unsafe database host" in r.text.lower()


# --- Rate limit ---------------------------------------------------------

def test_token_bucket_basic() -> None:
    _BUCKETS.clear()
    for _ in range(3):
        ok, _ = rl_check("1.2.3.4", "k", limit=3, window_sec=10)
        assert ok
    ok, retry = rl_check("1.2.3.4", "k", limit=3, window_sec=10)
    assert not ok
    assert retry > 0


def test_signup_rate_limit_kicks_in(client) -> None:
    _BUCKETS.clear()
    # 5 allowed per 10 min window, then 429
    for i in range(5):
        r = client.post("/signup", data={"email": f"u{i}@example.com"})
        assert r.status_code == 200
    r = client.post("/signup", data={"email": "u6@example.com"})
    assert r.status_code == 429


def test_tenants_create_rate_limit(client) -> None:
    _BUCKETS.clear()
    for _ in range(5):
        r = client.post("/v1/tenants", params={"name": "X"})
        assert r.status_code == 200
    r = client.post("/v1/tenants", params={"name": "X"})
    assert r.status_code == 429
