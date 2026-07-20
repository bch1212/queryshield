# QueryShield SEO Improver — 2026-07-20

**Site:** https://queryshield.dev · **Run type:** BASELINE (first dated report) · **Ranking source:** WebSearch (US / desktop) · **Deploy model:** COMMIT-AND-FLAG (human triggers `railway up`)

## Executive Summary

This is the **baseline run** — no prior report existed, so there is no week-over-week movement to compare against. Rankings were captured for all 10 tracked keywords via WebSearch.

QueryShield **owns its brand-exact and primary-descriptor queries**: it ranks **#1 for "secure SQL proxy for AI agents"** (its own `<title>` match) and **#3 for "QueryShield"** (behind two unrelated projects that share the name — a Boston University secure-MPC demo and a healthcare fraud tool). For every broader category-intent keyword ("database access control for LLM agents", "protect database from AI agents", "safe database access for AI agents", "SQL guardrails for LLM", "text to SQL security", etc.), QueryShield **does not rank in the top results** — these are the growth opportunities.

The landing page had **all six known technical-SEO gaps open** (no meta description, canonical, OpenGraph/Twitter, JSON-LD, robots.txt, or sitemap.xml). This run **closes all six** — the highest-leverage early work — via 5 minimal, additive edits. Nothing was deployed; changes are committed and awaiting a manual Railway deploy.

## Movement vs. Last Week

None — baseline run. All keywords recorded as `new`. Movement tracking begins next week against this snapshot.

| Keyword | Position | Ranking URL |
|---|---|---|
| secure SQL proxy for AI agents | **1** | queryshield.dev/ |
| QueryShield | **3** | queryshield.dev/ |
| database access control for LLM agents | NR | — |
| read only SQL proxy AI | NR | — |
| protect database from AI agents | NR | — |
| query firewall for AI | NR | — |
| safe database access for AI agents | NR | — |
| SQL guardrails for LLM | NR | — |
| text to SQL security | NR | — |
| AI agent database permissions | NR | — |

`NR` = not present in the top WebSearch results for that query.

## Last Week's Changes — Did They Work?

N/A — no prior run. **Not deployed** history is empty.

## This Week's Improvements Made

All edits are marketing-HTML / additive SEO routes only. No app logic, auth, or query behavior touched.

| ID | Change | File | Target keyword(s) |
|---|---|---|---|
| QS-SEO-001 | Added `<meta name="description">` to landing `<head>` | `queryshield/web.py` | secure SQL proxy for AI agents; database access control for LLM agents |
| QS-SEO-002 | Added canonical + robots meta + OpenGraph + Twitter Card tags | `queryshield/web.py` | brand SERP presentation; social sharing |
| QS-SEO-003 | Added JSON-LD: `SoftwareApplication` + `FAQPage` (3 Q&As) | `queryshield/web.py` | protect database from AI agents; block DELETE/DROP; MCP database access |
| QS-SEO-004 | Added `GET /robots.txt` route (allows crawl, disallows /dashboard, /auth/, /v1/, points to sitemap) | `queryshield/main.py` | crawlability / indexation |
| QS-SEO-005 | Added `GET /sitemap.xml` route (homepage + login) | `queryshield/main.py` | crawlability / indexation |

**FAQ schema questions** (chosen to match striking-distance category intent):
1. "How does QueryShield protect a database from AI agents?"
2. "Can AI agents run DELETE, DROP, or UPDATE through QueryShield?"
3. "Does QueryShield work with the Model Context Protocol (MCP)?"

**Validation performed:** `ast.parse` on both files (OK); full `queryshield.main:app` import (OK); both JSON-LD blocks parse as valid JSON (`SoftwareApplication`, `FAQPage`); `/robots.txt`, `/sitemap.xml`, and `/` all confirmed registered on the app router.

## ⚠️ DEPLOY PENDING

Changes are **committed to GitHub `origin/main` but NOT live** on queryshield.dev. A human must trigger the Railway deploy.

**Manual deploy command** (from repo root, requires a project-scoped Railway token / `railway link` to project `73846f59-a7e7-4e98-b6c0-02c907252a2c`):

```bash
cd /Users/bretthalverson/Projects/_mcp_email_work/queryshield
railway up
```

After deploy, verify live: `https://queryshield.dev/robots.txt`, `https://queryshield.dev/sitemap.xml`, and view-source on `https://queryshield.dev/` for the meta/JSON-LD tags.

## Improvements NOT Made (backlog for future runs)

- **Category-intent landing copy / dedicated content pages** — QueryShield ranks nowhere for "database access control for LLM agents", "safe database access for AI agents", "SQL guardrails for LLM", "text to SQL security". These need on-page copy or dedicated pages targeting each intent. (Capped at 5 changes/run; these are next.)
- **Submit sitemap to Google Search Console** — out of scope for this loop (no GSC access); flag for manual action once sitemap is live.
- **OG/Twitter image** — `summary_large_image` card is declared but no `og:image` asset exists yet; add a static social image + `og:image` tag in a future run.
- **Expand sitemap** once category/AEO content pages exist.

## Data Notes

- **Ranking source is WebSearch**, not Google Search Console. Positions reflect where `queryshield.dev` appeared in WebSearch result lists (US, desktop). Treat as directional, not exact SERP rank; absolute positions may differ from Google's live SERP.
- **Discrepancy flagged:** WebSearch for "QueryShield" surfaced **already-indexed `/aeo/guides/` pages** on the live site (e.g. `queryshield.dev/aeo/guides/rbac-for-ai-agents`, `.../prevent-sql-injection-llm-queries`, `.../block-delete-drop-llm-sql`). **These routes do NOT exist in this repo checkout** (`queryshield/main.py` / `web.py`). They were likely added by a prior effort in a different checkout/deploy, or reflect stale index data. No action taken this run — but the running deployment and this repo may have diverged; worth reconciling before the next content push so new pages don't collide with existing AEO routes.
- Brand-name competition: "QueryShield" is a contested name (BU secure-MPC research demo, HCFraudShield healthcare tool, a NAACL enterprise-data-leakage paper). Brand SERP dominance will require sustained authority signals, not just on-page tags.
