# PROJECT PLAN & TIMELINE

> Living document. Everyone updates the **Progress Log** at the bottom when they finish
> a unit of work. Project-wide status lives here — nowhere else.
>
> Planning session: 2026-10-18. Minutes: `docs/meetings/2026-10-18_team_planning.md`.
> Full technical context: `docs/PROJECT_CONTEXT.md`.

---

## 1. Milestones

| Milestone | Deadline (approx.) | Success criteria |
|-----------|--------------------|-------------------|
| **M1 — Progress report** | **Nov 1, 2026** | Written progress report delivered, backed by: real-data threshold report (A), real-network Wi-Fi validation results (B), real-device test log (C), fixed dashboard test + evidence pack (D) |
| **M2 — Presentation & demo** | **Jan 18, 2027** | Live end-to-end demo on a real phone + real Wi-Fi; pilot classroom test completed (Dec 2026); slides, demo script, and video ready; 2 dry runs done |
| **M3 — Final submission** | **Mar 18, 2027** | Code freeze Mar 2; release build v1.0 (APK + backend deployed on school machine); final report assembled from all chapters; repository cleaned up |

## 2. Phase plan

### Phase 1 — M1: Real-data validation (Oct 19 → Nov 1, 2026)

| Week | A (lead, ML) | B (backend/Wi-Fi) | C (Flutter/devices) | D (docs/dashboard) |
|------|--------------|-------------------|---------------------|--------------------|
| Oct 19–25 | Enroll ≥3 people × ≥3 selfies, run `evaluate_threshold.py`, fill `docs/threshold_report.md` with real FAR/FRR/EER, pick threshold | Validate `/wifi/scan` + `/wifi/check/{mac}` on a real router; test subnet auto-detect, 60 s dedupe, BSSID pinning; document results | Full flow on a REAL Android phone: settings → login → enroll → start → end → history; log issues | Fix the failing dashboard test; review + commit the uncommitted dashboard redesign; run tests, save evidence + screenshots |
| Oct 26 – Nov 1 | Review members' results; integrate; verify 124/124 tests green | Consolidate network results into a summary doc for the report | Fix device-test bugs found; write device test summary | Collect each member's input **by Oct 29**; assemble and deliver progress report **Nov 1** |

### Phase 2 — M2: Pilot & demo (Nov 2 → Jan 18, 2027)

| Period | Work |
|--------|------|
| November | B: deploy backend on the school/demo machine (Docker or bare), seed demo data, write deployment guide. C: UX polish (loading/empty/error states, dark mode), release APK v0.9, test on a second phone. A: YOLO conf/img-size experiments, robustness tests (lighting/angle/glasses), finalize threshold config. D: finish dashboard polish (status colors, filters, print view), report template for M2. |
| **December** | **Pilot classroom test with 5–10 real students** (A leads execution, B runs the server, C supports app users, D documents + records video + observes). Afterwards: triage all findings, fix the top issues. |
| Jan 1–17 | D: slides, demo script, record demo video. A: dry-run integration test, freeze demo scope by Jan 15. B: stable demo environment + backup plan (offline demo data). C: demo phone prepared (charged, app installed, camera tested). Two full dry runs before the date. |

### Phase 3 — M3: Polish & submission (Jan 19 → Mar 18, 2027)

| Period | Work |
|--------|------|
| Jan 19 – Feb 15 | Fix all pilot/demo findings. B: production hardening checklist (CORS origins, `TIMEZONE=Asia/Jakarta`, upload caps, DB backup). C: final app polish, app icon/splash/name, versioning. A: re-verify accuracy numbers on final hardware, anti-spoofing limitation write-up. D: start assembling the final report. |
| Feb 16 – Mar 1 | Each member writes their final-report chapter (see TASK.md files) and hands it to D **by Mar 1**. D compiles, A reviews the whole report. |
| Mar 2–15 | **Code freeze Mar 2.** Regression: 124/124 tests, smoke test, one more end-to-end pass on real device. Release build v1.0. Final repo cleanup (no stray logs/DBs). |
| Mar 16–18 | Buffer. Final submission. |

## 3. Deliverables per member per milestone

| Member | M1 (Nov 1, 2026) | M2 (Jan 18, 2027) | M3 (Mar 18, 2027) |
|--------|------------------|-------------------|-------------------|
| A | `docs/threshold_report.md` filled with real numbers + chosen threshold | Demo pipeline stable; pilot test executed + analyzed | Final accuracy chapter; frozen ML config; AGENTS.md current |
| B | Real-network Wi-Fi validation results | Backend deployed on demo machine + demo data seeded | Deployment guide; hardening done; backend chapter |
| C | Real-device test log + quick fixes | Demo phone ready; APK v0.9 | Release APK v1.0; mobile app chapter |
| D | Failing test fixed; dashboard redesign committed; evidence pack; progress report | Slides + demo script + video; dashboard final | Final report assembled; testing & conclusion chapter |

