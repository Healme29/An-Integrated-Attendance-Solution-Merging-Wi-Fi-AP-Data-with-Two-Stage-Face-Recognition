# Server Website — Interface Design Inputs

> **Scope:** design inputs for the **server website** (the FastAPI dashboard at
> `/dashboard`, its pages, and the endpoints they call), not the Flutter app in `mobile/**`.
> **Owner:** B · **Created:** 2026-11-18 · **Updated after the 2026-11-13 project pull.**
> **Ownership boundary:** this folder stores inputs and notes only. The page actually
> rendered is `backend/static/dashboard.html`, which is **C's file**. Agree a change with C
> before it is implemented; do not edit it from here.

This is the known place for design material, so a brief, an annotated screenshot, or a link
to a design board is not lost in a chat thread. Anything placed here is reviewed before
someone touches the UI.

## Folder layout

| Path | What goes here |
|---|---|
| `input_forms/` | Briefs and field lists: which inputs a page needs, allowed values, validation rules, and what happens on submit |
| `references/` | Screenshots of the current UI, links to inspiration, and the exact URL / window size they were captured at |
| `mockups/` | Wireframes and proposed layouts, with a version number in the filename |
| `feedback/` | Review notes from the team or the lecturer, tied to a mockup filename |

Each subfolder has a `.gitkeep` so it exists in a fresh clone. Prefer a link over a large
binary; put a short note file beside any image that is committed.

## Rules for anything placed here

1. **English, always.** Labels, annotations, captions and review notes follow the project
   language rule — the same English the dashboard and the report use.
2. **No real student data.** Use `seed_demo.py` against an isolated `DATABASE_PATH` and
   capture the seeded names, or blur names, NIMs, MAC addresses and faces. Face photos and
   `*.pkl` embeddings are never committed.
3. **Name files** `YYYY-MM-DD_<topic>_<description>.<ext>`, for example
   `2026-11-18_attendance-filter_mockup-v1.png`.
4. **Keep the index below current** so a reviewer can find an item without opening every
   folder.

## Current behaviour a designer must design around

> Updated 2026-11-24 after `git pull origin main` (`011840a`). The 2026-11-18 note below was
> replaced; the Wi-Fi/ARP design it described is archived on `wifi-backup-prepull` (`a9ca24d`).
> Source of truth: `../current_system_qr.md` · decision: `../DECISIONS.md` D-015.

- The teacher dashboard at `/dashboard` is C's file. The current backend has no `/wifi/*`,
  `/schedules/*` or `/prompt/*` routes. The live endpoints are `/teachers/*`, `/classes/*`,
  `/qr-sessions/*`, `/students/*`, `/faces/*` and `/attendance/*`.
- Presence proof is the **client IP inside `SCHOOL_SUBNET`** (default `192.168.0.0/16`,
  loopback allowed). An address outside it gets `403` and **no row** — never a `face_only`
  row, a status that no longer exists. Do not claim room-level verification: this is a subnet
  gate, not an AP/BSSID check.
- Student flow: log in by NIM → scan the projected QR → selfie →
  `POST /attendance/check-qr?student_id=&token=`. The token rotates every 5 s with a 10 s
  grace on the previous one; a phase change issues a new token and invalidates the old one.
- Session phases are `start → spot (optional) → end → closed`. Rows are `partial` for
  start/spot and `verified` for end; the roster collapses them into
  `verified / partial / pending / absent`. Manual attendance is teacher-only and after close.
- Teacher actions require a Bearer token from `POST /teachers/login`. Status chips and copy
  must use the API's own values; do not invent statuses.
- The previous FORM-style mockup and all Wi-Fi measurements are dated evidence only. If a
  number is quoted in a design note, cite `../evidence/2026-11-13-windows/` and label it
  historical; do not present those figures as current system behaviour.

## Three-view split (2026-11-24)

The single FORM-style mockup was split into three standalone files so each audience has its own
design. All three share the same `:root` palette and text hierarchy, documented once in
`feedback/2026-11-24_design-system_notes.md`:

| View | File | Audience |
|---|---|---|
| Project overview website | `mockups/2026-11-24_landing_mockup-v1.html` | public / presentation opening |
| Student dashboard | `mockups/2026-11-24_student-dashboard_mockup-v1.html` | student checking in |
| Teacher dashboard | `mockups/2026-11-24_teacher-dashboard_mockup-v1.html` | teacher running a session |

None of them is an implemented route: the real teacher dashboard is C's
`backend/static/dashboard.html`, and the real student flow is the Flutter app.

## Index

| Date | Item | File | Status |
|---|---|---|---|
| 2026-11-24 | **Project overview website v1 — public intro, links to both views** | `mockups/2026-11-24_landing_mockup-v1.html` | proposal — not implemented |
| 2026-11-24 | Review notes for the project overview | `feedback/2026-11-24_landing_mockup-v1_notes.md` | awaiting C/D decision |
| 2026-11-24 | **Student dashboard v1 — active session, QR, own rows** | `mockups/2026-11-24_student-dashboard_mockup-v1.html` | proposal — not implemented |
| 2026-11-24 | Review notes for the student dashboard | `feedback/2026-11-24_student-dashboard_mockup-v1_notes.md` | awaiting C's decision |
| 2026-11-24 | **Teacher dashboard v1 — session control, live roster, CSV** | `mockups/2026-11-24_teacher-dashboard_mockup-v1.html` | proposal — not implemented |
| 2026-11-24 | Review notes for the teacher dashboard | `feedback/2026-11-24_teacher-dashboard_mockup-v1_notes.md` | awaiting C's decision |
| 2026-11-24 | Shared design system — palette and text hierarchy used by all three | `feedback/2026-11-24_design-system_notes.md` | authoritative reference |
| 2026-11-18 | FORM-style landing mockup, v2 palette (#FFE14F / #192853 / #ECF4F7) — Wi-Fi era | `mockups/2026-11-18_student-attendance_mockup-v1.html` | historical — superseded by the 2026-11-24 mockup |
| 2026-11-18 | Review notes for that mockup — Wi-Fi era | `feedback/2026-11-18_student-attendance_mockup-v1_notes.md` | historical |
