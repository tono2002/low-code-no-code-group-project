# App Plan — Student Marketplace

## 1. App Overview
Student Marketplace is an English-language web app where students at a school buy and sell
second-hand items among themselves — textbooks, electronics, furniture, calculators, lab
supplies, and more. Each person signs in with their own email and password. To post an
item, a seller uploads one photo; the app sends that photo to Google Gemini, which reads
the image and drafts a title, description, category, and a realistic price range. The
seller tweaks the fields and publishes. Everyone else sees the item in a reverse-chronological
feed of cards. The backend (database, auth, file storage) is already provisioned in
Supabase; the frontend is a React + Vite single-page app.

## 2. Key Components
Core:
- **Per-user accounts** — sign up / log in with email + password via Supabase Auth. The
  session is restored on reload and kept in sync through `onAuthStateChange`.
- **Listing feed** — all `listings` rows ordered by `created_at` descending, rendered as a
  responsive grid of cards (photo, title, category, price range).
- **Sell flow** — upload a photo to the `item-photos` Storage bucket (public URL kept),
  optionally generate the fields with AI, edit them, and insert a `listings` row owned by
  the current user.
- **AI listing assistant (the core feature)** — send the uploaded image inline (base64) to
  Gemini `gemini-2.5-flash` with a prompt that demands a strict JSON object; parse it and
  fill the form.

Enhancing:
- Gemini key is overridable in the UI (defaults from `VITE_GEMINI_API_KEY`), so each user
  can bring their own key.
- Graceful empty state ("Be the first — hit Sell") and a "No photo" card placeholder.

## 3. App Structure
The app is auth-gated. Logged-out users only ever see the **Auth** page; logged-in users
get the feed and the sell page.

Screens:
- **Auth** — a card with a Login / Sign up toggle, email + password fields, one primary
  button. On success the auth listener swaps to the app automatically.
- **Feed** (`/`) — header (brand, Sell, email, log out) + a grid of listing cards. Newest
  first. Empty and loading states handled.
- **Sell** (`/sell`) — three numbered blocks: (1) Photo upload, (2) Generate with AI
  (Gemini key field + button), (3) editable Details (title, description, category select,
  price min/max). Footer: Cancel / Publish.

Navigation flow: launch → `AuthContext` checks for a Supabase session → if none, show
**Auth**; if present, show **Feed**. The header's **Sell** button routes to `/sell`;
**Publish** inserts the row and routes back to `/`. **Log out** clears the session and
returns to **Auth**.

## 4. User Interface
Light theme on a soft grey background (`#f6f7f9`), white cards, a single blue primary
accent (`#2563eb`). Plain CSS with `:root` design tokens (see `DESIGN.md`). Shared
patterns: primary / ghost buttons, labeled form fields, listing cards, category chips,
error (red) and notice (green) inline messages.

- **Auth:** centered 380px card, brand "🎓 Student Marketplace", a two-tab segmented
  Login/Sign up control, two fields, one full-width primary button, inline error/notice.
- **Feed:** sticky header; an `auto-fill minmax(220px, 1fr)` grid of cards. Each card: 4:3
  image (or "No photo" placeholder), title, a blue category chip, and `€{min}–{max}`.
- **Sell:** narrow (640px) column of three bordered blocks; a live preview thumbnail after
  upload; a password-style Gemini key input showing the active model; disabled states while
  uploading / generating / publishing.

## 5. Backend Requirements
Backend exists in **Supabase** (Postgres + Auth + Storage); the frontend talks to it
directly with `@supabase/supabase-js` using the anon/publishable key. No custom server.

Schema (already created — do not modify):
- **listings** — `id` int8 PK, `created_at` timestamptz, `user_id` uuid FK→`auth.users`,
  `title` text, `description` text, `category` text, `price_min` numeric, `price_max`
  numeric, `image_url` text.

Auth: Supabase email/password. Row Level Security is expected to scope inserts to the
authenticated user (`auth.uid() = user_id`) while allowing public read of the feed.
Storage: a **public** bucket `item-photos`; objects are world-readable so `image_url`
works without signing.

## 6. APIs and Libraries
External:
- **Supabase JS** (`@supabase/supabase-js`) — auth, `from('listings')` queries,
  `storage.from('item-photos')` uploads + `getPublicUrl`.
- **Google Gemini REST** — `POST
  https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent`
  with header `x-goog-api-key`. Body: `contents[0].parts` = an `inline_data` part (base64
  image + mime type) plus a text prompt; `generationConfig.response_mime_type =
  "application/json"`. Response parsed from `candidates[0].content.parts[].text` (``` fences
  stripped, then `JSON.parse`).

Frontend libraries: react, react-dom, react-router-dom, @supabase/supabase-js, vite,
@vitejs/plugin-react. Plain CSS — no UI framework.

## 7. Testing Strategy
- **Manual smoke (primary):** sign up → land on feed → open Sell → upload a photo →
  Generate with AI fills the fields → edit → Publish → row appears at the top of the feed
  with the right image and `€min–max`. Log out → see the Auth page → log back in.
- **AI robustness:** verify the ``` fence stripping and JSON parsing against a response
  wrapped in a ```json block; confirm an invalid/empty key surfaces a visible error and
  doesn't crash the form; confirm an unknown category falls back to "Other".
- **Edge cases:** publishing without a photo is blocked; price fields accept empty (stored
  as null) and render as a single price or "Price on request"; very long titles wrap.
- No automated test framework is included by design (course scope).

## 8. Platform-Specific Considerations
- **Vite env:** only `VITE_`-prefixed vars reach the browser. The Supabase anon key and the
  Gemini key are client-side by design here; restrict the Gemini key by HTTP referrer once
  deployed.
- **Client-side routing:** deploys need an SPA fallback so deep links resolve. A
  `public/_redirects` (`/* /index.html 200`) is included for Netlify.
- **Storage paths:** uploads are keyed by `user_id` to avoid collisions and keep a user's
  photos grouped.
- **CORS / keys:** Gemini is called directly from the browser; that's acceptable for a
  course demo but means the key is exposed to anyone using the app with the env default.

## 9. Out of Scope for v1
- Editing or deleting a listing after it's published (create + read only).
- A listing detail page, messaging between buyer and seller, or "mark as sold".
- Search, category filters, sorting beyond newest-first, or pagination.
- Image moderation, resizing/compression, or multiple photos per listing.
- Password reset, email verification flows, social / SSO login.
- Server-side proxying of the Gemini call to hide the key.

## 10. Definition of Done
- A new user signs up with email + password and is taken to the feed; the session survives
  a page reload.
- The feed reads `listings` newest-first and renders each card with image, title, category,
  and `€{price_min}–{price_max}`.
- On Sell, a photo uploads to `item-photos` and its public URL is retained.
- "Generate with AI" sends the image to Gemini, parses the JSON (even when ``` fenced), and
  fills title, description, category, price_min, price_max.
- Publish inserts a `listings` row with the current user's id and the image URL, then
  routes to the feed where the new item appears on top.
- Errors (bad Gemini key, failed upload, failed insert) are shown to the user, not
  swallowed.
- `npm install && npm run dev` runs the app with only the documented env vars set.
