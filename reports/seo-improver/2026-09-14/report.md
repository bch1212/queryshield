# QueryShield SEO Improver — 2026-09-14

**Site:** https://queryshield.dev · **Run type:** Week 5 (movement vs. 2026-08-13, a 32-day gap) · **Ranking source:** WebSearch (US / desktop) · **Deploy model:** COMMIT-AND-FLAG (human triggers `railway up`)

## Executive Summary

**Two of QueryShield's three #1 positions are gone.** "secure SQL proxy for AI agents", the one head term the site owned, fell **#1 → #7**. "prevent SQL injection from LLM generated queries" fell **#1 → unranked**. The only #1 left is "how to block DELETE and DROP from LLM generated SQL". The brand query slipped #5 → #6, which is within noise.

**The week-3 guides never picked up.** The 2026-08-13 run deployed three guides and Brett submitted the sitemap to GSC. After 32 days live, none of the three ranks for its own target query, and none appears in the brand SERP. Week-2 guides ranked within about 7 days, so this looks more like an **indexation problem than a content problem**. That needs a human check in GSC URL Inspection (see Data Notes).

**This loop didn't run for four weeks.** The next report after 2026-08-13 is this one, so the "first clean read on 2026-08-20" promised last run never happened. Movement below covers 32 days, not 7.

**Two process findings came out of this run:**
1. **An indexed legacy URL returns 404.** `/aeo/attacks/time-based-sql-injection-prompt` is still in the search index (it showed up for `site:queryshield.dev` and a topical query) but 404s in production. Fixed with a 301 (QS-SEO-020).
2. **Two guides made product claims the code doesn't support.** They claimed column allow-listing, deny-by-default tables, a per-query timeout, and system-table blocking. None of these exist in `safety.py`, `rls.py`, or `proxy.py`. Corrected (QS-SEO-024).

**Five changes committed and pushed (`eff04d8`), not deployed.** They are: recovery copy for the head term, a new guide for "read only SQL proxy AI", a deeper SQL-injection guide, the legacy 301, and the accuracy fixes.

## Movement vs. Last Run (2026-08-13)

