# COMPLETE PROJECT CONTEXT — AI TEAM PROMPT

## 1. PROJECT OVERVIEW

**Project:** An Integrated Attendance Solution Merging Wi-Fi AP Data with Two-Stage Face Recognition

**Objective:** Build an automated attendance system for schools. Students simply come to class, take a selfie at the beginning and end of the lesson, and the system automatically records attendance — with verification that they are actually in the room (Wi-Fi) and their face matches (face recognition).

**Three Attendance Requirements:** Attendance is only granted if ALL of these conditions are met:
1. **Wi-Fi AP:** The student's device MAC address is detected on the class network (correct Access Point)
2. **Time:** Check-in is within valid class schedule hours (±15 minute grace period)
3. **Two Selfies:** Face matches in BOTH the START AND END selfie of class (two-stage verification)

---

## 2. TECH STACK

| Layer | Technology | Version |
|-------|------------|---------|
| **Backend** | Python + FastAPI | 0.115.0 |
| **Server** | Uvicorn | 0.30.6 |
| **Database** | SQLite (async via aiosqlite) | 0.20.0 |
| **Face Detection** | Ultralytics YOLOv8 (`yolov8m-face.pt`) | 8.2.100 |
| **Face Recognition** | InsightFace ArcFace (`buffalo_l`) | >=2.0 |
| **Runtime ML** | ONNX Runtime | 1.18.1 |
| **Wi-Fi Scan (Win)** | `arp -a` command | - |
| **Wi-Fi Scan (Linux)** | Scapy ARP (`srp()`) | 2.5.0 |
| **Mobile Frontend** | Flutter (Android + iOS) | >=3.0.0 |
| **HTTP Client** | `http` package | ^1.2.2 |
| **Camera** | `camera` package | ^0.11.0+2 |
| **Testing** | pytest + pytest-asyncio + httpx | latest |

---

## 3. DIRECTORY STRUCTURE (COMPLETE)

```
project-root/
├── AGENTS.md                           # AI coding assistant guide
├── README.md                           # Project documentation
├── LICENSE                             # MIT License
├── next_steps.txt                      # 6-week action plan
├── progress_report.txt                 # Readiness assessment (~5%)
│
├── docs/                               # Task documentation
│   ├── TASK_A_LEAD.md                  # Task A — Face Recognition Pipeline
│   ├── TASK_B.md                       # Task B — Attendance Orchestrator
│   ├── TASK_C.md                       # Task C — Flutter Mobile App
│   ├── TASK_D.md                       # Task D — Wi-Fi + Testing
│   └── PROMPT_AI_TEAM.md              # This file — complete context
│
├── backend/                            # FastAPI Backend
│   ├── main.py                         # Entry point, CORS, router registration
│   ├── config.py                       # All configuration (paths, thresholds, timeouts)
│   ├── requirements.txt                # Python dependencies
│   ├── attendance.db                   # SQLite database (auto-created)
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py                 # Async SQLite: get_db(), init_db(), 5 tables
│   │   └── schemas.py                  # Pydantic models: Student, Face, Attendance, Schedule, WiFi
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── face_detection.py           # YOLOv8-face: detect_faces(), detect_faces_from_bytes()
│   │   ├── face_recognition.py         # InsightFace: get_embedding(), compare_faces(), is_match(), save/load
│   │   ├── wifi_scanner.py             # ARP scan: scan_network_arp(), check_mac_on_network(), log_ap_access()
│   │   └── attendance.py               # Orchestrator: get_schedules_for_now(), recognize_face(), mark_attendance()
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── students.py                 # CRUD /students/
│   │   ├── faces.py                    # POST /faces/enroll, /faces/recognize
│   │   ├── attendance.py               # POST /attendance/check, GET /today, /student/{id}
│   │   ├── schedules.py                # CRUD /schedules/
│   │   └── wifi.py                     # GET /wifi/scan, /wifi/check/{mac}
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   └── helpers.py                  # ensure_dir(), image_bytes_to_array()
│   │
│   ├── data/
│   │   ├── models/
│   │   │   └── yolov8m-face.pt        # ~50MB — download from YapaLab/yolo-face releases
│   │   └── embeddings/
│   │       └── student_1.pkl           # Pickled face embeddings per student
│   │
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py                 # Test fixtures: DB, mocks (face, recognition, wifi)
│       ├── test_services.py            # Unit tests for services
│       ├── test_routers.py             # Integration tests for API endpoints
│       └── test_attendance_scenarios.py # Scenario-based: perfect, mismatch, wrong room, late
│
└── mobile/                             # Flutter App
    ├── pubspec.yaml                    # Dependencies: http, camera, path_provider, shared_preferences, intl
    │
    └── lib/
        ├── main.dart                   # Entry point, MaterialApp, theme
        ├── models/
        │   └── student.dart            # Student model, AttendanceResult model
        ├── screens/
        │   ├── home_screen.dart         # Main: schedule dropdown, check-type toggle, camera button
        │   ├── camera_screen.dart       # Camera preview, capture, upload to API
        │   └── attendance_screen.dart   # Result: success/failure icon, name, confidence
        └── services/
            └── api_service.dart         # HTTP client: getStudents, createStudent, checkAttendance, scanWifi, getSchedules
```

