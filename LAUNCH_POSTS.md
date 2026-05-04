# Launch posts — staged drafts

Brett owns posting timing. Nothing goes out unless he fires it manually.

Each section is copy-paste ready. Targets are listed in priority order; you don't need to do them all.

---

## Show HN

**Title** (≤ 80 chars):

```
Show HN: QueryShield – secure SQL proxy for AI agents (NL→SQL, AST safety, RLS)
```

**Body:**

```
I built QueryShield because every AI agent that touches a customer database is one bad prompt away from a data breach. The agents send natural language; QueryShield translates to SQL via Claude, validates the SQL at the AST level (sqlglot — never keyword filtering, which is trivially bypassable), enforces per-agent row-level security, and audit-logs every call. Connection strings stay in an encrypted vault; agents never see them.

What's actually interesting under the hood:

- safety.py uses sqlglot's parser to enforce SELECT-only, reject stacked statements, deny-list dangerous functions (pg_sleep, xp_cmdshell, lo_import, ...), and require a LIMIT. Comment-bypass tricks like `/**/dr/**/op` get parsed structurally and rejected.
- rls.py rewrites WHERE clauses at the AST level — never string concat. Schema and table whitelists too.
- The proxy runs validate_sql twice — once on the model's output, once on the post-RLS rewrite — so even a buggy RLS rule can't accidentally smuggle DML through.
- Native MCP server (stdio + streamable-HTTP), so any Claude Desktop / Cursor / LangGraph / Vercel AI agent can drop it in.

Pricing: $500/mo Starter (3 DBs, 1M queries) → $3,500/mo Enterprise (unlimited, SSO, SIEM webhook). Free 14-day trial, no credit card.

The code is MIT, deployed to Railway, source: https://github.com/bch1212/queryshield
Live: https://queryshield.dev
MCP Registry: io.github.bch1212/queryshield
PyPI: queryshield-mcp

Happy to answer anything about the AST validator design or the RLS engine.
```

**HN tactics:** post Tuesday/Wednesday morning ET. Reply to every early comment within 15 minutes. Do not link to social media or self-vote.

---

## Product Hunt

**Tagline (≤ 60 chars):**

```
The security layer your AI agent stack is missing.
```

**Description:**

```
QueryShield is a secure proxy that sits between your AI agents and your databases. Agents send natural language; we translate to safe SQL, enforce per-agent row-level security, and audit-log every call. Connection strings never leave the vault.

✓ AST-based safety (sqlglot) — only SELECT, no DDL/DML, no stacked statements, no dangerous functions
✓ Per-agent RLS — schema/table whitelists + WHERE-clause injection at the AST
✓ Append-only audit log — metadata only, never row contents
✓ MCP-native — drop into Claude Desktop, Cursor, LangGraph, Vercel AI in one line
✓ PostgreSQL, MySQL, MSSQL, SQLite

Free tier: 3 databases, 1M queries/month, no credit card.
```

**Gallery assets to attach:** dashboard screenshot, architecture diagram, MCP-config-snippet GIF.

---

## /r/ClaudeAI

**Title:**

```
I built a security layer for Claude agents that touch databases — open source, MCP-native
```

**Body:**

```
Hey all — wanted to share QueryShield, an MCP server I built for the case where you want an agent to query a real database without giving it the connection string or trusting it not to write a `DROP TABLE`.

The flow: agent calls `query_database("how many users signed up last week", database_alias="prod")`. QueryShield (a) translates NL → SQL via Claude, (b) parses the SQL with sqlglot and rejects anything that isn't a SELECT (no keyword filtering — that's trivially bypassed), (c) injects a WHERE clause based on the agent's RLS policy, (d) executes against the customer DB, (e) audit-logs the metadata.

The code is MIT and the pip package is `queryshield-mcp`. Listed in the official MCP Registry as `io.github.bch1212/queryshield`. The hosted proxy runs at queryshield.dev — free 14-day trial.

I'd love feedback on the AST validator if anyone has time — that's the most security-critical piece. The 24 test cases in `tests/test_safety.py` cover obvious bypass attempts but I'd like more eyes.
```

**Subreddit etiquette:** post once, don't crosspost-spam. Reply to questions, don't lecture.

---

## /r/mcp

**Title:**

```
QueryShield MCP server — secure SQL proxy with RLS + audit log
```

**Body:**

```
Just published `queryshield-mcp` to PyPI and the official MCP Registry as `io.github.bch1212/queryshield`. It's a stdio MCP server (also exposed over streamable-HTTP at `https://api.queryshield.dev/mcp/`) that gives agents three tools:

- `query_database(database_alias, question, max_rows)` — natural language
- `query_database_sql(database_alias, sql, max_rows)` — pre-built SELECT
- `get_audit_log(limit)` — recent call history for the agent

Each call goes through sqlglot AST validation (SELECT-only, no DDL/DML, no `pg_sleep`/`xp_cmdshell`/etc, LIMIT required), per-agent row-level security via WHERE injection, and gets append-only audit-logged.

