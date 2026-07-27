"""HTML templates for the web surface.

Pulled out of ``main.py`` so route handlers stay readable. All pages are
single-file (no external CSS/JS) and use the same dark/cool palette.
"""

import json

_BASE_CSS = """
:root { --fg:#0f172a; --muted:#475569; --bg:#fafafa; --card:#fff; --line:#e2e8f0;
        --accent:#2563eb; --accent-hover:#1d4ed8; --danger:#dc2626; --ok:#10b981; }
* { box-sizing: border-box; }
body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
       color: var(--fg); background: var(--bg); line-height: 1.55; }
a { color: var(--accent); text-decoration: none; } a:hover { text-decoration: underline; }
.wrap { max-width: 880px; margin: 0 auto; padding: 48px 24px; }
.btn { display: inline-block; background: var(--accent); color: #fff; padding: 10px 18px;
       border-radius: 8px; border: 0; font-size: 15px; cursor: pointer; font-weight: 500; }
.btn:hover { background: var(--accent-hover); text-decoration: none; }
.btn.secondary { background: #fff; color: var(--accent); border: 1px solid var(--line); }
.btn.secondary:hover { background: var(--bg); }
.btn.danger { background: var(--danger); }
input[type=email], input[type=text], select, textarea {
  width: 100%; padding: 10px 12px; border: 1px solid var(--line); border-radius: 8px;
  font-size: 15px; font-family: inherit; background: #fff; }
label { display: block; font-size: 13px; color: var(--muted); margin: 12px 0 6px; font-weight: 500; }
code, pre { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13.5px; }
pre { background: #0f172a; color: #e2e8f0; padding: 14px 16px; border-radius: 8px; overflow-x: auto; margin: 12px 0; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 20px; margin: 16px 0; }
h1 { font-size: 36px; margin: 0 0 8px; letter-spacing: -0.5px; }
h2 { font-size: 20px; margin: 24px 0 12px; }
h3 { font-size: 16px; margin: 16px 0 8px; }
.tag { color: var(--muted); font-size: 17px; margin-bottom: 28px; }
.pill { display: inline-block; background: #eef2ff; color: var(--accent);
        padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; margin-right: 6px; }
.error { background: #fef2f2; color: var(--danger); padding: 10px 12px; border-radius: 6px; font-size: 14px; }
.muted { color: var(--muted); font-size: 13px; }
.row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.row > * { flex: 1; min-width: 0; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
th { color: var(--muted); font-weight: 500; font-size: 12px; text-transform: uppercase; letter-spacing: 0.4px; }
tr:last-child td { border-bottom: 0; }
.kbd { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px;
       background: #f1f5f9; padding: 2px 6px; border-radius: 4px; border: 1px solid var(--line); }
.nav { display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px; }
.nav .brand { font-weight: 600; font-size: 18px; color: var(--fg); }
.nav .links { display: flex; gap: 16px; align-items: center; }
"""