---

## 4. DATABASE SCHEMA (5 TABLES)

```sql
-- Table: students
-- Stores student data
CREATE TABLE students (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,              -- Full name
    nim             TEXT UNIQUE NOT NULL,        -- Student ID Number
    mac_address     TEXT,                       -- Device MAC address (for Wi-Fi check)
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: faces
-- Stores face data (embedding vector + image path)
CREATE TABLE faces (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER NOT NULL,           -- FK → students.id
    embedding       BLOB NOT NULL,              -- Pickled list of numpy arrays (512-D)
    image_path      TEXT,                       -- Path to image file on disk
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- Table: schedules
-- Class schedules
CREATE TABLE schedules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    class_name      TEXT NOT NULL,              -- Class name (e.g., "Math 101")
    day_of_week     INTEGER NOT NULL,           -- 0=Monday, 6=Sunday
    start_time      TEXT NOT NULL,              -- "HH:MM" format
    end_time        TEXT NOT NULL,              -- "HH:MM" format
    ap_bssid        TEXT,                       -- Class Access Point BSSID
    room            TEXT                        -- Room name
);

-- Table: attendance
-- Attendance records
CREATE TABLE attendance (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER NOT NULL,           -- FK → students.id
    schedule_id     INTEGER NOT NULL,           -- FK → schedules.id
    check_type      TEXT NOT NULL CHECK(check_type IN ('start', 'end')),
    confidence      REAL,                       -- Face match score (0.0 - 1.0)
    wifi_verified   INTEGER DEFAULT 0,          -- 0=false, 1=true
    status          TEXT NOT NULL DEFAULT 'pending', -- pending | present | face_only | partial | verified
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (schedule_id) REFERENCES schedules(id)
);

-- Table: ap_logs
-- Wi-Fi scan logs
CREATE TABLE ap_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    mac_address     TEXT NOT NULL,
    ip_address      TEXT,
    bssid           TEXT,
    ssid            TEXT,
    scan_time       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Status Values
| Status | Meaning |
|--------|---------|
| `pending` | Default — not yet processed |
| `present` | Face match + Wi-Fi verified (single check, legacy) |
| `face_only` | Face match OK, but Wi-Fi not verified |
| `partial` | Only "start" check-in (waiting for "end") |
| `verified` | "start" AND "end" complete → attendance VALID |

---

## 5. API ENDPOINTS (COMPLETE — 15 Endpoints)

### Students
| Method | Path | Description | Request | Response |
|--------|------|-------------|---------|----------|
| GET | `/students/` | List all (optional filter `?nim=`) | - | `[StudentResponse]` |
| POST | `/students/` | Create student | `{name, nim, mac_address?}` | `StudentResponse` |
| GET | `/students/{id}` | Get by ID | - | `StudentResponse` |
| DELETE | `/students/{id}` | Delete student | - | `{message}` |
| PUT | `/students/{id}/mac` | Update MAC | `?mac_address=` | `{message}` |

### Faces
| Method | Path | Description | Request | Response |
|--------|------|-------------|---------|----------|
| POST | `/faces/enroll?student_id=` | Enroll face | Multipart: `file` (image) | `{message, student_id, face_count}` |
| POST | `/faces/recognize` | Recognize face | Multipart: `file` (image) | `{recognized, student_id?, student_name?, confidence}` |

### Attendance
| Method | Path | Description | Request | Response |
|--------|------|-------------|---------|----------|
| POST | `/attendance/check?schedule_id=&check_type=` | Check attendance | Multipart: `file` (selfie) | `AttendanceResponse` |
| GET | `/attendance/today` | Today's records | - | `[AttendanceResponse]` |
| GET | `/attendance/student/{id}` | Student history | - | `[{..., class_name, room}]` |

### Schedules
| Method | Path | Description | Request | Response |
|--------|------|-------------|---------|----------|
| GET | `/schedules/` | List all | - | `[ScheduleResponse]` |
| POST | `/schedules/` | Create | `ScheduleCreate` | `ScheduleResponse` |
| DELETE | `/schedules/{id}` | Delete | - | `{message}` |

### Wi-Fi
| Method | Path | Description | Request | Response |
|--------|------|-------------|---------|----------|
| GET | `/wifi/scan` | Scan network | `?subnet=` | `{devices, subnet, count, timestamp}` |
| GET | `/wifi/check/{mac}` | Check MAC | - | `{mac_address, on_network}` |

---

## 6. PYDANTIC SCHEMAS (Data Contract)

```python
class StudentCreate(BaseModel):
    name: str
    nim: str
    mac_address: Optional[str] = None

