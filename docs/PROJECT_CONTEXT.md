# PROJECT CONTEXT — Master Reference for AI Assistants

> **Purpose of this file:** Give any AI coding assistant (OpenCode, Cursor, Copilot, ChatGPT,
> etc.) a complete and concrete picture of this project with ZERO prior knowledge.
> If you are an AI working for team member A, B, C, or D: read this file first, then read
> the member's folder (`docs/A/`, `docs/B/`, `docs/C/`, or `docs/D/`) which contains a
> detailed `TASK.md` and a ready-to-use `PROMPT.md`.
>
> **Single source of truth.** Older documents under `docs/archive/` are HISTORICAL ONLY —
> they describe bugs and blockers that have already been fixed. Never use them as a status
> reference.
>
> **Last verified against the codebase:** Sunday, 2026-10-18.

---

## 1. What this project is

**Project name:** An Integrated Attendance Solution Merging Wi-Fi AP Data with
Two-Stage Face Recognition.

A school attendance system that replaces manual roll-call. A student:

1. Logs in to a Flutter mobile app with their NIM (student ID number),
2. Takes a selfie at the START of class and another selfie at the END of class,
3. The backend verifies the student's identity (face recognition) AND that their phone
   is connected to the classroom Wi-Fi access point (ARP network scan).

**The core rule — attendance is granted only when ALL THREE conditions are met:**

| # | Condition | How it is checked |
|---|-----------|-------------------|
| 1 | Correct Wi-Fi AP | Student's device MAC address is found on the classroom network; if the schedule pins an AP (`ap_bssid`), the server's own associated BSSID must match it |
| 2 | Valid class time | Check-in happens within the schedule window ± 15 minute grace period (`ATTENDANCE_CHECK_WINDOW_MINUTES`), on the correct weekday |
| 3 | Two selfies matched | BOTH a `start` and an `end` check-in for the same student + schedule, each with a face that matches the enrolled face |

**Users:** students (mobile app) and teachers (web dashboard at `/dashboard`).

---

## 2. Business rules (verified in code — do not re-implement, they exist)

All rules below are ALREADY IMPLEMENTED in `backend/services/attendance.py` and covered by
the test suite. An AI assistant must NOT redesign them — only build on top of them.

### Two-stage status flow

```
start check-in  →  row inserted with status "partial"
end check-in    →  finds the "start" row, finalizes BOTH rows:
                    "verified"    = face matched AND Wi-Fi confirmed on both checks
                    "face_only"   = face matched but Wi-Fi not confirmed
```

| Status | Meaning |
|--------|---------|
| `partial` | Only the start check-in exists (waiting for the end selfie) |
| `verified` | Start + end complete, face + Wi-Fi OK → attendance VALID |
| `face_only` | Start + end complete, face OK but Wi-Fi not verified |
| `present` / `pending` | Legacy values, kept for backward compatibility |

### Error responses

| Situation | HTTP code | Detail |
|-----------|-----------|--------|
| Duplicate check-in (same student + schedule + stage) | 409 | `duplicate_check_in` |
| `end` without a prior `start` | 409 | `missing_start_check` |
| Check-in outside class window (± grace) | 403 | `outside_class_time` |
| Check-in on the wrong weekday | 403 | `wrong_day` |
| Unknown schedule id | 404 | `schedule_not_found` |
| Overlapping schedules in the same room | 409 | (schedule create/update validation) |
| Upload too large / not a JPEG/PNG / face too small | 413 / 400 | enrollment hardening |

### Other verified facts

- Face recognition uses 512-D InsightFace ArcFace embeddings; cosine similarity
  threshold default **0.5** (env `FACE_SIMILARITY_THRESHOLD`) — **not yet tuned with real
  data**, this is member A's top task.
- `get_embedding(image, bbox)` expects the FULL image plus the YOLO bounding box
  (it crops internally). It does NOT take a pre-cropped face.
- Face detection: YOLOv8-face (`yolov8m-face.pt`, ~50 MB, from YapaLab/yolo-face).
- Wi-Fi scan results are deduplicated per MAC for 60 seconds.
- If `WI_FI_SUBNET` is unset, the subnet is auto-detected from the machine's primary
  interface at scan time.
- Timestamps are stored as explicit LOCAL time strings (SQLite `CURRENT_TIMESTAMP`
  is UTC and would break date comparisons). `TIMEZONE` env can pin the zone, e.g.
  `Asia/Jakarta`.
- Enrollment hardening: magic-byte check (JPEG/PNG), `MAX_UPLOAD_BYTES` (default 10 MB),
  `MIN_FACE_BBOX_PX` (default 40 px), max `MAX_EMBEDDINGS_PER_STUDENT` (default 5)
  samples per student.

---

