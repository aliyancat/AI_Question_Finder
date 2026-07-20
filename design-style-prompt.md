# Design System Prompt — "Playful Pastel Brutalism"

Copy-paste this whole thing to your AI (Claude, Cursor, v0, whatever) when asking it to build or restyle your site.

---

## 1. Overall Vibe (one-liner to give the AI)

> "Design this like a playful pastel neo-brutalist product — bright candy colors, thick black outlines, chunky rounded cards, hard offset drop-shadows (no blur), bold friendly typography, floating pastel shapes in the background, and pill-shaped badges everywhere. It should feel fun, safe, and trustworthy at the same time — like Notion, Duolingo, and a Memphis-design poster had a baby."

This style is a deliberate mashup of:
- **Playful UI** — bright, cheerful, rounded, approachable, minimal shadow noise
- **Pastel UI** — soft lavender/yellow/blue/peach/coral as the core palette
- **Card UI** — every piece of content lives in its own bordered card (Notion/Spotify-style)
- **Soft Neo-Brutalism** — thick black borders, flat colors, high contrast, but rounded instead of sharp
- **Memphis-inspired accents** — scattered geometric shapes (circles, tilted squares) as pure decoration, no function

---

## 2. Color Palette (exact hex values)

### Base / Background
| Name | Hex | Use |
|---|---|---|
| Cream / Off-white | `#FFFEF5` or `#FDFBF0` | Page background |
| Ink Black | `#111111` / `#1A1A1A` | Borders, headings, primary text |
| Charcoal Gray | `#4B5563` | Body/paragraph text |

### Primary Accent (Brand)
| Name | Hex | Use |
|---|---|---|
| Indigo/Violet | `#6366F1` or `#4F46E5` | Primary brand color, key headline word, links |
| Hot Pink / Magenta | `#FF3D8A` or `#EC4899` | High-attention accent word (e.g. "AI" highlight) |

### Pastel Support Colors (for cards, tags, badges — rotate through these)
| Name | Hex |
|---|---|
| Soft Yellow | `#FDE68A` |
| Butter Yellow (background blob) | `#FFF3B0` |
| Lavender | `#D8B4FE` / `#E9D8FD` |
| Sky Blue | `#BAE6FD` / `#DBEAFE` |
| Mint Green | `#86EFAC` / `#D1FAE5` |
| Peach | `#FDBA74` |
| Coral | `#FF6B4A` |
| Baby Pink | `#FBCFE8` |

### Functional / Status Colors
| Status | Background | Text |
|---|---|---|
| Success / Available | `#DCFCE7` | `#16A34A` |
| Matched / Info | `#E0E7FF` | `#4F46E5` |
| Warning / Limited | `#FFEDD5` | `#EA580C` |
| Verified | `#D1FAE5` | `#059669` |

**Rule of thumb:** Background stays neutral cream. Every card/badge/button gets ONE pastel or bright color as its fill, always paired with a **solid black border**.

---

## 3. Typography

- **Font family:** A bold, rounded-friendly sans-serif — e.g. **Poppins, DM Sans, Inter, Plus Jakarta Sans,** or **Space Grotesk** for headings.
- **Headings (H1/H2):** Extra bold (800–900 weight), large size (48–72px for hero), tight line-height, black color by default.
  - Within headings, **highlight 1–2 key words** in the accent color (indigo) or wrap a word in a **filled pastel/bright box with a black border and slight rotation** (like the "AI" badge — yellow background, black border, pink bold text, rounded corners, subtle rotate -2deg to 2deg).
- **Body text:** Regular weight, gray (`#4B5563`), comfortable line-height (1.6), max-width constrained for readability (~600px).
- **Buttons/labels:** Bold or semi-bold, slightly larger tracking, always paired with an icon (arrow, chat bubble, checkmark).
- **Badges/pills:** Small, bold, uppercase or normal case, 12–14px.

---

## 4. Borders, Shadows & Shapes (the "soft brutalism" signature)

This is the most important part — it's what makes the style recognizable.

- **Border:** Every card, button, badge, and nav element gets a **solid black (or near-black) border, 2px–3px thick.** No thin 1px hairlines.
- **Corner radius:** Generous rounding — 12px–24px depending on element size (buttons/badges more rounded, almost pill-shaped; cards 16–20px).
- **Shadows:** NOT soft/blurred drop shadows. Use **hard offset shadows** — a solid black rectangle shadow offset by 3–6px with zero blur, e.g. `box-shadow: 4px 4px 0px #111111;`. This is the neo-brutalist signature move — it makes flat elements feel "poppable" and tactile.
- **Hover state:** On hover, shift the element slightly toward its shadow (e.g. `translate(2px, 2px)`) and reduce the shadow offset to `2px 2px 0px` — mimics a physical "push-down" button press.
- **Buttons:** Solid bright fill (green, indigo, black), black border, hard shadow, rounded-full or rounded-xl, bold white/black text, icon + arrow on the right.

---

## 5. Decorative Background Elements

