# An Integrated Attendance Solution Merging Wi-Fi AP Data with Two-Stage Face Recognition

This project combines Wi-Fi AP connection logs and two-stage face recognition (beginning + end of class) to verify student attendance. All three conditions (correct AP, valid class time, both selfies matched) must be true for attendance to be marked.

## Features

- **Face Detection**: YOLOv8-face model for accurate face detection with landmarks
- **Face Recognition**: InsightFace ArcFace for 512-D embedding extraction and matching
- **Wi-Fi AP Verification**: Detects devices on classroom network via ARP scan
- **Two-Stage Check**: Face scan at start AND end of class
- **Mobile App**: Flutter cross-platform app (Android + iOS)

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

### Mobile

```bash
cd mobile
flutter pub get
flutter run
```

## How It Works

1. **Enrollment**: Student photos are processed through YOLOv8 (detection) + InsightFace (embedding) and stored
2. **Attendance Check**: Camera captures photo → YOLOv8 detects face → InsightFace matches against database
3. **Wi-Fi Verification**: Simultaneously checks if student's device is on the classroom network
4. **Result**: Attendance marked only if face matches AND device is on correct network

## Project Structure

```
├── backend/
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Settings & constants
│   ├── requirements.txt
│   ├── models/
│   │   ├── database.py         # SQLite schema
│   │   └── schemas.py          # Pydantic models
│   ├── services/
│   │   ├── face_detection.py   # YOLOv8 detection
│   │   ├── face_recognition.py # InsightFace recognition
│   │   ├── wifi_scanner.py     # Wi-Fi AP detection
│   │   └── attendance.py       # Attendance logic
│   ├── routers/
│   │   ├── students.py         # Student CRUD
│   │   ├── faces.py            # Face enrollment
│   │   ├── attendance.py       # Attendance endpoints
│   │   ├── schedules.py        # Class schedules
│   │   └── wifi.py             # Wi-Fi scan
│   └── data/
│       ├── models/             # YOLOv8 weights
│       └── embeddings/         # Stored face embeddings
└── mobile/
    └── lib/
        ├── main.dart
        ├── models/
        │   └── student.dart
        ├── screens/
        │   ├── home_screen.dart
        │   ├── camera_screen.dart
        │   └── attendance_screen.dart
        └── services/
            └── api_service.dart
```

## License

MIT License - see [LICENSE](LICENSE) for details.