LANDING_HTML = (
    """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>QueryShield — secure SQL proxy for AI agents</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="description" content="QueryShield is a secure SQL proxy for AI agents: send natural language, get SELECT-only validated SQL with per-agent row-level security and full audit. Your LLM agents never see database credentials.">
    <link rel="canonical" href="https://queryshield.dev/">
    <meta name="robots" content="index, follow">
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="QueryShield">
    <meta property="og:title" content="QueryShield — secure SQL proxy for AI agents">
    <meta property="og:description" content="A secure proxy between your AI agents and your databases. SELECT-only AST validation, per-agent row-level security, and append-only audit. Agents never see connection strings.">
    <meta property="og:url" content="https://queryshield.dev/">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="QueryShield — secure SQL proxy for AI agents">
    <meta name="twitter:description" content="Secure database access control for LLM agents: natural language in, safe validated SQL out, with per-agent RLS and full audit.">
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "SoftwareApplication",
      "name": "QueryShield",
      "applicationCategory": "SecurityApplication",
      "operatingSystem": "Any",
      "description": "A secure SQL proxy and database access control layer for AI agents. Translates natural language to SELECT-only validated SQL, enforces per-agent row-level security, and audit-logs every query. MCP-native.",
      "url": "https://queryshield.dev/",
      "offers": { "@type": "Offer", "price": "500", "priceCurrency": "USD" }
    }
    </script>
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "FAQPage",
      "mainEntity": [
        {
          "@type": "Question",
          "name": "How does QueryShield protect a database from AI agents?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "QueryShield sits between your AI agents and your databases as a secure proxy. It validates every query at the AST level (SELECT-only, no stacked statements, no forbidden functions), applies per-agent row-level security, and audit-logs every call. Agents never see connection strings."
          }
        },
        {
          "@type": "Question",
          "name": "Can AI agents run DELETE, DROP, or UPDATE through QueryShield?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "No. QueryShield's AST validator only allows SELECT statements. INSERT, UPDATE, DELETE, DROP, and stacked statements are rejected before they ever reach your database."
          }
        },
        {
          "@type": "Question",
          "name": "Does QueryShield work with the Model Context Protocol (MCP)?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "Yes. QueryShield is MCP-native and listed in the official MCP Registry. Install queryshield-mcp and drop it into Claude Desktop, Cursor, or any MCP-aware client."
          }
        }
      ]
    }
    </script>
    <style>"""
    + _BASE_CSS
    + """
    .hero { padding: 32px 0 8px; }
    .signup-card { max-width: 460px; margin-top: 24px; }
    </style>
</head>
<body>
<div class="wrap">
    <nav class="nav">
        <span class="brand">QueryShield</span>
        <span class="links">
            <a href="/login">Log in</a>
            <a href="/docs">API</a>
            <a href="/aeo/guides">Guides</a>
            <a href="https://github.com/bch1212/queryshield">GitHub</a>
        </span>
    </nav>

    <div class="hero">
        <h1>The security layer your AI agent stack is missing.</h1>
        <p class="tag">A secure proxy between your agents and your databases. Send natural language; get safe SQL, per-agent row-level security, and full audit. Agents never see connection strings.</p>
        <p>
            <span class="pill">SELECT-only AST validator</span>
            <span class="pill">Per-agent RLS</span>
            <span class="pill">Append-only audit</span>
            <span class="pill">MCP-native</span>
        </p>
    </div>

    <div class="card signup-card">
        <h2 style="margin-top:0">Sign up — get an API key in 30 seconds</h2>
        <form method="post" action="/signup">
            <label for="email">Work email</label>
            <input id="email" name="email" type="email" required placeholder="you@company.com">
            <label for="workspace">Workspace name (optional)</label>
            <input id="workspace" name="workspace" type="text" placeholder="Acme">
            <p style="margin: 18px 0 0;"><button type="submit" class="btn">Create my workspace</button></p>
        </form>
        <p class="muted" style="margin-top: 16px;">Free tier: 3 databases · 1M queries/month · no credit card.</p>
    </div>

    <h2>How it works</h2>
    <ol>
        <li>You sign up; we hand you an admin API key + dashboard.</li>
        <li>You register your DB connection string. We encrypt it at rest with AES-128 (Fernet); your agents never see it.</li>
        <li>Your agent calls <span class="kbd">POST /v1/query</span> in natural language. We translate to SQL via Claude, validate at the AST level, apply your row-level security policy, execute, and audit-log every call.</li>
    </ol>

    <h2>MCP integration</h2>
    <p>Drop into Claude Desktop / Cursor / any MCP-aware client:</p>
    <pre><code>pip install queryshield-mcp

# .mcp.json or claude_desktop_config.json
{
  "queryshield": {
    "command": "queryshield-mcp",
    "env": { "QUERYSHIELD_API_KEY": "qs_..." }
  }
}</code></pre>
    <p>Listed in the <a href="https://registry.modelcontextprotocol.io/v0/servers?search=queryshield">official MCP Registry</a> as <span class="kbd">io.github.bch1212/queryshield</span>.</p>

    <h2>Guides</h2>
    <p>Practical answers to the questions teams ask before giving an AI agent database access:</p>
    <ul>
        <li><a href="/aeo/guides/block-delete-drop-llm-sql">How do I block DELETE and DROP from LLM-generated SQL?</a></li>
        <li><a href="/aeo/guides/prevent-sql-injection-llm-queries">How do I prevent SQL injection from LLM-generated queries?</a></li>
        <li><a href="/aeo/guides/rbac-for-ai-agents">How do I enforce RBAC for AI agents accessing a database?</a></li>
    </ul>

    <h2>Pricing</h2>
    <table>
        <thead><tr><th>Tier</th><th>Monthly</th><th>Databases</th><th>Queries/month</th></tr></thead>
        <tbody>
            <tr><td>Starter</td><td>$500</td><td>3</td><td>1M</td></tr>
            <tr><td>Pro</td><td>$1,500</td><td>10</td><td>10M (audit export)</td></tr>
            <tr><td>Enterprise</td><td>$3,500</td><td>unlimited</td><td>SSO + SIEM webhook</td></tr>
        </tbody>
    </table>

    <p class="muted" style="margin-top: 48px;">Docs: <a href="/docs">/docs</a> · Health: <a href="/health">/health</a> · <a href="https://github.com/bch1212/queryshield">github.com/bch1212/queryshield</a></p>
</div>
</body>
</html>
"""
)


