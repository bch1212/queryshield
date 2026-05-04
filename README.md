# QueryShield

Secure SQL proxy between AI agents and enterprise databases.

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
- `get_audit_log(limit)` — recent attempts for the calling agent

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
| Audit log becomes the data exfil vector        | only metadata is stored — never rows        |
| `VAULT_KEY` rotation                           | re-encrypt rows under new key (script-driven) |

`safety.py` is the single most important module. Every additional check
that lands there should ship with a test in `tests/test_safety.py`.

---

## Pricing

| Tier        | Monthly | Databases | Queries / month | Notes                  |
| ----------- | ------- | --------- | --------------- | ---------------------- |
| Starter     | $500    | 3         | 1,000,000       |                        |
| Pro         | $1,500  | 10        | 10,000,000      | audit export           |
| Enterprise  | $3,500  | unlimited | unlimited       | SSO, SIEM webhook      |

Targets `$32.5K MRR @ 15 customers (10 Pro + 5 Enterprise)`.

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

42 tests cover:

- AST safety (24 cases — direct DDL, comments, encoded keywords, multiple
  statements, forbidden functions, missing LIMIT)
- RLS engine (6 cases — whitelist enforcement, WHERE injection, conjunction
  with existing predicates)
- Proxy end-to-end against a SQLite "customer DB" (5 cases — happy path,
  blocked DML, RLS row filtering, table whitelist, cache hit)
- HTTP integration via FastAPI TestClient (7 cases — full provisioning →
  query flow, scoped agent with RLS, auth failures)
