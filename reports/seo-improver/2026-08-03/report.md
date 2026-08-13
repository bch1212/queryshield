# QueryShield SEO Improver — 2026-08-03

**Site:** https://queryshield.dev · **Run type:** Week 3 (movement vs. 2026-07-27) · **Ranking source:** WebSearch (US / desktop) · **Deploy model:** COMMIT-AND-FLAG (human triggers `railway up`)

## Executive Summary

**Last week's bet paid off, and fast.** Week 2 recreated three `/aeo/guides/*` pages at slugs search engines had already indexed but which were returning 404. Those pages are now **live and ranking within seven days**:

| Guide | Query it now ranks for | Position |
|---|---|---|
| `block-delete-drop-llm-sql` | "how to block DELETE and DROP from LLM generated SQL" | **#1** |
| `prevent-sql-injection-llm-queries` | "prevent SQL injection from LLM generated queries" | **#2** |
| `rbac-for-ai-agents` | "RBAC for AI agents accessing a database" | **#6** |

That is three new ranking URLs from one week of work, and it settles a strategic question: **long-tail, question-format guide pages rank quickly for QueryShield; broad category head terms do not.** Every broad head term ("query firewall for AI", "text to SQL security", "database access control for LLM agents", …) is still **NR** and is contested by Akamai, Cloudflare, Oracle, IBM, and arXiv — QueryShield will not win those on on-page work alone.

So this week doubles down on the pattern that works: **three new guide pages** aimed at long-tail questions where QueryShield's actual differentiator is the answer, plus landing-page copy and `Organization` schema. The site goes from 3 guides to 6, and the sitemap from 6 URLs to 9.

Core tracked keywords were **flat across the board** — "secure SQL proxy for AI agents" holds **#1**, and the brand query "QueryShield" **recovered its footing at #5** (it was #5 last week after a −2 dip; no further slide).

## Movement vs. Last Week

