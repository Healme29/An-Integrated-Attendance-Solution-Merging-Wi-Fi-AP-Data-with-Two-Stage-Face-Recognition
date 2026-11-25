# Final Report Chapter — "Backend Architecture & Attendance Flow" (B8)

> **Status:** outline, not prose. Deliverable for **M3** (B8 in `docs/B/TASK.md`), handed to **D**
> by **2027-03-01**. Owner: B. Rewritten 2026-11-24 after `git pull origin main` (`011840a`);
> it now describes the **rotating-QR** system, not the archived Wi-Fi/ARP design.
> **Scope of this chapter:** only the backend and the network layer. The face-recognition
> accuracy study is A's chapter; the dashboard is D's; the mobile app is C's. This chapter
> cites their results, it does not reproduce them.
> **Rule for every number in this chapter:** it must trace to a file under `docs/B/evidence/`
> or a table in `docs/B/*.md`. If it cannot, it is written as **not measured yet** with the
> reason and the owner — no estimates dressed up as measurements.
> **Current source of truth:** `docs/B/current_system_qr.md`. Direction decision: D-015 in
> `DECISIONS.md`. Wi-Fi measurements in `network_validation.md` and
> `evidence/2026-11-13-windows/` are cited only as *dated historical evidence*, inside an
> appendix clearly labelled as belonging to `wifi-backup-prepull` (`a9ca24d`).

---

## 0. One-paragraph thesis (write this last)

The backend grants attendance only when three independent conditions agree — the client is on
the school network, the scanned QR token belongs to the current phase of an active class
session, and the selfie matches the enrolled face of the logged-in student — and it records
*which* conditions actually held instead of collapsing them into a single "present" flag. The
chapter's argument is that this separation, together with the session phase machine
(`start → spot → end → closed`), is what makes the system auditable: a wrong subnet is a
visible `403`, a face mismatch writes no row at all, an early check-in stays `partial` until
the final phase turns it `verified`, and a teacher's manual correction carries an author, a
time and a reason. Every performance and reliability claim is backed by a re-runnable script
and raw console output; what has not been measured (hotspot with two real phones, accepted
real-face latency) is named as such.

---

## 1. Where the chapter sits

| Order | Chapter | Owner | What this chapter takes from it |
|---|---|---|---|
| 1 | Problem & requirements | D | the three-condition rule, the audit requirement |
| 2 | System architecture (overall) | D | the box diagram; this chapter expands the backend box |
| **3** | **Backend architecture & attendance flow (this chapter)** | **B** | request flow, services, database, QR session lifecycle, deployment |
| 4 | Face pipeline & accuracy | A | YOLO + ArcFace threshold 0.5, FAR/FRR numbers, robustness, liveness |
| 5 | Mobile application | C | how the app validates a token and uploads the selfie |
| 6 | Dashboard & teacher workflow | C/D | how a session phase becomes a visible roster status |
| 7 | Evaluation, limitations, future work | D | the honest-open-items list from §8 below |

Target length: **6–9 pages** excluding figures, roughly 2,800–3,500 words. Section 3.3
(request flow) and §3.5 (QR session lifecycle) carry the chapter's evidence weight; §3.7
(deployment) carries the measured G1 numbers.

---

## 2. Section-by-section outline

### 3.1 Design constraints and decisions (≈ 1 page)

- Three conditions, and the consequence of each failing, as one table:
  **condition → HTTP status → row written? → roster status**. Client IP outside
  `SCHOOL_SUBNET` → `403`, no row; token invalid/expired or no active session → `400`, no row;
  face not recognised / multiple faces / liveness gate → `400`, no row; face belongs to another
  student → `403`, **no row written**; duplicate for the current phase → `409`; `spot`/`end`
  without a prior `start` → `409`; exact photo reused the same day → `409`; four recognitions
  already running → `429` with `Retry-After: 3`.
