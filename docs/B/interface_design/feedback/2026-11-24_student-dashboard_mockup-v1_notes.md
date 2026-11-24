# Review notes — `2026-11-24_student-dashboard_mockup-v1.html`

> **Owner:** B · **Status:** proposal for C, not an implementation · **Supersedes:**
> `2026-11-18_student-attendance_mockup-v1.html` (archived Wi-Fi/AP design, see D-015).
> **Current system:** `docs/B/current_system_qr.md` · direction decision: `docs/B/DECISIONS.md`
> D-015. The actual UI files remain C-owned; this folder stores design inputs only.

## What was deliberately kept identical to the previous design

The request was to keep the **same palette, colours and text hierarchy**. The `:root` block and
the type scale are copied verbatim from the 2026-11-18 mockup — no new colour, font or size was
introduced. Supporting colours in components (`#12624F`, `#8A5200`, `#A88600`, `#9AAEC2`,
`#DCE8EE`) are the same values used there.

| Token | Hex | Role (unchanged) |
|---|---|---|
| `--bg` / Canvas | `#ECF4F7` | page background, panel surfaces |
| `--ink` / Structure | `#192853` | headings, body copy, buttons, QR placeholder, marquee |
| `--lime` / Signal | `#FFE14F` | active state, focus accent, "pass" tag, lime band |
| `--muted` | `#5A6B82` | supporting copy, eyebrows, captions |
| `--line` | `rgba(25,40,83,.16)` | dividers |
| `--font` | Space Grotesk → Segoe UI → system-ui | headings and body |
| `--mono` | DM Mono → SFMono-Regular → Consolas | eyebrows, labels, chips, captions |

Text hierarchy, unchanged from v1:

| Element | Size / treatment |
|---|---|
| Logo `A.TTEND` | 27 px / 700 / −2 px tracking, dot in `#A88600` |
| Hero `h1` | `clamp(70px, 11.5vw, 166px)` / 700 / `.86` line-height / −.095em; middle word outlined with a 1.5 px ink stroke |
| Eyebrow and section labels | 11 px DM Mono, uppercase |
| Section `h2` | `clamp(42px, 6vw, 76px)` / −.07em / `.95` line-height |
| Lime-band copy | `clamp(30px, 4.5vw, 59px)` / −.06em / 1.12 |
| Contact `h2` | `clamp(55px, 10vw, 130px)` / −.09em / `.9` |
| Card title (`h3`) | 19 px / 600 |
| `Today's rows` title | 15 px / 600 (same size as the lime-band mono label and hero button) |
| Signal value / body row | 15 px / 600 and 13 px |
| Nav / footer / chips | 10–12 px DM Mono, uppercase |
| Captions | 10 px DM Mono, uppercase, 1.6 line-height |

Structural conventions also kept: 88 px nav, `min(1400px, 90%)` container, 11 px mono eyebrow
with an 8 px navy dot and yellow glow, inverted scrolling marquee with yellow `✳`, asymmetric
two-column grid, lime band with outlined flow pills, 19 px mono `✳`-free contact heading,
uppercase footer, `IntersectionObserver` reveal, mobile drawer with `aria-expanded`, and the
`prefers-reduced-motion` fallback.

## What changed in the copy for the QR system

| v1 (Wi-Fi era) | v2 (current at `011840a`) |
|---|---|
| "INTEGRATED ATTENDANCE — WI-FI AP + TWO-STAGE FACE RECOGNITION" | "INTEGRATED ATTENDANCE — ROTATING QR + FACE RECOGNITION" |
| "CORRECT AP / VALID CLASS WINDOW / START + END SELFIE" | "SCHOOL NETWORK / CURRENT QR TOKEN / MATCHING FACE" |
| Classroom AP, class window, start selfie, end selfie | School network, QR token, session phase, face + liveness |
| `GET /attendance/preflight` + `/attendance/check` | `GET /qr-sessions/active` → `POST /attendance/check-qr` |
| `face_only` as a normal result | no such status; roster is `verified / partial / pending / absent` |
| Flow: AP → window → start face → end face | Flow: Network → QR token → Face + liveness → Identity bound |
| Strict mode D-006 wording | `403` for an IP outside `SCHOOL_SUBNET`, no row written |

The QR artwork is a CSS placeholder (checkerboard + three finder squares), deliberately
labelled *illustrative*; the real image is rendered by
`GET /qr-sessions/active/qr.png`. There is no token, NIM, face photo or MAC address embedded
in the file; `A7K2Q9` is a fake 6-character token using the production alphabet's shape.
All names are `Demo Student N` from `seed_demo.py`.

## Accuracy notes a reviewer should check

- Token lifetime 5 s / previous-token grace 10 s are the configured defaults
  (`QR_ROTATION_SECONDS`, `QR_GRACE_SECONDS`); a phase change rotates the token and clears
  `prev_token`, which is why the copy says an old QR stops working immediately.
- A check-in in `start` or `spot` is `partial`; `end` is `verified`. The response and the
  roster derive status from row presence, while the SQL column is currently hardcoded
  `status='verified'` — an A-owned inconsistency recorded in `current_system_qr.md` §8. The
  copy shows the user-visible values, not the raw column.
- The 403 wording covers both the subnet gate and the identity-mismatch case; neither writes
  a row. Do not reintroduce `face_only`, `REQUIRE_CLASSROOM_WIFI` or `ap_bssid` wording.
- "Teacher Dashboard ↗" points at the existing `/dashboard`; the student flow itself lives
  in the Flutter app. This mockup is a **web briefing/companion page**, not a new endpoint.

## Decisions C needs to make

1. Keep this as a standalone briefing page linked from `/dashboard`, or fold the three
   sections into the teacher dashboard's sidebar navigation.
2. Make the two `127.0.0.1:8000` links relative before anything ships outside the demo laptop.
3. Self-host the two fonts or accept the offline fallback stack; the file works without them.
