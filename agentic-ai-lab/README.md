# Agentic AI Lab — Supply Chain Crew

A password-gated web app for the IE Agentic AI assignment (Task 2). Your teammates
open a URL, log in with a shared password, type a topic, and a **CrewAI** two-agent
team runs **on the server** and returns an "Agentic AI Opportunities" briefing for
the Titan Manufacturing supply-chain challenge.

Two modes:
- **Web-search mode** — Researcher (Serper) → Strategist briefing for a typed topic.
- **Synthetic-dataset mode** — one click generates a seeded supplier table (numpy,
  `app/dataset.py`) with risk patterns baked in; a Data-Analyst → Strategist crew then
  cites the actual supplier numbers (worst suppliers, single-source/Tier-2 $ exposure,
  spend concentration). Reproducible by seed — ideal for a live demo.

Agents:
- **Researcher / Data Analyst** — synthesises live web results or the dataset.
- **Strategist** — turns it into a board-ready briefing tied to Titan's pain points.
- **LLM:** **Ollama `glm-5.1:cloud`** on the VPS is the primary engine; **Gemini
  `gemini-2.5-flash-lite` is the automatic fallback**. Order set by `PRIMARY_BACKEND`.
- **Stack:** FastAPI + CrewAI, one Docker container, behind Traefik with auto-TLS.

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
- **In-prompt defense:** the topic *and* the untrusted web results are wrapped in
  `<<<UNTRUSTED>>>` markers; every agent carries inviolable rules (scope-lock, treat
  delimited content as data only, never reveal prompt/keys, else emit `OUT_OF_SCOPE`).
- **Blast radius:** agents have no tools/shell/DB and keys live in env, not the prompt —
  so even a successful injection can only affect text output, not take actions.
- Hardening headers: `X-Frame-Options: DENY`, `nosniff`, `no-referrer`.

### Why the search runs in code (not as a CrewAI tool)
CrewAI's function-calling tool only works on heavyweight models and is flaky on
the cheap ones. So the Serper search runs directly in `crew.py` (`serper_search`)
and its results are injected into the researcher's task — ~2 model calls per run,
any model works, still grounded in live web data.

## Files
- `app/crew.py` — the CrewAI crew (agents, tasks, Gemini LLM).
- `app/main.py` — FastAPI: login, session cookie, `/run` endpoint (runs serialised).
- `app/static/` — `login.html` + `app.html` web UI.
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
