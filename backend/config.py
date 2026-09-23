import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
MODELS_DIR = DATA_DIR / "models"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "attendance.db"))

YOLO_MODEL_PATH = MODELS_DIR / "yolov8m-face.pt"
YOLO_CONF_THRESHOLD = float(os.getenv("YOLO_CONF_THRESHOLD", "0.25"))
YOLO_IMG_SIZE = int(os.getenv("YOLO_IMG_SIZE", "1280"))

INSIGHTFACE_MODEL = os.getenv("INSIGHTFACE_MODEL", "buffalo_l")
FACE_SIMILARITY_THRESHOLD = float(os.getenv("FACE_SIMILARITY_THRESHOLD", "0.5"))

WI_FI_SCAN_TIMEOUT = int(os.getenv("WI_FI_SCAN_TIMEOUT", "3"))
WI_FI_SUBNET = os.getenv("WI_FI_SUBNET")  # None -> auto-detect local subnet at scan time

ATTENDANCE_CHECK_WINDOW_MINUTES = int(os.getenv("ATTENDANCE_CHECK_WINDOW_MINUTES", "15"))
