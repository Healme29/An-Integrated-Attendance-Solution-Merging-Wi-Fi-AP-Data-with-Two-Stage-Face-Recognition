# Current System — Rotating QR Attendance (source of truth for member B)

> **Status:** current at `HEAD = 011840a` (`origin/main`, pulled 2026-11-24).
> **Supersedes:** the Wi-Fi/ARP/schedule design in `network_validation.md`,
> `offline_fallback.md`, `demo_runbook.md`, `deployment_guide.md`, `guide_review.md`,
> `review_response.md` and the Wi-Fi evidence under `evidence/2026-11-13-windows/`.
> Those files remain as **historical measurements**, not as a description of the running code.
> Direction decision: **D-015** in `DECISIONS.md`. Old Wi-Fi code is archived locally on branch
> **`wifi-backup-prepull`** (`a9ca24d`).
> **Owner:** B · **Applies to:** backend deployment, demo environment, offline fallback, M3
> report chapter. Language rule: everything below is English (`AGENTS.md` §2.0).

---

## 1. What the system is now

The attendance rule is **three conditions**, but the network condition changed:

| Condition | How it is proved now | Failure |
|---|---|---|
| On the school network | the **client IP** is inside `SCHOOL_SUBNET` (loopback allowed; invalid config falls back to `ip.is_private`) | `403` |
| Valid class session | a **6-character rotating QR token** issued by an active `qr_sessions` row, valid for 5 s with a 10 s grace on the previous token | `400` |
| Matching face | YOLOv8-face detection → largest single face → passive liveness → ArcFace cosine ≥ `FACE_SIMILARITY_THRESHOLD` (0.5), matched to the **logged-in student** | `400` / `403` |

The old ARP/MAC scan, AP BSSID pinning, per-student MAC registration, class schedules,
`face_only` rows, strict classroom mode and auto-prompt polling **do not exist in the code**.
They were removed before the pull (`AGENTS.md` §"Key Facts" says so; note that `AGENTS.md:104`
incorrectly also claims the two-stage check-in is removed — see §5).

The two-stage idea **survives in a different form**: a teacher session moves through
`start → spot (optional, repeatable) → end → closed`, and a student's rows move from
`partial` (start/spot) to `verified` (end). Teacher manual rows are allowed only after close.

---

## 2. Configuration (`backend/config.py`)

Set these in the shell before starting `uvicorn`. The old variables
`WI_FI_SUBNET`, `REQUIRE_CLASSROOM_WIFI`, `ATTENDANCE_CHECK_WINDOW_MINUTES` and
`schedules.ap_bssid` are **dead** — `docker-compose.yml:17,19` still passes two of them and
must be corrected by whoever owns that file.

| Variable | Default | Meaning / demo value |
|---|---|---|
| `DATABASE_PATH` | `backend/attendance.db` | SQLite file; first start creates it |
| `DATA_DIR` | `backend/data` | models, embeddings and face crops |
| `YOLO_CONF_THRESHOLD` | `0.25` | detector confidence |
| `YOLO_IMG_SIZE` | `640` | 640 measured 3.8× faster than 1280 |
| `FACE_DUPLICATE_IO_MIN` | `0.6` | merge nested boxes above this containment |
| `MULTIPLE_FACES_MIN_RELATIVE_AREA` | `0.10` | a second face ≥10% of the largest is another person |
| `INSIGHTFACE_MODEL` | `buffalo_l` | ArcFace model pack |
| `FACE_SIMILARITY_THRESHOLD` | `0.5` | cosine acceptance |
| **`SCHOOL_SUBNET`** | `192.168.0.0/16` | client-IP gate; set to the demo hotspot subnet |
| `QR_ROTATION_SECONDS` | `5` | token lifetime |
| `QR_GRACE_SECONDS` | `10` | previous token still accepted |
| `QR_TOKEN_LENGTH` | `6` | unambiguous alphabet (no `I`, `O`, `0`, `1`) |
| `FINAL_CHECK_GRACE_MINUTES` | `5` | auto-close after the `end` phase |
| `TEACHER_USERNAME` | `teacher` | demo teacher login |
| `TEACHER_PASSWORD` | `attendance2026` | demo password; change for any real pilot |
| `TEACHER_TOKEN_HOURS` | `8` | bearer-token lifetime |
| `LIVENESS_ENABLED` | `true` | passive anti-spoof gate |
| `LIVENESS_MIN_SCORE` | `0.35` | additional score gate on top of the liveness verdict |
| `MAX_CONCURRENT_RECOGNITIONS` | `4` | semaphore; excess returns `429` + `Retry-After: 3` |
| `TIMEZONE` | system local | IANA name; `tzdata` required on Windows |
| `MAX_UPLOAD_BYTES` | 10 MiB | cap on enroll **and** check-in |
| `MAX_EMBEDDINGS_PER_STUDENT` | `5` | enrollment cap |
| `MIN_FACE_BBOX_PX` | `40` | tiny-face filter |
| `CORS_ORIGINS` | `*` | **set a single origin on the demo machine** |

