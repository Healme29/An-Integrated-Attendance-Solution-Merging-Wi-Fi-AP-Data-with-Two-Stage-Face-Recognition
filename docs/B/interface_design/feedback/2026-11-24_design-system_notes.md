# Shared design system — three views, one visual language (2026-11-24)

> **Owner:** B · **Applies to:** all three `2026-11-24_*_mockup-v1.html` files in `../mockups/`.
> This note is the single authoritative reference for the palette and text hierarchy. The
> per-mockup notes only describe content and accuracy.
> **Continuity:** this is the v2 system introduced on 2026-11-18 and rolled out to the live
> dashboard; no colour, font or size was invented for the QR redesign. See
> `2026-11-18_student-attendance_mockup-v1_notes.md` §"Design system v2" for the original
> decision (that file is historical only for its Wi-Fi copy, not for these tokens).

## File map

| View | File | Purpose |
|---|---|---|
| Project opening website | `../mockups/2026-11-24_landing_mockup-v1.html` | public intro: three conditions, the flow, links to both views |
| Student dashboard | `../mockups/2026-11-24_student-dashboard_mockup-v1.html` | student's active session, QR, check-in status, own rows |
| Teacher dashboard | `../mockups/2026-11-24_teacher-dashboard_mockup-v1.html` | session control, phase, live roster, export |

Each file is standalone: one `.html`, inline CSS and JS, no build step. The `:root` block is
identical in all three.

## Palette (identical to the 2026-11-18 v2 system)

| Token | Hex / value | Role |
|---|---|---|
| `--bg` / Canvas | `#ECF4F7` | page background |
| `--ink` / Structure | `#192853` | sidebar, headings, body copy, primary buttons, marquee, table structure |
| `--lime` / Signal | `#FFE14F` | active navigation, focus accent, "pass" tag, Live badge, lime band, key marker |
| `--muted` | `#5A6B82` | supporting copy, eyebrows, captions, table headers |
| `--line` | `rgba(25,40,83,.16)` | dividers |
| `--surface` | `#DCE8EE` | cards and panels (was `#DCE8EE` in v1) |
| `--font` | Space Grotesk → Segoe UI → system-ui → Arial | headings and body |
| `--mono` | DM Mono → SFMono-Regular → Consolas | eyebrows, labels, chips, captions |
| Supporting | `#12624F` success · `#B45309` warning · `#C4323C` danger · `#A88600` logo dot · `#9AAEC2` muted display word | statuses and small accents only |

Yellow is never used behind white text. Semantic chips keep green / amber / red. Fonts are
used only when installed locally; the fallback stack is deliberate so the demo works offline.

## Text hierarchy (identical scale in all three)

| Element | Size and treatment |
|---|---|
| Display heading | `clamp(70px, 11.5vw, 166px)` / 700 / `.86` / −.095em; middle word outlined with a 1.5 px ink stroke (landing only) |
| Page / section heading | `clamp(42px, 6vw, 76px)` / −.07em / `.95` (landing + student) |
| Lime-band copy | `clamp(30px, 4.5vw, 59px)` / −.06em / 1.12 (landing) |
| Dashboard page title | 30 px / −.05em (teacher — the established dashboard heading size) |
| Contact / record heading | `clamp(42px, 6vw, 76px)` / −.09em / `.9`, muted final word |
| Card title | 19 px / 600 |
| Stat value | 36 px / 700 / tabular numerals |
| Field value / body row | 15 px / 600 and 13 px |
| Eyebrow, section label, nav link, table header, flow pill | 11 px DM Mono, uppercase |
| Caption, chip, field key, table mono cell, footer | 10 px DM Mono, uppercase |

Reusable conventions: 8 px navy dot with a yellow glow before eyebrows; inverted navy marquee
with yellow `✳`; asymmetric `1.25fr / .75fr` two-column grid; 9 px yellow square before every
stat label; 1 px `--line` dividers; pill buttons (40 px radius); `IntersectionObserver` reveal
on the landing page; navy sidebar with a yellow active rail on the teacher view; mobile
navigation collapse; and a `prefers-reduced-motion` fallback.

## Navigation state (teacher view, revision 2)

A hover effect is temporary by design, so the teacher view now has two permanent states that
use only existing tokens:

| State | Visual | Persistence |
|---|---|---|
| Current page | yellow left rail + lime text + `●`, `aria-current="page"` | stays until another page is opened; deep links via `#session`, `#attendance`, … |
| Visited page | softer `✓` in lime at 55 % opacity | stored in `sessionStorage`, survives reloads |
| Hover | 3 px slide + 10 % lime wash | pointer only |

Both markers are explained by a legend in the sidebar footer (`● CURRENT · ✓ VISITED`).
Page content fades/slides in over 0.28 s; the animation is skipped under
`prefers-reduced-motion`.

## Phone layout check (390 px viewport, 2026-11-25)

All three files were measured at a 390 px viewport: no horizontal overflow; the landing and
student navigation drawers collapse; the landing hero drops to 64 px; student stats and cards
become one column; teacher stats become two columns (one below 420 px); the teacher table
becomes labelled cards; the teacher sidebar becomes an overlay drawer with a fixed top bar.
No colour, font or size token was changed for this revision.

## What is deliberately NOT in these mockups

- No Wi-Fi/AP/BSSID/ARP language, no `wifi_scanner`, no `REQUIRE_CLASSROOM_WIFI`, no
  `face_only`, no `/schedules/*` or `/wifi/*` (D-015 archived them).
- No real student data: names are `Demo Student N`, NIM values are demo values, the six-character
  token `A7K2Q9` is illustrative, and the QR artwork is a CSS placeholder labelled as such.
- No external images or embedded face photos. Google Fonts are optional and have local fallbacks.
- No claim of room-level presence: the network condition is a client-IP subnet gate.
