# An Integrated Attendance Solution Merging Wi-Fi AP Data with Two-Stage Face Recognition

This project combines Wi-Fi AP connection logs and two-stage face recognition (beginning + end of class) to verify student attendance. All three conditions (correct AP, valid class time, both selfies matched) must be true for attendance to be marked.

## Features

- **Face Detection**: YOLOv8-face model for accurate face detection with landmarks
- **Face Recognition**: InsightFace ArcFace for 512-D embedding extraction and matching
- **Wi-Fi AP Verification**: Detects devices on classroom network via ARP scan
- **Two-Stage Check**: Face scan at start AND end of class (`partial` → `verified`)
- **Mobile App**: Flutter cross-platform app (Android + iOS) with login by NIM, face enrollment, check-in, and attendance history
- **Teacher Dashboard**: Web page at `/dashboard` showing today's attendance, absent students, and CSV export
- **CSV Export**: `GET /attendance/export/csv?date=YYYY-MM-DD&schedule_id=N`

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python, FastAPI |
| Face Detection | YOLOv8 (`yolov8m-face.pt`) |
| Face Recognition | InsightFace ArcFace (`buffalo_l`) |
| Database | SQLite |
| Wi-Fi Detection | Scapy ARP scan |
| Mobile | Flutter |

## Quick Start

### Backend

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Download YOLOv8-face model
curl -L -o backend/data/models/yolov8m-face.pt https://github.com/YapaLab/yolo-face/releases/download/1.0.0/yolov8m-face.pt

# Start server
cd backend && uvicorn main:app --reload
```

API docs: `http://localhost:8000/docs`
Teacher dashboard: `http://localhost:8000/dashboard`

### Docker

```bash
# Build and start (from project root)
docker compose up -d --build

# View logs
docker compose logs -f backend
```

The InsightFace model (`buffalo_l`, ~330 MB) downloads automatically on first
startup into the `backend-data` volume, so it only happens once. If
`backend/data/models/yolov8m-face.pt` was downloaded before the build, it is
baked into the image; otherwise mount it:

```bash
docker run -v ./backend/data/models/yolov8m-face.pt:/app/data/models/yolov8m-face.pt ...
```

### Configuration (environment variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_PATH` | `backend/attendance.db` | SQLite database location |
| `DATA_DIR` | `backend/data` | Embeddings, faces, models |
| `FACE_SIMILARITY_THRESHOLD` | `0.5` | Cosine similarity threshold for a face match |
| `ATTENDANCE_CHECK_WINDOW_MINUTES` | `15` | Grace period before/after class |
| `WI_FI_SUBNET` | `192.168.1.0/24` | Network scanned for student devices |
| `YOLO_CONF_THRESHOLD` | `0.25` | Face detection confidence |

### Mobile

```bash
cd mobile
flutter pub get
flutter run
```

On first launch, log in with a student NIM. Set the backend URL in
**Settings** — `http://10.0.2.2:8000` for the Android emulator, or
`http://<school-server-ip>:8000` on a real phone.

## How It Works

1. **Enrollment**: Student photos are processed through YOLOv8 (detection) + InsightFace (embedding) and stored
2. **Attendance Check**: Camera captures photo → YOLOv8 detects face → InsightFace matches against database
3. **Wi-Fi Verification**: Simultaneously checks if student's device is on the classroom network
4. **Result**: Attendance marked only if face matches AND device is on correct network

## Project Structure

```
├── backend/
│   ├── main.py                 # FastAPI entry point + /dashboard
│   ├── config.py               # Settings (env-overridable)
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── static/
│   │   └── dashboard.html      # Teacher dashboard (vanilla JS)
│   ├── models/
│   │   ├── database.py         # SQLite schema
│   │   └── schemas.py          # Pydantic models
│   ├── services/
│   │   ├── face_detection.py   # YOLOv8 detection
│   │   ├── face_recognition.py # InsightFace recognition
│   │   ├── wifi_scanner.py     # Wi-Fi AP detection
│   │   └── attendance.py       # Two-stage attendance logic
│   ├── routers/
│   │   ├── students.py         # Student CRUD + NIM lookup
│   │   ├── faces.py            # Face enrollment
│   │   ├── attendance.py       # Check-in, today, history, CSV export
│   │   ├── schedules.py        # Class schedules (CRUD + validation)
│   │   └── wifi.py             # Wi-Fi scan
│   ├── tests/                  # 71 pytest tests
│   └── data/
│       ├── models/             # YOLOv8 weights
│       ├── embeddings/         # Stored face embeddings
│       └── faces/              # Enrolled face images
├── docker-compose.yml
└── mobile/
    └── lib/
        ├── main.dart           # Login-state routing
        ├── models/
        │   └── student.dart
        ├── screens/
        │   ├── login_screen.dart
        │   ├── home_screen.dart
        │   ├── camera_screen.dart
        │   ├── enroll_screen.dart
        │   ├── history_screen.dart
        │   ├── settings_screen.dart
        │   └── attendance_screen.dart
        └── services/
            ├── api_service.dart
            └── session_service.dart
```

## License

MIT License - see [LICENSE](LICENSE) for details.