class StudentResponse(BaseModel):
    id: int
    name: str
    nim: str
    mac_address: Optional[str]
    created_at: datetime

class FaceEnrollResponse(BaseModel):
    message: str
    student_id: int
    face_count: int

class AttendanceResponse(BaseModel):
    id: int
    student_id: int
    schedule_id: int
    check_type: str
    confidence: Optional[float]
    wifi_verified: bool
    status: str
    timestamp: datetime

class RecognizeResponse(BaseModel):
    recognized: bool
    student_id: Optional[int] = None
    student_name: Optional[str] = None
    confidence: float = 0.0

class ScheduleCreate(BaseModel):
    class_name: str
    day_of_week: int  # 0-6
    start_time: str  # "HH:MM"
    end_time: str    # "HH:MM"
    ap_bssid: Optional[str] = None
    room: Optional[str] = None

class ScheduleResponse(BaseModel):
    id: int
    class_name: str
    day_of_week: int
    start_time: str
    end_time: str
    ap_bssid: Optional[str]
    room: Optional[str]

class WifiDevice(BaseModel):
    ip: str
    mac: str

class WifiScanResponse(BaseModel):
    devices: list[WifiDevice]
    subnet: str
    timestamp: datetime
```

---

## 7. KNOWN BUGS & BLOCKERS (Priority 1)

### Blocker #1 — Face Enrollment Data Saving (0% readiness)
- **Location:** `backend/routers/faces.py:42`
- **Bug:** `(student_id, b"blob", ...)` stores the literal string `b"blob"` instead of the actual binary embedding
- **Fix:** Store pickle bytes from the embeddings list, save the original image file to disk

### Blocker #2 — Two-Stage Attendance Logic (0% readiness)
- **Location:** `backend/services/attendance.py`
- **Bug:** Each selfie is recorded independently, no relationship between "start" and "end" check-ins
- **Fix:** Implement pairing: start → status "partial"; end + found start → both records become "verified"

### Blocker #3 — Schedule Time Enforcement (0% readiness)
- **Location:** `backend/routers/attendance.py`
- **Bug:** No time validation. Students can check in at any time
- **Fix:** Call `get_schedules_for_now()` in the router and reject if the schedule is not active

### Blocker #4 — Mobile-Backend Data Contract Mismatch (0% readiness)
- **Location:** `mobile/lib/models/student.dart` + `mobile/lib/screens/camera_screen.dart`
- **Bug:** Flutter uses `AttendanceResult` (compatible with `/faces/recognize`) but calls `/attendance/check` which returns a different format
- **Fix:** Create `AttendanceCheckResponse` model that matches the backend response

---

## 8. CURRENT READINESS ASSESSMENT

| Requirement | Readiness | Notes |
|-------------|-----------|-------|
| Face enrollment saves data | **0%** | Image bytes never saved to disk. Embedding stored incorrectly |
| Two-stage attendance logic | **0%** | Start and end selfies are independent |
| Schedule time enforcement | **0%** | Can check in at any time |
| Mobile data contract | **0%** | Flutter expects different format |
| Student self-enrollment app | **0%** | No enroll screen in mobile |
| Teacher dashboard | **0%** | No web interface |
| Login/authentication | **0%** | No login system |
| Real device testing | **0%** | Only mocked tests |
| Wi-Fi scanning on campus | **10%** | Code exists but untested on real network |
| Database schema | **100%** | All 5 tables with proper constraints |
| API endpoint definitions | **100%** | 15 endpoints defined |
| Face detection & recognition code | **90%** | Code exists, needs bug fixes |
| Wi-Fi scanner logic | **80%** | Code exists, needs improvements |
| Flutter app screens | **70%** | Basic UI exists, needs connection |
| Unit tests | **80%** | 33+ tests with mocks |
| **OVERALL SCHOOL READINESS** | **~5%** | |

---

## 9. FACE RECOGNITION PIPELINE DETAILS

### YOLOv8-face (`yolov8m-face.pt`)
- **Model source:** YapaLab/yolo-face (GitHub releases)
- **File size:** ~50 MB
- **Conf threshold:** 0.25 (configurable in `config.py`)
- **Image size:** 1280 px (configurable)
- **Output:** bounding boxes (xyxy), confidence, optional landmarks
- **Format:** Ultralytics YOLO model, standard API

### InsightFace ArcFace (`buffalo_l`)
- **Model source:** Auto-downloaded by InsightFace on first use
- **Provider:** CPUExecutionProvider (ONNX Runtime)
- **Detection size:** 640×640 px
- **Embedding dimension:** 512-D float32 vector
- **Similarity metric:** Cosine similarity (sklearn)
- **Threshold:** 0.5 (must be tuned with real data)
- **Note:** `FaceAnalysis.get()` requires the full image (not a crop) — see bug in Blocker #2

---

## 10. WI-FI SCANNER DETAILS

### Windows (`arp -a`)
- Run `arp -a` via subprocess
- Parse output with regex: `(\d+\.\d+\.\d+\.\d+)\s+([\w-]{17})`
- Issue: ARP cache may be stale → need ping sweep first
- Npcap not required for `arp -a` (only for Scapy on Windows)

### Linux (Scapy)
- `ARP(pdst=subnet)` + `Ether(dst="ff:ff:ff:ff:ff:ff")` + `srp()`
- Requires Scapy installed: `pip install scapy`
- Requires root access / `sudo` for raw socket

### MAC Address Format
All MACs must be normalized: lowercase, `-` replaced with `:`.
- Input: `AA-BB-CC-DD-EE-FF` or `aa:bb:cc:dd:ee:ff`
- Normalized: `aa:bb:cc:dd:ee:ff`

---

## 11. CONFIGURATION (`backend/config.py`)

```python
# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = DATA_DIR / "models"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
DATABASE_PATH = BASE_DIR / "attendance.db"

