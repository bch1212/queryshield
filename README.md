# QueryShield

[![tests](https://github.com/bch1212/queryshield/actions/workflows/test.yml/badge.svg)](https://github.com/bch1212/queryshield/actions/workflows/test.yml)

Agent security suite. QueryShield is the lead product: a secure SQL proxy and a named credential vault, one `qs_` API key, one Stripe customer, and this docs site.

Agents call a single endpoint in plain English (or structured SQL). QueryShield:

1. Translates natural language → SQL via Claude with prompt caching.
2. Validates every query at the AST level — only `SELECT` is allowed, no
   stacked statements, no forbidden functions, LIMIT required.
3. Applies per-agent row-level security: schema/table whitelists and
   `WHERE` clause injection.
4. Executes against the customer DB and returns rows.
5. Logs every attempt to an append-only audit table — metadata only,
   never row contents.

Agents never see connection strings.

The credential vault stores other secrets (API tokens the agent is allowed to use). It is the AgentVault product, folded into this service. Permission patterns decide which names an agent can read. Database connection strings stay in a separate encrypted store and are not readable through the vault.

**Free tier / funnel:** [InjectShield](https://injectshield.dev) scans untrusted text for prompt injection. It stays in its own repository ([bch1212/injectshield](https://github.com/bch1212/injectshield)) and its own API ([api.injectshield.dev](https://api.injectshield.dev)). Start there, then create one QueryShield workspace when an agent needs a database or a vault. Docs: [injectshield.dev/docs](https://injectshield.dev/docs). Suite page on this service: `/suite`.

---

## Quickstart

```bash
pip install -r requirements.txt
cp .env.example .env
# Set ANTHROPIC_API_KEY, DATABASE_URL, VAULT_KEY (see below)

python -m queryshield.start
```

Generate a Fernet key for `VAULT_KEY` once and never lose it:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## End-to-end flow (curl)

```bash
# 1) Boot a tenant. Returns the admin API key — copy it.
curl -X POST localhost:8000/v1/tenants?name=Acme

# 2) Register the customer DB. Connection string is encrypted at rest.
curl -X POST localhost:8000/v1/databases \
  -H 'X-Admin-Key: qs_...' \
  -H 'Content-Type: application/json' \
  -d '{
    "alias": "prod",
    "db_type": "postgresql",
    "connection_string": "postgresql://reader:secret@db.acme.internal:5432/app",
    "allowed_tables": ["users", "orders"]
  }'

# 3) Provision a scoped agent (different from admin) for your AI app.
curl -X POST localhost:8000/v1/agents \
  -H 'X-Admin-Key: qs_...' \
  -H 'Content-Type: application/json' \
  -d '{ "name": "reporting", "tenant_id": "<tenant>" }'

# 4) Set the agent's RLS policy.
curl -X POST localhost:8000/v1/policies \
  -H 'X-Admin-Key: qs_...' \
  -H 'Content-Type: application/json' \
  -d '{
    "agent_id": "<agent>",
    "database_alias": "prod",
    "allowed_tables": ["users", "orders"],
    "row_filters": { "users": "tenant_id = 42" }
  }'

# 4b) Store a named credential and let one agent read it.
#     The value is write-only on this call. Empty permissions grant nothing.
curl -X POST localhost:8000/v1/credentials \
  -H 'X-Admin-Key: qs_...' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "openai_key",
    "provider": "openai",
    "value": "YOUR_SECRET"
  }'

curl -X POST localhost:8000/v1/agents \
  -H 'X-Admin-Key: qs_...' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "writer",
    "tenant_id": "<tenant>",
    "credential_permissions": ["openai_*"],
    "budget_daily": 5
  }'

# The agent uses the same qs_ key it uses for /v1/query.
curl -X POST localhost:8000/v1/vault/get/openai_key \
  -H 'X-API-Key: qs_...'

# 5) The agent queries.
curl -X POST localhost:8000/v1/query \
  -H 'X-API-Key: qs_...' \
  -H 'Content-Type: application/json' \
  -d '{
    "database_alias": "prod",
    "query": "how many active users do we have?",
    "mode": "nl",
    "max_rows": 10
  }'
```

---

## MCP integration

**Listed in the [official MCP Registry](https://registry.modelcontextprotocol.io/v0/servers?search=queryshield) as `io.github.bch1212/queryshield`.**

Install the client:

```bash
pip install queryshield-mcp
```

Then drop this into your Claude Desktop / Cursor / agent config:

```json
{
  "queryshield": {
    "command": "queryshield-mcp",
    "env": { "QUERYSHIELD_API_KEY": "qs_..." }
  }
}
```

Source for the standalone PyPI package lives in `packages/queryshield-mcp/`.

For MCP directory evaluators such as Glama, the repository root also includes a slim `Dockerfile` that launches the published `queryshield-mcp` stdio server for tool introspection. The container does not need `QUERYSHIELD_API_KEY` for MCP initialization/tool discovery; the key is only required when a discovered tool is actually invoked against a QueryShield API tenant.

## MCP integration (legacy)

Drop this into any MCP-aware client (Claude Desktop, Cursor, custom agents):

```json
{
  "queryshield": {
    "command": "python",
    "args": ["-m", "queryshield.mcp_server"],
    "env": {
      "QUERYSHIELD_API_KEY": "qs_...",
      "QUERYSHIELD_BASE_URL": "https://api.queryshield.io"
    }
  }
}
```

Tools exposed:

- `query_database(database_alias, question, max_rows)` — natural-language
- `query_database_sql(database_alias, sql, max_rows)` — pre-built SELECT
- `list_credentials()` — names this agent may read
- `get_credential(name, cost)` — one permitted secret, same API key
- `get_audit_log(limit)` — recent attempts for the calling agent

The PyPI package `queryshield-mcp` picks up the vault tools on its next release. Until then, `python -m queryshield.mcp_server` from this repo already exposes them.

---

## Security model

| Threat                                         | Defense                                    |
| ---------------------------------------------- | ------------------------------------------ |
| Agent crafts a `DROP TABLE`                    | sqlglot AST refuses non-SELECT             |
| Agent sneaks `;` and a second statement        | parser rejects `len(statements) > 1`       |
| Agent uses `pg_sleep`, `xp_cmdshell`, ...      | function deny-list at the AST node level   |
| Agent reads tables outside its scope           | RLS schema + table whitelist               |
| Agent reads other tenants' rows                | `row_filters` injected via AST `.where()`  |
| Connection string leaks via stack traces       | Fernet-encrypted, never returned in any API |
| Agent reads a secret it was not granted        | fnmatch permissions; empty list fails closed |
| Vault audit becomes the secret                 | credential access log stores metadata only  |
| Audit log becomes the data exfil vector        | only metadata is stored — never rows        |
| `VAULT_KEY` rotation                           | re-encrypt rows under new key (script-driven) |

`safety.py` is the single most important module. Every additional check
that lands there should ship with a test in `tests/test_safety.py`.

---

## Pricing

| Tier         | Monthly | Databases | Credentials | Queries / month | Notes                  |
| ------------ | ------- | --------- | ----------- | --------------- | ---------------------- |
| InjectShield | free    | —         | —           | —               | prompt-injection funnel, separate site |
| Starter      | $500    | 3         | 25          | 1,000,000       |                        |
| Pro          | $1,500  | 10        | 100         | 10,000,000      | audit export           |
| Enterprise   | $3,500  | unlimited | unlimited   | unlimited       | SSO, SIEM webhook      |

QueryShield tiers are one Stripe customer. InjectShield sign-up stays on [injectshield.dev](https://injectshield.dev) until that billing is folded in. Targets `$32.5K MRR @ 15 customers (10 Pro + 5 Enterprise)`.

---

## Deploy

The repo is Railway-ready. `python -m queryshield.start` is the entrypoint
(reads `PORT` via `os.getenv`, since Railway exec's the start command without
a shell). Provision Postgres + (optionally) Redis from Railway's marketplace
and the rest is env vars.

```
railway up
```

`/health` is the liveness check. `/ready` returns 503 if the control-plane
DB is unreachable.

---

## Tests

```bash
pip install pytest
python -m pytest tests/
```

100 tests cover the original safety, RLS, proxy, and HTTP suites plus the credential vault (encryption, `qs_` key hashing, permission checks, budgets, tenant isolation, and the column migration for existing databases). The original cases:

- AST safety (24 cases — direct DDL, comments, encoded keywords, multiple
  statements, forbidden functions, missing LIMIT)
- RLS engine (6 cases — whitelist enforcement, WHERE injection, conjunction
  with existing predicates)
- Proxy end-to-end against a SQLite "customer DB" (5 cases — happy path,
  blocked DML, RLS row filtering, table whitelist, cache hit)
- HTTP integration via FastAPI TestClient (7 cases — full provisioning →
  query flow, scoped agent with RLS, auth failures)

<!-- auto-deploy verification: 2026-05-04T16:20:07Z -->
