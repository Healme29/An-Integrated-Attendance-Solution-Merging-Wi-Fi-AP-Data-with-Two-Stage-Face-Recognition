# Review notes — `2026-11-24_landing_mockup-v1.html`

> **Owner:** B · **Status:** proposal for C/D, not an implementation.
> **Scope:** the project's opening website only — the public explanation of what the system
> does and where the two dashboards are. Role-specific detail is in
> `2026-11-24_student-dashboard_mockup-v1_notes.md` and
> `2026-11-24_teacher-dashboard_mockup-v1_notes.md`.
> Palette and text hierarchy: `2026-11-24_design-system_notes.md` (identical in all three).
> Current backend facts: `docs/B/current_system_qr.md` · decision `docs/B/DECISIONS.md` D-015.

## What this view shows

1. **Hero** — `A.TTEND` logo, the unchanged display headline "THREE SIGNALS. ONE ATTENDANCE.",
   a short project description, and links into the two dashboards.
2. **Marquee** — the three conditions: `SCHOOL NETWORK / CURRENT QR TOKEN / MATCHING FACE`.
3. **01 / The conditions** — a decision panel (all three conditions passing → `partial`) and a
   refusal panel (four ways a check-in is rejected with no row written).
4. **02 / How it decides** — the lime band with the four-step flow and the honest fine print
   (5 s rotation, 10 s grace, subnet gate rather than room-level proof).
5. **03 / Two views** — cards linking to the teacher and student mockups.

## Continuity with the 2026-11-18 mockup

Kept verbatim: single-file HTML, the `:root` tokens, the display headline, outline middle word,
inverted marquee with yellow `✳`, asymmetric two-column grid, lime band with outlined flow
pills, `IntersectionObserver` reveal, mobile drawer, and reduced-motion fallback.

Changed only where the system changed: Wi-Fi AP / class window / start+end selfie became
school network / QR token / face + liveness; `/attendance/preflight` + `/attendance/check`
became `GET /qr-sessions/active` → `POST /attendance/check-qr`; `face_only` was replaced by the
four current roster values. The old landing mockup is labelled historical in the folder index.

## What D/C need to decide

1. Use this as the briefing page linked from the dashboard, or as the opening slide of the
   presentation; it is not an implemented route.
2. The two dashboard links are relative to this file's folder — confirm that works wherever the
   mockups are published.
3. If the team wants the Google Fonts link removed for the offline venue, the fallback stack
   already preserves the layout; no other change is needed.
