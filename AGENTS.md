# AGENTS.md

## Language Convention

**OUTPUT AND INPUT IN ALL SYSTEMS OF THIS PROJECT MUST BE IN ENGLISH BECAUSE THIS ASSIGNMENT USES ENGLISH (THE RESULT).**

This covers, without exception: app UI text, API response bodies and error `detail`
strings, server logs, code comments, docstrings, identifier naming, commit messages, every
file under `docs/`, CSV headers, teacher-dashboard text, slides, demo video, and the final
report.

Two deliberate exceptions:

1. Conversation between team members (group chat) may be Indonesian.
2. Work-package instructions addressed to A, B and C are written in Indonesian
   (`docs/A/TASK.md`, `docs/B/TASK.md`, `docs/C/TASK.md`); instructions for D are in
   English (`docs/D/TASK.md`). Whatever those instructions *produce* is still English,
   per the rule above.

## Project

Integrated attendance system combining **rotating QR code** presence proof with **face recognition**.
The teacher starts a class session from the dashboard; a QR code is projected on the classroom
LCD and rotates every 5 seconds. Students scan the QR with the mobile app, take a selfie, and
attendance is granted only when all three conditions are met: the device is on the school
Wi-Fi, the QR token is valid, and the selfie matches the enrolled face.

## Architecture

- **Backend**: Python (FastAPI) — QR session lifecycle, rotating tokens, face detection/recognition, attendance logic
- **Frontend**: Flutter mobile app (Android + iOS) — QR scan, camera capture, status display
- **Database**: SQLite — students, faces, qr_sessions, attendance
- **Face Detection**: YOLOv8 (`yolov8m-face.pt` from `akanametov/yolo-face`)
- **Face Recognition**: InsightFace ArcFace (`buffalo_l`) — 512-D embeddings, cosine similarity threshold ~0.5
- **QR Codes**: `qrcode[pil]` server-side rendering; `mobile_scanner` in the app
- **Network check**: client IP must be inside `SCHOOL_SUBNET` (default `192.168.0.0/16`; loopback always allowed)

## Directory Layout

```
backend/          → FastAPI app, services, models, routers
backend/data/     → YOLOv8 model weights, stored embeddings
mobile/           → Flutter app (lib/screens, services, models)
```

## Build / Test / Lint

