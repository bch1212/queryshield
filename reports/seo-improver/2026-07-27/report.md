# QueryShield SEO Improver — 2026-07-27

**Site:** https://queryshield.dev · **Run type:** Week 2 (movement vs. 2026-07-20 baseline) · **Ranking source:** WebSearch (US / desktop) · **Deploy model:** COMMIT-AND-FLAG (human triggers `railway up`)

## Executive Summary

Last week's baseline run closed all six technical-SEO gaps (meta description, canonical, OpenGraph/Twitter, JSON-LD, robots.txt, sitemap.xml). **Those changes are now confirmed LIVE** on queryshield.dev — the human deploy happened. QueryShield still **owns "secure SQL proxy for AI agents" at #1** (its exact `<title>` match). For the brand query "QueryShield" it slipped from **#3 → #5** (normal volatility on a contested name — three unrelated projects share it). Every broad category-intent keyword remains **NR** (not ranking).

The headline finding this week: WebSearch still surfaces three **`/aeo/guides/*` URLs as indexed** for the "QueryShield" query, but **those URLs now return HTTP 404** — they were served by a prior deploy, never existed in this repo, and are gone from the live site. That is a live SEO liability (indexed URLs 404ing) *and* the single biggest opportunity, because those guide pages targeted exactly the category-intent keywords QueryShield ranks nowhere for.

This run **recreates all three guide pages at their already-indexed slugs**, adds a `/aeo/guides` index, wires internal links from the landing page, and expands the sitemap — 5 additive content/route changes. This recovers already-earned link equity, stops the 404s, and gives Google real pages to rank for "database access control for LLM agents", "text to SQL security", "protect database from AI agents", "RBAC for AI agents", etc. Nothing deployed; committed and awaiting manual `railway up`.

## Movement vs. Last Week

