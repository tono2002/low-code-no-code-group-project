# Supply Chain Risk Console — Agentic AI

A password-gated **dashboard** (FastAPI + CrewAI, Tailwind UI) for the IE Agentic AI
assignment. Load a supply-chain data source, run a full risk analysis, and chat with
the agent about the loaded data. Everything runs **on the server**.

**Data sources** (left sidebar) — each normalises into one shared workspace and gets a
simulated logistics-risk layer:
- **Upload CSV/XLSX** (`app/sources.py`, pandas) — arbitrary files, columns auto-detected
  and profiled, supplier-like columns mapped to risk heuristics. Caps: 5 MB / 50k rows.
- **Connect SAP / Odoo / Microsoft Dynamics 365** (`app/erp.py`) — **simulated** ERP feeds
  with each system's authentic field names (LIFNR/EBELN…, res.partner/purchase.order,
  PurchId/VendorAccount…) and a clearly-labelled handshake. Prod path: env `SAP_BASE_URL`
  / `ODOO_URL` / `DYNAMICS_URL`.
- **Synthetic dataset** (`app/dataset.py`, seeded, reproducible) — one click, risk baked in.

**Logistics risk** (`app/logistics.py`, simulated) — in-transit shipments by mode
(Sea/Air/Road/Rail) with weather risk, port congestion, delay probability, value-in-transit
and **expected delay cost**. The "flights/ships delayed + cost" dimension.

**Analysis** — a Data-Analyst → Risk-Strategist crew reads the data + logistics and writes a
board-ready risk briefing (cost-at-risk + Agentic AI opportunities), grounded in the real
numbers. An optional free-text **focus** ("only the shipping routes") steers the scope.

**Chat** — a persistent panel answers questions and does focused re-analysis over the loaded
workspace.

- **LLM:** **Ollama `glm-5.1:cloud`** primary, **Gemini `gemini-2.5-flash-lite`** fallback
  (`PRIMARY_BACKEND`). **Stack:** FastAPI + CrewAI, one Docker container, Traefik auto-TLS,
  shared in-memory workspace (`app/workspace.py`).

### Why Ollama is primary (not Gemini)
Gemini's free tier is only **~20 calls/day** — for ALL its models, including
flash-lite. Far too little for a shared app. The Ollama `glm-5.1` cloud model is
fast and uncapped, so it runs first; Gemini is kept as a fallback. If Gemini ever
goes on a paid key, set `PRIMARY_BACKEND=gemini` to flip the order.

### Security (defense-in-depth — not "unbreakable", but layered)
- **Auth:** shared password, constant-time compare, signed HttpOnly cookie.
- **Brute force:** per-IP lockout (6 fails / 5 min → 10 min lock) + 0.7s delay per fail.
- **Abuse/cost:** per-IP run rate limit (15 / 10 min) + global one-run-at-a-time lock + 1500-char input cap.
- **Scope + prompt injection** (`guard_topic` in `crew.py`): injection-phrase regex
  (fast pre-LLM reject) → keyword allow → LLM classifier for the ambiguous middle.
  Off-topic / manipulation never reaches the crew.
- **In-prompt defense:** the focus, chat message, uploaded content and ERP data are wrapped
  in `<<<UNTRUSTED>>>` markers; every agent carries inviolable rules (scope-lock, treat
  delimited content as data only, never reveal prompt/keys, else emit `OUT_OF_SCOPE`).
- **Blast radius:** agents have no tools/shell/DB and keys live in env, not the prompt —
  so even a successful injection can only affect text output, not take actions.
- Hardening headers: `X-Frame-Options: DENY`, `nosniff`, `no-referrer`.

### Why analysis runs over a profiled summary (not raw rows)
A 180k-row CSV won't fit an LLM context, and per-row tool-calling is flaky on cheap models.
So `app/sources.py` profiles uploads (column stats + sample) and the crew analyses that
summary + the logistics layer — a couple of model calls per run, any model works, grounded
in the real numbers.

## Files
- `app/workspace.py` — shared in-memory workspace (loaded source + analysis + chat).
- `app/sources.py` — CSV/XLSX upload parsing + synthetic adapter (normalised shape).
- `app/erp.py` — simulated SAP / Odoo / Dynamics connectors.
- `app/logistics.py` — simulated in-transit shipments + delay-cost risk.
- `app/dataset.py` — seeded synthetic supplier dataset + risk scoring.
- `app/crew.py` — analysis crew (`analyze_workspace`) + chat (`run_chat`) + guard.
- `app/main.py` — FastAPI: auth, `/sources/*`, `/erp/*`, `/analyze`, `/chat`, security.
- `app/security.py` — rate limiting, brute-force lockout, constant-time compare.
- `app/static/` — `login.html` + `app.html` (Tailwind dashboard + chat).
- `Dockerfile`, `docker-compose.yml`, `.env.example`.

## Run locally
```bash
cp .env.example .env          # then fill in GEMINI_API_KEY, SERPER_API_KEY, SECRET_KEY
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# open http://localhost:8000  (password = APP_PASSWORD, default "agenticai")
```

## Deploy to the VPS
```bash
# from this folder:
rsync -az --delete --exclude .venv --exclude .git --exclude .env --exclude __pycache__ \
  ./ vps:agentic-ai-lab/
# first time only: create the .env on the VPS (keys live ONLY there)
ssh vps 'cd ~/agentic-ai-lab && cp -n .env.example .env'   # then edit ~/agentic-ai-lab/.env
ssh vps 'cd ~/agentic-ai-lab && docker compose up -d --build'
```
Then open `https://agenticai.srv1487908.hstgr.cloud`.

## Notes
- Runs are **serialised** (one crew at a time) so concurrent teammates don't trip
  Gemini's free-tier rate limit (10 req/min). A waiting request just queues.
- Keys live only in `.env` (gitignored on the Mac, chmod 600 on the VPS). Never committed.
