# PROGRESS.md — Student Marketplace

Running log of what's built, what's next, and how to verify. Pair with `PRD.md` (spec),
`DESIGN.md` (visual language), and `CLAUDE.md` (working rules). Dates are absolute.

## Status: v1 functional — runs locally end-to-end, pending real-account smoke test.

## Shipped
- [x] **Project scaffold** (2026-06-17): React + Vite app cloned from the empty
      `tono2002/low-code-no-code-group-project` repo (git remote kept). `npm install &&
      npm run dev` works; production `npm run build` is clean.
- [x] **Supabase wiring**: `src/supabaseClient.js` creates the client from
      `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY`, with `CATEGORIES` and the
      `item-photos` bucket name exported as shared constants.
- [x] **Auth** (`pages/Auth.jsx` + `context/AuthContext.jsx`): Supabase email/password
      login + signup with a tab toggle; session restored on load and synced via
      `onAuthStateChange`. App is auth-gated in `App.jsx` (logged out → Auth, in →
      Feed/Sell). Verified email confirmation is OFF on the project (signup returns a
      session immediately).
- [x] **Feed** (`pages/Feed.jsx`): reads `listings` ordered by `created_at` desc, renders
      a responsive card grid (image, title, category chip, `€min–max`), with loading and
      empty states. Price formatting handles single price / "Price on request".
- [x] **Sell** (`pages/Sell.jsx`): photo upload to the `item-photos` bucket (public URL
      kept), a Gemini key field defaulting from `VITE_GEMINI_API_KEY` (overridable),
      "Generate with AI", editable title/description/category/price fields, and Publish →
      insert with the current user's id → route to feed.
- [x] **AI listing assistant** (`lib/gemini.js`): posts the inline base64 image + a
      JSON-only prompt to `gemini-2.5-flash` with `x-goog-api-key` and
      `response_mime_type: application/json`; strips ``` fences, `JSON.parse`s, maps into
      the form; unknown category falls back to "Other". Model name is a single constant
      (`GEMINI_MODEL`).
- [x] **Styling** (`src/styles.css`): light theme, design tokens at `:root` (see
      `DESIGN.md`), plain CSS only.
- [x] **Docs**: `README.md` (setup, env vars, Netlify deploy), plus `CLAUDE.md`, `PRD.md`,
      `DESIGN.md`, and this file. `.env.example` documents the three env vars; Netlify SPA
      fallback at `public/_redirects`.
- [x] **UI smoke test** (2026-06-17): dev server booted, login page renders, no console
      errors. Screenshot confirmed the Auth screen.
- [x] **Mock data** (2026-06-17): 8 demo listings inserted via the Supabase REST API
      covering every category, owned by a demo account (`demo.seller@example.com`).
- [x] **Mock images fixed** (2026-06-17): replaced the initial loremflickr URLs (which
      served a *random* image per refresh) with deterministic, hand-verified Unsplash URLs
      (`?w=600&h=450&fit=crop`) so images are stable and on-topic. Three titles aligned to
      their photos: Robot Vacuum Cleaner, Desk Calculator, Braun Filter Coffee Machine.
      NOTE: this is Supabase row data, not in git — re-seed via the same REST PATCH if the
      table is reset.
- [x] **Relocation** (2026-06-17): project moved out of `session 10/` to the sibling
      `group project/marketplace/` folder; temporary preview config in `session 10` reverted.

- [x] **AI recognize & price + camera capture** (2026-06-17): the Sell "Generate with AI"
      step is now framed as **"Recognize & estimate price"** — Gemini identifies the item
      from the uploaded photo and returns a single `recommended_price` + a range +
      `price_reason`, shown in a prominent estimate banner (and prefilled into the fields).
      Photo step now has **📷 Take photo** (camera `capture`) and **⬆️ Upload photo**
      buttons. `lib/gemini.js` prompt/return extended with `recommended_price` and
      `price_reason`. Verified: Gemini call returns correct JSON (e.g. bike → €280, range
      €200–350 + reason); build clean; HMR applied. *(Full in-browser click-through still
      to do.)*

## In progress / next
- [ ] **AI image generation (blocked — needs paid Gemini plan)**: optional "generate image
      with AI from my description" checkbox. The image model `gemini-2.5-flash-image`
      returns **429 quota exceeded** on the current free-tier key, so it's deferred until
      billing is enabled — then build + verify end-to-end.
- [ ] **Real-account end-to-end smoke test**: sign up a fresh user in the browser, upload a
      real photo, run Generate with AI against a live Gemini key, publish, and confirm the
      item lands on top of the feed with a real `item-photos` URL.
- [ ] **Replace placeholder images**: the mock listings use loremflickr URLs; either
      re-shoot via the Sell upload or set stable image URLs.
- [ ] **Decide on Gemini key exposure** before any public deploy (referrer-restrict the key
      or proxy the call server-side).

## Backlog (candidate v2)
- [ ] Listing detail page + seller contact (email) / "message seller".
- [ ] Edit / delete / "mark as sold" for a user's own listings.
- [ ] Feed category filter + search + pagination.
- [ ] Image compression/resize and a size limit before upload.
- [ ] Password reset / email verification; optional SSO.
- [ ] Deploy to Netlify with env vars set and the SPA redirect live.

## Definition of Done (v1) — from PRD §10
- [ ] New user signs up and lands on the feed; session survives reload.
- [x] Feed reads `listings` newest-first; card shows image, title, category, `€min–max`.
- [ ] Sell uploads a photo to `item-photos` and keeps the public URL. *(code done; verify live)*
- [ ] "Generate with AI" fills the form from the photo via Gemini. *(code done; verify with real key)*
- [ ] Publish inserts the row with the user's id + image URL and shows it on top of the feed.
- [x] Errors (bad key, failed upload/insert) are shown, not swallowed.
- [x] `npm install && npm run dev` runs with only the documented env vars.

## How to verify quickly
```bash
cd "group project/marketplace"
npm install
npm run dev          # http://localhost:5173
```
Log in with the demo account (`demo.seller@example.com` / `demo123456`) to see the seeded
feed, or sign up your own. For the AI feature, paste a Gemini API key on the Sell page (or
set `VITE_GEMINI_API_KEY` in `.env`).
