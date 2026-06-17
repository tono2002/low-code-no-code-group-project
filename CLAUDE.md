# CLAUDE.md — Student Marketplace

Guidance for working in this project. Built as a final project for a low-code / no-code
course. Pair this with `PRD.md` (what to build), `DESIGN.md` (how it looks), `PROGRESS.md`
(what's done), and `README.md` (how to run it).

## Project

A tiny campus marketplace where students post second-hand items (textbooks, electronics,
furniture, calculators, lab supplies) and browse a feed of listings. The standout feature
is **AI-assisted listing**: snap a photo on the Sell page and Google Gemini writes the
title, description, category, and a price range for you.

**Stack:** React + Vite (frontend) · Supabase (auth, Postgres, Storage) ·
Google Gemini `gemini-2.5-flash` (vision → structured listing). Plain CSS, no UI framework.

## Golden rules

- **Keep it low-code-friendly and runnable.** `npm install && npm run dev` must just work.
  No TypeScript, no test framework, no extra tooling unless trivial.
- **Do not create new Supabase tables.** The backend is already provisioned. Work against
  the existing `listings` table and the `item-photos` Storage bucket.
- **All config via env vars.** Never hard-code keys. `.env` is gitignored; `.env.example`
  is the contract.
- **One Gemini model constant.** The model name lives only in `src/lib/gemini.js`
  (`GEMINI_MODEL`) so it's a one-line swap.
- **English UI.** Unlike the sibling Spielportal project, this app's interface is English.

## Architecture

```
src/
  main.jsx              entry — Router + AuthProvider + global CSS
  App.jsx               auth gate: logged-out → Auth, logged-in → Feed/Sell
  supabaseClient.js     Supabase client + CATEGORIES + PHOTO_BUCKET constants
  context/AuthContext   Supabase session state (getSession + onAuthStateChange)
  lib/gemini.js         image → Gemini → parsed { title, description, category, price }
  components/Header.jsx  top bar: brand, Sell, email, log out
  pages/Auth.jsx        email/password login + signup
  pages/Feed.jsx        grid of listings, newest first
  pages/Sell.jsx        photo upload → AI generate → editable fields → publish
```

## Data model (existing — do not alter)

`listings` table:

| column        | type          | notes                                  |
| ------------- | ------------- | -------------------------------------- |
| `id`          | int8 PK       | auto                                   |
| `created_at`  | timestamptz   | feed orders by this, desc              |
| `user_id`     | uuid          | FK → `auth.users`; set to current user |
| `title`       | text          |                                        |
| `description` | text          |                                        |
| `category`    | text          | one of the six `CATEGORIES`            |
| `price_min`   | numeric       |                                        |
| `price_max`   | numeric       |                                        |
| `image_url`   | text          | public URL from `item-photos` bucket   |

Storage: public bucket **`item-photos`**; uploads keyed `"{user_id}/{timestamp}.{ext}"`.

Categories (must stay in sync with `supabaseClient.js`): Books & Notes, Electronics,
Furniture, Calculators, Lab & Supplies, Other.

## Conventions

- Components are small function components with hooks; no class components.
- Keep styling in `src/styles.css` using the CSS variables defined at `:root` (see
  `DESIGN.md`). Avoid inline styles for anything reusable.
- Surface errors visibly (red text near the action), never swallow them — especially the
  Gemini call, which can fail on a bad key, quota, or unparseable JSON.
- After editing the AI prompt or response handling, re-test with a real photo end-to-end.

## Environment

- `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` — required.
- `VITE_GEMINI_API_KEY` — optional default for the Sell page; users can paste their own
  key in the UI, which overrides the env value.

## Open questions / to confirm

- Should listings be editable / deletable after publishing? (Currently create + read only.)
- Add a category filter and/or search to the feed?
- Show the seller's contact (email) on a listing detail view, or keep it a flat feed?
- Image moderation / size limits on upload before going public?
