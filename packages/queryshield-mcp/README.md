# queryshield-mcp

MCP client for [QueryShield](https://queryshield.dev) — the agent security suite. One `QUERYSHIELD_API_KEY` reaches the SQL proxy and the named credential vault. [InjectShield](https://injectshield.dev) is the free prompt-injection funnel and stays a separate project.

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
- `list_credentials()` — credential names this agent may read
- `get_credential(name, cost=0)` — decrypt one permitted credential
- `get_audit_log(limit)` — recent attempts for the calling agent

`list_credentials` and `get_credential` are in this source tree. They ship in the next PyPI release of `queryshield-mcp`. The Docker image used for MCP directory introspection still installs the published package until that release is out.

## License

MIT

---

mcp-name: io.github.bch1212/queryshield