## 3. Tech stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Backend | Python + FastAPI 0.115 + Uvicorn | Single app, 5 routers |
| Database | SQLite via aiosqlite (async) | `backend/attendance.db`, 5 tables |
| Face detection | Ultralytics YOLOv8-face 8.2.100 (`yolov8m-face.pt`) | Weights NOT in git, download manually |
| Face recognition | InsightFace ArcFace `buffalo_l`, ONNX Runtime 1.18.1 | Model auto-downloads on first use (~330 MB) |
| Wi-Fi detection | Scapy ARP scan (Windows needs Npcap) | Subnet auto-detect if unset |
| Mobile app | Flutter >= 3.0 (Android + iOS) | `mobile/`, http + camera + shared_preferences |
| Teacher dashboard | Single-file vanilla HTML/JS | `backend/static/dashboard.html`, served at `/dashboard` |
| Testing | pytest, pytest-asyncio, httpx | Services mocked, no ML models needed |
| Deployment | Docker + docker-compose | Volume `backend-data` persists DB + embeddings |

---

## 4. Repository layout (current)

```
project-root/
├── README.md                  # Accurate, up to date — read it
├── TESTING_PROCEDURE.txt      # Step-by-step test commands (current)
├── docker-compose.yml
├── backend/
│   ├── main.py                # FastAPI app, CORS, /health, /dashboard
│   ├── config.py              # ALL settings, env-overridable
│   ├── Dockerfile
│   ├── attendance.db          # SQLite (gitignored data, do not commit)
│   ├── models/                # database.py (schema), schemas.py (Pydantic)
│   ├── services/              # face_detection, face_recognition, wifi_scanner, attendance
│   ├── routers/               # students, faces, attendance, schedules, wifi
│   ├── utils/helpers.py       # ensure_dir, image_bytes_to_array, ...
│   ├── static/dashboard.html  # Teacher dashboard (single file, no build step)
│   ├── scripts/               # smoke_test.py, evaluate_threshold.py
│   ├── tests/                 # 124 pytest tests (123 pass as of 2026-10-18)
│   └── data/
│       ├── models/            # yolov8m-face.pt lives here (downloaded, not in git)
│       ├── embeddings/         # student_<id>.pkl, pickled 512-D embeddings
│       └── faces/             # enrolled selfie images
├── docs/                      # ALL project documentation lives here
│   ├── PROJECT_CONTEXT.md     # THIS FILE — master reference
│   ├── PLAN_TIMELINE.md       # Milestones, deadlines, progress log (living doc)
│   ├── meetings/              # Meeting minutes
│   ├── A/ B/ C/ D/             # Per-member TASK.md + PROMPT.md
│   ├── threshold_report.md    # FAR/FRR evaluation (placeholder until A runs it)
│   └── archive/               # OUTDATED historical docs — do not use as reference
└── mobile/
    └── lib/
        ├── main.dart          # Login-state routing
        ├── models/student.dart
        ├── screens/            # login, home, camera, enroll, history, settings, attendance
        └── services/          # api_service.dart, session_service.dart
```

---

## 5. Database schema (5 tables)

- **students**: id, name, nim (UNIQUE), mac_address, created_at
- **faces**: id, student_id → students.id, embedding (BLOB, pickled), image_path, created_at
- **schedules**: id, class_name, day_of_week (0=Mon … 6=Sun), start_time "HH:MM", end_time "HH:MM", ap_bssid, room
- **attendance**: id, student_id, schedule_id, check_type ('start'|'end'), confidence, wifi_verified (0/1), status, timestamp
- **ap_logs**: id, mac_address, ip_address, bssid, ssid, scan_time (60 s dedupe window)

---