- Why the backend is a single FastAPI process with SQLite rather than a service mesh: one demo
  laptop, no internet on stage (D-002), and the measured workload is 24 concurrent requests
  (all 200, wall 823 ms) — beyond the demo's needs. Recast the old "24 check-ins" measurement
  honestly as a *generic HTTP concurrency* measurement from the Wi-Fi-era evidence, not as a
  QR check-in measurement.
- The decisions that shaped the current code, each one sentence plus a pointer:
  **D-015** (follow `main`'s QR direction; archive Wi-Fi), D-002 (native run preferred, Docker
  optional), D-012 (`dill` is a real reproducibility gap), D-014 (lazy model load + deliberate
  warm-up). D-001…D-011 and D-013 are cited only in the historical appendix.
- **Evidence:** `DECISIONS.md` D-002, D-012, D-014, D-015; `current_system_qr.md` §1, §8.

### 3.2 Component architecture (≈ 1 page + 1 figure)

- Layer table: router → service → model/utils, with the actual module names at `011840a`:
  - routers: `students.py`, `faces.py`, `qr_sessions.py`, `teachers.py`, `classes.py`,
    `attendance.py`;
  - services: `qr_service.py`, `attendance.py`, `liveness.py`, `face_detection.py`,
    `face_recognition.py`, `photo_guard.py`;
  - models: `database.py` (six tables), `schemas.py`, `config.py`, `utils/helpers.py`.
- Why token/session lifecycle (`qr_service.py`) is separate from recognition
  (`services/attendance.py`), and why `qr_service.validate_token()` and
  `attendance.check-qr` both check the token: the first gives fast feedback in the app, the
  second is the enforcement point next to the database write.