| Keyword | This Run | Last Run | Δ | Status |
|---|---|---|---|---|
| secure SQL proxy for AI agents | **7** | 1 | **−6** | **lost** |
| how to block DELETE and DROP from LLM generated SQL | **1** | 1 | 0 | flat (holds #1) |
| prevent SQL injection from LLM generated queries | **NR** | 1 | — | **dropped** |
| QueryShield | **6** | 5 | −1 | lost (noise) |
| RBAC for AI agents accessing a database | NR | NR | 0 | flat |
| database access control for LLM agents | NR | NR | 0 | flat |
| read only SQL proxy AI | NR | NR | 0 | flat |
| protect database from AI agents | NR | NR | 0 | flat |
| query firewall for AI | NR | NR | 0 | flat |
| safe database access for AI agents | NR | NR | 0 | flat |
| SQL guardrails for LLM | NR | NR | 0 | flat |
| text to SQL security | NR | NR | 0 | flat |
| AI agent database permissions | NR | NR | 0 | flat |
| how to give an AI agent safe access to a production database | NR | NR | 0 | flat (32 days live) |
| what is a query firewall for AI agents | NR | NR | 0 | flat (32 days live) |
| how do I stop an AI agent from seeing database credentials | NR | NR | 0 | flat (32 days live) |
| read-only database access for AI agents MCP | NR | — | — | new-tracked |
| SQL guardrails for AI agents | NR | — | — | new-tracked |

- **Gained: 0** · **Lost: 2** (head term −6, brand −1) · **Dropped: 1** · **New ranking URLs: 0** · **Flat: 13** · **Newly tracked: 2**
- **Head term: what took #1–#6.** A Cast AI Cloud SQL Proxy doc, two USPTO patents (proxy-based MCP access for AI agents, secure code execution for AI agents), an NHI glossary entry on Cloud SQL Auth Proxy, the SQLumAI GitHub repo, and the LlamaFirewall arXiv paper. They are mostly explanatory and definitional pages. The landing H1 ("The security layer your AI agent stack is missing.") didn't contain the term, and the page never explained what a secure SQL proxy is. **GateSQL**, flagged at #3 last run, is not in the top results this time.
- **SQL-injection guide: what displaced it.** Research content took over: an arXiv paper on text-to-SQL backdoor attacks, a ResearchGate systematic analysis, the P2SQL arXiv paper, an OpenAI community thread, and patents. The guide still ranks **#10 on the brand query**, so it's indexed; it lost on depth for its own query.
- **Brand SERP:** homepage #6, then `block-delete-drop-llm-sql` #8, `rbac-for-ai-agents` #9, `prevent-sql-injection-llm-queries` #10. The Glama MCP listing is #4. Academic and healthcare QueryShields still hold #1–#3 and #5. The `Organization` + `sameAs` schema has now been live 32 days with no brand gain.

## Last Run's Changes — Did They Work?

**Deployed?** ✅ **Yes**, re-verified this run. Production matches the repo as of `304ecf9`: sitemap has **9** `<loc>` entries, landing has **3** JSON-LD blocks, and `/aeo/guides/query-firewall-for-ai-agents` and `/aeo/guides/rbac-for-ai-agents` return 200.

| Change (2026-08-13) | Outcome after 32 days live |
|---|---|
| QS-SEO-011–013: three new guides (credentials, safe production access, query firewall) | ❌ **None rank** for their target query; none appears in brand SERP. Likely not indexed (unverified — needs GSC). |
| QS-SEO-015: landing `Organization` + `sameAs` JSON-LD | ❌ No brand movement (#5 → #6). |
| QS-SEO-016: `twitter:card` → `summary` | Not measurable via rankings. |
| QS-SEO-017/018: CollectionPage + TechArticle schema | ❌ No measurable effect; both schema-carrying guides that ranked #1 either held (DELETE/DROP) or dropped (SQLi). |
| QS-SEO-019: RBAC guide depth (response to #6 → NR) | ❌ Still NR. The SERP is dominated by Oso, Protecto, WorkOS, NeuralTrust, and an arXiv paper. |

**Verdict:** last run's schema and content work didn't produce ranking gains. The deploy happened, the pages are live, and the sitemap was submitted, yet the three new guides are invisible. Before writing more guides, the most useful next step is a human checking **GSC → URL Inspection** on those three URLs. If they show "Discovered – currently not indexed", the problem is crawl priority or site authority, not on-page content.

## This Week's Improvements Made

All edits are marketing HTML, guide content, and one additive redirect route. **No app logic, auth, or query behavior touched.**

| ID | Change | File(s) | Target keyword(s) |
|---|---|---|---|
| QS-SEO-020 | **301** from indexed-but-404 `/aeo/attacks/time-based-sql-injection-prompt` → `/aeo/guides/prevent-sql-injection-llm-queries` (`include_in_schema=False`) | `main.py` | prevent SQL injection from LLM generated queries; recovers link equity from the legacy URL |
| QS-SEO-021 | SQL-injection guide: new sections "How prompt injection becomes SQL injection" (3-step chain) and "Time-based SQL injection through prompt injection" (`pg_sleep` timing channel, why read-only roles don't stop it); description and FAQ answer updated to name `pg_sleep`/`SLEEP` | `web.py` | prevent SQL injection from LLM generated queries (#1 → NR); text to SQL security |
| QS-SEO-022 | **New guide** `/aeo/guides/read-only-sql-proxy-for-ai-agents`: read-only user vs. read-only proxy, what the proxy enforces, read-only access over MCP, when a read-only user is enough. Added to `AEO_GUIDES_ORDER`, so it's picked up automatically by the sitemap, index ItemList, related-guides links, and TechArticle/FAQ/Breadcrumb schema. Guides-index description updated. | `web.py` | read only SQL proxy AI; read-only database access for AI agents MCP |
| QS-SEO-023 | Landing: H1 → **"Secure SQL proxy for AI agents"** (old slogan moved into the lead paragraph); new "What is a secure SQL proxy for AI agents?" section with a 4-point list and a link to the new guide; matching FAQPage question added; new guide added to landing Guides list | `web.py` | secure SQL proxy for AI agents (#1 → #7) |
| QS-SEO-024 | **Claim accuracy fixes.** Query-firewall guide said "table, column, and function allow-listing, denying by default" and "query timeout", followed by "QueryShield implements each of these". It now lists a function deny-list, per-agent schema/table allow-lists, and a mandatory LIMIT plus the proxy's hard row cap. Block-DELETE guide said "no … system tables are referenced", now names the actual deny-listed functions. SQLi guide's "block system catalogs" removed. | `web.py` | trust / E-E-A-T on query firewall for AI, block DELETE/DROP |

**Why these five.** Two go at the lost #1 positions (023 head term, 020 + 021 SQL injection). 022 closes the backlog item flagged as most winnable last run: the "read only SQL proxy AI" SERP is still ProxySQL/Oracle, with only a dev.to post answering the AI-agent question. 024 isn't a ranking play. The site was stating capabilities the product doesn't have, and that's a liability for a security product.

**How claims were grounded.** Every enforcement claim in the new and edited copy was checked against the code:
- `safety.py`: single statement; SELECT/UNION/CTE root; INSERT/UPDATE/DELETE/DROP/CREATE/ALTER/TRUNCATE/MERGE rejected anywhere in the tree; function deny-list; LIMIT required.
- `rls.py`: per-agent schema/table allow-lists (an empty list means allow any, which is why "deny by default" was removed); row-filter injection.
- `config.py`: `max_rows_hard_limit`.
- `proxy.py`: every branch, including rejects, calls `log_query`.
- `audit.py`: append-only.

**Sanity checks run before commit — all passed:**
- `ast.parse` on `web.py` and `main.py` → parses OK.
- The time-based claims are backed by the live validator: `pg_sleep`, `SLEEP`, `BENCHMARK`, `pg_read_file`, and `dblink` are rejected, including `pg_sleep` inside a CTE, a `CASE`, and a subquery. `MERGE` is rejected.
- App imports. Via TestClient: all **11** SEO routes return **200** (including the new guide), the legacy URL returns **301** → SQLi guide, and an unknown slug still returns **404**.
- Every JSON-LD block parses on every page. Landing has `SoftwareApplication`, `Organization`, `FAQPage`; `/aeo/guides` has `CollectionPage`; each of 7 guides has `TechArticle`, `FAQPage`, `BreadcrumbList`. Exactly one `<h1>` per page.
- Sitemap emits **10** `<loc>` entries (was 9). No `summary_large_image` regression.
- **Existing test suite: 66 passed, 0 failed.**

**Commit:** `eff04d8`, pushed to `origin/main` (`304ecf9..eff04d8`), branch in sync with origin.

## ✅ DEPLOYED — 2026-09-14

**Update to this report.** It was originally written with a DEPLOY PENDING section. When Brett authorized the deploy in-session, it turned out to be **already live**. Railway's `queryshield-api` service (`300a2546-…`) auto-deployed from the GitHub push: its latest deployment is commit `6893157` (this report's commit, which includes `eff04d8`), status **SUCCESS**, created 2026-09-14T21:55Z, minutes after the push. No `railway up` was needed or run.

**This changes the deploy model.** The scheduled task assumes commit-and-flag (push, then a human runs `railway up`), but **pushing to `main` deploys to production.** Future runs should treat `git push` as the deploy step.

**Why Brett's `railway up` said "service not found":** the service name `queryshield-api` is correct. It exists in project `queryshield` / env `production`, and the repo's CLI link resolves to it. The most likely cause is running the command outside the linked repo directory, or with a `RAILWAY_TOKEN` env var scoped to a different project. Either way, no manual deploy is required.

**Live verification against queryshield.dev — all passed:**

| Check | Result |
|---|---|
| `/aeo/attacks/time-based-sql-injection-prompt` | **301** → `/aeo/guides/prevent-sql-injection-llm-queries` (QS-SEO-020) |
| SQLi guide "Time-based SQL injection" section | present (QS-SEO-021) |
| `/aeo/guides/read-only-sql-proxy-for-ai-agents` | **200** on apex and www (QS-SEO-022) |
| `sitemap.xml` `<loc>` count | **10** (was 9) |
| Landing `<h1>` | `Secure SQL proxy for AI agents` (QS-SEO-023) |
| Landing head-term section + FAQ entry | present (QS-SEO-023) |
| Query-firewall guide "query timeout" claim | **gone**; "hard row cap" present (QS-SEO-024) |
| `/health` | `{"status":"ok"}` |

**Remaining human step:** resubmit the sitemap in GSC so the new guide and the redirect get picked up, and use that visit for the URL Inspection check on the three 08-13 guides (backlog item #1).

## Improvements NOT Made (backlog)

- **GSC indexation check on the three week-3 guides (human, highest priority).** 32 days live plus a manual sitemap submit, and still absent from every SERP including the brand query. This loop has no GSC access. Check URL Inspection for `/aeo/guides/ai-agent-database-credentials`, `/safe-production-database-access`, and `/query-firewall-for-ai-agents`. If they aren't indexed, request indexing, and consider pausing new guide creation until indexation is understood.
- **Missed loop runs (2026-08-20 → 2026-09-07).** Four scheduled weeks produced no reports. Worth checking the scheduled task's run history to see why.
- **"SQL guardrails for LLM" / "SQL guardrails for AI agents" guide.** Both NR. The SERP includes two open-source GitHub tools (`QueryGuard`, `sql-semantic-guard`) and no product page. Deferred to stay within the 5-change cap and because of the indexation question above.
- **Sitemap `<lastmod>` + TechArticle `dateModified`.** Would signal freshness on the edited SQLi guide and help recrawl the unindexed guides. It needs a per-guide `updated` field in `AEO_GUIDES`. Deferred (cap).
- **Pricing copy inconsistency (product decision, not changed).** The landing signup card says "Free tier: 3 databases · 1M queries/month · no credit card". The pricing table lists **Starter at $500** with the same limits, and `TIER_LIMITS["starter"]` in `models.py` is 3 DBs / 1M queries / `price_cents: 50_000`. The `SoftwareApplication` JSON-LD offer is `price: 500`. Either the free tier is Starter-without-billing or the copy is wrong; a human should reconcile it.
- **RBAC guide checklist** still recommends "deny by default on tables and columns". That's framed as general advice, not a QueryShield capability, so it was left alone. If a product claim is ever attached to it, it will need the same correction as QS-SEO-024.
- **Other legacy `/aeo/attacks/*` URLs.** Only one surfaced in search. If GSC shows more 404s under `/aeo/attacks/`, add them to the redirect (or convert it to a small mapping).
- **An `og:image` asset.** Carried over; still needs a design asset.
- **Head-term strategy.** "query firewall for AI", "text to SQL security", "database access control for LLM agents", and "AI agent database permissions" are held by Akamai, Cloudflare, F5, Cerbos, WorkOS, Oso, and arXiv. Five runs of on-page work haven't moved any of them. That's an off-page authority decision for a human.

## Data Notes

- **Ranking source is WebSearch**, not Google Search Console. Position = index of the first `queryshield.dev` URL in the WebSearch result list (US, desktop). It's directional, not exact SERP rank. Single-position moves (brand #5 → #6) are noise. **#1 → #7 on the head term and #1 → absent on the SQLi guide are large enough to treat as real.**
- **All 18 searches succeeded on the first attempt** this run (no "unavailable" retries).
- **The comparison window is 32 days, not 7**, because runs for 2026-08-20, 08-27, 09-03, and 09-07 don't exist. Deltas can't be attributed to a single week.
- **`site:queryshield.dev` via WebSearch returned only the homepage and the legacy `/aeo/attacks/…` URL.** WebSearch `site:` coverage is incomplete (block-DELETE, RBAC, and SQLi guides are demonstrably indexed via the brand query but didn't show up), so this is **not** proof the week-3 guides are unindexed. It's why the GSC check is flagged instead of asserted.
- **Legacy URL provenance:** `/aeo/attacks/time-based-sql-injection-prompt` doesn't appear anywhere in this repo's git history. It predates the current codebase's SEO pages (the 2026-07-27 commit message says it "recreate[d] indexed /aeo/guides/*" pages). Confirmed 404 in production, and `/aeo/attacks` and `/aeo` also 404.
- **`NR`** = not present in the top WebSearch results. **`new-tracked`** = first measurement for a keyword added this run.
- **No app/auth/query logic touched.** Only HTML string constants and guide data in `web.py`, plus one additive redirect route in `main.py`.