_LOGIN_TEMPLATE = (
    """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>QueryShield — Log in</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>"""
    + _BASE_CSS
    + """
    .login-card { max-width: 420px; margin: 60px auto 0; }
    </style>
</head>
<body>
<div class="wrap">
    <nav class="nav"><span class="brand"><a href="/">QueryShield</a></span></nav>

    <div class="card login-card">
        <h1 style="font-size: 24px;">Log in</h1>
        <p class="muted">We'll email you a one-click sign-in link.</p>
        <form method="post" action="/login">
            <label for="email">Email</label>
            <input id="email" name="email" type="email" required>
            <p style="margin: 18px 0 0;"><button type="submit" class="btn">Send link</button></p>
        </form>
        __ERROR_BLOCK__
        <p class="muted" style="margin-top: 24px;">No account? <a href="/">Sign up</a>.</p>
    </div>
</div>
</body>
</html>
"""
)


class _LoginRenderer(str):
    """str subclass so callers keep using ``LOGIN_HTML.replace("__ERROR__", msg)``.

    Renders an error block only when a non-empty message is passed.
    """

    def replace(self, key, value="", *a, **kw):  # type: ignore[override]
        if key == "__ERROR__":
            block = (
                f'<p class="error" style="margin-top: 16px;">{value}</p>' if value else ""
            )
            return _LOGIN_TEMPLATE.replace("__ERROR_BLOCK__", block)
        return super().replace(key, value, *a, **kw)


LOGIN_HTML = _LoginRenderer(_LOGIN_TEMPLATE)


SIGNUP_RESULT_HTML = (
    """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>QueryShield — Welcome</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>"""
    + _BASE_CSS
    + """
    .key { word-break: break-all; background: #0f172a; color: #fef3c7;
           padding: 14px 16px; border-radius: 8px; font-family: ui-monospace, monospace;
           font-size: 14px; user-select: all; }
    .copy-btn { margin-top: 8px; }
    .ok { color: var(--ok); font-weight: 600; }
    </style>
</head>
<body>
<div class="wrap">
    <nav class="nav"><span class="brand"><a href="/">QueryShield</a></span></nav>

    <div class="card">
        <p class="ok">✓ Workspace created.</p>
        <h2 style="margin-top: 0;">Your API key</h2>
        <p>This is shown <strong>once</strong>. Save it now — we don't store the cleartext.</p>
        <div class="key" id="api-key">__API_KEY__</div>
        <button class="btn secondary copy-btn"
                onclick="navigator.clipboard.writeText(document.getElementById('api-key').textContent); this.textContent='Copied'">
            Copy
        </button>

        <h3>Quickstart</h3>
        <pre><code>curl -X POST __BASE__/v1/databases \\
  -H 'X-Admin-Key: __API_KEY__' \\
  -H 'Content-Type: application/json' \\
  -d '{"alias":"prod","db_type":"postgresql","connection_string":"postgresql://..."}'

curl -X POST __BASE__/v1/query \\
  -H 'X-API-Key: __API_KEY__' \\
  -H 'Content-Type: application/json' \\
  -d '{"database_alias":"prod","query":"how many users signed up last week","mode":"nl"}'</code></pre>

        <h3>MCP integration</h3>
        <pre><code>pip install queryshield-mcp

# .mcp.json
{
  "queryshield": {
    "command": "queryshield-mcp",
    "env": { "QUERYSHIELD_API_KEY": "__API_KEY__" }
  }
}</code></pre>

        <p class="muted" style="margin-top: 32px;">
            Also sent to <strong>__EMAIL__</strong> with a magic link to your dashboard.
        </p>
    </div>
</div>
</body>
</html>
"""
)


VERIFY_FAILED_HTML = (
    """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>QueryShield — Link expired</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>"""
    + _BASE_CSS
    + """</style>
</head>
<body>
<div class="wrap">
    <nav class="nav"><span class="brand"><a href="/">QueryShield</a></span></nav>
    <div class="card">
        <h1 style="font-size: 24px;">That link is expired or already used.</h1>
        <p class="muted">Magic links expire 30 minutes after issue and can only be used once.</p>
        <p><a class="btn" href="/login">Get a new link</a></p>
    </div>
</div>
</body>
</html>
"""
)