Scatter a few **pure-decoration geometric shapes** behind/around the content — never functional, just atmosphere:
- Large soft-edge **blob/circle** in pastel yellow or lavender, placed off to one side, low opacity or flat fill, no border (creates depth without noise).
- **Tilted squares/rectangles** (rotate 10–20deg) in pastel purple, pink, or blue — placed in corners, sometimes with a thin border, sometimes flat.
- These shapes should sit **behind** text/cards (z-index low), sized large (150–350px), and never more than 3–4 on a page so it doesn't get busy.

---

## 6. Component Patterns

### Navbar
- Logo: small rounded-square icon (colorful, e.g. an icon on a white card with black border) + bold wordmark + small italic/light tagline underneath in accent color.
- Nav links: simple black text, active link gets an underline in the accent color.
- CTA button on the far right: solid bright color (green works well), black border, bold white text, icon, rounded-full or rounded-xl, hard shadow.

### Hero Section
- Small **pill-shaped announcement badge** above the headline (e.g. yellow background, black border, colored dot + bold text — "Now Live in X").
- Big bold headline split across 2 lines, with 1 keyword in accent color and 1 keyword in a highlighted box (see Typography section).
- Supporting paragraph in gray, shorter width.
- Two CTA buttons side by side: one solid/filled (primary), one white/outlined (secondary) — both with black border + rounded corners.
- To the side: a **stack of floating info cards** (see below) showing live/example data, each rotated very slightly or just stacked with spacing, each with its own hard shadow.

### Info/Data Cards (stacked, like the ride cards)
- White or cream background, black border (2px), rounded corners (12–16px), hard offset shadow.
- Small colored icon-chip on the left (rounded square, colored fill matching status).
- Bold title text + a small pill badge on the right showing status (Available/Matched/Limited) using the functional color table above.
- Secondary row below with small gray meta text (icons + details), separated by small dot separators (` • `).

### Feature/Trust Badge Strip
- A horizontal scrolling row of small pill badges, each with: icon + bold label, distinct pastel background, black border, rounded-full shape.
- Rotate through the pastel palette so no two adjacent pills share a color.
- Optional: thin black divider line above and below the strip.

### General Cards (features, testimonials, steps)
- Same black border + hard shadow + rounded corner treatment as above.
- Icon at the top in a colored rounded-square chip.
- Bold short title, gray supporting text underneath.
- Cards can have slight independent background tints (one card pastel yellow, next one white, next one pastel blue) to break monotony — always with black border regardless of fill color.

---

## 7. Iconography

- Simple, rounded, friendly line or filled icons (Lucide, Phosphor, or Heroicons style).
- Icons live inside small rounded-square or circular "chips" with a colored background + black border, not floating alone.
- Keep icon strokes bold/thick to match the chunky overall aesthetic.

---

## 8. Motion / Micro-interactions (optional, if interactive)

- Buttons: press-down effect on hover/click (shadow shrinks, element shifts toward shadow).
- Cards: subtle lift on hover (increase shadow offset slightly + tiny scale-up ~1.02).
- Badges: no motion needed, keep static.
- Background blobs: optional slow, subtle float/drift animation for extra life.

---

## 9. One-paragraph summary to paste directly into a prompt

> "Style this UI using a playful pastel neo-brutalist design system: cream (#FFFEF5) background, black (#111111) 2–3px borders on every card/button/badge, generous rounded corners (12–24px), and hard offset drop-shadows with zero blur (e.g. 4px 4px 0px black) instead of soft blurred shadows. Primary brand color is indigo/violet (#6366F1), with hot pink (#EC4899) and soft yellow (#FDE68A) as high-attention accents. Support colors are pastel lavender, sky blue, mint green, peach, and coral, used to color-code cards, pill badges, and icon chips — always paired with a black border. Typography is bold, rounded sans-serif (Poppins/DM Sans/Inter), with 1–2 keywords in headlines highlighted in accent color or boxed in a rotated colored badge. Add floating decorative pastel blobs and tilted squares in the background for atmosphere. Buttons and badges are pill-shaped or rounded-xl, bold, icon-forward, with a satisfying 'press down' hover interaction. The overall feel should be Notion/Duolingo/Memphis-poster energy: fun, chunky, trustworthy, and full of color-coded cards."

---

### Quick reference — copy this palette block into code (CSS variables)

```css
:root {
  --bg-cream: #FFFEF5;
  --ink: #111111;
  --text-gray: #4B5563;

  --brand-indigo: #6366F1;
  --brand-pink: #EC4899;

  --pastel-yellow: #FDE68A;
  --pastel-lavender: #D8B4FE;
  --pastel-blue: #BAE6FD;
  --pastel-mint: #86EFAC;
  --pastel-peach: #FDBA74;
  --pastel-coral: #FF6B4A;

  --status-success-bg: #DCFCE7;
  --status-success-text: #16A34A;
  --status-info-bg: #E0E7FF;
  --status-info-text: #4F46E5;
  --status-warning-bg: #FFEDD5;
  --status-warning-text: #EA580C;

  --border-width: 2px;
  --radius-card: 16px;
  --radius-pill: 999px;
  --shadow-hard: 4px 4px 0px var(--ink);
  --shadow-hard-hover: 2px 2px 0px var(--ink);
}
```
