"""Tests for the RLS engine — focus on the AST rewriting paths.

Resolution-from-DB tests need a real session and live in the integration
suite; here we stick to the pure-function ``apply_rls``.
"""
from __future__ import annotations

import pytest

from queryshield.models import RLSPolicy
from queryshield.rls import apply_rls


def _policy(**kwargs) -> RLSPolicy:
    base = dict(
        agent_id="agent-1",
        database_alias="prod",
        allowed_schemas=[],
        allowed_tables=[],
        row_filters={},
    )
    base.update(kwargs)
    return RLSPolicy(**base)


def test_no_op_when_no_filters() -> None:
    sql = "SELECT id FROM users LIMIT 10"
    out, modified = apply_rls(sql, _policy())
    assert not modified
    assert "users" in out.lower()


def test_row_filter_appended_when_no_where() -> None:
    sql = "SELECT id FROM users LIMIT 10"
    p = _policy(row_filters={"users": "tenant_id = '42'"})
    out, modified = apply_rls(sql, p)
    assert modified
    assert "tenant_id = '42'" in out


def test_row_filter_anded_with_existing_where() -> None:
    sql = "SELECT id FROM users WHERE active = TRUE LIMIT 10"
    p = _policy(row_filters={"users": "tenant_id = '42'"})
    out, modified = apply_rls(sql, p)
    assert modified
    lower = out.lower()
    assert "active = true" in lower
    assert "tenant_id = '42'" in out
    # Both predicates must be conjoined.
    assert " and " in lower


def test_table_whitelist_blocks_unlisted() -> None:
    sql = "SELECT id FROM secrets LIMIT 1"
    p = _policy(allowed_tables=["users", "orders"])
    with pytest.raises(PermissionError):
        apply_rls(sql, p)


def test_schema_whitelist_blocks_unlisted() -> None:
    sql = "SELECT id FROM private.secrets LIMIT 1"
    p = _policy(allowed_schemas=["public"])
    with pytest.raises(PermissionError):
        apply_rls(sql, p)


def test_table_whitelist_allows_listed() -> None:
    sql = "SELECT id FROM users LIMIT 1"
    p = _policy(allowed_tables=["users"])
    out, _ = apply_rls(sql, p)
    assert "users" in out.lower()