`pip install queryshield-mcp`. Source: https://github.com/bch1212/queryshield. MIT.
```

---

## /r/LangChain

**Title:**

```
Plugging Claude agents into a real database without giving them DROP rights — open source MCP server
```

**Body:**

```
Posting in case anyone here is wrestling with the same thing I was — getting a LangChain or LangGraph agent to query your prod data is great until someone realizes the agent has full SQL access.

QueryShield is the security layer I built. It's an MCP server (stdio + HTTP), MIT licensed, on PyPI as `queryshield-mcp`. Three tools your agent calls; under the hood it does NL→SQL via Claude, AST-level validation (sqlglot, not keyword filtering), per-agent row-level security, and audit logging. Connection strings stay encrypted in the vault.

LangGraph integration is one line if you have a `MultiServerMCPClient` setup — point it at the streamable-HTTP endpoint with `X-API-Key` auth.

Free tier: 3 DBs, 1M queries/month at queryshield.dev. Repo: https://github.com/bch1212/queryshield.
```

---

## Twitter / X (@brett_halv)

**Tweet 1 (announce):**

```
Shipped QueryShield: a security layer for AI agents that need to touch real databases.

Agents call /query in plain English. We do NL→SQL via Claude, validate at the AST level (no DDL/DML), enforce per-agent row-level security, audit-log everything.

queryshield.dev — free trial.
```

**Tweet 2 (technical):**

```
The whole thing runs on a single insight: keyword filtering for SQL injection is bypassable in 30 seconds (`/**/dr/**/op`, hex escapes, encoded chars).

Use sqlglot to parse the AST. Reject anything that isn't a SELECT *structurally*. 24 tests in queryshield/tests/test_safety.py.

MIT.
```

**Tweet 3 (MCP):**

```
MCP-native distribution.

`pip install queryshield-mcp`
or list it in the MCP Registry: io.github.bch1212/queryshield

One line in your Claude Desktop / Cursor / LangGraph / Vercel AI config and your agent has secure DB access.
```

Space them out by 30+ minutes. Quote-tweet the first one once or twice over the next week with new angles (a feature highlight, a customer logo, a bug-bounty announcement).

---

## LinkedIn (Brett's profile)

```
Just shipped QueryShield — a secure SQL proxy that sits between AI agents and customer databases.

The problem: every team I talk to about agentic AI eventually hits the same wall. Their agent needs to read from a real production database to be useful. But giving an LLM raw SQL access to your data is a non-starter once Legal sees it.

QueryShield validates every query at the AST level (SELECT-only, no DDL/DML, no shell escapes), enforces per-agent row-level security with surgical WHERE-clause injection, and audit-logs every call. Connection strings stay in an encrypted vault — your agents never see them. MCP-native, so it drops into Claude Desktop, Cursor, LangGraph, and Vercel AI in one line.

Code is MIT (https://github.com/bch1212/queryshield). Hosted version with 14-day free trial at queryshield.dev. Tiers from $500–$3,500/mo.

If your team is putting AI agents in front of a SQL database in 2026, I'd love to hear about your security model.
```

LinkedIn is the one channel where the audience is right for the Enterprise pitch. Don't crosspost the HN/Reddit copy here — the tone should land for an IT director, not a hacker.

---

## QueryShield Discord webhook ping (post-launch ops)

When you fire any of the above, a heads-up in the QueryShield channel is useful — that's where ops alerts already land. Discord webhook URL is in `.deploy-secrets.env` as `QUERY_SHIELD_DISCORD_WEBHOOK_URL`.

Sample payload (curl):

```bash
curl -X POST "$QUERY_SHIELD_DISCORD_WEBHOOK_URL" \
  -H 'Content-Type: application/json' \
  -d '{"embeds":[{"title":"🚀 Launched on Show HN","description":"https://news.ycombinator.com/item?id=...","color":2293245}]}'
```

---

## Things to avoid

- **No cold email** to dev infra prospects. Per the standing rule for AgentFetch and dev-tools generally, this gets you blocked, not converted.
- **No Reddit posts from the salesbot bot account** (`claude_helper_bot`) — it's in warmup mode (≤ 50 karma in target subs). The Reddit posts above are for Brett's personal account.
- **No Twitter posts from `@grantiq_us`** — wrong brand.

---

## Recommended sequence

When you're ready:

1. Tuesday or Wednesday morning ET — Show HN.
2. Same day, 1 hour later — /r/mcp (the audience is awake by then).
3. Day 2 — Twitter announcement thread.
4. Day 3 — /r/ClaudeAI + /r/LangChain.
5. Day 5 — Product Hunt (Tuesday is best PH day; aim for the next one if Show HN was Tuesday).
6. Day 7 — LinkedIn long-form.

Don't do them all in one day — each cross-references the others, and they perform better when they layer over time.
