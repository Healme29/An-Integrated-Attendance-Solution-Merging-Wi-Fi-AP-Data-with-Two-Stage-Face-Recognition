# Review notes — `2026-11-24_teacher-dashboard_mockup-v1.html`

> **Owner:** B · **Status:** proposal for C, not an implementation. The real teacher dashboard
> is `backend/static/dashboard.html`, which is C-owned.
> **Scope:** the teacher's console only. The public intro is
> `2026-11-24_landing_mockup-v1.html`; the student's view is
> `2026-11-24_student-dashboard_mockup-v1.html`.
> Palette and text hierarchy: `2026-11-24_design-system_notes.md` (identical in all three).
> Current backend facts: `docs/B/current_system_qr.md` · decision `docs/B/DECISIONS.md` D-015.

## Revision 2 (2026-11-25) — mobile layout and persistent navigation markers

- **Phone layout:** below 768 px the sidebar becomes a hamburger drawer (overlay, `Escape`
  to close, `aria-expanded`), a fixed top bar carries the logo/Live badge, stat cards become
  two columns (one column below 420 px), the roster table becomes stacked cards with
  `data-label` headers, and action buttons become full width. Verified at a 390 px viewport:
  no horizontal overflow, navigation collapsed, single-column cards.
- **Persistent state:** each nav item now opens its own page (`#overview`, `#session`,
  `#attendance`, `#classes`, `#students`). The **current** page keeps a yellow left rail,
  lime text and a `●` marker even after the pointer leaves; `aria-current="page"` is set.
  Pages already **visited** keep a softer `✓` marker, stored in `sessionStorage`, so the
  marker survives a reload. Hover still slides the item 3 px and tints the background.
- **Page transition:** switching pages fades/slides the content in (0.28 s), disabled under
  `prefers-reduced-motion`. The drawer no longer flashes on first paint because its transform
  transition is enabled only after the first two animation frames.
- **"Roster" renamed to "Attendance" in the UI.** *Roster* is the class list — the set of
  students enrolled in a class and the per-student result rows. It is jargon, so the menu
  item and page title now read **Attendance**, with the subtitle "one row per student". The
  backend endpoint keeps its existing name, `GET /attendance/roster?qr_session_id=`.

## What this view shows

1. **Navy sidebar** — Overview / Session / Attendance / Classes / Students, with a persistent
   `●` on the current page, `✓` on visited pages, and a legend in the sidebar footer.
2. **Top bar** — breadcrumb reflecting the active page, lime `Live` badge, demo teacher identity.
3. **Overview** — four stats (in class, verified, partial, absent), the gate-behaviour card and
   short links into Session / Attendance / Classes.
4. **Session** — class, room, current token, rotation settings, state, the
   `start → spot → end → closed` phase strip, and the two teacher actions.
5. **Attendance** — one row per student with check type, start/end times and status chip;
   CSV export and the manual-entry rule underneath. On a phone each row is a labelled card.
6. **Classes** — class list with room, student count and session state.
7. **Students** — enrolled students with NIM and embedding count.

## Copy accuracy checked against `011840a`

- The `Live` badge, sidebar and stat treatment follow the v2 rollout already applied to the
  live dashboard; no new visual token was added.
- Phase transitions are `start → {spot, end, closed}`, `spot → {start, end, closed}`,
  `end → closed`; an invalid transition is 409. `end` auto-closes after
  `FINAL_CHECK_GRACE_MINUTES` (5).
- `START FINAL ATTENDANCE` maps to `POST /qr-sessions/phase {"phase":"end"}`; the new token
  invalidates the start-phase QR.
- Manual attendance maps to `POST /attendance/manual` and is allowed **only after close**, with
  `manual_by`, `manual_at` and `manual_reason` audited.
- Attendance endpoint: `GET /attendance/roster?qr_session_id=`; export:
  `GET /attendance/export/csv?date=&qr_session_id=`.
- Classes: `GET /classes/`; students: `GET /students/?nim=`; enrollment: `POST /faces/enroll`.
- No old status or route appears: no `face_only`, `/wifi/*`, `/schedules/*`, `ap_bssid` or
  `REQUIRE_CLASSROOM_WIFI`.

## What C needs to decide

1. Keep these five pages as separate views, or fold the Session/Attendance cards into the
   existing `/dashboard` layout; the sidebar navigation is a mockup convention, not a
   committed route change.
2. Wire the two buttons to the real endpoints above before using this as anything but a design
   reference.
3. Confirm that the four stat counts can be derived from the roster endpoint without an extra
   API call; if not, the labels should be reworded rather than the numbers estimated.
4. Confirm that "Attendance" is the preferred teacher-facing label; "roster" remains correct
   for the API and the report.
