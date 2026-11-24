# Review notes — `2026-11-24_student-dashboard_mockup-v1.html`

> **Owner:** B · **Status:** proposal for C, not an implementation.
> **Scope:** the student's own view only. The public intro is
> `2026-11-24_landing_mockup-v1.html`; the teacher console is
> `2026-11-24_teacher-dashboard_mockup-v1.html`.
> Palette and text hierarchy: `2026-11-24_design-system_notes.md` (identical in all three).
> Current backend facts: `docs/B/current_system_qr.md` · decision `docs/B/DECISIONS.md` D-015.

## What this view shows

1. **Header** — signed-in demo student and demo NIM, plus the network verdict (`IN SUBNET`).
2. **Three stats** — active session, rows today, roster status (`Partial`).
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