DASHBOARD_HTML = (
    """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>QueryShield — Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>"""
    + _BASE_CSS
    + """
    .stat { font-size: 28px; font-weight: 600; margin: 0; }
    .stat-row { display: flex; gap: 24px; flex-wrap: wrap; }
    .stat-row .card { flex: 1 1 180px; margin: 0; }
    .new-key { background: #fef3c7; padding: 10px 14px; border-radius: 8px;
               font-family: ui-monospace, monospace; word-break: break-all; user-select: all; margin: 12px 0; }
    </style>
</head>
<body>
<div class="wrap">
    <nav class="nav">
        <span class="brand"><a href="/">QueryShield</a></span>
        <span class="links">
            <a href="https://github.com/bch1212/queryshield">GitHub</a>
            <a href="/docs">API</a>
            <a href="/auth/logout">Log out</a>
        </span>
    </nav>

    <h1 id="workspace">Loading…</h1>
    <p class="muted" id="owner"></p>

    <div id="upgrade-banner" class="card" style="display:none; background:#ecfdf5; border-color:#10b981;">
        <strong>You're on the new tier.</strong> Stripe processed your subscription successfully.
    </div>

    <div class="stat-row">
        <div class="card">
            <p class="muted" style="margin:0">Tier</p>
            <p class="stat" id="tier">—</p>
            <div id="upgrade-actions" style="margin-top:8px;"></div>
        </div>
        <div class="card"><p class="muted" style="margin:0">Queries this period</p><p class="stat" id="queries">—</p></div>
        <div class="card"><p class="muted" style="margin:0">Databases</p><p class="stat" id="dbcount">—</p></div>
    </div>

    <h2>API keys</h2>
    <p class="muted">Your admin key is shown only at signup. Lost it? Rotate to mint a new one. Issuing additional agents lets you scope different RLS policies per app.</p>
    <div class="card">
        <table id="agents-table">
            <thead><tr><th>Name</th><th>Prefix</th><th>Created</th><th></th></tr></thead>
            <tbody></tbody>
        </table>
        <details style="margin-top: 16px;">
            <summary class="muted" style="cursor:pointer;">+ Create another agent</summary>
            <div class="row" style="margin-top: 12px;">
                <input id="new-agent-name" type="text" placeholder="reporting-bot">
                <button class="btn secondary" onclick="createAgent()">Create agent</button>
            </div>
            <div id="new-agent-result"></div>
        </details>
    </div>

    <h2>Databases</h2>
    <div class="card">
        <table id="db-table">
            <thead><tr><th>Alias</th><th>Type</th><th>Created</th><th></th></tr></thead>
            <tbody></tbody>
        </table>
        <details style="margin-top: 16px;">
            <summary class="muted" style="cursor:pointer;">+ Register a database</summary>
            <div style="margin-top: 12px;">
                <label>Alias</label>
                <input id="db-alias" type="text" placeholder="prod">
                <label>Type</label>
                <select id="db-type">
                    <option value="postgresql">PostgreSQL</option>
                    <option value="mysql">MySQL</option>
                    <option value="mssql">MSSQL / Azure SQL</option>
                    <option value="sqlite">SQLite</option>
                </select>
                <label>Connection string (encrypted at rest)</label>
                <input id="db-cs" type="text" placeholder="postgresql://reader:secret@host:5432/db">
                <p class="muted" style="margin-top: 8px;">Tip: use a <em>read-only</em> database role. QueryShield's safety check + RLS only run inside our service; defense in depth means the DB itself should refuse writes.</p>
                <button class="btn secondary" onclick="registerDb()">Register</button>
                <div id="db-result"></div>
            </div>
        </details>
    </div>

    <h2>Recent activity</h2>
    <div class="card">
        <table id="audit-table">
            <thead><tr><th>When</th><th>Agent</th><th>Database</th><th>SQL</th><th>Rows</th><th>Result</th></tr></thead>
            <tbody></tbody>
        </table>
        <p id="audit-empty" class="muted" style="display:none;">No queries yet — fire one with the curl above to see it land here.</p>
    </div>
</div>

<script>
async function load() {
    const r = await fetch("/dashboard/data", { credentials: "same-origin" });
    if (r.status === 401) { window.location = "/login"; return; }
    const d = await r.json();

    document.getElementById("workspace").textContent = d.tenant.name || "Workspace";
    document.getElementById("owner").textContent = d.tenant.owner_email || "";
    document.getElementById("tier").textContent = d.tenant.tier;
    document.getElementById("queries").textContent =
        d.tenant.queries_used.toLocaleString() + " / " + d.tenant.queries_limit.toLocaleString();
    document.getElementById("dbcount").textContent =
        d.databases.length + " / " + (d.tenant.databases_limit > 1000 ? "∞" : d.tenant.databases_limit);

    // Upgrade actions — show buttons for tiers above the current one.
    const TIERS = [["pro","Pro · $1,500/mo"],["enterprise","Enterprise · $3,500/mo"]];
    const upgradeBox = document.getElementById("upgrade-actions");
    const idx = ["starter","pro","enterprise"].indexOf(d.tenant.tier);
    upgradeBox.innerHTML = TIERS.slice(idx).map(([t,label]) =>
        `<button class="btn secondary" style="margin-right:6px; margin-top:4px;"
                 onclick="upgrade('${t}')">Upgrade to ${label.split(' · ')[0]}</button>`
    ).join("");

    // Show the success banner if we just came back from Stripe Checkout.
    const params = new URLSearchParams(location.search);
    if (params.get("upgraded")) {
        document.getElementById("upgrade-banner").style.display = "block";
    }

    const agents = document.querySelector("#agents-table tbody");
    agents.innerHTML = d.agents.map(a => `
        <tr>
            <td>${esc(a.name)}</td>
            <td><span class="kbd">${esc(a.key_prefix)}…</span></td>
            <td class="muted">${a.created_at ? a.created_at.slice(0,10) : ""}</td>
            <td><button class="btn secondary" onclick="rotate('${a.id}', '${esc(a.name)}')">Rotate</button></td>
        </tr>
    `).join("") || `<tr><td colspan="4" class="muted">No agents yet.</td></tr>`;

    const dbs = document.querySelector("#db-table tbody");
    dbs.innerHTML = d.databases.map(x => `
        <tr>
            <td><span class="kbd">${esc(x.alias)}</span></td>
            <td>${esc(x.db_type)}</td>
            <td class="muted">${x.created_at ? x.created_at.slice(0,10) : ""}</td>
            <td><button class="btn secondary" onclick="deleteDb('${esc(x.alias)}')">Remove</button></td>
        </tr>
    `).join("") || `<tr><td colspan="4" class="muted">No databases registered yet.</td></tr>`;

    const audit = document.querySelector("#audit-table tbody");
    if (d.audit.length === 0) {
        audit.innerHTML = "";
        document.getElementById("audit-empty").style.display = "block";
    } else {
        document.getElementById("audit-empty").style.display = "none";
        audit.innerHTML = d.audit.map(e => `
            <tr>
                <td class="muted" style="white-space:nowrap;">${e.created_at.slice(0,16).replace("T"," ")}</td>
                <td><span class="kbd">${esc((e.agent_id||"").slice(0,8))}</span></td>
                <td>${esc(e.database_alias)}</td>
                <td><code style="font-size:12px">${esc(e.sql_executed.slice(0,90))}${e.sql_executed.length>90?"…":""}</code></td>
                <td>${e.row_count}</td>
                <td>${e.blocked_reason ? `<span style="color:var(--danger)">blocked</span>` : `<span style="color:var(--ok)">ok</span>`}</td>
            </tr>
        `).join("");
    }
}

function esc(s) { return String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;"}[c])); }

async function rotate(agentId, name) {
    if (!confirm(`Rotate API key for "${name}"? Old key stops working immediately.`)) return;
    const fd = new FormData(); fd.append("agent_id", agentId);
    const r = await fetch("/dashboard/agents/rotate", { method: "POST", body: fd, credentials: "same-origin" });
    const d = await r.json();
    alert(`New API key (shown once):\\n\\n${d.api_key}\\n\\nCopy it before closing this dialog.`);
    load();
}

async function createAgent() {
    const name = document.getElementById("new-agent-name").value.trim();
    if (!name) return;
    const fd = new FormData(); fd.append("name", name);
    const r = await fetch("/dashboard/agents", { method: "POST", body: fd, credentials: "same-origin" });
    const d = await r.json();
    document.getElementById("new-agent-result").innerHTML =
        `<div class="new-key">${esc(d.api_key)}</div><p class="muted">Copy this now — it's shown only once.</p>`;
    document.getElementById("new-agent-name").value = "";
    load();
}

async function registerDb() {
    const alias = document.getElementById("db-alias").value.trim();
    const dbType = document.getElementById("db-type").value;
    const cs = document.getElementById("db-cs").value.trim();
    if (!alias || !cs) { alert("Alias and connection string are required."); return; }
    const fd = new FormData();
    fd.append("alias", alias); fd.append("db_type", dbType); fd.append("connection_string", cs);
    const r = await fetch("/dashboard/databases", { method: "POST", body: fd, credentials: "same-origin" });
    if (!r.ok) { document.getElementById("db-result").innerHTML = `<p class="error">${esc(await r.text())}</p>`; return; }
    document.getElementById("db-result").innerHTML = `<p class="muted">✓ Registered.</p>`;
    document.getElementById("db-alias").value = "";
    document.getElementById("db-cs").value = "";
    load();
}

async function deleteDb(alias) {
    if (!confirm(`Remove database "${alias}"? Stored credentials will be deleted.`)) return;
    await fetch("/dashboard/databases/" + encodeURIComponent(alias), { method: "DELETE", credentials: "same-origin" });
    load();
}

async function upgrade(tier) {
    const fd = new FormData(); fd.append("tier", tier);
    const r = await fetch("/dashboard/upgrade", { method: "POST", body: fd, credentials: "same-origin" });
    if (!r.ok) {
        alert("Upgrade failed: " + (await r.text()));
        return;
    }
    const d = await r.json();
    if (d.checkout_url) {
        window.location = d.checkout_url;
    }
}

load();
</script>
</body>
</html>
"""
)


