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

- The dashboard currently has these sections: Overview, Architecture, Attendance Sheet,
  Schedules, Face Enrollment, Attendance, Wi-Fi Scanner, Recognition Demo. It reads
  `/students/`, `/schedules/`, `/schedules/active`, `/attendance/today`,
  `/attendance/export/csv`, `/attendance/preflight`, `/wifi/scan` and `/health`.
- **Strict classroom mode** (`REQUIRE_CLASSROOM_WIFI=true`, D-006) is the demo setting:
  a check-in from a device not visible on the classroom network returns `403` and writes **no
  row**. It does not silently become `face_only`. Any UI copy about "not connected" has to
  say this plainly. With the flag off, `face_only` remains a normal documented status.
- The mobile app lists only `/schedules/active` and calls `/attendance/preflight` before the
  camera opens, so "no active class" and "not on the classroom network" are **blocked before
  a selfie is taken**. The website should not design a flow that contradicts that ordering.
- `day_of_week` is Python numbering (Monday = 0 … Sunday = 6). The current dashboard still
  filters with the browser's `Date.getDay()` (Sunday = 0), so "Today's Schedule" is empty on
  weekdays — an open C-owned defect, not a layout constraint to copy.
- Wi-Fi evidence is L2/AP-coverage level, not proof of room presence. Use the wording in
  `../network_validation.md` and `../DECISIONS.md`; do not promise stronger presence in UI
  copy.
- Measured timings and Windows evidence belong in `../evidence/2026-11-13-windows/`; quote
  those numbers in a design note rather than inventing placeholders.

## Index

| Date | Item | File | Status |
|---|---|---|---|
| — | none yet | — | — |
