# Review notes — `2026-11-24_student-dashboard_mockup-v1.html`

> **Owner:** B · **Status:** proposal for C, not an implementation.
> **Scope:** the student's own view only. The public intro is
> `2026-11-24_landing_mockup-v1.html`; the teacher console is
> `2026-11-24_teacher-dashboard_mockup-v1.html`.
> Palette and text hierarchy: `2026-11-24_design-system_notes.md` (identical in all three).
> Current backend facts: `docs/B/current_system_qr.md` · decision `docs/B/DECISIONS.md` D-015.

## Revision 2 (2026-11-25) — phone layout and persistent navigation markers

The same revision applied to the teacher dashboard is applied here, using the student's
horizontal top nav instead of a sidebar:

- **Phone layout:** below 900 px a fixed navy top bar carries the logo, overview link and a
  hamburger button; the nav becomes a right-side drawer with overlay, `Escape` to close and
  `aria-expanded`. Stats become two columns (one below 420 px), QR artwork shrinks to 140 px,
  buttons go full width, and each "Today's rows" entry becomes a labelled two-line card
  (phase / time / status) below 600 px. Verified at a 390 px viewport: no horizontal overflow.
- **Persistent state:** the active section keeps an ink pill with lime text and a `●` marker;
  visited sections keep a soft `✓`. Both are stored in `sessionStorage`, so they survive a
  reload. Hover still lifts the item 2 px with a light ink wash. The legend
  `● CURRENT · ✓ VISITED` sits at the bottom of the drawer.
- **Scroll sync:** scrolling updates the active item automatically; clicking an item suppresses
  that sync briefly so the marker does not jump during the smooth scroll. Deep links
  `#top`, `#checkin`, `#rows`, `#record` work on load.
- **Terminology:** the stat "Roster status" became **Attendance status** and the caption
  "ROSTER VALUES" became **STATUS VALUES**, for consistency with the teacher view. The API
  endpoint `GET /attendance/roster` is unchanged.

## What this view shows

1. **Header** — signed-in demo student and demo NIM, plus the network verdict (`IN SUBNET`).
2. **Three stats** — active session, rows today, attendance status (`Partial`).
3. **Projected QR card** — class/phase/token context, CSS QR placeholder, and the
   `SCAN & CHECK IN` action. The real image is `GET /qr-sessions/active/qr.png`.
4. **Three-signal card** — school network, current QR token, face + liveness, identity binding
   and the resulting row status.
5. **Today's rows** — `start` → partial, `spot` → partial, `end` → pending/absent, using the
   roster's own values (`verified / partial / pending / absent`).
6. **My record** — points at `GET /attendance/student/{id}` and notes that a teacher correction
   only appears after the session closes.

## Copy accuracy checked against `011840a`

- Token: 6 characters, rotates every 5 s, previous token valid 10 s. A phase change rotates the
  token and clears `prev_token` — hence the note under the session control in the teacher view.
- A failed condition writes **no row**: outside `SCHOOL_SUBNET` → 403, invalid/expired token →
  400, wrong face or identity mismatch → 403, duplicate for the phase → 409.
- `face_only` does not exist; it must not be reintroduced as a status.
- "SCAN & CHECK IN" is a visual affordance only. This page does not implement a scanner; the
  student flow lives in the Flutter app, and the check-in call is
  `POST /attendance/check-qr?student_id=&token=` with a multipart selfie.
- Liveness is passive and on by default (`LIVENESS_ENABLED=true`, minimum score 0.35).

## What C needs to decide

1. Link this from `/dashboard` as a companion page, or treat it only as a design reference for
   the Flutter student screens.
2. Make the `127.0.0.1:8000` API-docs link relative before anything ships outside the demo laptop.
3. Confirm the student-facing wording of the 403 cases with A, since the exact `detail` strings
   come from the backend.