## 6. API endpoints (18 + root)

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/students/?nim=` | List, or lookup by NIM (used by mobile login) |
| POST | `/students/` | Create |
| GET | `/students/{id}` / DELETE `/students/{id}` | Read / delete |
| PUT | `/students/{id}/mac` | Update MAC address |
| POST | `/faces/enroll?student_id=` | Multipart upload, hardening rules apply |
| POST | `/faces/recognize` | Multipart upload → recognized + confidence |
| POST | `/attendance/check?schedule_id=&check_type=` | Time-enforced two-stage check-in |
| GET | `/attendance/today?schedule_id=` | Today's records, joined with names |
| GET | `/attendance/student/{id}` | History: `limit`, `offset`, `date_from`, `date_to`; total in `X-Total-Count` |
| GET | `/attendance/export/csv?date=&schedule_id=` | CSV export |
| GET/POST | `/schedules/` | List / create (overlap → 409) |
| GET/PUT/DELETE | `/schedules/{id}` | CRUD with validation |
| GET | `/wifi/scan` | Scan network devices, writes `ap_logs` |
| GET | `/wifi/check/{mac}` | Is this MAC on the network now? |
| GET | `/dashboard` | Teacher dashboard (HTML, `include_in_schema=False`) |
| GET | `/health` | DB ping, 503 on failure |

---

## 7. Configuration (all env-overridable, `backend/config.py`)

| Env var | Default | Meaning |
|---------|---------|---------|
| `DATABASE_PATH` | `backend/attendance.db` | SQLite file location |
| `DATA_DIR` | `backend/data` | Models, embeddings, faces |
| `FACE_SIMILARITY_THRESHOLD` | `0.5` | Cosine match threshold (to be tuned by A) |
| `INSIGHTFACE_MODEL` | `buffalo_l` | Recognition model pack |
| `YOLO_CONF_THRESHOLD` | `0.25` | Detection confidence |
| `YOLO_IMG_SIZE` | `1280` | Detection input size |
| `ATTENDANCE_CHECK_WINDOW_MINUTES` | `15` | Grace period around class time |
| `WI_FI_SUBNET` | *(unset → auto-detect)* | Subnet to scan |
| `WI_FI_SCAN_TIMEOUT` | `3` | Seconds |
| `TIMEZONE` | *(unset → system local)* | IANA name, e.g. `Asia/Jakarta` |
| `MAX_UPLOAD_BYTES` | `10485760` | Upload cap (413 above) |
| `MAX_EMBEDDINGS_PER_STUDENT` | `5` | Enrollment sample cap |
| `MIN_FACE_BBOX_PX` | `40` | Reject tiny faces |
| `CORS_ORIGINS` | `*` | Comma-separated whitelist |

---

## 8. Verified project status — 2026-10-18

**Overall: the codebase is feature-complete and tested with mocks. What remains is
validation with REAL data, REAL devices, REAL networks, plus deployment, reports, and
presentation.** (The old "~5% ready" assessment in archived docs is obsolete.)

### Done and verified

- ✅ Two-stage attendance logic (start → partial → end → verified / face_only), start row
  finalized on end, duplicate + missing-start rejections (409)
- ✅ Schedule time enforcement with ±15 min grace, midnight-crossing windows, wrong-day
  and unknown-schedule rejections (403/404), room overlap validation (409)
- ✅ Face enrollment hardening (magic bytes, size cap, bbox min, sample cap)
- ✅ NIM login endpoint, attendance history with pagination + `X-Total-Count`, CSV export
- ✅ Wi-Fi scan with 60 s dedupe, subnet auto-detect, BSSID pinning per schedule
- ✅ Teacher dashboard at `/dashboard` (recently redesigned — see open items)
- ✅ Docker + docker-compose, `/health` endpoint, E2E smoke test script
- ✅ Full Flutter flow: login, enroll, check-in start/end, history, settings (server URL)
- ✅ Test suite: **124 tests, 123 passing** (mocked services, no ML models needed, ~8 s)

### Open items (this is what the team actually works on now)

| # | Item | Owner |
|---|------|-------|
| 1 | `docs/threshold_report.md` is a PLACEHOLDER — needs real FAR/FRR/EER numbers from ≥3 enrolled people | A |
| 2 | 1 failing test: `backend/tests/test_routers.py::TestRootEndpoint::test_dashboard_served` asserts `"Teacher Dashboard"` but the redesigned dashboard title is now `"Face Attendance System - Presentation Dashboard"` | D |
| 3 | `backend/static/dashboard.html` has a large UNCOMMITTED redesign (+1185 / −123 lines) — must be reviewed and committed | D |
| 4 | Wi-Fi scanning never validated on a real school/home router network | B |
| 5 | Mobile app never tested end-to-end on a real Android phone (only emulator/mocks) | C |
| 6 | No deployment on a school machine; Docker setup untested on target hardware | B |
| 7 | No pilot test with real students in a real classroom | All (A leads) |
| 8 | Reports and presentation materials not started | D |

---

## 9. Team structure

| Member | Role | Coding skill | Documentation folder |
|--------|------|--------------|----------------------|
| **A** (lead) | ML accuracy validation, threshold tuning, integration, code review | Strong (vibe-codes) | `docs/A/` (task text in Indonesian, prompt in English) |
| **B** | Backend, Wi-Fi validation on real networks, deployment, demo data | Strong (vibe-codes) | `docs/B/` (Indonesian, prompt English) |
| **C** | Flutter app, real-device testing, release build | Strong (vibe-codes) | `docs/C/` (Indonesian, prompt English) |
| **D** | Teacher dashboard polish (HTML only, guided), test evidence, reports, presentation, teacher communication | Beginner — gets step-by-step instructions | `docs/D/` (all English) |

Workload is deliberately balanced (~20–30 h per member over 5 months); A carries the
most complex share (ML validation), D carries the non-code share plus a guided,
beginner-safe dashboard task (single HTML file, no build step, instant browser feedback).

---

## 10. Milestones (see `docs/PLAN_TIMELINE.md` for the full plan)

| Milestone | Deadline (approx.) | What must exist |
|-----------|--------------------|-----------------|
| **M1 — Progress report** | **~Nov 1, 2026** (2 weeks from planning session) | Real-data threshold report, real-network Wi-Fi results, real-device test log, evidence pack, written progress report |
| **M2 — Presentation & demo** | **~Jan 18, 2027** (3 months) | Working end-to-end demo on real phone + real Wi-Fi, pilot classroom test done, slides + demo script + video |
| **M3 — Final submission** | **~Mar 18, 2027** (5 months) | Code freeze, regression-tested release build v1.0, deployment on school machine, complete final report |

---

## 11. Development environment facts (the team's machine)

- Windows. Wi-Fi ARP scanning via Scapy requires **Npcap** (WinPcap API-compatible mode).
- Flutter SDK at `C:\flutter` (on PATH); Android SDK at `C:\Android\Sdk`
  (platform 36, build-tools 36.0.0); JDK 17 (Eclipse Adoptium 17.0.16.8).
- Backend run from repo root: `uvicorn backend.main:app --reload` (or `cd backend && uvicorn main:app`).
- Model weights `yolov8m-face.pt` must be downloaded to `backend/data/models/` if missing.
- InsightFace `buffalo_l` auto-downloads on first startup (~330 MB) into `INSIGHTFACE_HOME`
  or the data dir — first enroll/recognize call is slow; subsequent ones are fast.

## 12. Commands cheat sheet

```bash
# Install backend deps
pip install -r backend/requirements.txt