## 4. Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| Wi-Fi scan doesn't see student devices on school router | `face_only` status already covers it; document as known behavior; demo on a network we control |
| Camera/ML accuracy poor in classroom lighting | Enroll in the actual classroom; tune threshold on the deployment camera (A) |
| Demo-day network failure | B prepares an offline fallback: pre-seeded demo data + phone hotspot |
| D blocked on dashboard code | One tiny change at a time, with AI guidance (see `docs/D/PROMPT.md`); escalate to A/B if stuck >30 min |
| Deadline drift | Progress Log review every Sunday; A pings members who go quiet |

## 5. Progress Log (append newest entry at the top)

### 2026-10-26 — C: REAL-DEVICE TEST PASSED (C1 core) + edge-case evidence + v0.9 prep; A: 3-student threshold re-run
- **C1 PASSED on the real phone** (Samsung Galaxy S24, Android 16): install,
  login (NIM), Settings + Test Connection, camera + selfie, **START →
  `partial`**, END check, History — user-confirmed; details + environment
  notes in `docs/C/device_test_log.md`.
  - Connectivity path documented: campus WLAN blocks phone→PC HTTP
    (firewall/AP isolation) → **`adb reverse tcp:8000 tcp:8000` + URL
    `http://127.0.0.1:8000`**; Wi-Fi verification stays server-side (ping
    sweep + ARP) and is unaffected. A laptop-clock drift of 8 h was also
    found and fixed during testing (cause of all schedule 403s).
- **Edge-case evidence (server-side, schedule id 18 `EDGE demo`):** fresh
  held-out photo → 200 `partial` (0.893); duplicate same-stage second photo →
  **409** ("Already checked in (start)"); same-photo replay → **409**;
  Willian (no valid MAC) → `prompt:false,
  reason:device_not_seen_on_network`. All logged in C's device log.
- **C3 fix:** camera init failure previously showed an infinite spinner (+
  latent `LateInitializationError` crash on dispose) — now error state with
  instructions + **Retry** (`53ba44d`).
- **C4/C5 prep:** friendly empty states for schedules & history (`de4a1bf`);
  release prep v0.9.0+1 + new launcher icon in 5 densities (`c0ee76b`).
  Release-side C5 next: `flutter build apk --release`, install on a SECOND
  phone (Nov item).
- **Handover review recorded:** `docs/C/review_7803d27.md` — prompt draft
  accepted (spec-compliant). C2 summary finalized:
  `docs/C/progress_summary_for_D.md` (the D-input that was due Oct 29 — done
  early).
- **A's M1 blocker cleared:** student #3 enrolled (5 embeddings from
  `gambar_percobaan/orang_3`) → `evaluate_threshold.py` re-run with **3
  students / 13 samples / 23 genuine + 55 impostor pairs**: FAR = FRR = 0.00
  in the 0.25–0.65 band → **threshold kept 0.5** (decision note in
  `docs/threshold_report.md`).

### 2026-10-25 — A (covering B): Docker deployment verified + seed script + compose fixes
- **B3 done:** image builds and runs; `GET /health` OK; `TIMEZONE=Asia/Shanghai` applied;
  smoke test **15/15** against the container (and 15/15 against the native server).
- **Compose/Dockerfile fixes (real bugs found during deployment):**
  - the volume `backend-data:/app/data` used to **shadow the baked-in YOLO weights**;
    state now lives in `/app/data/dbdata` (verified: `yolov8m-face.pt` visible at runtime);
  - `TIMEZONE` and `CORS_ORIGINS` were not passed into the container at all;
  - host port is now overridable via `BACKEND_PORT`;
  - torch/torchvision installed from the **CPU wheel index** — the default CUDA wheels
    added ~3 GB for nothing (image now 3.4 GB total).
- **China deployment note documented:** Docker Hub is unreachable from this network;
  `docs/B/deployment_guide.md` explains registry mirrors (`docker.m.daocloud.io`,
  `dockerproxy.com`) + `docker desktop restart`.
- **Confirmed limitation (measured):** `/wifi/scan` inside the container returns
  `devices: []` (subnet defaults to `192.168.1.0/24`, BSSID null) — containers cannot see
  the host Wi-Fi LAN. Wi-Fi presence requires native run or Linux host networking; the
  guide now states this explicitly.
