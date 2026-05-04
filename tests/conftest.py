"""Test fixtures.

We use a per-session SQLite file for the internal control-plane DB and a
separate one for the simulated customer DB. Anthropic + Stripe are not
exercised in unit tests — those live behind environment guards in their
respective modules.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

# Make sure the package under test is importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Configure env BEFORE any queryshield module is imported. This MUST happen
# at conftest import time (not in a fixture) because models.py creates the
# SQLAlchemy ENGINE at module import using the env-time DATABASE_URL.
_TEST_TMP = tempfile.mkdtemp(prefix="queryshield-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_TMP}/control.db"
os.environ["VAULT_KEY"] = "RIaPxXZl9MNm7ESjqpsnbsiBCDkfErP6Mum0lmGD-7w="  # fixed test key
os.environ["ENVIRONMENT"] = "test"
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"


@pytest.fixture()
def control_db():
    """Init the control plane schema fresh for every test."""
    from queryshield.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]
    from queryshield.models import Base, ENGINE

    Base.metadata.drop_all(bind=ENGINE)
    Base.metadata.create_all(bind=ENGINE)
    yield
    Base.metadata.drop_all(bind=ENGINE)


@pytest.fixture()
def sample_customer_db():
    """A small SQLite file populated with a users + orders schema."""
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    path = f.name
    c = sqlite3.connect(path)
    try:
        c.executescript(
            """
            CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, tenant_id TEXT, active INTEGER);
            CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, amount REAL, tenant_id TEXT);
            INSERT INTO users (id, name, tenant_id, active) VALUES
                (1, 'alice', 't1', 1),
                (2, 'bob', 't2', 1),
                (3, 'carol', 't1', 0);
            INSERT INTO orders (id, user_id, amount, tenant_id) VALUES
                (10, 1, 50.0, 't1'),
                (11, 2, 80.0, 't2'),
                (12, 1, 25.0, 't1');
            """
        )
        c.commit()
    finally:
        c.close()
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass
