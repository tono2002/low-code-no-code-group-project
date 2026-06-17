# 🎓 Student Marketplace

A tiny campus marketplace where students post second-hand items and browse a feed of
listings. Built for a low-code / no-code course final project.

**Stack:** React + Vite + Supabase (auth, database, storage) + Google Gemini for the
AI "describe my photo" feature.

## Features

- **Email/password auth** (Supabase). Logged-out users see a login/signup page;
  logged-in users see the feed.
- **Feed** — a grid of listing cards (photo, title, category, `€min–max`), newest first.
- **Sell** — upload a photo, optionally **Generate with AI** (Gemini reads the photo and
  fills in title/description/category/price), edit the fields, and publish.

## Prerequisites

- Node.js 18+ and npm
- A Supabase project with:
  - a `listings` table (columns: `id`, `created_at`, `user_id`, `title`, `description`,
    `category`, `price_min`, `price_max`, `image_url`)
  - a **public** Storage bucket named `item-photos`
  - Email auth enabled (Authentication → Providers → Email)
- A Google Gemini API key — https://aistudio.google.com/app/apikey

## Setup

```bash
npm install
cp .env.example .env   # then fill in your keys
npm run dev
```

Open the printed local URL (default http://localhost:5173).

### Environment variables (`.env`)

| Variable                 | Required | Description                                                        |
| ------------------------ | -------- | ------------------------------------------------------------------ |
| `VITE_SUPABASE_URL`      | yes      | Supabase project URL (Project Settings → API).                     |
| `VITE_SUPABASE_ANON_KEY` | yes      | Supabase anon/public key (Project Settings → API).                 |
| `VITE_GEMINI_API_KEY`    | no       | Default Gemini key for the Sell page. Can be overridden in the UI. |

> Vite only exposes variables prefixed with `VITE_` to the browser. The Supabase anon
> key and the Gemini key are used client-side by design for this project.

## How the AI feature works

On the Sell page, after a photo is uploaded, **Generate with AI** sends the image to
Gemini (`gemini-2.5-flash`) and asks for a JSON object
(`{title, description, category, price_min, price_max}`), which is parsed and dropped
into the form. The model name lives in one constant in
[`src/lib/gemini.js`](src/lib/gemini.js) (`GEMINI_MODEL`) so it's easy to swap.

## Project structure

```
marketplace/
├── index.html
├── package.json
├── vite.config.js
├── .env.example
├── README.md
└── src/
    ├── main.jsx              # app entry, providers, router
    ├── App.jsx              # auth-gated routing (feed vs. login)
    ├── styles.css           # all styling (plain CSS)
    ├── supabaseClient.js    # Supabase client + CATEGORIES + bucket name
    ├── context/
    │   └── AuthContext.jsx  # session state from Supabase auth
    ├── lib/
    │   └── gemini.js        # Gemini API call + JSON parsing
    ├── components/
    │   └── Header.jsx       # top bar (Sell, email, log out)
    └── pages/
        ├── Auth.jsx         # login / signup
        ├── Feed.jsx         # grid of listings
        └── Sell.jsx         # upload + AI + publish
```

## Deploy to Netlify

This is a static Vite site, so any static host works. For Netlify:

1. Push this folder to a GitHub repo.
2. In Netlify: **Add new site → Import an existing project**, pick the repo.
3. Build settings:
   - **Build command:** `npm run build`
   - **Publish directory:** `dist`
4. **Site settings → Environment variables** — add `VITE_SUPABASE_URL`,
   `VITE_SUPABASE_ANON_KEY`, and (optionally) `VITE_GEMINI_API_KEY`.
5. Deploy.

Because the app uses client-side routing, add a SPA redirect so deep links work. Create
a `public/_redirects` file (or a `netlify.toml`) with:

```
/*  /index.html  200
```

CLI alternative:

```bash
npm run build
npx netlify-cli deploy --prod --dir=dist
```

## Scripts

| Command           | What it does                       |
| ----------------- | ---------------------------------- |
| `npm run dev`     | Start the Vite dev server.         |
| `npm run build`   | Production build into `dist/`.     |
| `npm run preview` | Preview the production build.      |

## Automation layer (Zapier)

The app emits database events that a set of **Zapier** workflows react to. These Zaps run
*outside* this repo (configured in the Zapier dashboard); the app changes in
`AUTOMATION_TASKS.md` (sold status, etc.) are what make them fire. Recommended trigger:
**Supabase Database Webhooks** (Supabase → Database → Webhooks) pointed at a Zapier
"Catch Hook".

| Zap | Trigger | Actions |
| --- | --- | --- |
| **1. Price dataset** | New row in `listings` | Append to a master Google Sheet (title, category, price range, AI estimate, photo, date); on `status='sold'`, patch the row with `sale_price` + days-to-sell. |
| **2. Buyer alerts** | New row in `listings` | Look up matching `saved_searches`; email those users. |
| **3. Seasonal push** | Scheduled (move-in / move-out weeks) | Email a starter-pack digest; remind leavers to list. |
| **4. Sale lifecycle** | `listings` row updated to `status='sold'` | Write final price to the Sheet; email buyer + seller a pickup confirmation. |
| **5. Moderation** | New row in `listings` | Flag price outliers; route oddities to a Slack/email review queue. |
| **6. Welcome email** | New user in Supabase Auth | Send a welcome email explaining the AI listing flow. |

**The data flywheel:** Zap 1 + Zap 4 together build a Google Sheet of *asking price → AI
estimate → actual sale price → time-to-sell*. That dataset is the training set for a future
campus-specific pricing model that replaces the generic LLM estimate.

### Schema for the automation layer

These columns/tables back the Zaps. Run in the Supabase SQL editor **before** the sold/saved-
search features go live (see `AUTOMATION_TASKS.md`):

```sql
-- A1: sale lifecycle
alter table listings add column if not exists status text not null default 'active';
alter table listings add column if not exists sold_at timestamptz;
alter table listings add column if not exists sale_price numeric;

-- A3: keep the AI's original estimate on the row (price-training dataset)
alter table listings add column if not exists ai_recommended_price numeric;
alter table listings add column if not exists ai_price_reason text;

-- A2: saved searches (buyer alerts)
create table if not exists saved_searches (
  id bigint generated by default as identity primary key,
  created_at timestamptz not null default now(),
  user_id uuid not null references auth.users (id),
  category text,
  keyword text
);
```

### Security notes

- The Gemini key is currently client-side (fine for the course demo). For a public deploy,
  proxy the Gemini call through a serverless function so the key isn't exposed.
- Enable Supabase **Row Level Security** before production: public read of active listings,
  but inserts/updates scoped to `auth.uid() = user_id`.