- Why detection and recognition are separate modules (A's pipeline: YOLO then ArcFace), and
  why liveness is its own service (passive anti-spoof before any expensive embedding compare).
- **Figure 3.1:** component diagram (boxes + arrows, built from the module list above; no
  invented components and no Wi-Fi scanner box).
- **Evidence:** source tree at `011840a`; `current_system_qr.md` §3, §4.

### 3.3 Check-in request flow (≈ 1.5 pages + 1 figure, the core of the chapter)

Walk the actual code path in `backend/routers/attendance.py` and
`backend/services/attendance.py`, in this order:

1. client IP in `SCHOOL_SUBNET` → `403` otherwise;
2. token valid for the **current phase** → `400` otherwise (previous token only within
   `QR_GRACE_SECONDS`);
3. student exists (404), session exists (404), student is in the class roster (403), no
   duplicate for this phase/`spot_round` (409), `spot`/`end` have a prior `start` row (409);
4. upload ≤ `MAX_UPLOAD_BYTES` (413) and JPEG/PNG magic bytes (400);
5. concurrency semaphore → `429` when four recognitions are already running;
6. **recognition:** decode → YOLO detection in a thread → nested-box dedupe (containment ≥
   0.6) → reject a second face ≥10% of the largest → largest face → padded crop → passive
   liveness (blur 0.20, screen grid 0.35, colour variance 0.20, white reflections 0.25;
   `LIVENESS_MIN_SCORE` 0.35) → ArcFace embedding → cosine compare against every enrolled
   student's embeddings;
7. **identity binding** — the recognised student must equal the query `student_id`, otherwise
   `403` and **no row is written**; closes the "friend in front of my camera" hole (cite
   `docs/A/DECISIONS.md` explicitly — its numbering collides with B's D-003);
8. **capture-replay guard** — SHA-256 of the exact bytes once per student per day (409);
9. insert the row with `check_type` = current phase, `spot_round`, `confidence`,
   `ip_address`, `faces_detected` and a local timestamp; `start`/`spot` → `partial`,
   `end` → `verified`. State honestly that the SQL hardcodes `status='verified'` while the
   response computes `partial`/`verified` and the roster derives status from row presence —
   a known A-owned inconsistency, not a feature.
10. teacher moves the phase to `end` (new token, old token rejected immediately), then closes;
    manual rows are possible only after close and carry `manual_by/at/reason`.

- **Figure 3.2:** swimlane/flow diagram of these steps with the HTTP status at each exit.
  Build it from this list — do not draw a generic UML activity diagram.
- **Table 3.x:** every error string the app can receive, verbatim, with status code and the
  test that pins it (`backend/tests/test_attendance_qr.py`, `test_qr_sessions.py`).
- Explain that token validation in the app is fast feedback, not a substitute for the
  server-side check at step 2.
- **Evidence:** the source files above; `test_attendance_qr.py`; **38 passed** suite.

### 3.4 Data model and persistence (≈ 1 page)

- Six tables and what each guarantees: `students` (`nim UNIQUE`, legacy `mac_address` unused),
  `faces` (512-D embedding as BLOB, one to many, max 5 per student), `classes` and
  `class_students` (a student belongs to one class), `qr_sessions` (`token`, `prev_token`,
  `token_rotated_at`, `phase`, `spot_round`, `is_active`), `attendance` (one row per
  phase/check, `check_type`, `confidence`, `ip_address`, `faces_detected`, audit columns for
  manual rows).
- **Figure 3.3 (optional):** ER diagram of the six tables.
- The migration story is a result, not a footnote: `init_db()` enables WAL, rebuilds an old
  schedule-based `attendance` table into `qr_session_id = 0`, adds the phase/manual columns,
  and **drops** `schedules`, `schedule_students` and `ap_logs`. This is how the two generations
  coexist on one laptop without a destructive manual step.
- Timestamp rules: stored as explicit local time via `now_local()` with server-side
  `TIMEZONE` (the old `CURRENT_TIMESTAMP` UTC bug is historical evidence for why this is
  deliberate). Measured: +8.0 h gap proves `Asia/Shanghai` is applied.
- Concurrency and durability: 24 parallel writes / 24 parallel reads, zero
  `database is locked` (historical generic measurement); backup by file copy (1.2 ms for
  40 KB), restore 13.9 s to healthy.
- **Evidence:** `models/database.py`; `hardening_checklist.md` §5; `demo_environment.md` §7.

### 3.5 QR session lifecycle and presence proof (≈ 1.5 pages + 1 table, the differentiator)

- Three facts that replace the old AP/MAC discussion: the QR payload is
  `{session_id, token, class_name, phase, spot_round}`; the token is 6 characters from an
  unambiguous alphabet, rotates every 5 s and the previous token stays valid 10 s; on a phase
  change the token is **regenerated and `prev_token` cleared**, so a start-phase QR dies the
  moment the teacher presses "Start Final Attendance".
- The phase machine and why it exists: `start → spot (optional, repeatable) → end → closed`;
  allowed transitions only (`start→{spot,end,closed}`, `spot→{start,end,closed}`, `end→closed`),
  invalid transition `409`, `end` auto-closes after `FINAL_CHECK_GRACE_MINUTES` (5). A
  student's rows move `partial → verified`; a roster is `verified / partial / pending / absent`.
- Presence proof is now the **client IP inside `SCHOOL_SUBNET`** (default `192.168.0.0/16`,
  loopback allowed for local testing, invalid config falls back to `ip.is_private`). Say
  plainly that this is weaker than AP-level location: the report must not claim room-level
  verification. The demo controls the hotspot; `403` outside it is the gate working.
- Teacher ownership: `POST /teachers/login` → Bearer token → all `/classes/*`, session,
  roster and manual endpoints; process-local tokens expire after 8 h by default and the demo
  password is a default that must change for a real pilot.
- Honest gaps, stated in the chapter: the **flat hotspot with two phones is not measured yet**
  for the QR flow; accepted real-face check-in latency is **not measured yet**; the token TTL
  assumes phones have workable time synchronisation but does not depend on phone clocks
  (the server rotates the token).
- **Table 3.y:** configuration × default × effect — `SCHOOL_SUBNET`, `QR_ROTATION_SECONDS`,
  `QR_GRACE_SECONDS`, `QR_TOKEN_LENGTH`, `FINAL_CHECK_GRACE_MINUTES`, `TEACHER_*`,
  `LIVENESS_ENABLED`, `LIVENESS_MIN_SCORE`, `MAX_CONCURRENT_RECOGNITIONS`.
- **Evidence:** `current_system_qr.md` §2–§5; `test_qr_sessions.py` (18 tests).

### 3.6 Security and failure behaviour (≈ 1 page)

- Threat table with the control that answers it: photo of a friend → identity binding;
  replayed file → SHA-256 once-per-day guard; second face in frame → `multiple_faces_detected`;
  printed photo / screen → passive liveness score; oversized upload → `MAX_UPLOAD_BYTES` (413);
  non-JPEG/PNG → magic-byte check; stale QR → 5 s rotation + 10 s grace, phase change kills the
  previous token; teacher-only actions → Bearer token; open API → demo-only posture,
  hotspot-scoped firewall and a single CORS origin (D-013, now superseded in part by D-015).
- Failure behaviour, measured, including the ones still open: missing model → `500` (should
  be `503`), corrupt DB → process alive without binding the port, upload cap applied on enroll
  and check-in but the `/faces/recognize` history of the gap should be re-checked at HEAD.
  Each is stated as a known gap with an owner.
- **Table 3.z:** attack/abuse → control → test or measurement → residual gap.
- **Evidence:** `hardening_checklist.md` §2.1, §7a, §11 (read with its superseded banner);
  `current_system_qr.md` §8.

### 3.7 Deployment and demo environment (≈ 1 page)

- Native `uvicorn` on the demo laptop is the supported path; Docker is optional. Do **not**
  repeat the old "Docker cannot see the Wi-Fi LAN" reasoning — the current network check is
  the HTTP client IP, so Docker is no longer disqualified for that reason; it is simply not on
  the demo path. `docker-compose.yml` now passes `SCHOOL_SUBNET`, `QR_ROTATION_SECONDS` and
  `QR_GRACE_SECONDS`.
- The G1 numbers on the actual machine remain valid evidence for install/start cost: install
  577 s, cold start 17.3 s, health 5.4 ms, seed 0.7 s, restore 13.9 s. Say plainly that Windows
  is ~3× slower to start than the Linux machine (17.3 s vs 5.9 s) and that `torch` import
  dominates. Startup at `011840a` only runs `init_db()` — there is no eager model warm-up, so
  a recognition request must be made before the audience arrives (13.4 s cold → 1.5 s warm).
- Offline readiness: the two model artefacts (sizes + InsightFace cache location outside
  `DATA_DIR`), the wheelhouse validated with `--no-index --find-links wheelhouse` (79 packages
  resolved against the new `requirements.txt`, including `qrcode[pil]`), and `dill==0.3.8`
  still missing from `requirements.txt` and the Dockerfile — a real reproducibility gap.
- Demo path: teacher login → create class → add students → `/qr-sessions/start` → project
  `/qr-sessions/active/qr.png` → student scans and uploads a selfie →
  `/attendance/check-qr` → phase to `end` → roster/CSV. `seed_demo.py --reset` creates an
  active start-phase session; `smoke_test.py` performs a no-real-face E2E check including the
  phase-change token invalidation.
- **Table 3.w:** G1 measurements with the command that produced each.
- **Evidence:** `demo_environment.md` §7; `deployment_guide.md` (historical banner — use
  `current_system_qr.md` §6 for current steps); `offline_fallback.md` §1 (QR ladder to be
  written); `current_system_qr.md` §6.

### 3.8 Threats to validity of this chapter's claims (≈ 0.5 page)

- One physical laptop; numbers do not transfer to different hardware without a re-run.
- The demo hotspot is not the campus network, and the two-phone rung is unmeasured.
- No real face photo on the measurement machine, so accepted-check-in latency is unmeasured
  (A's chapter has the accuracy numbers).
- Concurrency was measured at 24 clients, not a full classroom of 40+.
- The suite is **38 tests** and ML inference is mocked — behaviour, not accuracy. The old
  "209 passed" number belongs to `wifi-backup-prepull` and must not appear as current.
- Wi-Fi scan latencies and BSSID findings belong to an archived design and are cited only in
  the labelled historical appendix.

### 3.9 Appendix A — the archived Wi-Fi path (≈ 0.5 page, clearly dated)

- One paragraph: before D-015, presence was attempted via ARP/MAC scanning and AP BSSID
  pinning; the campus network isolated clients, so only the gateway was visible. The negative
  finding is a result and is preserved because it explains *why* the project moved to QR.
- Cite `ap_management_plane.md`, `network_validation.md` and
  `evidence/2026-11-13-windows/` **only here**, each with its superseded banner. Never present
  `/wifi/scan`, `wifi_verified`, `face_only`, `ap_bssid`, `REQUIRE_CLASSROOM_WIFI` or "209
  tests" as capabilities of the shipped system.

---

## 3. Figure and table plan

| ID | Type | Content | Source | Status |
|---|---|---|---|---|
| 3.1 | component diagram | routers → services → DB/models (no Wi-Fi box) | source tree at `011840a` | to draw |
| 3.2 | flow diagram | check-in steps 1–10 with HTTP exits | `routers/attendance.py` | to draw |
| 3.3 | ER diagram (optional) | six tables + relations | `models/database.py` | to draw |
| 3.4 | state diagram | `start → spot → end → closed`, token rotation at each change | `services/qr_service.py` | to draw |
| 3.5 | fallback ladder | 5 QR-era rungs, time-to-switch | `current_system_qr.md` §6.4 | text ready |
| 3.x | table | condition → status → row → roster status | this doc §3.1 | text ready |
| 3.y | table | config × default × effect | `current_system_qr.md` §2 | text ready |
| 3.z | table | threat → control → residual gap | `hardening_checklist.md`, `current_system_qr.md` §8 | text ready |
| 3.w | table | G1 measurements + command | `demo_environment.md` §7 | text ready |

Diagrams: keep them monochrome and text-labelled; the report must still read if they are
printed in black and white.

---

## 4. Reusable text already written (do not rewrite from scratch)

| Chapter need | Reuse from |
|---|---|
| current endpoints, config, DB, flow, fallback | `docs/B/current_system_qr.md` §2–§6 |
| direction rationale | `DECISIONS.md` D-015 (D-001…D-014 only in Appendix A) |
| deployment steps and measured G1 numbers | `demo_environment.md` §7; `current_system_qr.md` §6 |
| demo/offline reasoning | `offline_fallback.md` §0–§4 **after** its QR rewrite, otherwise `current_system_qr.md` §6.4 |
| hardening gaps and owners | `hardening_checklist.md` §2.1, §7a, §11 (superseded banner; re-verify references) |
| check-in rules and error semantics | `test_attendance_qr.py`, `test_qr_sessions.py` names |

---

## 5. What is missing before this chapter can be called done

| # | Missing | Why it matters | Owner | Target |
|---|---|---|---|---|
| 1 | Hotspot rung with two real phones | §3.5 currently ends in "not measured yet"; the demo's actual network is unproven | B | before dry run #1 |
| 2 | Real-face accepted check-in timing | §3.3/§3.6 can describe the path but not time the matching step | B (+A for a consented photo) | before dry run #2 |
| 3 | `dill==0.3.8` in `requirements.txt` and Dockerfile | §3.7 must either say "pinned" or keep the reproducibility gap | A | before code freeze (2027-03-02) |
| 4 | Re-verify `/faces/recognize` upload cap and diagnose `status='verified'` hardcoding | §3.6 must not assert a gap that no longer exists, nor hide one that does | A | before code freeze |
| 5 | Diagrams 3.1–3.5 | text is ready, drawings are not | B | before 2027-03-01 |
| 6 | Final report template / length limits from D | word budget above is a proposal | D | before writing starts |
| 7 | A's threshold + FAR/FRR numbers and liveness evidence | §3.6 refers to them without restating; needs the final values | A | before 2027-03-01 |

Items 1–4 are the same open items as `current_system_qr.md` §8. If any is still open on
2027-03-01, the chapter says so in §3.8 rather than quietly dropping it — the same rule the
demo docs follow.
