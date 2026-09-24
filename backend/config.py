import os
from datetime import datetime
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

# None -> use the server's system local time. Set to an IANA name
# (e.g. "Asia/Jakarta") so schedule windows stay consistent regardless
# of the server machine's locale. Requires the 'tzdata' package on Windows.
TIMEZONE = os.getenv("TIMEZONE")

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
MAX_EMBEDDINGS_PER_STUDENT = int(os.getenv("MAX_EMBEDDINGS_PER_STUDENT", "5"))
MIN_FACE_BBOX_PX = int(os.getenv("MIN_FACE_BBOX_PX", "40"))

# Comma-separated list of allowed CORS origins. "*" (default) keeps the
# dev/teacher dashboard open; set e.g. "http://192.168.1.10:8000" in production.
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]


def now_local() -> datetime:
    """Current time in the configured timezone (system local if TIMEZONE unset).

    Returns a naive datetime so it stays comparable with HH:MM schedule
    strings and SQLite DATE() expressions.
    """
    if TIMEZONE:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo(TIMEZONE)).replace(tzinfo=None)
    return datetime.now()