# YOLOv8
YOLO_MODEL_PATH = MODELS_DIR / "yolov8m-face.pt"
YOLO_CONF_THRESHOLD = 0.25
YOLO_IMG_SIZE = 1280

# InsightFace
INSIGHTFACE_MODEL = "buffalo_l"
FACE_SIMILARITY_THRESHOLD = 0.5

# Wi-Fi
WI_FI_SCAN_TIMEOUT = 3        # seconds
WI_FI_SUBNET = "192.168.1.0/24"

# Attendance
ATTENDANCE_CHECK_WINDOW_MINUTES = 15
```

---

## 12. COMPLETE DEPENDENCIES

### Python (`requirements.txt`)
```
fastapi==0.115.0
uvicorn[standard]==0.30.6
ultralytics==8.2.100
insightface>=2.0
onnxruntime==1.18.1
opencv-python==4.10.0.84
numpy==1.26.4
scikit-learn==1.5.1
scapy==2.5.0
pydantic==2.9.2
python-multipart==0.0.12
aiosqlite==0.20.0
Pillow==10.4.0
# Testing
pytest==8.3.3
pytest-asyncio==0.24.0
httpx==0.27.2
```

### Flutter (`pubspec.yaml`)
```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.2.2
  camera: ^0.11.0+2
  path_provider: ^2.1.4
  shared_preferences: ^2.3.2
  intl: ^0.19.0
```

---

## 13. TESTING INFRASTRUCTURE

### Mock Strategy (in `conftest.py`)
- `mock_face_detection`: Return fake face list `{bbox, confidence, crop}` — patches all `detect_faces_from_bytes()` functions
- `mock_face_recognition`: Return fake embedding (random 512-D) + fake comparison (index 0, score 0.85) — patches `get_embedding`, `compare_faces`, `load_embeddings`
- `mock_wifi_scanner`: Return `True` for `check_mac_on_network()`
- `mock_is_match`: Return `True` for `is_match()`
- Test DB: Redirect to temporary file `test_attendance.db`, auto-cleanup per test

### Test Files
| File | Tests | Focus |
|------|-------|-------|
| `test_services.py` | 12 tests | Unit: face detection, face recognition, Wi-Fi, attendance |
| `test_routers.py` | 18 tests | Integration: all API endpoints |
| `test_attendance_scenarios.py` | 5 tests | Scenario: perfect, mismatch, missing second, wrong room, late |

### Run Tests
```bash
cd backend
pytest -v
# With coverage:
pytest --cov=. --cov-report=term
```

---

## 14. CURRENT DATA FLOW (As Is)

```
User uploads image (selfie)
    ↓
