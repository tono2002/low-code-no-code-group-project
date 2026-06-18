# Executive Summary — Supply Chain Risk Console (Agentic AI)

> Living draft for the report/presentation. **Kept in sync with the app — update this
> whenever the app changes.** Not shown on the website. Last updated: 2026-06-18.

## The problem
Titan Manufacturing Corporation (TMC) — a global industrial-machinery maker (56,000
employees, 28 plants, 14 countries) — suffers from **fragmented operational intelligence**
in its supply chain: supplier delays up 28%, $14M/quarter in line-stoppage losses, no
visibility beyond Tier-1 suppliers, and expedited-logistics costs up 52%. Decisions are
manual and reactive; data is scattered across SCADA, EDI, email and spreadsheets.

## Our solution
A password-gated **Supply Chain Risk Console**: a web app where a user loads supply-chain
data, an **agentic AI crew** produces a board-ready risk analysis (with costs), and a
persistent chat answers follow-up questions and focused re-analyses. It demonstrates how
autonomous agents can unify scattered data and turn it into proactive, quantified decisions.

## How it works (pipeline)
1. **Load a data source** — upload a CSV/XLSX (auto-profiled), connect a (simulated) ERP
   (SAP S/4HANA · Odoo · MS Dynamics 365), pull a public dataset (USAID), or generate a
   synthetic one. Everything normalises into one workspace.
2. **Enrich** — a simulated **logistics-risk layer** (sea/air/road/rail shipments with
   weather, port congestion, delay probability and expected delay cost) and a **LightGBM**
   late-delivery model (per-supplier risk %, feature importance) are computed on load.
3. **Analyse** — a Data-Analyst → Risk-Strategist agent crew writes the risk briefing,
   grounded in the real numbers, with an optional free-text focus (e.g. "only shipping").
4. **Converse** — a chat agent answers questions and runs focused re-analyses over the data.

## Key capabilities
- Multi-source ingestion (file upload, ERP connectors, public data, synthetic).
- Quantified, full supply-chain risk analysis **with costs** (supplier + logistics).
- Real ML pipeline (LightGBM) for late-delivery risk prediction + explainability.
- Agentic AI opportunities mapped to the specific suppliers/shipments in the data.
- Conversational Q&A + re-analysis over the loaded workspace.

## Agentic AI opportunities (the case-study deliverable)
The crew surfaces opportunities such as: a **Tier-2 visibility / risk-sentinel agent**
(map sub-tier dependencies, flag concentration), a **predictive delivery & expediting
agent** (pre-empt high-delay shipments), and a **dynamic safety-stock / dual-sourcing
agent** — each tied to quantified exposure (e.g. spend-at-risk, expected delay cost).

## Architecture & engineering
- FastAPI + CrewAI, single Docker container behind Traefik (auto-TLS), Ollama
  (`kimi-k2.7-code`) primary LLM with Gemini fallback. Runs **autonomously** (auto-restart,
  health-checked, survives reboots).
- Security: shared-password auth + brute-force lockout, rate limiting, prompt-injection /
  scope guard, untrusted-data isolation; agents have no tools/secrets in-prompt.
- Fast (quick analysis ~50s) with an optional deep multi-agent mode.

## Honest scope
ERP connections and logistics/weather signals are **simulated** (clearly labelled; real
APIs are an env-config away). The ML model is trained on **simulated history** — the
*pipeline* is real, the data is illustrative. No paid APIs.

## Status / results
Live at `https://agenticai.srv1487908.hstgr.cloud`. End-to-end verified: all data sources
load, analysis cites real figures (e.g. ~$240k expected delay cost, named worst suppliers),
chat answers grounded questions, attacks are blocked, container stays healthy.
