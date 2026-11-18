# Final Report Chapter — "Backend Architecture & Attendance Flow" (B8)

> **Status:** outline, not prose. Deliverable for **M3** (B8 in `docs/B/TASK.md`), handed to **D**
> by **2027-03-01**. Owner: B.
> **Scope of this chapter:** only the backend and the network layer. The face-recognition
> accuracy study is A's chapter; the dashboard is D's; the mobile app is C's. This chapter
> cites their results, it does not reproduce them.
> **Rule for every number in this chapter:** it must trace to a file under `docs/B/evidence/`
> or a table in `docs/B/*.md`. If it cannot, it is written as **not measured yet** with the
> reason and the owner — no estimates dressed up as measurements.

---

## 0. One-paragraph thesis (write this last)

The backend grants attendance only when three independent conditions agree — the right
class window, the student's device visible on the classroom network, and two matching
selfies — and it records *which* conditions actually held instead of collapsing them into a
single "present" flag. The chapter's argument is that this separation is what makes the
system auditable: a Wi-Fi failure produces a different, visible row (`face_only`) rather than
a wrong one, and a strict mode can refuse the check-in entirely. Every performance and
reliability claim in the chapter is backed by a re-runnable script and raw console output.

---

## 1. Where the chapter sits

| Order | Chapter | Owner | What this chapter takes from it |
|---|---|---|---|
| 1 | Problem & requirements | D | the three-condition rule, the audit requirement |
| 2 | System architecture (overall) | D | the box diagram; this chapter expands the backend box |
| **3** | **Backend architecture & attendance flow (this chapter)** | **B** | request flow, services, database, Wi-Fi, deployment |
| 4 | Face pipeline & accuracy | A | threshold 0.5, FAR/FRR numbers, robustness |
| 5 | Mobile application | C | how the app calls preflight and uploads the selfie |
| 6 | Dashboard & teacher workflow | C/D | how a row becomes a visible status |
| 7 | Evaluation, limitations, future work | D | the honest-open-items list from §8 below |

Target length: **6–9 pages** excluding figures, roughly 2,800–3,500 words. Section 5
(network validation) and §7 (deployment) are the two sections with the most measured content,
so they carry the chapter's evidence weight.

---

## 2. Section-by-section outline

### 3.1 Design constraints and decisions (≈ 1 page)

- Three conditions, and the consequence of each failing: wrong time → `403`; wrong network →
  `403` in strict mode or `face_only` row otherwise; face mismatch → `403`; duplicate stage →
  `409`. One table: **condition → HTTP status → row written? → status value**.
- Why the backend is a single FastAPI process with SQLite rather than a service mesh: demo
  machine is one laptop, no internet on stage (D-002), and the measured workload is 24
  concurrent check-ins (all 200, wall 823 ms) — beyond the demo's needs.
- The decisions that shaped the code, each one sentence plus a pointer to `DECISIONS.md`:
  D-002 (native run), D-011 (locale-independent netmask), D-013 (open API only on a
  controlled hotspot), D-014 (lazy model load + deliberate warm-up).
- **Evidence:** `DECISIONS.md` D-001…D-014; `hardening_checklist.md` §5.

### 3.2 Component architecture (≈ 1 page + 1 figure)

- Layer table: router → service → model/utils, with the actual module names
  (`backend/routers/*.py`, `services/attendance.py`, `services/face_detection.py`,
  `services/face_recognition.py`, `services/wifi_scanner.py`, `services/photo_guard.py`,
  `models/database.py`, `config.py`).
- Why face detection and face recognition are separate modules (A's two-stage pipeline,
  YOLO then ArcFace) and why `attendance.py` is the only place that combines all three
  conditions — one enforcement point, mirrored by `/attendance/preflight`.
- **Figure 3.1:** component diagram (boxes + arrows, built from the module list above; no
  invented components).
- **Evidence:** source tree; `docs/PROJECT_CONTEXT.md` §2.

### 3.3 Check-in request flow (≈ 1.5 pages + 1 figure, the core of the chapter)

Walk the actual code path in `backend/routers/attendance.py` and
`backend/services/attendance.py`, in this measured order:

1. validate `check_type` (400);
2. student exists (404);
3. read upload → SHA-256 fingerprint; **face detection + recognition** (400
   `Face not recognized: <reason>`; `multiple_faces_detected` for a second person);
