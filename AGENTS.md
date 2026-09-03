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

Flutter setup:
```bash
cd mobile && flutter pub get && flutter run
```

## Key Facts

- YOLOv8-face model: `yolov8m-face.pt` (50 MB) — download from `github.com/YapaLab/yolo-face/releases`
- InsightFace model: `buffalo_l` (auto-downloaded on first use)
- Attendance requires ALL 3 conditions: correct AP + valid class time + face match
- Two-stage check: selfie at start AND end of class
- Wi-Fi detection requires Npcap on Windows (WinPcap API-compatible mode)
- Cosine similarity threshold: 0.5 (adjust based on testing)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/students/` | List all students |
| POST | `/students/` | Create student (name, nim, mac_address) |
| GET | `/students/{id}` | Get student by ID |
| DELETE | `/students/{id}` | Delete student |
| PUT | `/students/{id}/mac` | Update MAC address |
| POST | `/faces/enroll?student_id=` | Enroll face (upload image) |
| POST | `/faces/recognize` | Recognize face (upload image) |
| POST | `/attendance/check?schedule_id=&check_type=` | Check attendance with face scan |
| GET | `/attendance/today` | Get today's attendance |
| GET | `/attendance/student/{id}` | Get student attendance history |
| GET | `/schedules/` | List schedules |
| POST | `/schedules/` | Create schedule |
| DELETE | `/schedules/{id}` | Delete schedule |
| GET | `/wifi/scan` | Scan network devices |
| GET | `/wifi/check/{mac}` | Check if MAC is on network |

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
   cd backend && uvicorn main:app --reload
   ```

4. API docs available at: `http://localhost:8000/docs`

5. Flutter mobile:
   ```bash
   cd mobile && flutter pub get && flutter run
   ```