Backend setup:
```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

Backend tests (services mocked, no ML models needed):
```bash
python -m pytest backend/tests -q
```

End-to-end smoke test against a running server:
```bash
python backend/scripts/smoke_test.py --base-url http://127.0.0.1:8000
```

Flutter setup:
```bash
cd mobile && flutter pub get && flutter run
```

This machine: Flutter SDK at `C:\flutter` (on user PATH), Android SDK at `C:\Android\Sdk` (platform 36, build-tools 36.0.0), JDK 17 at `C:\Program Files\Eclipse Adoptium\jdk-17.0.16.8-hotspot`.

## Key Facts

- YOLOv8-face model: `yolov8m-face.pt` (50 MB) — download from `github.com/YapaLab/yolo-face/releases`
- InsightFace model: `buffalo_l` (auto-downloaded on first use; set `INSIGHTFACE_HOME` to relocate)
- Attendance requires ALL 3 conditions: school Wi-Fi (subnet check) + valid rotating QR token + face match
- Teacher flow: POST `/qr-sessions/start` → dashboard renders `/qr-sessions/active/qr.png`,
  auto-refreshed every 5 s; POST `/qr-sessions/end` closes the session
- **One active session at a time**: starting a new session auto-closes the previous one
- QR token: 6-char uppercase alphanumeric (unambiguous alphabet), rotates every
  `QR_ROTATION_SECONDS` (default 5); the previous token stays valid for `QR_GRACE_SECONDS`
  (default 10) after rotation, so slow scans do not fail
- Student flow: login by NIM → scan QR (`/qr-sessions/validate`) → selfie →
  `POST /attendance/check-qr?student_id=&token=` with multipart image
- Check-in is bound to the logged-in `student_id`: the accepted face must match that
  student, otherwise 403 `identity mismatch` (no row written). A second *significant*
  face in the frame (area ≥ 10% of the largest) → 400 `Multiple faces detected`; nested
  duplicate boxes of one face are merged first (containment ≥ 0.6)
- Duplicate check-ins for the same session rejected (409)
- Requests from outside `SCHOOL_SUBNET` → 403 `You are not connected to the school network.`
- No active session (or session ended) → 400 `No active class session` / `Invalid or expired QR code`
- Enrollment stores only the largest distinct face and rejects photos with two people
- `attendance.faces_detected` records the raw YOLO box count per check-in (audit);
  `attendance.ip_address` records the client IP (audit)
- `get_embedding(image, bbox)` expects the FULL image + YOLO bbox (crops with margin internally)
- Cosine similarity threshold: 0.5 (env `FACE_SIMILARITY_THRESHOLD`)
- Config is env-overridable: `DATABASE_PATH`, `DATA_DIR`, `SCHOOL_SUBNET`,
  `QR_ROTATION_SECONDS`, `QR_GRACE_SECONDS`, `QR_TOKEN_LENGTH`, `YOLO_CONF_THRESHOLD`,
  `YOLO_IMG_SIZE`, `INSIGHTFACE_MODEL`, `TIMEZONE`, `MAX_UPLOAD_BYTES`,
  `MAX_EMBEDDINGS_PER_STUDENT`, `MIN_FACE_BBOX_PX`
- `TIMEZONE` (IANA name, e.g. `Asia/Jakarta`) — set on the server so timestamps stay
  consistent across machines; unset → system local time
- Enrollment hardening: JPEG/PNG magic-byte check, `MAX_UPLOAD_BYTES` cap (413), `MIN_FACE_BBOX_PX` filter, max `MAX_EMBEDDINGS_PER_STUDENT` samples per student
- Removed in v2 (QR redesign): schedules/schedule-based rosters, per-student MAC collection,
  ARP scanning (`wifi_scanner.py`, scapy), two-stage start/end check-ins, auto-prompt polling
- **Database policy: current schema only.** Migrations are additive (`ALTER TABLE ... ADD COLUMN`);
  a database from the removed schedule-based design is **refused at startup** with a clear
  `RuntimeError` instead of being rebuilt (the old rebuild dropped `schedules`,
  `schedule_students`, `ap_logs` and rewrote every attendance row to `qr_session_id=0`).
  Keep such files in `backups/`, delete/rename the live `attendance.db`, restart, then restore
  demo data with `python backend/scripts/seed_demo.py --reset` and re-enroll faces.
  Contract tests: `backend/tests/test_schema.py`.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/students/?nim=` | List students, or look up one by NIM (login) |
