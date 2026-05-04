"""Row-level security engine.

Two responsibilities:

1. Resolve the policy for an authenticated request — given an api key, find
   the agent, and given a (agent, database_alias), return the RLS policy.
2. Apply the policy to a SELECT statement by injecting a WHERE filter
   AT THE AST LEVEL (never string concatenation — that's how injection
   attacks happen).

Policy semantics:
- ``allowed_schemas`` / ``allowed_tables`` are whitelists. Empty list
  means "no filter" (allow any). Non-empty means "only these are allowed".
- ``row_filters`` maps lowercased table_name -> a SQL WHERE-clause
  fragment, e.g. ``{"orders": "tenant_id = '42'"}``. The fragment is
  appended via AST.where(); we don't string-concat into the original SQL.
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

import sqlglot
from sqlglot import exp
from sqlalchemy import select

from queryshield.models import (
    Agent,
    RLSPolicy,
    RLSPolicyRow,
    SessionLocal,
    hash_api_key,
)

log = logging.getLogger("queryshield.rls")


def get_policy_for_agent(api_key: str, database_alias: str) -> Optional[Tuple[RLSPolicy, Agent]]:
    """Resolve (policy, agent) from an API key + alias.

    Returns None when the key isn't recognised. When the key is recognised
    but no policy exists for the alias, we return an open policy (no
    schema/table whitelist, no row filters) — which will still get blocked
    by safety + can be tightened by the customer.
    """
    digest = hash_api_key(api_key)
    with SessionLocal() as session:
        agent = session.execute(
            select(Agent).where(Agent.api_key_hash == digest, Agent.active.is_(True))
        ).scalar_one_or_none()
        if agent is None:
            return None

        policy_row = session.execute(
            select(RLSPolicyRow).where(
                RLSPolicyRow.agent_id == agent.id,
                RLSPolicyRow.database_alias == database_alias,
            )
        ).scalar_one_or_none()

    if policy_row is None:
        policy = RLSPolicy(
            agent_id=agent.id,
            database_alias=database_alias,
            allowed_schemas=[],
            allowed_tables=[],
            row_filters={},
        )
    else:
        policy = RLSPolicy(
            agent_id=agent.id,
            database_alias=database_alias,
            allowed_schemas=[s.lower() for s in (policy_row.allowed_schemas or [])],
            allowed_tables=[t.lower() for t in (policy_row.allowed_tables or [])],
            row_filters={k.lower(): v for k, v in (policy_row.row_filters or {}).items()},
            read_only=policy_row.read_only,
        )

    # Detached copy so callers can't accidentally mutate the agent ORM row
    detached = Agent(
        id=agent.id,
        tenant_id=agent.tenant_id,
        name=agent.name,
        api_key_hash=agent.api_key_hash,
        api_key_prefix=agent.api_key_prefix,
        active=agent.active,
        created_at=agent.created_at,
    )
    return policy, detached


def upsert_policy(
    agent_id: str,
    database_alias: str,
    allowed_schemas: list[str],
    allowed_tables: list[str],
    row_filters: dict[str, str],
    read_only: bool = True,
) -> None:
    with SessionLocal() as session:
        existing = session.execute(
            select(RLSPolicyRow).where(
                RLSPolicyRow.agent_id == agent_id,
                RLSPolicyRow.database_alias == database_alias,
            )
        ).scalar_one_or_none()
        if existing is not None:
            existing.allowed_schemas = allowed_schemas
            existing.allowed_tables = allowed_tables
            existing.row_filters = row_filters
            existing.read_only = read_only
        else:
            session.add(
                RLSPolicyRow(
                    agent_id=agent_id,
                    database_alias=database_alias,
                    allowed_schemas=allowed_schemas,
                    allowed_tables=allowed_tables,
                    row_filters=row_filters,
                    read_only=read_only,
                )
            )
        session.commit()


# --- AST-level enforcement ---------------------------------------------

def apply_rls(sql: str, policy: RLSPolicy, dialect: Optional[str] = None) -> Tuple[str, bool]:
    """Inject WHERE filters and validate schema/table whitelists.

    Returns ``(rewritten_sql, modified_flag)``.

    Raises ``PermissionError`` if the query touches a forbidden schema/table.
    """
    statement = sqlglot.parse_one(sql, read=dialect)
    modified = False

    # Enforce schema/table whitelist for every Table node anywhere in the AST.
    for table in statement.find_all(exp.Table):
        table_name = (table.name or "").lower()
        # ``db`` is the schema in sqlglot's vocabulary
        schema_name = (table.db or "public").lower()

        if policy.allowed_schemas and schema_name not in policy.allowed_schemas:
            raise PermissionError(
                f"schema '{schema_name}' is not allowed for this agent"
            )
        if policy.allowed_tables and table_name not in policy.allowed_tables:
            raise PermissionError(
                f"table '{table_name}' is not allowed for this agent"
            )

    # Inject row filters. We do this on the outermost Select only — the
    # alternative (rewriting every nested Select that touches a filtered
    # table) is much more complex and rarely what users want.
    outermost = statement
    if isinstance(outermost, exp.With):
        outermost = outermost.this  # type: ignore[assignment]

    if isinstance(outermost, exp.Select):
        filtered_tables = {
            (t.name or "").lower()
            for t in outermost.find_all(exp.Table)
            if (t.name or "").lower() in policy.row_filters
        }

        if filtered_tables:
            combined = " AND ".join(
                f"({policy.row_filters[t]})" for t in sorted(filtered_tables)
            )
            existing_where = outermost.find(exp.Where)
            if existing_where is not None:
                # Build "(<existing>) AND (<combined>)"
                new_clause = f"({existing_where.this.sql(dialect=dialect)}) AND ({combined})"
                outermost = outermost.where(new_clause, append=False)
            else:
                outermost = outermost.where(combined)
            modified = True

            # If we started inside a WITH, swap the rewritten SELECT back in.
            if isinstance(statement, exp.With):
                statement.set("this", outermost)
            else:
                statement = outermost

    return statement.sql(dialect=dialect), modified
