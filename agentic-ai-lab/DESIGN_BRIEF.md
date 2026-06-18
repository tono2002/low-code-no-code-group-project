# Design Brief — Supply Chain Risk Console

Hand this file (plus `app/static/app.html` and `app/static/login.html`) to a design-focused
AI (Lovable / v0 / Bolt / Cursor) to **upgrade the visual design** of the app. The goal is a
more polished, modern, "enterprise SaaS dashboard" look — **without changing what the app does
or breaking its backend contract**.

---

## 1. What the app is
A password-gated **supply-chain risk console** for a university Agentic-AI project (case
study: *Titan Manufacturing*, an industrial-machinery maker). A user loads a supply-chain
data source, the system runs an AI risk analysis (incl. simulated logistics + a LightGBM
late-delivery model), and the user chats with the agent about the data.

- **Audience:** a class/board presentation — should look credible and professional.
- **Tone:** serious enterprise analytics tool (think Linear / Vercel / Datadog dark dashboards).
- **Language:** English. **Theme:** dark.
- **Live:** https://agenticai.srv1487908.hstgr.cloud

## 2. Hard constraints (do not break these)
- **No build step / no framework.** The frontend is **one static file** `app/static/app.html`
  served by a FastAPI backend, using **Tailwind via CDN** + a little vanilla JS. Keep it that
  way: no React/Vue/Svelte, no npm build, no bundler. Tailwind CDN + custom CSS is fine.
- **Keep the backend contract** (section 4): the JS may be refactored, but it must still call
  the same endpoints with the same params and render the same response fields.
- Keep the **login page** (`login.html`) visually consistent with the app.
- Keep it **single-page** (no client router). Markdown is rendered with `marked` +
  sanitized with `DOMPurify` (keep sanitization — security requirement).
- Don't add external calls that leak data (no analytics/CDN trackers beyond Tailwind/marked/DOMPurify).

## 3. Current layout (what to redesign)
Three-column dashboard:
- **Top bar:** brand ("🛰️ Supply Chain Risk Console / Agentic AI · Titan Manufacturing"),
  a workspace-status pill, and a Log out link.
- **Left sidebar:** "Data source" buttons (Upload CSV/XLSX, Connect SAP, Connect Odoo,
  Connect MS Dynamics 365, Public dataset (USAID), Synthetic dataset); then "Run analysis"
  with an optional **focus** textarea, a "Deep analysis (multi-agent)" checkbox, and a button.
- **Main area:** an empty state, then once a source is loaded: an (optional) ERP connection
  panel, **KPI cards**, a **data table**, a **logistics-risk table** (shipments), an **ML
  late-delivery card** (predictions + feature-importance bars), and the **analysis briefing**
  (rendered markdown).
- **Right panel:** a **persistent chat** (message bubbles + input) about the loaded data.

### What to improve
- Make it feel like a premium analytics product: better spacing, typography scale, card
  hierarchy, subtle depth/shadows, refined color system, nicer empty/loading states,
  micro-interactions (hover/focus), a real risk **severity color language** (green/amber/red),
  optional small charts (e.g. a donut for risk mix, bars for delay cost) — Tailwind + inline
  SVG or a CDN chart lib is OK if it stays buildless.
- Improve responsive behavior (the 3 columns should gracefully stack/collapse on narrow widths;
  the chat could become a slide-over on mobile).
- Keep it fast and legible; don't over-animate.

## 4. Backend API contract (MUST keep working)
All routes require an auth cookie (set by logging in). The JS calls:

| Action | Request | Key response fields to render |
|---|---|---|
| Load synthetic | `GET /sources/synthetic?n=12` | the **workspace** object (below) |
| Load public CSV | `GET /sources/url?key=usaid` | `{ok, workspace}` |
| Upload file | `POST /sources/upload` (multipart `file`) | `{ok, workspace}` or `{ok:false, error}` |
| Connect ERP | `GET /erp/connect?system=sap\|odoo\|dynamics` then `GET /erp/data?system=...` | connect → handshake; data → **workspace** |
| Run analysis | `POST /analyze` form `focus` (string), `deep` (`true`/`false`) | `{ok, result (markdown), backend}` |
| Chat | `POST /chat` form `message` | `{ok, result (markdown), backend}` |
| Hydrate | `GET /workspace` | current **workspace** (or `{loaded:false}`) |

**Workspace object** (what every data load returns / `/workspace` gives):
```json
{
  "loaded": true,
  "source": "synthetic|upload|public|erp:sap|erp:odoo|erp:dynamics",
  "label": "Synthetic dataset (seed 42)",
  "summary": { "any_kpi_name": value, "...": "..." },        // render as KPI cards
  "table": { "columns": ["..."], "rows": [["..."], ...] },   // generic data table
  "connection": {                                             // present only for ERP sources
    "label": "SAP S/4HANA (simulated)", "system_id": "S4H", "client": "100",
    "protocol": "...", "auth": "...", "host": "...", "modules": ["..."], "note": "...", "simulated": true
  },
  "logistics": {
    "summary": { "shipments": 14, "value_in_transit_usd": 0, "expected_delay_cost_usd": 0,
                 "high_risk_shipments": 0, "worst_lane": "...", "by_mode": {"Sea":7,...} },
    "shipments": [ { "shipment_id","mode","carrier","origin","destination",
                     "eta_days","delay_probability","value_in_transit_usd","expected_delay_cost_usd" } ]
  },
  "forecast": {                                               // LightGBM model (may be null)
    "model": "LightGBM (binary late-delivery)", "holdout_auc": 0.71, "train_rows": 1200,
    "simulated_training": true, "predicted_late_count": 6,
    "predictions": [ { "supplier": "...", "late_risk_pct": 95.6 } ],
    "feature_importance": [ { "feature": "on_time_rate", "importance_pct": 32.8 } ]
  },
  "analysis_md": "## markdown briefing or null",
  "chat": [ { "role": "user|assistant", "content": "..." } ]
}
```
Notes for rendering:
- Tables are **generic** (`columns` + `rows`) — render any source the same way. Highlight rows
  by a column matching `/risk/i` (≥55 red, ≥38 amber) or `/delay/i` (>10 red, >0 amber).
- KPI `summary` keys vary by source — render them dynamically (label = key with `_`→space).
- `backend` shows which engine answered (e.g. "Ollama (kimi-k2.7-code:cloud)") — show as a small badge.
- Long actions (analyze ~30–90s) need a clear loading state; chat replies stream in as a bubble.

## 5. Current design tokens (change freely, just stay cohesive + dark)
- Background `#0a0e16`, panels `#111827` / `#0e1521`, borders `#1f2a3a`, text `#cbd5e1`/`#e5e7eb`,
  accent indigo `#6366f1`, success `#22c55e`, warning `#f5c842`, danger `#f85149`.
- Font: system sans (Tailwind default). A nicer font via CDN (e.g. Inter) is welcome.

## 6. Deliverable
Updated `app/static/app.html` (and `login.html`), still buildless (Tailwind CDN + vanilla JS),
preserving every API call and rendered field above. Ship the full files.