# --- AEO / category-intent guide pages (SEO content) -------------------------
# Recreates the /aeo/guides/<slug> URLs that search engines already index (they
# were served by a prior deploy and currently 404), and targets category-intent
# keywords QueryShield does not yet rank for. All content only — no app logic.

_GUIDE_CTA = (
    '<div class="card" style="margin-top:40px">'
    '<h2 style="margin-top:0">Enforce this automatically with QueryShield</h2>'
    '<p class="tag" style="margin-bottom:16px">A secure SQL proxy for AI agents: '
    'natural language in, SELECT-only validated SQL out, per-agent row-level '
    'security, and an append-only audit log. Your agents never see connection '
    'strings.</p>'
    '<p><a class="btn" href="/">Get an API key — free tier</a> '
    '<a class="btn secondary" href="/docs">Read the API docs</a></p>'
    '</div>'
)


def _guide_related(current_slug):
    """Cross-links to the other guides so no page is orphaned."""
    items = []
    for slug in AEO_GUIDES_ORDER:
        if slug == current_slug:
            continue
        items.append(
            '<li><a href="/aeo/guides/' + slug + '">'
            + AEO_GUIDES[slug]["h1"] + "</a></li>"
        )
    return "<h2>Related guides</h2><ul>" + "".join(items) + "</ul>"