4. **identity binding** — the recognised student must equal the logged-in `student_id`
   (403); closes the "friend in front of my camera" hole (A's multi-face decision record —
   note the numbering collides with B's D-003, so cite `docs/A/DECISIONS.md` explicitly);
5. **capture-replay guard** — the same photo bytes once per student per day (409);
6. **schedule validation** — exists (404), correct weekday (403), inside
   `start−grace … end+grace` (403);
7. **two-stage pairing + Wi-Fi** in `mark_attendance()` — duplicate stage (409), `end`
   without `start` (409), Wi-Fi verified on the student's MAC *and* (when pinned) the
   server's BSSID; strict mode refuses with 403, otherwise the row is written;
8. status: `start` → `partial`; `end` → `verified` if Wi-Fi held on **both** stages, else
   `face_only`; the `start` row is updated to the final status;
9. record the photo fingerprint and return the row.

- **Figure 3.2:** swimlane/flow diagram of these steps with the HTTP status at each exit.
  Build it from this list — do not draw a generic UML activity diagram.
- **Table 3.x:** every error string the app can receive, verbatim, with status code and the
  test that pins it (`backend/tests/test_attendance_scenarios.py`,
  `test_identity_binding.py`, `test_classroom_wifi_strict.py`, `test_hardening.py`).
- Explain why preflight exists and that it mirrors, not replaces, the enforcement.
- **Evidence:** the source files above; **209 passed** suite.

### 3.4 Data model and persistence (≈ 1 page)

- Five tables and what each guarantees: `students`, `faces` (512-D embedding as BLOB, one to
  many), `schedules` (weekday + window + optional `ap_bssid`), `attendance` (one row per
  stage, `wifi_verified`, `status`, `faces_detected` audit column), `ap_logs` (60 s dedupe).
- The two timestamp rules that caused real bugs and are now deliberate: timestamps are stored
  as **explicit local time** (SQLite `CURRENT_TIMESTAMP` is UTC and broke `DATE()` filtering),
  and `TIMEZONE` is server-side so windows behave the same on any machine. Measured: +8.0 h
  gap proves `Asia/Shanghai` is applied.
- Concurrency and durability: 24 parallel writes / 24 parallel reads, zero
  `database is locked`; backup by file copy (1.2 ms for 40 KB), restore 13.9 s to healthy.
- **Figure 3.3 (optional):** ER diagram of the five tables.
- **Evidence:** `models/database.py`; `hardening_checklist.md` §5; `demo_environment.md` §7.

### 3.5 Wi-Fi presence verification (≈ 1.5 pages + 1 table, the chapter's differentiator)

- The two layers and why both: (1) the student's registered MAC must appear in the server's
  ARP table; (2) when a schedule pins an AP, the **server's own** BSSID must match — a
  single SSID spans many APs, so the server's AP is the only location fact it can verify.
- How the subnet is discovered per platform, and the /24 sweep cap with a warning
  (a real /17 interface would otherwise mean 65k hosts). Table: capability × Linux/Windows/
  macOS, with "measured" vs "code path".
- The Windows bug worth a paragraph: a localized `ipconfig` translates `Subnet Mask`, so the
  English-label parser silently degraded to a /24 guess; fixed by a locale-independent parse
  with a contiguity check (D-011), pinned by 4 tests.
- What the campus network showed and why it matters: only the gateway visible, on both Linux
  and Windows → client isolation/VLAN segmentation. This is why the demo uses a hotspot the
  team controls, and why `face_only` is a documented state, not a bug.
- Honest gap, stated in the chapter: the **flat hotspot with two phones is not measured
  yet**; owner and plan named. Multi-device formatting is proven by unit tests only.
- **Table 3.y:** scan latency fresh/cached (4,281 ms / 29 ms), device count, subnet, BSSID
  per platform and network.
- **Evidence:** `network_validation.md` §2–§8; `evidence/2026-11-13-windows/`.

### 3.6 Security and failure behaviour (≈ 1 page)

- Threat table with the control that answers it: photo of a friend → identity binding;
  replayed file → SHA-256 once-per-day guard; second face in frame → `multiple_faces_detected`;
  oversized upload → `MAX_UPLOAD_BYTES` (413 on enroll, gap on recognize — see below);
  non-JPEG/PNG → magic-byte check; wrong classroom → MAC + BSSID; open API → demo-only
  posture, hotspot-scoped firewall and a single CORS origin (D-013).
- Failure behaviour, measured, including the ones still open: missing model → `500` (should
  be `503`), corrupt DB → process alive without binding the port, upload cap not applied on
  `/faces/recognize`. Each is stated as a known gap with an owner, because a report that
  lists only what works is not an evaluation.
- **Table 3.z:** attack/abuse → control → test or measurement → residual gap.
- **Evidence:** `hardening_checklist.md` §2.1, §7a, §11.

### 3.7 Deployment and demo environment (≈ 1 page)

- Native `uvicorn` on the demo laptop is the supported path; Docker is optional and cannot
  see the host Wi-Fi LAN (D-002). One paragraph on why, one on what Docker is still good for.
- The G1 numbers on the actual machine: install 577 s, cold start 17.3 s, health 5.4 ms,
  restart persistence, seed 0.7 s, restore 13.9 s. Say plainly that Windows is ~3× slower to
  start than the Linux machine (17.3 s vs 5.9 s) and that `torch` import dominates.
- Offline readiness: the two model artefacts (sizes + cache location outside `DATA_DIR`),
  the warm-up requirement (13.4 s cold → 1.5 s warm), `dill` missing from the pinned
  requirements (a real reproducibility gap), and the fallback ladder in one figure/table.
- **Table 3.w:** G1 measurements with the command that produced each.
- **Evidence:** `demo_environment.md` §7; `deployment_guide.md` §12–§13;
  `offline_fallback.md`; `demo_runbook.md` §2.

### 3.8 Threats to validity of this chapter's claims (≈ 0.5 page)

- One physical laptop; numbers do not transfer to different hardware without a re-run.
- Campus network ≠ demo hotspot; the hotspot rung is unmeasured.
- No real face photo on the measurement machine, so matching latency and the accepted
  check-in are unmeasured (A's chapter has the accuracy numbers).
- Concurrency was measured at 24 clients, not a full classroom of 40+.
- The suite is **209 tests**, but ML inference in tests is mocked — behaviour, not accuracy.

---

## 3. Figure and table plan

| ID | Type | Content | Source | Status |
|---|---|---|---|---|
| 3.1 | component diagram | routers → services → DB/models | source tree | to draw |
| 3.2 | flow diagram | check-in steps 1–9 with HTTP exits | `routers/attendance.py` | to draw |
| 3.3 | ER diagram (optional) | five tables + relations | `models/database.py` | to draw |
| 3.4 | fallback ladder | 5 rungs, time-to-switch | `offline_fallback.md` §1 | to draw |
| 3.x | table | condition → status → row | this doc §3.1 | text ready |
| 3.y | table | scanner capability × platform | `network_validation.md` §8.3 | text ready |
| 3.z | table | threat → control → residual gap | `hardening_checklist.md` | text ready |
| 3.w | table | G1 measurements + command | `demo_environment.md` §7 | text ready |

Diagrams: keep them monochrome and text-labelled; the report must still read if they are
printed in black and white.

---

## 4. Reusable text already written (do not rewrite from scratch)

| Chapter need | Reuse from |
|---|---|
| network results, findings F1–F6 | `network_validation.md` §3, §6.4, §7.5, §8.4 |
| check-in rules and error semantics | `PROJECT_CONTEXT.md` §2; `test_attendance_scenarios.py` names |
| deployment steps and measured numbers | `deployment_guide.md` §12–§13 |
| demo/offline reasoning | `offline_fallback.md` §0–§4 |
| hardening gaps and owners | `hardening_checklist.md` §2.1, §7a, §11 |
| decision rationale | `DECISIONS.md` D-002, D-006, D-011…D-014 |

---

## 5. What is missing before this chapter can be called done

| # | Missing | Why it matters | Owner | Target |
|---|---|---|---|---|
| 1 | Hotspot rung with two phones | §3.5 currently ends in "not measured yet"; the demo's actual network is unproven | B | before dry run #1 |
| 2 | Real-face accepted check-in timing | §3.4/§3.6 can describe the path but not time the matching step | B (+A for a consented photo) | before dry run #2 |
| 3 | `dill==0.3.8` in `requirements.txt` | §3.7 must either say "pinned" or keep the reproducibility gap | A | before code freeze (2027-03-02) |
| 4 | Upload-cap fix on `/faces/recognize` | otherwise §3.6 lists a known hole in the shipped build | A | before code freeze |
| 5 | Diagrams 3.1–3.4 | text is ready, drawings are not | B | before 2027-03-01 |
| 6 | Final report template / length limits from D | word budget above is a proposal | D | before writing starts |
| 7 | A's threshold + FAR/FRR numbers | §3.6 refers to them without restating; needs the final values | A | before 2027-03-01 |

Items 1–4 are the same open items as `review_response.md` §9 and
`hardening_checklist.md` §11. If any is still open on 2027-03-01, the chapter says so in
§3.8 rather than quietly dropping it — that is the same rule the demo docs follow.
