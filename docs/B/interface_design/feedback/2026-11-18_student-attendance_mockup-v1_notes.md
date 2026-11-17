# Review notes — `2026-11-18_student-attendance_mockup-v1.html`

> **Owner:** B · **Status:** proposal for C, not an implementation · **Input:** the
> "FORM — Creative Studio" single-file HTML supplied by the team lead.

## What was kept from the source

- The single-file delivery: one `.html`, inline CSS and JS, no build step.
- The visual system: cream/lime/ink palette, Space Grotesk + DM Mono, oversized
  outline headline, scrolling marquee, two-column asymmetric grid, lime band,
  `IntersectionObserver` reveal, mobile drawer, reduced-motion fallback.

## What was changed to fit this project

| Source element | Replacement | Reason |
|---|---|---|
| `FORM — Creative Studio` title / `F.RM` logo | `ATTEND — Student Attendance System` / `A.TTEND` | Names the actual project |
| "Selected Work" with two Unsplash photos | "Attendance Sheet" with two CSS data panels | Removes external image requests (offline demo) and shows product data instead of stock photography |
| "Design with purpose / think differently" marquee | `CORRECT AP / VALID CLASS WINDOW / START + END SELFIE` | The three conditions for attendance |
| Creative-studio hero copy | "Three signals. One attendance." + the exact rule | Matches the system's decision logic |
| "Who we are" lime band | "How it decides": AP → window → start face → end face | Explains the four-step flow and the strict-mode 403 |
| "Let's make it happen" contact | "Open the dashboard" shortcuts to `/dashboard` and `/docs` | Useful operator action instead of a fictitious studio email |
| `hello@example.com`, `© FORM STUDIO` | live URLs, `© Student Attendance System` | No placeholder identity left in the mockup |

## Accuracy constraints built into the copy

- Statuses are only `verified`, `partial` and `face_only` — these are the values the
  backend actually writes.
- Strict mode is described honestly: an off-network device gets `403` and **no row**;
  it does not silently become `face_only` (D-006).
- Wi-Fi is labelled AP-coverage level, not room-presence proof. No claim stronger than
  `network_validation.md` / `DECISIONS.md`.
- The phone app's pre-camera check order (`/schedules/active` then
  `/attendance/preflight`) is stated, so the web design cannot imply a different flow.
- All people are `Demo Student N` from `seed_demo.py`. No NIM, MAC or face photo is
  embedded; the names are explicitly marked illustrative.

## Known open item, deliberately not fixed here

The real dashboard's "Today's Schedule" card filters with `new Date().getDay()`
(Sunday = 0) against backend `day_of_week` (Monday = 0), so it is empty on weekdays.
That is a C-owned defect in `backend/static/dashboard.html`; this mockup does not
implement a fix, it only avoids repeating the assumption in its copy.

## What C needs to decide

1. Keep this as a **landing/briefing page** linked from the dashboard, or fold its
   sections into the existing sidebar navigation.
2. The `<link>` to Google Fonts is optional — fallbacks are declared. For an offline
   venue either self-host the two fonts or accept the system-font rendering.
3. The two URLs in the mockup point at `127.0.0.1:8000`. If the dashboard is served on
   another host/port, they must be made relative before it ships.

---

## Design system v2 — lead-requested palette (2026-11-18)

The first version used the source template's cream/lime palette. On the lead's
instruction it was replaced with a higher-contrast system:

| Token | Hex | Role |
|---|---|---|
| Signal | `#FFE14F` (gargoyle gas) | Active navigation, focus rings, chart accent, "Live" badge, key numbers' marker |
| Structure | `#192853` (deep navy) | Sidebar, headings, primary buttons, body copy, chart bars |
| Canvas | `#ECF4F7` (pale blue) | Page background, table hover, chart surfaces |

Supporting tokens derived from those three: `--text-secondary #5A6B82`,
`--border #D7E3EA`, `--success #12624F`, `--warning #B45309`, `--danger #C4323C`,
`--accent-light #FFF7CC`. Semantic colours were darkened until they carried white
text at a readable contrast; yellow is never used behind white text.

Typography and hierarchy changes in both the mockup and the live dashboard:
Inter/Segoe UI with tabular numerals for every count and timestamp, DM Mono for
eyebrows, table headers and status chips, uppercase tracking on section labels,
34 px stat values, 26 px page headings, and a yellow square before each card title.

## Live dashboard rollout

On the lead's explicit instruction, `backend/static/dashboard.html` (normally C-owned)
was restyled **without changing any presentation logic**:

- **Overview / live dashboard** — navy sidebar, yellow "Live" badge and active rail,
  pale-blue canvas, tabular stat values, card-title markers.
- **Management** — Attendance Sheet, Schedules and Face Enrollment inherit the same
  table, tab, modal and form-focus treatment; the active sheet tab now uses the yellow
  underline.
- **Operations** — Attendance, Wi-Fi Scanner and Recognition Demo inherit the same
  chip language (`verified`, `partial`, `face_only`), buttons and toasts.
- Inline architecture-diagram gradients and the two Chart.js colour arrays were moved
  to the new palette as well.
- Two layout defects were corrected while restyling: wide tables/charts no longer
  stretch the page (`.main { min-width: 0 }`, chart grid drops to one column below
  1100 px).

Verified in the browser at 800 px and 1000 px: no horizontal overflow, sidebar
`rgb(25,40,83)`, active item and "Live" badge `rgb(255,225,79)`, canvas
`rgb(236,244,247)`. The seeded instance still shows 5 students / 4 verified / 11
rows. C should review before this is merged, since the file is theirs.
