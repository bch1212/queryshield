"""HTML templates for the web surface.

Pulled out of ``main.py`` so route handlers stay readable. All pages are
single-file (no external CSS/JS) and use the same dark/cool palette.
"""

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
