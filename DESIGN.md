# Design System — Student Marketplace

The visual language for Student Marketplace: an English-language web app for students to
buy and sell second-hand items. Tone: clean, friendly, and lightweight — a calm grey
canvas, white cards, and a single confident blue for actions. Pair this with `PRD.md` and
`CLAUDE.md`. All tokens live as CSS variables in `src/styles.css`.

## 1. Principles
- **Light and uncluttered.** Soft grey background, content on white cards. Let the product
  photos carry the color.
- **One accent, used sparingly.** Blue is for primary actions, links, active tabs, and
  category chips — nothing else competes with it.
- **One primary action per screen.** A single filled blue button (Log in / Publish / Sell);
  everything secondary is a quiet ghost button.
- **Legible over decorative.** High-contrast text, generous fields, no thin grey-on-grey.
- **Content-first feed.** The card grid is the hero; chrome stays minimal.

## 2. Color tokens
| Token            | Hex       | Use                                            |
| ---------------- | --------- | ---------------------------------------------- |
| `--bg`           | `#f6f7f9` | App background (soft grey)                     |
| `--surface`      | `#ffffff` | Cards, header, inputs                          |
| `--border`       | `#e3e6ea` | Borders on cards, inputs, ghost buttons        |
| `--text`         | `#1c2024` | Primary text                                   |
| `--muted`        | `#6b7280` | Labels, captions, secondary text               |
| `--primary`      | `#2563eb` | Primary actions, links, active tab, chips      |
| `--primary-dark` | `#1d4ed8` | Primary hover / pressed                        |
| `--danger`       | `#dc2626` | Error text                                     |
| `--success`      | `#16a34a` | Success / confirmation text                    |

**Text on blue:** always white (`#ffffff`) on a `--primary` fill.
**Chips / active tabs:** `--primary` text on a `#eff4ff` tint.

## 3. Typography
- **Family:** system stack — `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
  Helvetica, Arial, sans-serif`. No web-font loading.
- **Scale (px / weight):**
  - Brand / app title: 18–22 / 700
  - Page title (H2): 20 / 700
  - Section heading (H3): 15 / 600
  - Body / inputs: 14–16 / 400
  - Label: 14 / 600
  - Caption / muted: 13 / 400, color `--muted`
- Line-height ~1.4–1.5 for body; titles tighter.

## 4. Spacing, radius, layout
- **Spacing scale (px):** 4, 6, 8, 12, 14, 18, 24. Container padding 20–24. Field gap 14.
- **Radius:** 8 (buttons, inputs), 12 (cards, blocks), 999 (chips / pills).
- **Borders:** 1px `--border`. Cards add a soft shadow `0 1px 3px rgba(0,0,0,.08)`.
- **Containers:** feed max-width 1080px; forms (Sell, Auth) narrow at 640 / 380px.
- **Grid:** `repeat(auto-fill, minmax(220px, 1fr))`, 18px gap.

## 5. Components
- **Button** — radius 8, padding 9×16, text 14/600.
  - *Primary:* `--primary` fill, white text; hover `--primary-dark`. (One per screen.)
  - *Ghost:* transparent fill, `--border` border, `--text` label; hover light grey.
  - *Disabled:* 55% opacity, `not-allowed` cursor.
- **Field** — `--text` label (14/600) above the control. Inputs/selects/textarea:
  `--surface` bg, 1px `--border`, radius 8, padding 10×12, text inherits. Focus: 2px
  `--primary` outline (inset) + blue border.
- **Card (listing)** — white, 1px `--border`, radius 12, soft shadow, overflow hidden.
  A 4:3 image (object-fit cover) or a centered "No photo" placeholder, then a body with
  title, category chip, and price.
- **Block (Sell)** — white, 1px `--border`, radius 12, padding 18; a 15/600 heading and a
  vertical stack of fields.
- **Chip** — category label: `--primary` text on `#eff4ff`, radius 999, padding 2×8,
  12px/600. Self-aligned to the start.
- **Tabs (Auth)** — two equal buttons; the active one gets a blue border, blue text, and a
  `#eff4ff` fill; the inactive one is muted.
- **Header** — sticky white bar, 1px bottom border; brand on the left, actions on the
  right (Sell primary button, muted email, ghost Log out).
- **Inline message** — `--danger` text for errors, `--success` text for notices; placed
  next to the relevant action. No modal alerts.

## 6. States & motion
- **Hover:** primary darkens to `--primary-dark`; ghost buttons get a light grey fill.
  Transitions ≤150ms.
- **Focus:** visible 2px blue outline on every input (keyboard accessible).
- **Busy:** buttons disable and relabel during async work ("Uploading photo…",
  "Analyzing photo…", "Publishing…").
- **Errors/success:** surfaced as inline text near the action, never as browser alerts.
- Keep motion minimal — no decorative animation.

## 7. Iconography & imagery
- Brand mark: 🎓. The AI action uses ✨; the Sell action uses a `+` affordance.
- Imagery is user-supplied product photos, shown 4:3 cover-cropped on cards and as a
  small preview thumbnail on the Sell page. A clear "No photo" placeholder when absent.

## 8. Accessibility
- Body text and labels meet WCAG AA contrast on the light background; `--muted` (`#6b7280`)
  is the lightest text used for meaningful content.
- Every interactive control has a visible focus outline; inputs are paired with `<label>`.
- Don't rely on color alone — error/success states carry text, not just red/green.
- Images use descriptive `alt` (the listing title); the "No photo" state is real text.

## 9. Voice & copy
- **Language:** English throughout. Tone: friendly, plain, second person. Short button
  labels ("Sell", "Publish", "Log in", "Generate with AI"). Clear errors in sentences
  ("Please upload a photo before publishing."), never raw codes.
- Empty states encourage action ("Be the first — hit 'Sell' to post something.").

## 10. App identity
- Name: **Student Marketplace**. Brand emoji: 🎓.
- Platform: web (React + Vite), responsive single-column-to-grid layout. Light theme only.
- Categories (fixed set, shown as chips and select options): Books & Notes, Electronics,
  Furniture, Calculators, Lab & Supplies, Other.
