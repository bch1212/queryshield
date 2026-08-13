# QueryShield SEO Improver — 2026-08-13

**Site:** https://queryshield.dev · **Run type:** Week 4 (movement vs. 2026-08-03) · **Ranking source:** WebSearch (US / desktop) · **Deploy model:** COMMIT-AND-FLAG (human triggers `railway up`)

## Executive Summary

**Last week's work was never committed, and therefore never deployed.** The 2026-08-03 report stated that its changes were "committed to GitHub `origin/main`." They were not. This run found `queryshield/web.py` sitting dirty in the working tree with all five of week 3's changes uncommitted, and the `reports/seo-improver/2026-08-03/` directory untracked. Production confirms it: all three guides week 3 wrote return **404** on queryshield.dev today.

That is the headline finding, and it invalidates the "did last week's changes work?" question entirely — there was nothing live to measure. The three keywords week 3 added as targets are still NR because **the pages that target them do not exist in production.**

This run's first job was recovery: week 3's work is now committed and pushed, along with this week's changes, in a single commit (`35997b4`). **Deploy status: initially flagged as pending per the commit-and-flag model, then authorized by Brett in-session and deployed the same day — everything in this report is now live and verified.** See the DEPLOYED section below.

On rankings, the deployed surface held and improved slightly. **"prevent SQL injection from LLM generated queries" moved #2 → #1**, giving QueryShield two #1 positions on long-tail guide queries. "secure SQL proxy for AI agents" holds **#1** and the brand query holds **#5**. One genuine loss: **"RBAC for AI agents accessing a database" fell from #6 to unranked** — the only tracked position lost since the loop began.

Because the deploy backlog is the binding constraint, this run deliberately stayed **under** the 5-change cap: four changes, all technical-SEO and content depth that compound with what is already queued, rather than a seventh guide page that would sit undeployed alongside the other three.

**New competitor worth flagging:** `gatesql.dev` ("GateSQL — Secure PostgreSQL access for AI agents") now ranks **#3** for "secure SQL proxy for AI agents" — a direct positional competitor on the one head term QueryShield owns, with near-identical positioning (scoped sessions instead of credentials, read-only enforced at the proxy).

## Movement vs. Last Week

