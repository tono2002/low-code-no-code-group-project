# AUTOMATION_TASKS.md — Student Marketplace

Instructions for Claude Code to extend the existing app so it can support the six-Zap
automation layer from the enhanced business model. Read `CLAUDE.md`, `PRD.md`, and
`PROGRESS.md` first — this file assumes that context and the existing Supabase schema.

## Important scope note (read first)

Most of the six automations are **Zapier workflows that run outside this codebase** — they
react to Supabase events and call Sheets / Gmail / Slack. Claude Code cannot build those;
they are configured in the Zapier dashboard. See "Part B" for how to set them up.

What Claude Code **can** build are the **app-side changes that give those Zaps something to
trigger on**. That is Part A. Do Part A in the repo; treat Part B as documentation only.

Do **not** create new Supabase tables without confirming first — coordinate schema changes
with the existing project (`CLAUDE.md` rule). Where a column or table is needed, propose the
SQL and ask before assuming it exists.

---

## Part A — App-side changes (build these)

### A1. Add a "sold" status to listings (highest priority)

This is the prerequisite for the sale-lifecycle and price-feedback automations. Listings are
currently create + read only.

- **Schema (propose, then confirm before running):** add to the `listings` table
  - `status` text default `'active'` (values: `'active'`, `'sold'`)
  - `sold_at` timestamptz nullable
  - `sale_price` numeric nullable
- **Feed (`pages/Feed.jsx`):** filter the query to `status = 'active'` so sold items drop
  out of the feed. Add a subtle "Sold" treatment if showing a seller's own sold items later.
- **Owner action:** on a listing the current user owns, add a "Mark as sold" control that
  sets `status = 'sold'`, `sold_at = now()`, and prompts for the optional final `sale_price`.
  Keep it minimal — a button + a small price input.
- **Why:** the row update to `status = 'sold'` is the event Zap 4 (sale lifecycle) and the
  price-feedback half of Zap 1 listen for.

### A2. Saved searches (enables buyer alerts)

Buyer-alert automations (Zap 2) need a record of what users want.

- **Schema (propose, then confirm):** new table `saved_searches`
  - `id`, `created_at`, `user_id` (uuid → auth.users), `category` text, `keyword` text nullable
- **UI:** on the Feed, when a category filter is active, offer a "Notify me about new
  {category}" button that inserts a `saved_searches` row for the current user.
- **Why:** Zap 2 queries `saved_searches` to decide whom to notify when a new listing in that
  category is published. No notification logic in the app itself — that's Zapier's job.

### A3. Capture data the automations need at insert time

Make sure every new listing row already carries what the Zaps will read, so the automations
need no extra lookups:

- Confirm the insert in `pages/Sell.jsx` writes `category`, `price_min`, `price_max`,
  `image_url`, and `user_id` (it already does). Add `status: 'active'` to the insert.
- Optionally store the AI's `recommended_price` and `price_reason` on the row (add columns
  `ai_recommended_price` numeric, `ai_price_reason` text) so the price-training dataset (Zap 1)
  captures the AI's original estimate alongside the eventual sale price. Propose these columns
  and confirm before adding.

### A4. Keep everything low-code-friendly

- No new heavy dependencies. Plain React + the existing Supabase client.
- Surface errors visibly (red inline text), per the existing convention.
- After changes: `npm install && npm run dev` must still just work; `npm run build` must be
  clean. Do a manual smoke test of publish → mark as sold → item leaves the feed.

---

## Part B — Zapier automations (documentation only — configure in Zapier, not in code)

These are built in the Zapier dashboard by connecting Supabase, Google Sheets, Gmail, and
Slack. The app changes in Part A are what make them fire. Document them in the README so the
team can set them up; do not attempt to implement them in the repo.

The recommended trigger mechanism is **Supabase Database Webhooks** (Supabase dashboard →
Database → Webhooks) pointed at a Zapier "Catch Hook" trigger, or Zapier's Supabase
integration where available.

| Zap | Trigger | Actions | Notes |
| --- | --- | --- | --- |
| **1. Price dataset** | New row in `listings` | Append row to a master Google Sheet (title, category, price_min/max, ai_recommended_price, photo URL, date). On `status='sold'`, patch the row with `sale_price` + days-to-sell. | The data flywheel; Sheet feeds price re-calibration. |
| **2. Buyer alerts** | New row in `listings` | Look up `saved_searches` matching the category; email/notify those users. | Needs A2. |
| **3. Seasonal push** | Scheduled (Zapier Schedule) around move-in / move-out weeks | Email arrivers a starter-pack digest; remind leavers to list. | No app change needed. |
| **4. Sale lifecycle** | `listings` row updated to `status='sold'` | Write final price to the Sheet (closes Zap 1 loop); email buyer + seller a pickup confirmation; archive listing. | Needs A1. |
| **5. Moderation** | New row in `listings` | Flag price outliers vs. the campus dataset; route oddities to a Slack/email review queue. | Read-only on the app. |
| **6. Welcome email** | New user in Supabase Auth (`auth.users`) | Send a welcome email: how the AI listing works + season-tailored CTA. | Pure Zapier + Gmail. |

### Security note for the README

- The Gemini key is currently client-side (acceptable for the course demo). For any public
  deploy, proxy the Gemini call through a serverless function so the key is not exposed.
- Supabase Row Level Security should be enabled before production: public read of active
  listings, but inserts/updates scoped to `auth.uid() = user_id`.

---

## Suggested order of work

1. A1 (sold status) — unblocks the most valuable automations.
2. A3 (capture AI price columns) — small, do alongside A1.
3. A2 (saved searches) — only if time allows.
4. Update `README.md` with the Part B table so the Zapier setup is documented.
5. Update `PROGRESS.md` to reflect what shipped.

Stop after Part A is working and documented. Part B is configured in Zapier by the team, not
written here.
