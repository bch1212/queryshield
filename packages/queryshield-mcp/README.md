# queryshield-mcp

MCP client for [QueryShield](https://queryshield.dev) — a secure SQL proxy that sits between AI agents and customer databases. Agents call a single endpoint; QueryShield translates NL → SQL via Claude, validates at the AST level (no DDL/DML), enforces per-agent row-level security, and audit-logs every query.

## Install

```bash
pip install queryshield-mcp
```

## Configure

Provision an agent API key at https://queryshield.dev, then add to your MCP client config:

```json
{
  "queryshield": {
    "command": "queryshield-mcp",
    "env": {
      "QUERYSHIELD_API_KEY": "qs_..."
    }
  }
}
```

Self-hosting? Set `QUERYSHIELD_BASE_URL` to point at your deploy.

## Tools

- `query_database(database_alias, question, max_rows)` — natural-language query
- `query_database_sql(database_alias, sql, max_rows)` — structured SELECT
- `get_audit_log(limit)` — recent attempts for the calling agent

## License

MIT

---

mcp-name: io.github.bch1212/queryshield