def render_guide(slug):
    """Return the full HTML for one AEO guide, or None if the slug is unknown."""
    g = AEO_GUIDES.get(slug)
    if g is None:
        return None
    url = "https://queryshield.dev/aeo/guides/" + slug
    ld_faq = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": g["h1"],
                "acceptedAnswer": {"@type": "Answer", "text": g["answer"]},
            }
        ],
    }
    ld_breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "QueryShield",
             "item": "https://queryshield.dev/"},
            {"@type": "ListItem", "position": 2, "name": "Guides",
             "item": "https://queryshield.dev/aeo/guides"},
            {"@type": "ListItem", "position": 3, "name": g["h1"], "item": url},
        ],
    }
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n'
        '    <meta charset="utf-8">\n'
        "    <title>" + g["title"] + "</title>\n"
        '    <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '    <meta name="description" content="' + g["description"] + '">\n'
        '    <link rel="canonical" href="' + url + '">\n'
        '    <meta name="robots" content="index, follow">\n'
        '    <meta property="og:type" content="article">\n'
        '    <meta property="og:site_name" content="QueryShield">\n'
        '    <meta property="og:title" content="' + g["title"] + '">\n'
        '    <meta property="og:description" content="' + g["description"] + '">\n'
        '    <meta property="og:url" content="' + url + '">\n'
        '    <meta name="twitter:card" content="summary">\n'
        '    <meta name="twitter:title" content="' + g["title"] + '">\n'
        '    <meta name="twitter:description" content="' + g["description"] + '">\n'
        '    <script type="application/ld+json">\n'
        + json.dumps(ld_faq, indent=2) + "\n    </script>\n"
        '    <script type="application/ld+json">\n'
        + json.dumps(ld_breadcrumb, indent=2) + "\n    </script>\n"
        "    <style>" + _BASE_CSS + "</style>\n"
        "</head>\n<body>\n<div class=\"wrap\">\n"
        '    <nav class="nav"><span class="brand"><a href="/">QueryShield</a></span>'
        '<span class="links"><a href="/aeo/guides">Guides</a>'
        '<a href="/">Sign up</a></span></nav>\n'
        '    <p class="muted"><a href="/">QueryShield</a> &rsaquo; '
        '<a href="/aeo/guides">Guides</a></p>\n'
        "    <h1>" + g["h1"] + "</h1>\n"
        + g["body"] + "\n"
        + _GUIDE_CTA + "\n"
        + _guide_related(slug) + "\n"
        "</div>\n</body>\n</html>\n"
    )