| Keyword | This Week | Last Week | Δ | Status |
|---|---|---|---|---|
| secure SQL proxy for AI agents | **1** | 1 | 0 | flat (holds #1) |
| QueryShield | **5** | 5 | 0 | flat |
| database access control for LLM agents | NR | NR | 0 | flat |
| read only SQL proxy AI | NR | NR | 0 | flat |
| protect database from AI agents | NR | NR | 0 | flat |
| query firewall for AI | NR | NR | 0 | flat |
| safe database access for AI agents | NR | NR | 0 | flat |
| SQL guardrails for LLM | NR | NR | 0 | flat |
| text to SQL security | NR | NR | 0 | flat |
| AI agent database permissions | NR | NR | 0 | flat |
| how to block DELETE and DROP from LLM generated SQL | **1** | not tracked | — | **new** |
| prevent SQL injection from LLM generated queries | **2** | not tracked | — | **new** |
| RBAC for AI agents accessing a database | **6** | not tracked | — | **new** |

- **Gained:** none on previously-tracked terms · **Lost:** none · **New ranking URLs: 3** (all three recreated guides) · **Dropped:** none · **Flat:** all 10 core keywords.
- **Three long-tail keywords added to tracking** this run because the guides earned positions on them. Three more were added as targets and currently sit NR (see rankings.csv): "how to give an AI agent safe access to a production database", "what is a query firewall for AI agents", "how do I stop an AI agent from seeing database credentials" — these are what the new pages aim at, so next week measures them from a clean baseline.
- **Brand query detail:** for "QueryShield", queryshield.dev now occupies **4 of the top 10 results** (homepage #5, `/login` #7, and guides at #8/#9/#10), plus the Glama MCP listing at #6. The three academic/healthcare QueryShields still hold #1–#4.

## Last Week's Changes — Did They Work?

**Deployed?** ✅ **Yes — confirmed live this run.** Verified directly against production:

- `/aeo/guides`, `/aeo/guides/block-delete-drop-llm-sql`, `/aeo/guides/prevent-sql-injection-llm-queries`, `/aeo/guides/rbac-for-ai-agents` → all **HTTP 200** (were 404 last week).
- `https://queryshield.dev/sitemap.xml` → live with **6 `<loc>` entries**, matching the repo.
- Live guide `<title>` matches the repo exactly ("How do I enforce RBAC for AI agents accessing a database? — QueryShield").
- Landing page serves the Guides section with all three internal links.

**Did they move rankings?** **Yes — unambiguously.** The 404 → 200 recovery converted three dead indexed URLs into three ranking pages inside one crawl cycle, one of them at #1. This is the clearest causal result the loop has produced: the pages were the only change, and they went from serving errors to ranking.

Week 1's technical-SEO foundation (meta/canonical/OG/JSON-LD/robots/sitemap) remains live and is very likely what let the recreated guides get crawled and ranked this quickly — the sitemap pointed at them the day they came back.

## This Week's Improvements Made

All edits are marketing-HTML content in `queryshield/web.py`. **No app logic, auth, or query behavior touched — and `main.py` needed no change at all**, because routes, sitemap, index page, and cross-links all derive from `AEO_GUIDES` / `AEO_GUIDES_ORDER`.

| ID | Change | File(s) | Target keyword(s) |
|---|---|---|---|
| QS-SEO-011 | New guide `/aeo/guides/ai-agent-database-credentials` — "How do I stop an AI agent from seeing database credentials?" | `web.py` | how do I stop an AI agent from seeing database credentials; protect database from AI agents |
| QS-SEO-012 | New guide `/aeo/guides/safe-production-database-access` — "How do I give an AI agent safe access to a production database?" | `web.py` | safe database access for AI agents; how to give an AI agent safe access to a production database |
| QS-SEO-013 | New guide `/aeo/guides/query-firewall-for-ai-agents` — "What is a query firewall for AI agents?" | `web.py` | query firewall for AI; what is a query firewall for AI agents |
| QS-SEO-014 | Landing page: all 6 guides linked (was 3) + "Browse all guides" link + hero line weaving "query firewall for AI", "database access control for LLM agents", "text-to-SQL security" | `web.py` | striking-distance category intent; crawl discovery |
| QS-SEO-015 | Landing `Organization` JSON-LD with `sameAs` (GitHub, Glama MCP listing) + `publisher` link from `SoftwareApplication` | `web.py` | QueryShield (brand entity disambiguation) |

**Why these three guides.** Each targets a question where QueryShield's actual architecture *is* the best answer, and where the current SERP is generic blog advice rather than an entrenched vendor:

- **Credentials guide** — the SERP is full of "rotate your secrets" advice. QueryShield's answer is categorically different (the agent never holds a database credential at all), which is the strongest differentiator on the site and had no dedicated page.
- **Safe production access guide** — the top results all recommend read-only users and read replicas. The page argues *why that is insufficient* and lays out the layered pattern, which is a genuinely contrarian angle on a crowded query.
- **Query firewall guide** — "firewall for AI" is dominated by Akamai/Cloudflare prompt-firewall products. The page defines the *query* firewall category as distinct from network and prompt firewalls, which is a definitional gap nobody currently owns.

**Why `Organization` schema.** "QueryShield" is the one tracked keyword that is stuck (#5) purely because three unrelated projects share the name. `sameAs` pointing at the GitHub repo and the Glama MCP listing is the standard entity-disambiguation signal for telling search engines which QueryShield this domain is.

**Sanity checks run before commit — all passed:**
- `ast.parse` on `web.py` and `main.py` → parses OK.
- Full `queryshield.main:app` imports; all 10 SEO routes return **200** via TestClient; unknown slug still correctly **404s**.
- All 3 landing JSON-LD blocks (`SoftwareApplication`, `Organization`, `FAQPage`) and both blocks on each of the 6 guides validate as JSON.
- Each guide: exactly one `<h1>`, correct self-canonical, quote-safe title/description (no broken meta attributes).
- Sitemap now emits **9 `<loc>` entries**; every guide is linked from both the index and the landing page (no orphans).
- **Existing test suite: 66 passed, 0 failed.**

## ⚠️ DEPLOY PENDING

Changes are **committed to GitHub `origin/main` but NOT live** on queryshield.dev. A human must trigger the Railway deploy.

**Manual deploy command** (from repo root, requires a project-scoped Railway token / `railway link` to project `73846f59-a7e7-4e98-b6c0-02c907252a2c`):

```bash
cd /Users/bretthalverson/Projects/_mcp_email_work/queryshield && railway up
```

**After deploy, verify live (all should be 200 OK):**
- `https://queryshield.dev/aeo/guides/ai-agent-database-credentials`
- `https://queryshield.dev/aeo/guides/safe-production-database-access`
- `https://queryshield.dev/aeo/guides/query-firewall-for-ai-agents`
- Confirm `https://queryshield.dev/sitemap.xml` now lists **9** URLs.
- Confirm the landing page `<head>` contains the new `Organization` JSON-LD block.

## Improvements NOT Made (backlog)

- **Submit the updated sitemap to Google Search Console** — still out of scope for this loop (no GSC access), and now the highest-value manual action. Last week's guides took ~7 days to rank without a manual submit; a submit after this deploy should shorten that for the three new pages.
- **OG/Twitter image asset** — the homepage still declares `twitter:card: summary_large_image` with **no `og:image`**, which is a mismatch (the card degrades). Either add a real static image or downgrade the card to `summary`. Not done here because it needs a binary asset, and the 5-change cap was spent on content that ranks. **Flagged as the top candidate for next run.**
- **Head-term strategy** — "query firewall for AI", "text to SQL security", and "database access control for LLM agents" are contested by Akamai, Cloudflare, Oracle, and IBM. Three weeks of evidence says on-page work will not crack these; they need off-page authority (the HN/Lobsters-style discussions already ranking on these SERPs are the realistic route). Worth an explicit decision rather than more landing-copy tweaks.
- **Remaining NR long-tails without a page** — "read only SQL proxy AI" and "SQL guardrails for LLM" could each get a guide (capped at 5 changes/run).

## Data Notes

- **Ranking source is WebSearch**, not Google Search Console. Positions are the index of the first `queryshield.dev` URL in the WebSearch result list (US, desktop). Directional, not exact SERP rank — treat single-position moves as noise.
- **`NT` in rankings.csv** = not tracked in a prior run, so no delta is computable. `NR` = not present in the top WebSearch results.
- **The three "new" keywords added to tracking were not cherry-picked after the fact in a way that inflates the result** — they are the exact question strings the recreated guide `<h1>`s target, and the guides rank for them. But note they are long-tail: high position, low volume. The honest read is "the content format works," not "traffic is solved."
- **Last week's repo/live divergence is fully resolved.** The `/aeo/guides/*` URLs that were indexed-but-404 now serve 200 from this repo's code, verified against production this run. No divergence remains.
- **`main.py` was not modified this week** — new guides are pure data additions to `AEO_GUIDES`, so routing/sitemap/index pick them up automatically. This makes the change trivially reversible (revert one commit, one file).
- **No app/auth/query logic touched.** Only HTML string constants in `web.py`.
