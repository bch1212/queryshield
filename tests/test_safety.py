"""Tests for queryshield.safety.

The safety module is the single most important piece of the system: if it
ever lets a non-SELECT through, the whole proxy is compromised. These tests
cover the obvious bypass attempts plus the structural cases.
"""
from __future__ import annotations

import pytest

from queryshield.safety import validate_sql


# --- Allowed --------------------------------------------------------------

ALLOWED = [
    "SELECT id, name FROM users LIMIT 100",
    "SELECT id FROM users WHERE created_at > '2024-01-01' LIMIT 50",
    "WITH t AS (SELECT id FROM users LIMIT 10) SELECT id FROM t LIMIT 5",
    "SELECT id FROM users UNION SELECT id FROM admins LIMIT 20",
    "SELECT u.id, u.name FROM users u JOIN orgs o ON o.id = u.org_id LIMIT 100",
    "SELECT COUNT(*) AS n FROM events LIMIT 1",
]


@pytest.mark.parametrize("sql", ALLOWED)
def test_allowed_queries_pass(sql: str) -> None:
    ok, reason = validate_sql(sql)
    assert ok, f"expected pass, got: {reason}"


# --- Direct DDL / DML ----------------------------------------------------

DML_BLOCKED = [
    "INSERT INTO users (id) VALUES (1)",
    "UPDATE users SET name='x' WHERE id=1",
    "DELETE FROM users WHERE id=1",
    "DROP TABLE users",
    "CREATE TABLE foo (id INT)",
    "ALTER TABLE users ADD COLUMN x INT",
    "TRUNCATE TABLE users",
]


@pytest.mark.parametrize("sql", DML_BLOCKED)
def test_dml_blocked(sql: str) -> None:
    ok, _reason = validate_sql(sql)
    assert not ok


# --- Multiple statements -------------------------------------------------

def test_stacked_statements_blocked() -> None:
    ok, reason = validate_sql("SELECT 1 LIMIT 1; DROP TABLE users")
    assert not ok
    assert "multiple" in reason.lower()


def test_stacked_select_blocked() -> None:
    ok, _ = validate_sql("SELECT 1 LIMIT 1; SELECT 2 LIMIT 1")
    assert not ok


# --- Comment / whitespace / encoding tricks ------------------------------

def test_comment_around_drop_blocked() -> None:
    ok, _ = validate_sql("SELECT 1 LIMIT 1 /* */; /**/DR/**/OP TABLE users")
    assert not ok


def test_inline_comment_in_select_still_blocked_if_dml() -> None:
    # The keyword-filter naive impl would miss this; AST check catches it.
    ok, _ = validate_sql("SELECT/*hi*/ 1 LIMIT 1; INSERT INTO x VALUES(1)")
    assert not ok


# --- Forbidden functions ------------------------------------------------

def test_pg_sleep_blocked() -> None:
    ok, reason = validate_sql("SELECT pg_sleep(10) LIMIT 1")
    assert not ok
    assert "forbidden function" in reason.lower()


def test_load_file_blocked() -> None:
    ok, _ = validate_sql("SELECT load_file('/etc/passwd') LIMIT 1")
    assert not ok


def test_xp_cmdshell_blocked() -> None:
    ok, _ = validate_sql("SELECT * FROM xp_cmdshell('whoami') LIMIT 1")
    assert not ok


# --- LIMIT requirement --------------------------------------------------

def test_missing_limit_blocked() -> None:
    ok, reason = validate_sql("SELECT id FROM users")
    assert not ok
    assert "limit" in reason.lower()


# --- Empty / malformed --------------------------------------------------

def test_empty_blocked() -> None:
    ok, _ = validate_sql("")
    assert not ok


def test_garbage_blocked() -> None:
    ok, _ = validate_sql("not sql at all !!!")
    assert not ok


# --- Subquery integrity -------------------------------------------------

def test_dml_in_subquery_blocked() -> None:
    # sqlglot won't accept this as a select-shaped subquery, but make sure
    # the whole-tree walk would still block it if it ever did parse.
    ok, _ = validate_sql(
        "SELECT id FROM (DELETE FROM users RETURNING id) AS d LIMIT 5"
    )
    assert not ok