AEO_GUIDES = {
    "block-delete-drop-llm-sql": {
        "title": "How do I block DELETE and DROP from LLM-generated SQL? — QueryShield",
        "description": (
            "Read-only database users help, but they are not enough to protect a "
            "database from AI agents. Learn how AST-level SELECT-only validation "
            "blocks DELETE, DROP, UPDATE, and stacked statements before they reach "
            "your database."
        ),
        "h1": "How do I block DELETE and DROP from LLM-generated SQL?",
        "answer": (
            "Validate every LLM-generated query at the AST (abstract syntax tree) "
            "level and allow only SELECT statements. QueryShield parses each query, "
            "rejects INSERT, UPDATE, DELETE, DROP, and stacked statements, and only "
            "then executes it against your database. Agents never receive write "
            "access or connection strings."
        ),
        "body": (
            "<p>The obvious answer &mdash; give the AI agent a read-only database "
            "user &mdash; is a good first layer, but it is not sufficient on its own. "
            "Read-only roles can be misconfigured, they do not stop expensive or "
            "data-exfiltrating <span class=\"kbd\">SELECT</span>s, and they push the "
            "security boundary onto every database you connect. To reliably "
            "<strong>protect a database from AI agents</strong>, block destructive "
            "statements <em>before</em> they ever reach the wire.</p>"
            "<h2>Validate at the AST level, not with string matching</h2>"
            "<p>Blocklisting the words <span class=\"kbd\">DROP</span> or "
            "<span class=\"kbd\">DELETE</span> in the raw SQL text is trivially "
            "bypassed with comments, casing, or encoding. Instead, parse the query "
            "into an abstract syntax tree and inspect the statement type. QueryShield "
            "allows a query only when:</p>"
            "<ul>"
            "<li>the statement is a single <span class=\"kbd\">SELECT</span> "
            "(no <span class=\"kbd\">INSERT</span>, <span class=\"kbd\">UPDATE</span>, "
            "<span class=\"kbd\">DELETE</span>, <span class=\"kbd\">DROP</span>, "
            "<span class=\"kbd\">ALTER</span>, or <span class=\"kbd\">TRUNCATE</span>);</li>"
            "<li>there are no stacked statements (no <span class=\"kbd\">;</span> "
            "chaining a second command);</li>"
            "<li>no forbidden functions or system tables are referenced;</li>"
            "<li>a <span class=\"kbd\">LIMIT</span> is present, capping how much data "
            "any single call can return.</li>"
            "</ul>"
            "<h2>Defense in depth</h2>"
            "<p>Pair AST validation with a read-only replica and per-agent row-level "
            "security so that even a novel bypass is contained. Every accepted and "
            "rejected query is written to an append-only audit log, so you can prove "
            "what an agent did and did not run.</p>"
        ),
    },
    "prevent-sql-injection-llm-queries": {
        "title": "How do I prevent SQL injection from LLM-generated queries? — QueryShield",
        "description": (
            "Text-to-SQL security is more than escaping strings. Learn how AST "
            "validation, allow-listing, and per-agent guardrails stop SQL injection "
            "and prompt-injection attacks in LLM-generated SQL."
        ),
        "h1": "How do I prevent SQL injection from LLM-generated queries?",
        "answer": (
            "Do not trust the LLM's output as safe SQL. Parse every generated query, "
            "allow only SELECT statements with no stacked commands or forbidden "
            "functions, enforce a mandatory LIMIT, and apply per-agent row-level "
            "security. QueryShield performs this validation on every query so "
            "injected or prompt-manipulated SQL is rejected before execution."
        ),
        "body": (
            "<p><strong>Text-to-SQL security</strong> is a distinct problem from "
            "classic parameterized-query hygiene. With an LLM in the loop, the query "
            "itself is generated from untrusted natural language, so a prompt "
            "injection can steer the model into producing SQL that is syntactically "
            "valid but unauthorized, destructive, or data-leaking.</p>"
            "<h2>Why escaping is not enough</h2>"
            "<p>Parameterization protects individual literals, but the LLM writes the "
            "<em>whole statement</em> &mdash; table names, joins, and clauses "
            "included. The real guardrail is a validation layer that inspects the "
            "generated SQL as structure, not text.</p>"
            "<h2>What a validation layer should enforce</h2>"
            "<ul>"
            "<li><strong>SELECT-only:</strong> reject any write or DDL statement at "
            "the AST level.</li>"
            "<li><strong>No stacked statements:</strong> a single query per call, so "
            "<span class=\"kbd\">SELECT 1; DROP TABLE users</span> can never run.</li>"
            "<li><strong>Function &amp; table allow-listing:</strong> block system "
            "catalogs and dangerous functions the agent has no business calling.</li>"
            "<li><strong>Mandatory LIMIT:</strong> cap result size so a single call "
            "cannot exfiltrate an entire table.</li>"
            "<li><strong>Per-agent row-level security:</strong> scope every query to "
            "the rows that agent is allowed to see.</li>"
            "</ul>"
            "<p>QueryShield applies all of these as a proxy in front of your "
            "database, and audit-logs every decision. Because the agent only ever "
            "talks to the proxy, it never sees connection strings or credentials to "
            "abuse in the first place.</p>"
        ),
    },
    "rbac-for-ai-agents": {
        "title": "How do I enforce RBAC for AI agents accessing a database? — QueryShield",
        "description": (
            "Database access control for LLM agents means scoping each agent to only "
            "the rows and tables it needs. Learn how per-agent row-level security and "
            "scoped API keys enforce least-privilege permissions for AI agents."
        ),
        "h1": "How do I enforce RBAC for AI agents accessing a database?",
        "answer": (
            "Give each AI agent its own scoped identity and enforce row-level "
            "security per agent, rather than sharing one broad database user. "
            "QueryShield issues per-agent API keys, applies a row-level security "
            "policy on every query, and audit-logs each call, so an agent can reach "
            "only the data its role permits."
        ),
        "body": (
            "<p>Most AI agent stacks share a single database connection with broad "
            "privileges, which means every agent can read everything. Effective "
            "<strong>database access control for LLM agents</strong> requires "
            "least-privilege, per-agent permissions &mdash; the same role-based "
            "access control (RBAC) principles you already apply to human users.</p>"
            "<h2>Scope identity per agent</h2>"
            "<p>Issue each agent its own credential instead of a shared secret. "
            "QueryShield hands out per-agent API keys so you can grant, rotate, and "
            "revoke access for one agent without touching the others, and every "
            "audit-log entry ties a query back to a specific agent.</p>"
            "<h2>Enforce row-level security on every query</h2>"
            "<p>Role-based table grants are coarse. Row-level security (RLS) lets you "
            "say &ldquo;this agent may read orders for tenant A only.&rdquo; "
            "QueryShield applies a per-agent RLS policy to every validated query "
            "before it executes, so scope is enforced deterministically outside the "
            "LLM &mdash; even if a prompt injection tries to widen it.</p>"
            "<h2>Least privilege, provable after the fact</h2>"
            "<p>Combine scoped keys and RLS with SELECT-only AST validation and an "
            "append-only audit log. The result is that an agent&rsquo;s blast radius "
            "is bounded by its permissions, and you can prove exactly which rows each "
            "agent touched.</p>"
        ),
    },
}

