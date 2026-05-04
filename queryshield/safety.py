"""SQL safety validator — AST-based via sqlglot.

We deliberately don't keyword-filter ("DROP" in sql.lower()) because that's
trivially bypassable (`/**/dr/**/op`, encoded characters, hex escapes, etc.).
The whole point of using sqlglot is to make every check structural.

Public entry point: ``validate_sql(sql, dialect=None) -> (is_safe, reason)``.

Failure modes we treat as unsafe:
- parse error (we can't reason about it -> reject)
- multi-statement input (anything after `;`)
- non-SELECT root
- nested DDL/DML in any subquery, CTE, or expression
- forbidden built-in functions (pg_sleep, lo_import, copy, ...)
- missing LIMIT (the proxy enforces a row cap regardless, but we still
  require it in the SQL so query-cost is bounded at the DB)
"""
from __future__ import annotations

from typing import Optional, Tuple

import sqlglot
from sqlglot import exp

# Statements that must never appear, anywhere, in a query body.
FORBIDDEN_STATEMENT_TYPES: tuple = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Create,
    exp.Alter,
    exp.TruncateTable,
    exp.Merge,
    exp.Command,  # generic catch — includes things sqlglot can't classify
)

# Functions that should never run via the proxy.
# All lowercase. Add to this list rather than relaxing AST checks.
FORBIDDEN_FUNCTIONS: frozenset[str] = frozenset(
    {
        # Postgres
        "pg_sleep",
        "pg_read_file",
        "pg_read_binary_file",
        "pg_ls_dir",
        "pg_stat_file",
        "lo_import",
        "lo_export",
        "copy",
        "dblink",
        "dblink_exec",
        # MSSQL
        "xp_cmdshell",
        "sp_executesql",
        "openrowset",
        "openquery",
        "opendatasource",
        # MySQL
        "load_file",
        "sleep",
        "benchmark",
        # Generic exfil / waste-cycles
        "system",
        "shell",
    }
)


def validate_sql(sql: str, dialect: Optional[str] = None) -> Tuple[bool, str]:
    """Returns (is_safe, reason). ``reason`` is "OK" on success."""
    if not isinstance(sql, str) or not sql.strip():
        return False, "empty SQL"

    try:
        statements = sqlglot.parse(sql, read=dialect)
    except Exception as e:  # noqa: BLE001 — broad: any parse failure is unsafe
        return False, f"SQL parse error: {e}"

    # Filter out None entries that sqlglot returns for trailing whitespace/comments.
    statements = [s for s in statements if s is not None]

    if not statements:
        return False, "no parseable statement"
    if len(statements) > 1:
        return False, "multiple statements not allowed"

    statement = statements[0]

    # --- root must be SELECT (or a UNION-of-SELECTs / WITH...SELECT) -----
    if not _is_read_only_root(statement):
        return False, f"only SELECT is allowed, got: {type(statement).__name__}"

    # --- no nested DDL/DML anywhere --------------------------------------
    for node in statement.walk():
        # walk() yields the root too — skip it for the type check
        if node is statement:
            continue
        if isinstance(node, FORBIDDEN_STATEMENT_TYPES):
            return False, f"forbidden statement type: {type(node).__name__}"

        # Anonymous = parsed-but-unknown function name. We compare the lower
        # name against our deny-list. This catches calls sqlglot doesn't have
        # a dedicated AST class for (most pg_* / xp_* etc.).
        if isinstance(node, exp.Anonymous):
            name = (node.name or "").lower()
            if name in FORBIDDEN_FUNCTIONS:
                return False, f"forbidden function: {name}"

        # Some functions sqlglot DOES have a class for. Catch the named ones.
        if isinstance(node, exp.Func):
            name = (getattr(node, "name", None) or node.sql_name() if hasattr(node, "sql_name") else "")
            if isinstance(name, str) and name.lower() in FORBIDDEN_FUNCTIONS:
                return False, f"forbidden function: {name}"

    # --- LIMIT clause is required ---------------------------------------
    # For UNIONs the LIMIT can hang off the outer Union node; for plain
    # SELECT it lives on the statement itself.
    if statement.find(exp.Limit) is None:
        return False, "query must include a LIMIT clause"

    return True, "OK"


def _is_read_only_root(statement: exp.Expression) -> bool:
    """SELECT, UNION-of-SELECTs, and CTE-wrapped SELECT all qualify."""
    if isinstance(statement, exp.Select):
        return True
    if isinstance(statement, exp.Union):
        # Each branch of the union must itself be read-only.
        left = statement.left
        right = statement.right
        return _is_read_only_root(left) and _is_read_only_root(right)
    if isinstance(statement, exp.With):
        # `WITH ... SELECT` parses as With(this=Select(...))
        inner = statement.this
        return _is_read_only_root(inner) if inner is not None else False
    return False