| POST | `/students/` | Create student (name, nim) |
| GET | `/students/{id}` | Get student by ID |
| DELETE | `/students/{id}` | Delete student |
| POST | `/faces/enroll?student_id=` | Enroll face (upload image) |
| POST | `/faces/recognize` | Recognize face (upload image) |
| POST | `/teachers/login` | Teacher login (`{username, password}` -> bearer token, `TEACHER_TOKEN_HOURS`) |
| POST | `/teachers/verify` | Check whether the current bearer token is still valid |
| POST | `/teachers/logout` | Drop the bearer token |
| POST | `/classes/` | Teacher creates a class (canonical session owner) |
| GET | `/classes/` | List classes |
| GET | `/classes/{id}/students` | Class roster (enrolled students) |
| POST | `/classes/{id}/students` | Enroll students into a class (`{student_ids: [...]}`) |
| DELETE | `/classes/{id}/students/{student_id}` | Remove one student from a class (profile is kept) |
| DELETE | `/classes/{id}` | Delete a class (teacher auth) |
| POST | `/qr-sessions/start` | Teacher starts a class session (auto-closes any active one) |
| POST | `/qr-sessions/end` | Teacher ends the session (`{session_id?}`, returns total attendance) |
| POST | `/qr-sessions/phase` | Teacher moves the phase: `start` \| `end` \| `closed` (`FINAL_CHECK_GRACE_MINUTES`) |
| GET | `/qr-sessions/history` | Teacher's recent sessions (teacher auth) |
| GET | `/qr-sessions/active` | Active session info (rotates the token when stale) |
| GET | `/qr-sessions/active/token` | Current rotating token (lightweight dashboard poll) |
| GET | `/qr-sessions/active/qr.png` | QR code image (PNG) of the current token for the LCD |
| POST | `/qr-sessions/validate` | Validate a scanned token (`{token}` → `{valid, session_id, ...}`) |
| POST | `/attendance/check-qr?student_id=&token=` | QR check-in with face scan (subnet-checked, identity-bound) |
| GET | `/attendance/today?qr_session_id=` | Today's attendance (joined names, optional filter) |
| GET | `/attendance/student/{id}` | Get student history (supports `limit`, `offset`, `date_from`, `date_to`; total in `X-Total-Count`) |
| GET | `/attendance/export/csv?date=&qr_session_id=` | Export attendance as CSV |
| GET | `/attendance/roster?qr_session_id=` | Class roster + attendance status for one session |
| GET | `/attendance/export/csv?qr_session_id=` | Same endpoint: roster CSV when a session is given, raw check-in CSV otherwise |
| POST | `/attendance/manual` | Teacher writes an audited manual attendance row after the session closes |
| GET | `/dashboard` | Teacher web dashboard (HTML: QR + live attendance + students) |
| GET | `/health` | Health check with database ping (503 on DB failure) |

## Database Schema

Current schema is defined in `backend/models/database.py` (that file is the source of truth;
`backend/tests/test_schema.py` asserts it).

- **students**: id, name, nim, mac_address (unused), created_at
- **faces**: id, student_id, embedding, image_path, created_at
- **classes**: id, class_name, room, created_by, created_at
- **class_students**: id, class_id, student_id, added_at (`UNIQUE(class_id, student_id)`)
- **qr_sessions**: id, token, prev_token, token_rotated_at, created_by, class_id, class_name,
  room, started_at, ended_at, is_active, phase (`start|end|closed`), spot_round, phase_started_at
- **attendance**: id, student_id, qr_session_id, check_type (`start|end|spot`), spot_round,
  confidence, ip_address, status, timestamp, faces_detected, manual_by, manual_at, manual_reason

There is no `teachers` table: teacher login uses `TEACHER_USERNAME`/`TEACHER_PASSWORD` env vars
and an in-memory bearer token, so restarting the server logs every teacher out.

## Setup Steps

1. Download YOLOv8-face model:
   ```bash
   curl -L -o backend/data/models/yolov8m-face.pt https://github.com/YapaLab/yolo-face/releases/download/1.0.0/yolov8m-face.pt
   ```

2. Install backend dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. Start backend server:
   ```bash
   uvicorn backend.main:app --reload
   ```

4. API docs available at: `http://localhost:8000/docs`

5. Flutter mobile:
   ```bash
   cd mobile && flutter pub get && flutter run
   ```

## Demo Flow

1. Open `http://127.0.0.1:8000/dashboard` (teacher)
2. Enter class name + room → "Start Class Session" → project the QR on the LCD (rotates every 5 s)
3. On the phone: log in with NIM → "Scan QR Code" → scan → selfie
4. The dashboard live-attendance list updates every 5 s; "Export CSV" downloads the sheet
5. "End Session" closes the class (QR check-ins are refused afterwards)
6. Optional demo seed: `python backend/scripts/seed_demo.py --reset`