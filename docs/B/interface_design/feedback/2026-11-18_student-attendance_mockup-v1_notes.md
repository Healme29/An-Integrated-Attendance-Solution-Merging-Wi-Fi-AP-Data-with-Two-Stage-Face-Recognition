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