`INSIGHTFACE_HOME` is not read by `config.py`; the Dockerfile and compose file set it to
`/app/data/dbdata/insightface`. On native Windows, InsightFace 2.1 still hard-codes
`~/.insightface`, i.e. `%USERPROFILE%\.insightface\models\buffalo_l`, regardless of `DATA_DIR`.

---

## 3. Endpoints (32 total: 29 router + 3 app-level)

### Teacher authentication — `backend/routers/teachers.py`
All teacher actions need `Authorization: Bearer <token>`; otherwise `401` with
`WWW-Authenticate: Bearer`. Tokens are process-local and expire after 8 h by default.

| Method | Path | Purpose |
|---|---|---|
| POST | `/teachers/login` | `{username,password}` → `{token, teacher}`, 401 on bad credentials |
| POST | `/teachers/verify` | `{token}` → `{valid, teacher}` |
| POST | `/teachers/logout` | invalidate bearer token |

### Classes — `backend/routers/classes.py`

| Method | Path | Purpose |
|---|---|---|
| POST | `/classes/` | create a class (teacher) |
| GET | `/classes/` | list classes |
| GET | `/classes/{class_id}/students` | roster ordered by NIM |
| POST | `/classes/{class_id}/students` | add student; removes them from any other class first |
| DELETE | `/classes/{class_id}/students/{student_id}` | remove student |
| DELETE | `/classes/{class_id}` | delete class; **409 if any session exists** |

### QR sessions — `backend/routers/qr_sessions.py`

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/qr-sessions/start` | teacher | start a session; requires a class with ≥1 enrolled student; closes any previous active session |
| POST | `/qr-sessions/phase` | teacher | `{phase}` → `spot` / `start` / `end` / `closed`; invalid transition 409 |
| POST | `/qr-sessions/end` | teacher | end session, return `total_attendance` |
| GET | `/qr-sessions/history` | teacher | recent sessions (`?limit=10`, clamped 1–50) |
| GET | `/qr-sessions/active` | public | active session + token, or `{"active": false}` |
| GET | `/qr-sessions/active/token` | public | token only, or `null` |
| GET | `/qr-sessions/active/qr.png` | public | PNG QR payload, `Cache-Control: no-store` |
| POST | `/qr-sessions/validate` | public | `{token}` → phase and `spot_round` |

The QR payload is `{session_id, token, class_name, phase, spot_round}`. A phase change
generates a **new token and clears `prev_token`**, so a start-phase QR stops working the
moment the teacher moves to `end`.

### Students and faces

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/students/?nim=` | public | list students / login lookup |
| POST | `/students/` | teacher | create (400 on duplicate NIM) |
| GET | `/students/{id}` | public | get student |
| DELETE | `/students/{id}` | teacher | cascade-delete attendance, class links, faces |
| POST | `/faces/enroll?student_id=` | public | multipart selfie; 400/404/413 rules |
| POST | `/faces/recognize` | public | multipart selfie → recognized student + confidence |

