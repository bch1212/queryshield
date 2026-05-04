# QueryShield — Claude Code Context

## What this is
Secure SQL proxy between AI agents and customer databases. Agents POST to
`/v1/query` in NL or structured SQL. QueryShield validates → translates →
applies row-level security → executes → audits. Agents never see connection
strings.

## Architecture
- `proxy.py` — engine. Every query flows through `execute_query()`.
- `safety.py` — sqlglot AST validator. **Never use keyword filtering.**
- `rls.py` — AST-level WHERE injection + schema/table whitelists. Never
  string concat.
- `vault.py` — Fernet-encrypted credential store, in our internal Postgres.
  Replaces AWS Secrets Manager from the original spec (Brett's stack uses
  Railway, no AWS).
- `nl_to_sql.py` — Claude tool_use loop with `get_schema` + `validate_query`
  tools. Prompt caching on system + schema.
- `schema.py` — DB introspection with two-tier cache (in-process + Redis).
- `cache.py` — result cache. Redis if `REDIS_URL`, else in-process dict.
- `audit.py` — append-only metadata log. **Never log row contents.**
- `billing.py` — Stripe-backed quotas. 30-day rolling reset.
- `mcp_server.py` — FastMCP wrapper, distribution channel for agent
  frameworks.
- `main.py` — FastAPI app and HTTP surface.
- `start.py` — Railway entrypoint. Reads `PORT` via `os.getenv` (Railway
  exec's startCommand without a shell, so `$PORT` doesn't expand).

## Critical rules
- NEVER allow non-SELECT — `safety.py` blocks at the AST level.
- NEVER log query result rows — audit table holds metadata only.
- NEVER return raw connection strings in any API response.
- VAULT_KEY rotation = re-encrypt every row under the new key. Losing the
  key means losing access to every registered DB.
- Customer DB credentials should be **read-only** at the source. Defense
  in depth — even if safety + RLS were bypassed, the DB would refuse writes.

## Pricing tiers (`models.TIER_LIMITS`)
- Starter: $500/mo · 3 DBs · 1M queries/mo
- Pro: $1,500/mo · 10 DBs · 10M queries/mo · audit export
- Enterprise: $3,500/mo · unlimited · SSO, SIEM webhook

## MRR target
$32.5K @ 15 customers (10 Pro + 5 Enterprise). First 3 customers =
Brett's own agent stack (CastIQ, AgentFetch, GrantIQ).

## When changing safety.py
Every new check needs a test in `tests/test_safety.py`. The whole product
is built on the assumption that `validate_sql()` returns False for anything
unsafe. A regression there = a customer-side data breach.

## When changing rls.py
Same standard — add a case to `tests/test_rls.py` and at least one
end-to-end case in `tests/test_proxy_sqlite.py` confirming the rewrite
runs against a real DB.

## Deployment notes
- `python -m queryshield.start` — Railway-friendly entrypoint.
- Internal control-plane DB: Postgres provisioned by Railway. Stores
  tenants, agents, encrypted DB credentials, RLS policies, audit log.
- Customer DBs: Postgres, MySQL, MSSQL supported. SQLite supported for
  testing and small deployments.