AEO_GUIDES_ORDER = [
    "block-delete-drop-llm-sql",
    "prevent-sql-injection-llm-queries",
    "rbac-for-ai-agents",
]


def render_guides_index():
    """Return the HTML for the /aeo/guides index page (lists all guides)."""
    cards = []
    for slug in AEO_GUIDES_ORDER:
        g = AEO_GUIDES[slug]
        cards.append(
            '<div class="card"><h2 style="margin-top:0">'
            '<a href="/aeo/guides/' + slug + '">' + g["h1"] + "</a></h2>"
            '<p class="muted" style="font-size:15px">' + g["description"] + "</p></div>"
        )
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n'
        '    <meta charset="utf-8">\n'
        "    <title>Guides — securing database access for AI agents — QueryShield</title>\n"
        '    <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '    <meta name="description" content="Practical guides on securing database '
        'access for AI agents: blocking DELETE/DROP from LLM SQL, preventing SQL '
        'injection in text-to-SQL, and enforcing RBAC and row-level security for AI '
        'agents.">\n'
        '    <link rel="canonical" href="https://queryshield.dev/aeo/guides">\n'
        '    <meta name="robots" content="index, follow">\n'
        "    <style>" + _BASE_CSS + "</style>\n"
        "</head>\n<body>\n<div class=\"wrap\">\n"
        '    <nav class="nav"><span class="brand"><a href="/">QueryShield</a></span>'
        '<span class="links"><a href="/">Sign up</a></span></nav>\n'
        "    <h1>Guides</h1>\n"
        '    <p class="tag">Securing database access for AI agents &mdash; the '
        "specific problems QueryShield solves.</p>\n"
        + "".join(cards) + "\n"
        + _GUIDE_CTA + "\n"
        "</div>\n</body>\n</html>\n"
    )