POST /attendance/check (FastAPI Router)
    ↓
recognize_face(image_bytes)
    ↓
detect_faces_from_bytes() → [{bbox, confidence, crop}]
    ↓
get_embedding(best_face_crop)  ← BUG: needs full image, not crop
    ↓
compare_faces(embedding, all_students_embeddings) → (best_idx, score)
    ↓
is_match(score) → bool
    ↓
mark_attendance(student_id, schedule_id, check_type, confidence)
    ↓
check_mac_on_network(student.mac_address) → bool
    ↓
INSERT INTO attendance (...) → status = "present" or "face_only"
```

---

## 15. TARGET DATA FLOW (Desired State)

```
Student opens app → login with NIM
    ↓
Select schedule → select check_type (START)
    ↓
Take selfie
    ↓
POST /attendance/check?schedule_id=X&check_type=start
    ↓
Time validation: Is the current time within schedule? (grace ±15 min)
    ↓
detect_faces(full_image) → best face
    ↓
get_embedding(full_image, bbox) → 512-D vector
    ↓
compare_faces(embedding, all_embeddings) → match
    ↓
Check existing: Is there already a "start" for this student+schedule?
    → If YES → reject (duplicate)
    → If NO → proceed
    ↓
check_mac_on_network(student.mac_address)
    ↓
INSERT attendance (check_type="start", status="partial")
    ↓
Response: {status: "partial", wifi_verified: bool, ...}
    ↓
[Student attends class...]
    ↓
Take SECOND selfie (END)
    ↓
POST /attendance/check?schedule_id=X&check_type=end
    ↓
[Same: time validation → detection → recognition → duplicate check]
    ↓
Find existing "start" record for the SAME student+schedule
    → If FOUND → update "start" and "end" to status="verified"
    → If NOT FOUND → reject "Must check in at start of class first"
    ↓
Response: {status: "verified", wifi_verified: bool, ...}
```

---

## 16. TIMELINE & TARGET

| Week | Target | Owner |
|------|--------|-------|
| **Week 1** | Fix all Priority 1 Blockers (#1-#4) | A+B+C+D |
| **Week 1** | Threshold tuning face recognition | A |
| **Week 1** | Two-stage logic + schedule enforcement | B |
| **Week 1** | Fix data contract + error handling | C |
| **Week 1** | Wi-Fi scanner improvements + update tests | D |
| **Week 2** | Login + enroll screens (Flutter) | C |
| **Week 2** | Comprehensive testing scenarios | D |
| **Week 2** | Integration testing end-to-end | A (lead) |
| **Target:** | **End-to-end testable via Swagger UI + Android phone** | **All** |

---

## 17. IMPORTANT: COMMON PITFALLS

1. **Don't edit other people's files without coordination** — always coordinate with the file owner.
2. **Don't commit directly to `main`** — create your own branches: `task-a`, `task-b`, `task-c`, `task-d`.
3. **Pull requests must be reviewed by A (lead)** before merging.
4. **All changes must pass tests** — run `pytest -v` before committing.
5. **Don't push large files** — `yolov8m-face.pt` (50 MB) must not be in git. Already in `.gitignore`.
6. **Backup database** — `attendance.db` may contain test data. Don't commit.
7. **If stuck for >30 minutes** — ask in the group. Don't stay silent.

---

## 18. BASIC COMMANDS

```bash
# Setup backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload                         # Run server
pytest -v                                         # Run tests
pytest --cov=. --cov-report=term                   # Test with coverage

# Setup mobile
cd mobile
flutter pub get                                    # Install dependencies
flutter run                                        # Run on connected device

# Download model (if needed)
curl -L -o backend/data/models/yolov8m-face.pt https://github.com/YapaLab/yolo-face/releases/download/1.0.0/yolov8m-face.pt

# API docs (after server is running)
open http://localhost:8000/docs                    # Swagger UI
open http://localhost:8000/redoc                   # ReDoc
```