- **B4 (new):** `backend/scripts/seed_demo.py` — demo students, a schedule active now and
  sample attendance rows; flags `--reset`, `--students N`, `--db PATH`; tested against a
  temporary database (START before END, correct server timezone).
- **Smoke test bug fixed:** `GET /dashboard` check looked for "Teacher Dashboard" (a string
  that never existed); now checks the real page markers.

### 2026-10-25 — A (covering B): real-network Wi-Fi validation documented + data features verified
- **B1 deliverable created:** `docs/B/network_validation.md` with measured results on the
  real campus network — fresh scan **2.4 s**, cached **0 s**, 60 s dedupe confirmed
  (`ap_logs` +1 row across two back-to-back scans), known/unknown MAC checks correct,
  BSSID `54:2b:de:fd:90:21` stable, two real two-stage check-ins (`verified`, 0.71/0.72).
- **Real finding (bug class):** `detect_local_subnet()` hard-codes `/24` while the laptop
  interface is **/17** (`10.163.235.210/17`), and `_ping_sweep()` is capped at `.1–.254`.
  On the campus SSID only the gateway was visible → **client isolation or VLAN splitting**;
  ARP scanning works only on flat, small networks. Room-level presence therefore needs the
  AP management plane (M2) — also the prerequisite for the RSSI "outside the room" idea.
- **Demo-artifact warning recorded:** student Buchari (id 8) is registered with the
  campus **gateway's** MAC, so his Wi-Fi check always passes. Real pilot students must be
  enrolled with their own phone MAC.
- **B5 verified:** `docs/B/data_features_check.md` — history pagination (`X-Total-Count: 12`,
  `limit/offset` pages correct, newest first) and CSV export (`text/csv`, correct header,
  local timestamps, `yes/no` Wi-Fi column).
- **B2 summary ready:** paragraph + table for member D inside `network_validation.md §5`.

### 2026-10-25 — A: app renamed "Student Attendance", default backend URL fixed, phone login path cleared
- **Rename (English UI)**: Android launcher label, login title, home AppBar, MaterialApp
  title, dashboard sidebar + page title → **"Student Attendance"** ("Student Attendance
  System" for the teacher dashboard). API title stays "Face Attendance API" (internal,
  technical). `pubspec.yaml` package name `face_attendance` and import paths unchanged
  (internal technical identifier; renaming would churn every import for zero user value).
- **Login timeout root cause (real phone)**: `ApiService._defaultBaseUrl` was
  `http://10.0.2.2:8000` — an emulator-only alias. On the Galaxy S24 that host does not
  exist, so requests hung for 15 s and failed with "Server took too long to respond."
  Diagnosis evidence: the uvicorn access log had **no** `GET /students/?nim=...` entry,
  i.e. the request never left the phone; phone-browser `http://127.0.0.1:8000/health`
  returned OK (adb reverse path works).
  Fix: default is now `http://127.0.0.1:8000` (works for real device + emulator with
  `adb reverse tcp:8000 tcp:8000`; LAN users override in Settings), and the timeout
  message now tells the user exactly what to check.
- Analyzer clean, Flutter widget test + backend dashboard test green. Rebuilt
  `app-debug.apk`, reinstalled on the S24, app data cleared so the new default applies.
- Design discussion recorded for M2/M3 (see conversation): away-episode tracking via
  periodic ARP scans, RSSI threshold (~ -72 dBm ≈ "outside the room") read from the AP
  management plane (SSH/SNMP/controller API), teacher status overrides (izin/sakit),
  BSSID pinning using the existing `schedules.ap_bssid` column.

### 2026-10-25 — A: anti-cheat pass 1 + teacher-dashboard time bug FIXED + APK build started
- Cheat-hole review done (see conversation notes): biggest gaps = (1) borrowed/
  shared MAC for wifi_verified, (2) photo-file identity swap / replay, plus
  longer-term items (no server auth — device binding in M2; liveness
  detection; MAC randomization on phones documented for C1).
  First-line fixes implemented:
  - **One MAC = one student**: `POST /students/` and `PUT /students/{id}/mac`
    reject a MAC already registered to another student (409, normalized
    comparison — dashes/uppercase caught). 404 added for missing student on
    mac update. Live-verified.
  - **Photo replay guard**: `backend/services/photo_guard.py` + hook in
    `/attendance/check` — the same photo file may be accepted at most once
    per day per student (blocks shared-file identity swap); cross-day reuse
    still allowed; state is process-local (resets on restart, documented).