| Keyword | This Week | Last Week | Δ | Status |
|---|---|---|---|---|
| secure SQL proxy for AI agents | **1** | 1 | 0 | flat (holds #1) |
| QueryShield | **5** | 3 | −2 | dropped |
| database access control for LLM agents | NR | NR | 0 | flat |
| read only SQL proxy AI | NR | NR | 0 | flat |
| protect database from AI agents | NR | NR | 0 | flat |
| query firewall for AI | NR | NR | 0 | flat |
| safe database access for AI agents | NR | NR | 0 | flat |
| SQL guardrails for LLM | NR | NR | 0 | flat |
| text to SQL security | NR | NR | 0 | flat |
| AI agent database permissions | NR | NR | 0 | flat |

- **Gained:** none · **Lost:** none (dropped to NR) · **New:** none · **Dropped in rank:** "QueryShield" (#3 → #5) · **Flat:** everything else.
- **"QueryShield" −2 context:** the domain's overall SERP footprint actually *grew* — for that query WebSearch now also surfaces `queryshield.dev/login`, the Glama MCP listing, and the three `/aeo/guides/*` URLs. The homepage line moved down as more competing (and QueryShield-owned) results filled the page. `NR` = not present in top WebSearch results. Positions are directional (WebSearch, not Google Search Console).

## Last Week's Changes — Did They Work?

**Deployed?** ✅ **Yes — confirmed live.** Verified this run:

- `https://queryshield.dev/robots.txt` → live, correct content, includes `Sitemap:` line.
- `https://queryshield.dev/sitemap.xml` → live (homepage + login).
- `https://queryshield.dev/` head → live `<meta name="description">`, `<link rel="canonical">`, `og:*`, `twitter:card`, and both JSON-LD blocks (`SoftwareApplication`, `FAQPage`) all present in raw HTML.

**Did they move rankings?** Too early to attribute — technical SEO (meta/canonical/OG/schema/sitemap) is a foundation that pays off over multiple crawl cycles, not in 7 days. "secure SQL proxy for AI agents" held #1; brand query volatility (−2) is unrelated to on-page tags and expected for a contested name. No regressions introduced. The FAQPage schema is now eligible for rich results on the homepage.

## This Week's Improvements Made

All edits are marketing-HTML / additive SEO routes only. No app logic, auth, or query behavior touched. Both files still `ast.parse` OK; full `queryshield.main:app` imports; all JSON-LD blocks validated as JSON; new routes confirmed registered.

| ID | Change | File(s) | Target keyword(s) |
|---|---|---|---|
| QS-SEO-006 | Recreate guide `/aeo/guides/block-delete-drop-llm-sql` (full page + FAQPage & BreadcrumbList JSON-LD) | `web.py`, `main.py` | protect database from AI agents; block DELETE/DROP LLM SQL; read only SQL proxy AI |
| QS-SEO-007 | Recreate guide `/aeo/guides/prevent-sql-injection-llm-queries` | `web.py`, `main.py` | text to SQL security; SQL guardrails for LLM |
| QS-SEO-008 | Recreate guide `/aeo/guides/rbac-for-ai-agents` | `web.py`, `main.py` | database access control for LLM agents; AI agent database permissions |
| QS-SEO-009 | Add `/aeo/guides` index page + "Guides" nav link and Guides section on landing (internal linking, de-orphans guides) | `web.py`, `main.py` | topical authority; crawl discovery |
| QS-SEO-010 | Expand `sitemap.xml` to include `/aeo/guides` + the 3 guide URLs | `main.py` | recrawl / indexation of new content |

**Why the exact slugs matter:** the three slugs (`block-delete-drop-llm-sql`, `prevent-sql-injection-llm-queries`, `rbac-for-ai-agents`) match URLs search engines have **already indexed**. Serving real 200-OK pages at those exact paths recovers existing link equity instead of starting cold, and converts three 404s into ranking assets.

**Each guide page includes:** self-canonical, meta description, OpenGraph + Twitter tags, `FAQPage` JSON-LD (the H1 question + answer), `BreadcrumbList` JSON-LD, an H1 matching the indexed question, ~300 words of substantive answer content referencing QueryShield's mechanisms (SELECT-only AST validation, per-agent RLS, append-only audit, MCP-native), a signup CTA, and cross-links to the sibling guides.

## ⚠️ DEPLOY PENDING

Changes are **committed to GitHub `origin/main` (commit `24708b3`) but NOT live** on queryshield.dev. A human must trigger the Railway deploy.

**Manual deploy command** (from repo root, requires a project-scoped Railway token / `railway link` to project `73846f59-a7e7-4e98-b6c0-02c907252a2c`):

```bash
cd /Users/bretthalverson/Projects/_mcp_email_work/queryshield
railway up
```

**After deploy, verify live (all should be 200 OK):**
- `https://queryshield.dev/aeo/guides`
- `https://queryshield.dev/aeo/guides/block-delete-drop-llm-sql`
- `https://queryshield.dev/aeo/guides/prevent-sql-injection-llm-queries`
- `https://queryshield.dev/aeo/guides/rbac-for-ai-agents`
- Confirm `https://queryshield.dev/sitemap.xml` now lists 6 URLs.

## Improvements NOT Made (backlog for future runs)

- **Submit updated sitemap to Google Search Console** — out of scope for this loop (no GSC access). Flag for manual action once deployed, so the recreated guides get recrawled quickly and the 404 → 200 recovery is picked up fast.
- **OG/Twitter image asset** — homepage declares `summary_large_image` but there is still no `og:image` file. Add a static social image + `og:image` tag in a future run. (Guide pages use `summary` cards, which need no image.)
- **More category pages** — remaining NR keywords "query firewall for AI", "safe database access for AI agents", "read only SQL proxy AI" could each get a dedicated guide (capped at 5 changes/run).
- **Homepage copy for striking-distance intent** — weave "database access control for LLM agents" / "text-to-SQL security" phrasing into the hero/how-it-works copy.

## Data Notes

- **Ranking source is WebSearch**, not Google Search Console. Positions reflect where `queryshield.dev` appeared in WebSearch result lists (US, desktop). Directional, not exact SERP rank.
- **Divergence resolved (mostly):** last week flagged that the live site had `/aeo/guides/*` pages not in this repo. This week confirmed those URLs now **404** on the live site (checked `/aeo/guides/rbac-for-ai-agents` → HTTP 404) — so the live deploy no longer serves them and the repo never did. This run brings the repo's routes back into alignment with what search engines expect at those URLs. If a prior checkout still holds richer versions of these pages, reconcile before the next content push to avoid overwriting better copy.
- **Brand-name competition unchanged:** "QueryShield" is contested by a BU secure-MPC demo, an HCFraudShield healthcare tool, and a NAACL enterprise-data-leakage paper. Brand-SERP dominance needs sustained authority signals, not just on-page tags; the −2 dip is within normal noise for a shared name.
- **No app/auth/query logic touched** — all edits are HTML string content in `web.py` and additive `GET` routes in `main.py`.
