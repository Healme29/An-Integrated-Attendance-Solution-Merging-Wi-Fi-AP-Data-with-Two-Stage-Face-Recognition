# AGENTS.md

## Project

Integrated attendance system combining Wi-Fi AP connection logs with two-stage face recognition (start + end of class). Attendance is granted only when all three conditions are met: correct AP, valid class time, and both selfies matched.

## Architecture

- **Backend**: Python (FastAPI) — face detection, recognition, Wi-Fi AP check, attendance logic
- **Frontend**: Flutter mobile app (Android + iOS) — camera capture, status display
- **Database**: SQLite — students, faces, attendance, schedules, AP logs
- **Face Detection**: YOLOv8 (`yolov8m-face.pt` from `akanametov/yolo-face`)
- **Face Recognition**: InsightFace ArcFace (`buffalo_l`) — 512-D embeddings, cosine similarity threshold ~0.5
- **Wi-Fi AP**: Scapy ARP scan or router DHCP/ARP query — detect devices on classroom network

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
- Attendance requires ALL 3 conditions: correct AP + valid class time + both selfies matched
- Two-stage status flow: `start` → `partial`, `end` → `verified` (Wi-Fi ok) or `face_only` (no Wi-Fi); start row finalized on end check-in
- Duplicate check-ins rejected (409); `end` without prior `start` rejected (409)
- Attendance outside class window ± grace → 403; wrong day → 403; unknown schedule → 404
- `get_embedding(image, bbox)` expects the FULL image + YOLO bbox (crops with margin internally)
- Wi-Fi detection requires Npcap on Windows (WinPcap API-compatible mode)
- Cosine similarity threshold: 0.5 (env `FACE_SIMILARITY_THRESHOLD`)
- Config is env-overridable: `DATABASE_PATH`, `DATA_DIR`, `WI_FI_SUBNET`, `ATTENDANCE_CHECK_WINDOW_MINUTES`, `YOLO_CONF_THRESHOLD`, `YOLO_IMG_SIZE`, `INSIGHTFACE_MODEL`
- `WI_FI_SUBNET` unset → subnet auto-detected from the machine's primary interface at scan time

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/students/?nim=` | List students, or look up one by NIM (login) |
| POST | `/students/` | Create student (name, nim, mac_address) |
| GET | `/students/{id}` | Get student by ID |
| DELETE | `/students/{id}` | Delete student |
| PUT | `/students/{id}/mac` | Update MAC address |
| POST | `/faces/enroll?student_id=` | Enroll face (upload image) |
| POST | `/faces/recognize` | Recognize face (upload image) |
| POST | `/attendance/check?schedule_id=&check_type=` | Check attendance with face scan (time-enforced) |
| GET | `/attendance/today?schedule_id=` | Today's attendance (joined names, optional filter) |
| GET | `/attendance/student/{id}` | Get student attendance history |
| GET | `/attendance/export/csv?date=&schedule_id=` | Export attendance as CSV |
| GET | `/schedules/` | List schedules |
| POST | `/schedules/` | Create schedule (validated) |
| GET | `/schedules/{id}` | Get schedule by ID |
| PUT | `/schedules/{id}` | Update schedule (validated) |
| DELETE | `/schedules/{id}` | Delete schedule |
| GET | `/wifi/scan` | Scan network devices |
| GET | `/wifi/check/{mac}` | Check if MAC is on network |
| GET | `/dashboard` | Teacher web dashboard (HTML) |

## Database Schema

- **students**: id, name, nim, mac_address, created_at
- **faces**: id, student_id, embedding, image_path, created_at
- **schedules**: id, class_name, day_of_week, start_time, end_time, ap_bssid, room
- **attendance**: id, student_id, schedule_id, check_type, confidence, wifi_verified, status, timestamp
- **ap_logs**: id, mac_address, ip_address, bssid, ssid, scan_time

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
