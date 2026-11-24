# Review notes — `2026-11-18_student-attendance_mockup-v1.html`

> **HISTORICAL RECORD — SUPERSEDED (2026-11-24).** This page documents the Wi-Fi/ARP
> presence design that existed before `origin/main` was pulled. The running system at
> `011840a` uses rotating QR sessions, `SCHOOL_SUBNET`, classes, teacher login and liveness;
> `wifi_scanner.py`, `/wifi/*`, `/schedules/*`, `/me/prompt`, `ap_bssid`, `face_only` and the
> 209-test suite no longer exist. Keep this file only as dated evidence of the validation
> method and of decisions D-001–D-014.
> Current system: `docs/B/current_system_qr.md` · direction decision: `docs/B/DECISIONS.md` D-015 ·
> archived Wi-Fi code: branch `wifi-backup-prepull` (`a9ca24d`).

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
implement a fix, it only avoids repeating the assumption in its copy. The live
dashboard has since been corrected — see the critical-review revision pass below.

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
36 px stat values, 30 px page headings, 15 px card headings, 11 px table headers,
and a yellow square before each card title. Fonts are used only when installed
locally; the fallback stack is deliberate so the dashboard works offline.

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

---

## Critical-review revision pass (2026-11-18)

Source: `backend/static/STITP_Frontend_Critical_Review_and_OpenCode_Instructions.md`.
Each finding was checked against the current repository and backend before editing.
No backend code, schema, attendance rule, Wi-Fi rule or API contract was changed.

### P0 — correctness

| Finding | Resolution |
|---|---|
| Weekday mismatch (review 3.1) | `const today = (new Date().getDay() + 6) % 7;` matches the backend's Monday=0. The seeded Wednesday class now appears in "Today's Schedule". |
| Chart lifecycle (3.2) | `statusChart` / `classChart` refs are destroyed before each rebuild; `typeof Chart` guards show a text fallback instead of throwing when the CDN is unreachable. |
| Edit Student (3.3) | The dialog is now "Edit MAC Address": name/NIM are disabled, the hint says they are fixed after enrollment, the button reads "Update MAC". The request uses the real contract `PUT /students/{id}/mac?mac_address=...` (query parameter, not JSON body). A JSON body was confirmed to return 422 locally. |
| Output escaping (3.4) | `statusChip` and `checkChip` allowlist the CSS class and escape the label; enrollment messages and the recognition `reason` are escaped. `<script>` / `<img onerror>` probes render as text. |
| UTC date (3.5) | `getLocalDateInputValue()` builds `YYYY-MM-DD` from local `getFullYear/getMonth/getDate`. |
| Debug card (3.6) | The unused "Debug: All Stored Embeddings" card was removed. No raw embedding was ever rendered. |
| Chart title (6.1) | "Class Distribution" → "Scheduled Classes by Subject" — the chart counts schedule rows, not attendance. |

### P1 — presentation and CSS

- Yellow (`#FFE14F`) is reserved for accent/action: Wi-Fi `Yes`, `Scan complete` and
  `Recognized!` now use `--success` (`#12624F`); chart headings and stat numbers stay
  navy. Semantic chips keep green/amber/red.
- Spacing tokens `--space-1`…`--space-7` were introduced; readable type scale:
  30 px headings, 15 px card headings, 36 px stats, 11 px table headers, 13 px body.
- Review 4.4 resolved: the `DESIGN SYSTEM REFINEMENTS` override block was folded into
  the authoritative base rules and reduced to genuinely unique rules. There are no
  duplicate selectors in the base context; the only repeated selectors left are
  intentional `@media` overrides.

### P2 — responsiveness, accessibility, reliability

- A real mobile drawer replaces the unlabeled icon sidebar: `#menuToggle` with
  `aria-expanded`, `#navOverlay`, focus-visible outlines, Escape and overlay-click
  close, and automatic close on navigation.
- All three modals have `role="dialog"`, `aria-modal="true"` and an `aria-labelledby`
  target; `openModal()` moves focus to the first enabled field and `closeModal()`
  restores it to the trigger.
- Student search is debounced (250 ms) and guarded by a request sequence number so
  stale responses cannot overwrite newer results; `refreshCurrent()` ignores repeat
  triggers while a refresh is in flight.

### Verification actually performed

- `./venv/bin/python -m pytest backend/tests -q` → **209 passed** (4 pre-existing
  deprecation warnings; no failures).
- Browser checks on `http://127.0.0.1:8000/dashboard` (empty real DB) and
  `http://127.0.0.1:8097/dashboard` (seeded DB): local date `2026-11-18`, no debug
  card, MAC-only edit dialog, escaped HTML probes, no horizontal overflow,
  `Chart.getChart()` true for both canvases before and after two refreshes, and no
  console errors.
- 1000 px checked directly; 768 px layout checked by re-applying the file's own
  `@media (max-width: 768px)` rules in the review viewport: menu button visible,
  sidebar off-canvas at −260 px, main margin 0, drawer opens on click, no overflow.
- API contract confirmed with curl: JSON body → 422 `missing query mac_address`;
  query string → 200 `{"message":"MAC address updated"}`.

### Still open / deliberately deferred

- Chart.js is loaded from a CDN; this venue intermittently returns
  `ERR_CONNECTION_CLOSED`. The fallback message keeps the rest of the dashboard
  usable, but self-hosting Chart.js is the durable fix (infrastructure decision).
- P3 modularization (splitting the single-file dashboard into modules) was not done;
  it is a larger refactor and needs separate approval.
- `backend/static/dashboard.html` is normally C-owned. C must review this revision
  before it is merged. This revision pass is committed only on `task-b`; no merge,
  PR or push.