- Teacher-dashboard "wrong time" bug root cause: `schedules.created_at` was
  neither in the DB schema (older DBs) nor in `ScheduleResponse` (pydantic
  stripped it before the dashboard could read it). Fixed everywhere:
  column added to `models/database.py` + safe `ALTER TABLE` migration in
  `init_db`, INSERT now writes an explicit **CST** timestamp (consistent
  with attendance rows), and `ScheduleResponse.created_at` added.
  Live-verified: `"created_at":"2026-10-25T08:42:51"` (CST, correct).
- Demo-class creation in the browser simulator now matches the requested
  behaviour: press at 10:00 → class **10:01–10:10** (opens +1 min, closes
  +10 min, computed in server CST from the browser); log shows when the
  banner will appear. Headless sim produces the same window.
- Tests: 9 new anti-cheat tests in `backend/tests/test_anticheat.py`
  (+ conftest: schedules schema match, per-test photo-guard reset) —
  suite now **140/140**.
- Task-C handover note updated in `docs/C/TASK.md` (already reviewed);
  real-device route started: `flutter build apk --debug` for the user's
  Android phone (HP asli = C1) since Windows-desktop run stays blocked by
  the Developer-Mode symlink requirement.

### 2026-10-25 — A: simulator upgraded to REAL WEBCAM (camera screen opens from the banner)
- `docs/A/demo/auto_prompt_simulator.html` now mirrors the real app flow:
  **Enable camera (live webcam)** button (getUserMedia, permission once per
  browser), banner tap → phone display switches to a **camera screen**
  (mirrored preview + big white capture button, "Back" = cancel), optional
  **auto-capture 3 s** countdown, frame captured to canvas → JPEG →
  `POST /attendance/check`. File-upload flow kept as fallback (photo picker)
  when camera is denied/unavailable. All texts already English; headless
  sim terminal output translated to English too.
- Rationale answered for the team: a web page cannot silently open a webcam
  (needs one user permission + requirement), so the old upload picker was a
  stand-in; the FLUTTER app itself does open the camera screen directly.
- C-task handover note added to `docs/C/TASK.md` (A prototyped the Flutter
  prompt integration; C reviews commit `7803d27` on branch `a` before
  continuing with real-device testing C1).
- GitHub push configured: `git config --global http.proxy
  socks5://127.0.0.1:10808`; branch `a` pushed & tracking origin.

### 2026-10-24 — A: Flutter auto-prompt integration drafted + TWO local simulators running
- Flutter side implemented (draft for **C** to review/own — user requested A
  to prototype it now): `mobile/lib/services/prompt_service.dart` (polling
  service, 20 s heartbeat, dedupe per stage `scheduleId:checkType`), API
  method `getCheckInPrompt`, banner card + "Check in now / Later" in
  `home_screen.dart` (lifecycle-aware: pauses when app backgrounded),
  `auto_check_in_on` toggle in `session_service.dart` + Settings switch.
  `flutter analyze`: **No issues found**. NOT committed to mobile branch —
  sits on task-a for C's review.
- Headless e2e test PASSED (`backend/scripts/simulate_phone.py`): creates a
  fresh demo schedule (unique room, midnight-safe window), then
  banner→tap→START (79.9%, partial) → banner flips END →tap (85.4%,
  verified) → `check_in_complete` banner stops. Full loop 90 s.
- Visual phone simulator: `docs/A/demo/auto_prompt_simulator.html`
  (browser window mimicking the app: banner, Log, photo upload stand-in for
  the camera, auto-tap option, demo-class creator with Shanghai-time
  windows). Served at http://127.0.0.1:8765/auto_prompt_simulator.html
  (`python -m http.server 8765` in `docs/A/demo`).
- Blocked for REAL desktop app run: Windows build needs Developer Mode
  (symlink) — admin denied in this shell. Everything else works on
  emulator/real phone; `10.0.2.2:8000` already the app default.

### 2026-10-24 — A: auto check-in prompt feature BUILT & VERIFIED live (tier 1)
- New endpoint `GET /me/prompt?student_id=N` (`backend/routers/prompt.py`,
  registered in `main.py`): polls-friendly contract for the mobile app —
  returns `prompt` (strict: schedule active + stage open + device MAC seen on
  the classroom network), `check_available`, `check_type` (auto start→end),
  `wifi_seen`, `bssid`, `reason`. READS existing services only; no attendance
  rule changed — check-ins still go through the fully-enforced
  `POST /attendance/check`.