### Attendance — `backend/routers/attendance.py`

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/attendance/check-qr?student_id=&token=` | public + IP gate | multipart selfie; writes `start` / `spot` / `end` row |
| POST | `/attendance/manual` | teacher | audited row, **only after the session is closed** |
| GET | `/attendance/roster?qr_session_id=` | teacher | `verified / partial / pending / absent` per student |
| GET | `/attendance/today?qr_session_id=` | public | today's rows |
| GET | `/attendance/export/csv?date=&qr_session_id=` | public | CSV export |
| GET | `/attendance/student/{id}` | public | history with `limit`, `offset`, `date_from`, `date_to`, `X-Total-Count` |

### App level — `backend/main.py`

`GET /` (service info), `GET /health` (200 `{"status":"ok","database":"ok"}`, **503** on DB
failure), `GET /dashboard` (teacher web UI, hidden from OpenAPI, `Cache-Control: no-store`).

There are **no** `/wifi/*`, `/schedules/*` or `/prompt/*` routes.

---

## 4. Check-in flow, in code order

1. Teacher logs in, creates a class and adds students (`/teachers/login`, `/classes/...`).
2. Teacher starts the session (`/qr-sessions/start`); token rotates every 5 s.
3. Dashboard polls `/qr-sessions/active` and reloads `/qr-sessions/active/qr.png`.
4. Student logs in by NIM and scans the QR (`/students/?nim=`, `/qr-sessions/validate`).
5. `POST /attendance/check-qr?student_id=&token=` with a selfie. The server checks, in order:
   1. client IP inside `SCHOOL_SUBNET` → `403` otherwise;
   2. token valid for the **current phase** → `400 otherwise`;
   3. student and session exist (404), student is in the class roster (403), no duplicate
      for this phase/round (409), `spot`/`end` have a prior `start` row (409);
   4. upload ≤ 10 MiB and JPEG/PNG magic bytes (413/400);
   5. concurrency semaphore → `429` when 4 recognitions are already running.
6. Recognition: image decode → YOLO detection (in a thread) → nested-box dedupe → reject a
   significant second face → largest face → padded crop → passive liveness (blur, screen
   grid, colour variance, white reflections) → ArcFace embedding → cosine compare against
   every enrolled student's embeddings.
7. **Identity binding:** the matched student must be the `student_id` in the query, otherwise
   `403` and **no row is written**.
8. SHA-256 replay guard: the exact same photo file may be used once per day (`409`).
9. Insert row with `check_type` = current phase, `spot_round`, `confidence`, `ip_address`,
   `faces_detected`, local timestamp. `start` → `partial`, `end` → `verified`.
10. Teacher moves to `end` (new QR token), then closes the session; manual rows are only
    possible after close. The roster and CSV collapse these rows into
    `verified / partial / pending / absent`.

Enrollment stores at most 5 embeddings per student as
`DATA_DIR/embeddings/student_<id>.pkl`, plus a crop under `DATA_DIR/faces/`.

---

## 5. Database (6 tables)

| Table | Key columns | Purpose |
|---|---|---|
| `students` | `id`, `nim UNIQUE`, `name`, `mac_address` *(legacy, unused)* | accounts |
| `faces` | `student_id`, `embedding BLOB`, `image_path` | enrolled profiles |
| `classes` | `id`, `class_name`, `room`, `created_by` | roster container |
| `class_students` | `class_id`, `student_id`, `UNIQUE(class_id, student_id)` | one class per student |
| `qr_sessions` | `token`, `prev_token`, `token_rotated_at`, `class_id`, `phase`, `spot_round`, `is_active` | rotating QR state |
| `attendance` | `qr_session_id`, `check_type`, `spot_round`, `confidence`, `ip_address`, `status`, `faces_detected`, `manual_by/at/reason` | audit rows |

`init_db()` enables WAL, migrates old `schedule_id` rows into `qr_session_id = 0`, and drops
`schedule_students`, `schedules` and `ap_logs` on startup. `AGENTS.md`'s four-table schema is
out of date; so is `CLAUDE_CONTEXT_UPDATE.txt` §"do not redesign the two-stage flow".

---

## 6. Demo / deployment runbook (replaces the Wi-Fi runbook)

### 6.1 One-time preparation (needs internet)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m pip install dill==0.3.8   # still missing from requirements
```

Python **3.12**; 3.13 cannot install the pinned wheels. Measured install on this laptop:
**577 s** (historical G1 evidence, still valid for the interpreter/deps). Then copy the two
model artefacts into place:

```powershell
New-Item -ItemType Directory -Force backend\data\models | Out-Null
Copy-Item backups\models\yolov8m-face.pt backend\data\models\yolov8m-face.pt
# 52,028,566 bytes, sha256 219f490a97d5722972e1660725fa7cfab54e46c944b833debc28c2302aa1be93
Copy-Item backups\models\buffalo_l "$env:USERPROFILE\.insightface\models\buffalo_l" -Recurse
# 5 .onnx files, 341,268,726 bytes
```

Offline reinstall without the internet uses the local wheelhouse (validated with
`pip install --dry-run --ignore-installed --no-index --find-links wheelhouse -r
backend\requirements.txt` → **79 packages resolved**, 2026-11-24):

```powershell
.\.venv\Scripts\python.exe -m pip install --no-index --find-links wheelhouse -r backend\requirements.txt
```

### 6.2 Start

```powershell
$env:TIMEZONE="Asia/Shanghai"
$env:SCHOOL_SUBNET="192.168.137.0/24"        # hotspot subnet, not WI_FI_SUBNET
$env:TEACHER_USERNAME="teacher"; $env:TEACHER_PASSWORD="attendance2026"
$env:LIVENESS_ENABLED="true"; $env:CORS_ORIGINS="http://127.0.0.1:8000"
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Startup only runs `init_db()`; there is **no eager model warm-up**. The first face request
still pays the model load (historically 13.4 s cold, 1.5 s warm). Call
`POST /faces/recognize` once with any valid image before the audience arrives.

### 6.3 Seed and rehearse

```powershell
.\.venv\Scripts\python.exe backend\scripts\seed_demo.py --reset --students 5
```

`--reset` wipes all tables and stale embedding/crop files, creates `Demo Class` /
`Demo Room A`, an active **start-phase** QR session and five `start` attendance rows.
**Stop the server first on Windows** (the script writes SQLite directly). Seed data has no
faces, so recognition must be demonstrated with a real enrolled student.

`python backend/scripts/smoke_test.py --base-url http://127.0.0.1:8000` performs a live,
no-real-face E2E check: health → dashboard text → teacher login → class/student/enroll →
session → active/token/validate/QR PNG → faceless 400s → phase change with **old token
rejected** → manual attendance → roster/CSV → cleanup.

### 6.4 Offline fallback ladder (QR version)

| Rung | Situation | Action |
|---|---|---|
| 1 | Normal | hotspot, laptop serves QR dashboard, phone scans QR and uploads a selfie |
| 2 | Phone not in `SCHOOL_SUBNET` | check hotspot IP; `403` is the gate working, not a bug. Do **not** widen the subnet on stage without saying so |
| 3 | Face path broken | show seeded session, dashboard + roster + CSV; never fake a `verified` row |
| 4 | Backend will not start | restore `attendance.db` from `backups\`, or `seed_demo.py --reset` after stopping the server |
| 5 | Laptop dies | D plays the backup video; slides contain screenshots |

Model pre-flight (offline, before the audience):

```powershell
Get-Item backend\data\models\yolov8m-face.pt | Select-Object Length   # 52028566
Get-ChildItem "$env:USERPROFILE\.insightface\models\buffalo_l"        # 5 .onnx files
```

---

## 7. Tests and current evidence

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

Result after the pull and after installing `qrcode[pil]==8.0.0`: **38 passed in 7.3 s**
(`.venv/pytest_after_pull.log`). Coverage: 18 QR-session tests (token rotation, grace,
phase transitions, spot rounds, subnet, teacher auth) and 20 attendance tests (two-stage
flow, duplicates, replay, identity binding, manual attendance, roster/CSV, enrollment
hardening, health). ML inference is mocked; no real face is required.

Old evidence (`docs/D/evidence/pytest_result.txt` = 139 tests, `smoke_test_result.txt` with
`/wifi/scan`, and the `docs/B/evidence/2026-11-13-windows/` measurements) is **historical**
and must never be presented as the current suite or current endpoints.

---

## 8. Known gaps and owners

| # | Gap | Owner |
|---|---|---|
| 1 | `dill==0.3.8` still missing from `backend/requirements.txt` and the Dockerfile → fresh install can 500 on recognition | A |
| 2 | `docker-compose.yml` passes dead `WI_FI_SUBNET` / `ATTENDANCE_CHECK_WINDOW_MINUTES`; comment still says "schedule windows" | B/A (compose is B-owned) |
| 3 | `AGENTS.md:104`, endpoint table and DB table list are stale; `CLAUDE_CONTEXT_UPDATE.txt` still mentions strict Wi-Fi mode | A/D (repo-level docs) |
| 4 | Teacher password is a demo default (`attendance2026`) and tokens are process-local | A |
| 5 | `status='verified'` is hardcoded in the INSERT while the response computes `partial`/`verified`; roster derives status from row presence | A |
| 6 | Hotspot run with two phones is still **not measured** for the QR flow | B |
| 7 | Real-face accepted check-in timing is still **not measured** | A/B |

Gap 2 is in a B-owned file (`docker-compose.yml`) and can be fixed without touching A's
files; it is deliberately listed rather than silently patched during a documentation sync.

---

## 9. Where the old Wi-Fi work went

- Branch `wifi-backup-prepull` at `a9ca24d` holds `wifi_scanner.py`, `/wifi/*`,
  `/schedules/*`, `scapy`, the 209-test suite, D-011…D-014 evidence and demo docs as they
  were before 2026-11-24.
- `docs/B/evidence/2026-11-13-windows/` keeps the raw measurements. They remain useful as
  *validation method* evidence (locale-independent parsing, concurrency, warm-up cost) but
  **not** as evidence that the current system scans Wi-Fi.
- `DECISIONS.md` D-001…D-014 describe that earlier system; D-015 records the switch.
