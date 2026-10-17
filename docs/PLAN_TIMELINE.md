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