- 7 new tests (`backend/tests/test_prompt.py`): whole suite now **131/131**
  (includes 124 baseline).
- Live verification (schedule "Uji Auto Prompt" id 9, Buchari MAC = gateway):
  prompt start ✅ → start check (confidence 0.972) → prompt flips to `end`
  ✅ → end check (0.955) → `reason: check_in_complete`, banner stops ✅.
  Willian (no valid MAC): `check_available=true` but `prompt=false`,
  `device_not_seen_on_network` ✅. Room-overlap guard also observed working.
- Spec for C (Flutter heartbeat + banner + auto-navigate):
  `docs/A/auto_prompt_spec.md`. Mobile files untouched (C's area).
- (Earlier same day: threshold evaluation with 2 students → report + live
  Wi-Fi/two-stage verification; see previous entries.)

### 2026-10-24 — A: end-to-end Wi-Fi + two-stage check-in VERIFIED live
- Server run with `TIMEZONE=Asia/Shanghai` (CST); Wi-Fi scan auto-detected
  subnet 10.163.207.0/24 and BSSID 54:2b:de:fd:90:21 correctly in local time.
- **Discovery: `/wifi/scan` on Windows does NOT need Npcap** — it uses ping
  sweep + `arp -a` (see `wifi_scanner.py::_scan_windows`). The "Npcap required
  on Windows" note in AGENTS.md/PROJECT_CONTEXT is outdated for this path;
  Npcap only matters for raw Scapy (Linux path) capture. Candidate doc fix.
- Set Buchari MAC (simulated as gateway device) via `PUT /students/8/mac`.
- `POST /attendance/check?schedule_id=8&check_type=start` with a HELD-OUT
  photo (never enrolled) → matched, confidence **0.943**, `wifi_verified=true`,
  status `partial` ✅ (recognition works on unseen photos, not just enrolled ones)
- `end` check with another held-out photo → confidence **0.688**,
  `wifi_verified=true`, **status `verified`** — both rows finalized ✅
- Full two-stage flow + Wi-Fi check automation confirmed working live.
- Observed issue for review: `students/faces.created_at` + `ap_logs.scan_time`
  use SQLite `CURRENT_TIMESTAMP` (UTC) while `attendance.timestamp` is local —
  inconsistent; fix candidate in `models/database.py`.

### 2026-10-24 — A: first enrollment + threshold evaluation done (2 students)
- Fixed environment: `onnxruntime` failed to import because NumPy 2.2.6 was
  installed; restored the pinned `numpy==1.26.4` from `backend/requirements.txt`.
- Created students: Buchari `F25040126` (id 8) and Willian `F25040128` (id 9).
- Enrolled faces: Buchari 5 selfies (varied location/lighting/expression),
  Willian 3 selfies. Stored under `gambar_percobaan/orang_1|orang_2/` (gitignored).
- Ran `evaluate_threshold.py` → wrote real FAR/FRR/EER to `docs/threshold_report.md`:
  genuine min **0.708** vs impostor max **0.224** → distributions fully separated.
  **Threshold kept at 0.5** (midpoint of safe gap [0.224, 0.708]).
- ⚠️ Pending: still 2/3 students — recruit `orang_3` and re-run the evaluation
  before the M1 progress report (~Nov 1). See caveats in `docs/threshold_report.md`.

### 2026-10-18 — Planning session + repository audit + docs restructure (all)
- Audited the repository against reality: 124 tests, **123 passing**, 1 failing
  (`test_dashboard_served` — stale `"Teacher Dashboard"` assertion vs. redesigned
  dashboard titled "Face Attendance System - Presentation Dashboard"). Assigned to D.
- Found ~1185 lines of **uncommitted** dashboard redesign work
  (`backend/static/dashboard.html`). Assigned to D (review → commit).
- Confirmed `docs/threshold_report.md` is still a placeholder → A's top priority.
- Restructured `docs/`: created `PROJECT_CONTEXT.md` (master AI reference),
  `PLAN_TIMELINE.md` (this file), `meetings/`, per-member folders `A/ B/ C/ D/`
  with `TASK.md` + `PROMPT.md`.
- Archived outdated docs to `docs/archive/` (old `TASK_*.md`, `PROMPT_AI_TEAM.md`,
  `PEMBAGIAN_TUGAS_2026-10.txt`). Deleted stale root files `progress_report.txt` and
  `next_steps.txt` (recoverable from git history). All progress tracking now lives in
  `docs/`.
- Next: Phase 1 starts Oct 19 — each member follows their `docs/<X>/TASK.md` P0 items.
