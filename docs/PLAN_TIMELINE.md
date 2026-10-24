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