| Keyword | This Week | Last Week | Δ | Status |
|---|---|---|---|---|
| secure SQL proxy for AI agents | **1** | 1 | 0 | flat (holds #1) |
| how to block DELETE and DROP from LLM generated SQL | **1** | 1 | 0 | flat (holds #1) |
| prevent SQL injection from LLM generated queries | **1** | 2 | **+1** | **gained** |
| QueryShield | **5** | 5 | 0 | flat |
| RBAC for AI agents accessing a database | **NR** | 6 | — | **dropped** |
| database access control for LLM agents | NR | NR | 0 | flat |
| read only SQL proxy AI | NR | NR | 0 | flat |
| protect database from AI agents | NR | NR | 0 | flat |
| query firewall for AI | NR | NR | 0 | flat |
| safe database access for AI agents | NR | NR | 0 | flat |
| SQL guardrails for LLM | NR | NR | 0 | flat |
| text to SQL security | NR | NR | 0 | flat |
| AI agent database permissions | NR | NR | 0 | flat |
| how to give an AI agent safe access to a production database | NR | NR | 0 | flat (page was 404 at measurement) |
| what is a query firewall for AI agents | NR | NR | 0 | flat (page was 404 at measurement) |
| how do I stop an AI agent from seeing database credentials | NR | NR | 0 | flat (page was 404 at measurement) |

- **Gained: 1** · **Lost: 1** · **New ranking URLs: 0** · **Dropped: 1** · **Flat: 13**
- **The RBAC drop is real and worth attention.** The SERP for that query is now dominated by substantive competitors — an arXiv paper on RBAC for industrial AI agents, WorkOS, Protecto, NeuralTrust, IBM, and notably Oso's "Why RBAC is Not Enough for AI Agents." QueryShield's RBAC guide was the thinnest of the three live guides (three short sections, no counter-argument, no checklist) and it lost to depth. Addressed this run — see QS-SEO-019.
- **Brand query detail:** for "QueryShield", queryshield.dev holds **#5** (homepage), **#7** (`/login`), **#8/#9/#10** (the three live guides), with the Glama MCP listing at #6. The academic/healthcare QueryShields still hold #1–#4. Unchanged from last week. The `Organization` + `sameAs` schema intended to fix this was **not live at measurement time**, so it had no chance to act on this week's number; it went live later the same day and gets its first real test on 2026-08-20.

## Last Week's Changes — Did They Work?

**Deployed?** ❌ **No — and not committed either.** This is a process failure, not a ranking failure.

Verified this run:

| Check | Result |
|---|---|
| `git status` on entry | `queryshield/web.py` **modified, uncommitted**; `reports/seo-improver/2026-08-03/` **untracked** |
| `git log` on entry | Latest commit was `1f48264` (week 2's report) — no week 3 commit existed |
| `https://queryshield.dev/aeo/guides/ai-agent-database-credentials` | **404** |
| `https://queryshield.dev/aeo/guides/safe-production-database-access` | **404** |
| `https://queryshield.dev/aeo/guides/query-firewall-for-ai-agents` | **404** |
| `https://queryshield.dev/aeo/guides/rbac-for-ai-agents` | 200 (week 2 content, deployed) |
| `https://queryshield.dev/sitemap.xml` | 200, still **6** `<loc>` entries (not 9) |

**Did they move rankings? Unmeasurable — the changes never reached production.** The three target keywords sitting at NR is the expected result of a 404, not evidence about the content. They get a clean first measurement only after a deploy.

**What *is* still working** is week 2's deployed content: both live guide pages that rank hold their positions, and one improved to #1. The week-2 conclusion — that long-tail question-format guides rank fast for this domain while broad head terms do not — remains supported by every deployed data point.

**Process note:** week 3's report asserted a successful commit and push that did not happen. Whatever produced that claim did not verify it. This run verified the push against `git status -sb` (`## main...origin/main`, clean) and the remote ref update (`1f48264..35997b4  main -> main`) after the fact.

## This Week's Improvements Made

All edits are marketing HTML and schema in `queryshield/web.py`. **No app logic, auth, or query behavior touched. `main.py` unchanged** — routes, sitemap, and cross-links all derive from `AEO_GUIDES` / `AEO_GUIDES_ORDER`.

| ID | Change | File(s) | Target keyword(s) |
|---|---|---|---|
| QS-SEO-016 | Fix `twitter:card` mismatch on landing: `summary_large_image` → `summary` (no `og:image` exists, so the card was degrading on every share) | `web.py` | brand / share CTR |
| QS-SEO-017 | `/aeo/guides` index: add OG + Twitter meta and `CollectionPage` + `ItemList` JSON-LD (the index had canonical only, no social or structured data) | `web.py` | guides hub crawl + entity structure |
| QS-SEO-018 | All guide pages: add `TechArticle` JSON-LD (`mainEntityOfPage`, `isPartOf`, `about`, `author`/`publisher`) alongside existing FAQ + Breadcrumb | `web.py` | all guide long-tails |
| QS-SEO-019 | `rbac-for-ai-agents`: add "Why RBAC alone is not enough for AI agents" (chained-permission problem) + a 5-point agent RBAC checklist | `web.py` | RBAC for AI agents accessing a database; AI agent database permissions |

**Also landed in the same commit — recovered from 2026-08-03** (written last week, never committed): QS-SEO-011 through QS-SEO-015 — the three new guides, the landing guide links and category-intent hero copy, and the landing `Organization` JSON-LD. These are unchanged from what week 3 authored; this run only committed them.

**Why only four changes.** The cap is five, but adding a seventh guide page this week would mean four undeployed guides instead of three, with no additional chance of ranking. The four chosen changes all strengthen pages that are *already queued for the same deploy*, so one `railway up` now ships two weeks of compounding work. Content expansion resumes next run, after the backlog clears.

**Why QS-SEO-019 specifically.** It is the direct response to the only position lost since this loop started. The competing pages that displaced it argue *against* naive RBAC for agents; the QueryShield page asserted RBAC without engaging that argument. The new section makes the page's answer to the emergent-permission-chain problem explicit — which is genuinely what per-query AST + RLS enforcement addresses — rather than adding keyword density.

**Sanity checks run before commit — all passed:**
- `ast.parse` on `web.py` and `main.py` → parses OK.
- `queryshield.main:app` imports; all **10** SEO routes return **200** via TestClient; unknown slug still **404s**.
- Every JSON-LD block on every page parses as JSON: landing → `SoftwareApplication`, `Organization`, `FAQPage`; `/aeo/guides` → `CollectionPage`; each of 6 guides → `TechArticle`, `FAQPage`, `BreadcrumbList`.
- Exactly one `<h1>` per page.
- No page declares `summary_large_image` without an `og:image` (regression guard for QS-SEO-016).
- Sitemap emits **9** `<loc>` entries.
- **Existing test suite: 66 passed, 0 failed.**

## ✅ DEPLOYED — 2026-08-13

**Update to this report.** The commit-and-flag step completed as designed (committed and pushed, deploy flagged for a human), and then **Brett authorized the deploy in-session and it was executed the same day.** The two-week backlog is cleared; everything described in this report is live.

- Committed and pushed to `origin/main`: `1f48264..35997b4` (changes) and `35997b4..bf717e4` (this report).
- Deployed with `railway up --service queryshield-api --ci` against project `73846f59-a7e7-4e98-b6c0-02c907252a2c` / service `300a2546-6603-443d-9a2c-30f3cd78de9d` — both IDs verified against the linked project before deploying. Result: **Deploy complete.**

**Live verification against queryshield.dev — all passed:**

| Check | Result |
|---|---|
| All 10 SEO routes | **200** (incl. the three guides that were 404 all week) |
| `/aeo/guides/ai-agent-database-credentials` | **200** (was 404) |
| `/aeo/guides/safe-production-database-access` | **200** (was 404) |
| `/aeo/guides/query-firewall-for-ai-agents` | **200** (was 404) |
| `sitemap.xml` `<loc>` count | **9** (was 6) |
| Landing `twitter:card` | `summary` (QS-SEO-016 live) |
| Landing JSON-LD blocks | **3**, incl. `Organization` (QS-SEO-015 live) |
| Landing guide links | **6** (was 3) |
| `/aeo/guides` | `CollectionPage` JSON-LD + `og:title` present (QS-SEO-017 live) |
| `rbac-for-ai-agents` | `TechArticle` schema + both new sections present (QS-SEO-018/019 live) |

**Repo/live divergence is now zero.** Six guides in the repo, six live.

**What this changes for next week's run:** the 2026-08-20 measurement is the first clean read on week 3's three guides and all of week 4's schema work. The three keywords marked `flat-undeployed` in `rankings.csv` get a real baseline for the first time — if the week-2 pattern holds (~7 days from live to ranking), they should show movement next run. Treat next week's numbers as the actual test of the guide-page strategy at 6 pages.

## Improvements NOT Made (backlog)

- **An `og:image` asset.** QS-SEO-016 fixed the *mismatch* by downgrading the card, which is the honest fix without a binary asset, but a real 1200×630 OG image would be strictly better and would let the large card come back. Needs a design asset, out of scope for this loop.
- **Submit the updated sitemap to Google Search Console.** Still no GSC access from this loop. Now the single highest-value manual action, and newly urgent: the deploy landed three brand-new URLs plus schema changes across six pages, all waiting to be discovered.
- **A guide for "read only SQL proxy AI" and "SQL guardrails for LLM".** Both still NR with no dedicated page. Deliberately deferred until the deploy backlog clears; "read only SQL proxy AI" looks especially winnable, since its SERP is entirely traditional proxies (Oracle, ProxySQL) with no AI-agent-native answer.
- **Competitive response to GateSQL.** `gatesql.dev` is new at #3 on QueryShield's #1 head term with nearly identical positioning. No action taken this run — flagging it for a human product/positioning decision rather than reacting with copy tweaks.
- **Head-term strategy remains unresolved.** Four weeks of evidence: "query firewall for AI", "text to SQL security", and "database access control for LLM agents" are held by Akamai, Cloudflare, Oracle, IBM, Cerbos, and arXiv. On-page work has not moved any of them a single position. These need off-page authority; that is a decision for a human, not another landing-copy iteration.

## Data Notes

- **Ranking source is WebSearch**, not Google Search Console. Position = index of the first `queryshield.dev` URL in the WebSearch result list (US, desktop). Directional, not exact SERP rank — treat single-position moves as noise. On that basis the "+1" on the SQL-injection guide is **within noise**; the RBAC **drop from #6 to absent** is a larger and more likely-real signal.
- **Four of sixteen searches returned "web search error: unavailable" on first attempt** ("database access control for LLM agents", "protect database from AI agents", "SQL guardrails for LLM", "AI agent database permissions"). All four were retried successfully and the retried results are what this report uses. No keyword was scored from a failed search.
- **`NR`** = not present in the top WebSearch results. **`flat-undeployed`** in rankings.csv marks the three keywords whose target pages exist in the repo but 404 in production — their NR is a deploy artifact, not a content signal.
- **Week 3's report contained an inaccurate claim** ("committed to GitHub `origin/main`"). Its *content* work was sound and is preserved verbatim in this run's commit; only the deploy-status claim was wrong. Its ranking figures were measured against the then-live week-2 site and remain valid.
- **Repo/live divergence peaked at its widest since the loop began** (6 guides in the repo, 3 live) and was **closed the same day** by the in-session deploy. As of end of this run: 6 in repo, 6 live.
- **The three `flat-undeployed` rows in `rankings.csv` were measured before the deploy** and reflect 404 pages. They are not a content signal and should not be carried forward as a trend — 2026-08-20 is their first real baseline.
- **No app/auth/query logic touched.** Only HTML string constants and JSON-LD builders in `web.py`.
