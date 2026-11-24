# Review notes — `2026-11-24_teacher-dashboard_mockup-v1.html`

> **Owner:** B · **Status:** proposal for C, not an implementation. The real teacher dashboard
> is `backend/static/dashboard.html`, which is C-owned.
> **Scope:** the teacher's console only. The public intro is
> `2026-11-24_landing_mockup-v1.html`; the student's view is
> `2026-11-24_student-dashboard_mockup-v1.html`.
> Palette and text hierarchy: `2026-11-24_design-system_notes.md` (identical in all three).
> Current backend facts: `docs/B/current_system_qr.md` · decision `docs/B/DECISIONS.md` D-015.

## What this view shows

1. **Navy sidebar** — Overview / Session / Roster / Classes / Students, with a yellow active
   rail; logo links back to the project overview.
2. **Top bar** — breadcrumb, lime `Live` badge, demo teacher identity.
3. **Four stats** — in class, verified, partial, absent; 36 px tabular values with the 9 px
   yellow square marker before each label.
4. **Active session card** — class, room, current token, rotation settings, state, the
   `start → spot → end → closed` phase strip, and the two teacher actions.
5. **Gate card** — allowed vs refused outcomes and the note that teacher actions require a
   Bearer token from `POST /teachers/login`.
6. **Live roster table** — student, check type, start/end times, status chip; CSV export and
   the manual-entry rule underneath.

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
- Roster endpoint: `GET /attendance/roster?qr_session_id=`; export:
  `GET /attendance/export/csv?date=&qr_session_id=`.
- No old status or route appears: no `face_only`, `/wifi/*`, `/schedules/*`, `ap_bssid` or
  `REQUIRE_CLASSROOM_WIFI`.

## What C needs to decide

1. Fold the session-control card into the existing `/dashboard` layout or keep it as a separate
   page; the sidebar here is a mockup convention, not a committed navigation change.
2. Wire the two buttons to the real endpoints above before using this as anything but a design
   reference.
3. Confirm that the four stat counts can be derived from the roster endpoint without an extra
   API call; if not, the labels should be reworded rather than the numbers estimated.