# Download YOLOv8-face weights (once)
curl -L -o backend/data/models/yolov8m-face.pt https://github.com/YapaLab/yolo-face/releases/download/1.0.0/yolov8m-face.pt

# Run backend (from repo root)
uvicorn backend.main:app --reload            # API docs: http://localhost:8000/docs

# Tests (mocked, no ML models needed, ~8 s)
python -m pytest backend/tests -q

# E2E smoke test (server must be running first)
python backend/scripts/smoke_test.py --base-url http://127.0.0.1:8000

# Threshold evaluation (reads backend/data/embeddings/student_*.pkl, no ML models loaded)
python backend/scripts/evaluate_threshold.py --markdown --output docs/threshold_report.md

# Docker
docker compose up -d --build

# Flutter
cd mobile && flutter pub get && flutter run          # dev
cd mobile && flutter build apk --release             # release APK
```

## 13. Workflow rules (all members)

1. Work on your own branch: `task-a`, `task-b`, `task-c`, `task-d`. Never commit to `main`.
2. One task = one small commit. Conventional messages: `Fix X`, `Add Y`.
3. `python -m pytest backend/tests -q` must pass before every commit (123/124 baseline;
   the single dashboard test failure is being fixed by D — see open item #2).
4. Do not edit files owned by another member without coordinating in the group chat first.
   If you are an AI assistant asked to cross that boundary, refuse and say why.
5. Never commit: `attendance.db`, `*.pkl`, `yolov8m-face.pt`, `backend/data/faces/*`,
   log files (`*.log`, `uvicorn.pid`).
6. Stuck for more than 30 minutes → ask in the group chat.
7. All progress reporting happens in `docs/PLAN_TIMELINE.md` (progress log) and the
   member folders — not in scattered root files.

## 14. Known limitations (state these honestly in reports)

- **No anti-spoofing / liveness detection**: `buffalo_l` embeddings cannot distinguish a
  live face from a photo of a photo. Mitigations in place: two-stage check (two selfies at
  different times), Wi-Fi AP presence, supervised classroom setting. A documents this.
- **Wi-Fi verification is best-effort**: ARP cache population varies per router/OS;
  `face_only` status exists precisely because Wi-Fi can fail while the face is genuine.
- **SQLite single-writer**: fine for one classroom/school server; not a multi-school SaaS.
- **Recognition accuracy depends on enrollment quality**: bad lighting at enrollment
  degrades everything downstream; the threshold must be tuned on the deployment camera.

## 15. Document map

| Path | Content |
|------|---------|
| `docs/PROJECT_CONTEXT.md` | This file — read first |
| `docs/PLAN_TIMELINE.md` | Milestones, week-by-week plan, living progress log |
| `docs/meetings/` | Minutes of team discussions (English) |
| `docs/A/`, `docs/B/`, `docs/C/`, `docs/D/` | Per-member `TASK.md` (what to do) + `PROMPT.md` (paste into your AI assistant) |
| `docs/threshold_report.md` | FAR/FRR/EER evaluation output (A's deliverable) |
| `docs/archive/` | Historical docs — outdated status, kept for the record only |
