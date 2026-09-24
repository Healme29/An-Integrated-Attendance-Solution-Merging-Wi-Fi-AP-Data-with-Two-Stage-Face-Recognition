import sys
import shutil
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Must patch DATABASE_PATH before any other imports
import config
TEST_DB = Path(__file__).resolve().parent / "test_attendance.db"
config.DATABASE_PATH = TEST_DB

# Keep test artifacts (face crops, embedding pickles) out of backend/data/
TEST_DATA_DIR = Path(tempfile.mkdtemp(prefix="attendance_test_data_"))
config.DATA_DIR = TEST_DATA_DIR
config.EMBEDDINGS_DIR = TEST_DATA_DIR / "embeddings"

import pytest
import pytest_asyncio
import aiosqlite
import numpy as np
from unittest.mock import patch
from fastapi.testclient import TestClient

from main import app


async def create_test_db():
    db = await aiosqlite.connect(str(TEST_DB))
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            nim TEXT UNIQUE NOT NULL,
            mac_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS faces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            embedding BLOB NOT NULL,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT NOT NULL,
            day_of_week INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            ap_bssid TEXT,
            room TEXT
        );
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            schedule_id INTEGER NOT NULL,
            check_type TEXT NOT NULL CHECK(check_type IN ('start', 'end')),
            confidence REAL,
            wifi_verified INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (schedule_id) REFERENCES schedules(id)
        );
        CREATE TABLE IF NOT EXISTS ap_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mac_address TEXT NOT NULL,
            ip_address TEXT,
            bssid TEXT,
            ssid TEXT,
            scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    await db.commit()
    await db.close()


def _remove_test_db():
    """Delete the test DB, retrying briefly (Windows can lag on file handles)."""
    import gc
    import time
    for _ in range(10):
        try:
            if TEST_DB.exists():
                TEST_DB.unlink()
            return
        except PermissionError:
            gc.collect()
            time.sleep(0.1)


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    _remove_test_db()
    if TEST_DATA_DIR.exists():
        shutil.rmtree(TEST_DATA_DIR, ignore_errors=True)
    await create_test_db()
    yield
    _remove_test_db()
    if TEST_DATA_DIR.exists():
        shutil.rmtree(TEST_DATA_DIR, ignore_errors=True)


@pytest_asyncio.fixture
async def test_db():
    async def _get():
        db = await aiosqlite.connect(str(TEST_DB))
        db.row_factory = aiosqlite.Row
        return db
    return _get


@pytest.fixture
def client():
    return TestClient(app)


def make_fake_embedding():
    return np.random.randn(512).astype(np.float32)


@pytest.fixture
def fake_jpeg():
    """Minimal valid JPEG, so enrollment's image-decoding step works."""
    import cv2
    ok, buf = cv2.imencode(".jpg", np.zeros((32, 32, 3), dtype=np.uint8))
    assert ok
    return buf.tobytes()


@pytest.fixture(autouse=True)
def mock_face_detection():
    fake_faces = [
        {
            "bbox": (10, 10, 100, 100),
            "confidence": 0.95,
            "crop": np.zeros((100, 100, 3), dtype=np.uint8)
        }
    ]
    with patch("services.face_detection.detect_faces_from_bytes") as m1, \
         patch("routers.faces.detect_faces_from_bytes") as m2, \
         patch("services.attendance.detect_faces_from_bytes") as m3:
        m1.return_value = fake_faces
        m2.return_value = fake_faces
        m3.return_value = fake_faces
        yield m1, m2, m3


@pytest.fixture(autouse=True)
def mock_face_recognition():
    fake_emb = make_fake_embedding()
    with patch("services.face_recognition.get_embedding") as mock_emb, \
         patch("services.face_recognition.compare_faces") as mock_cmp, \
         patch("services.face_recognition.load_embeddings") as mock_load, \
         patch("routers.faces.get_embedding") as mock_rf_emb, \
         patch("routers.faces.load_embeddings") as mock_rf_load, \
         patch("services.attendance.get_embedding") as mock_sa_emb, \
         patch("services.attendance.load_embeddings") as mock_sa_load, \
         patch("services.attendance.compare_faces") as mock_sa_cmp:
        mock_emb.return_value = fake_emb
        mock_cmp.return_value = (0, 0.85)
        mock_load.return_value = [fake_emb]
        mock_rf_emb.return_value = fake_emb
        mock_rf_load.return_value = [fake_emb]
        mock_sa_emb.return_value = fake_emb
        mock_sa_load.return_value = [fake_emb]
        mock_sa_cmp.return_value = (0, 0.85)
        yield mock_emb


@pytest.fixture(autouse=True)
def mock_wifi_scanner():
    with patch("services.attendance.check_mac_on_network") as mock:
        mock.return_value = True
        yield mock


@pytest.fixture(autouse=True)
def mock_current_bssid():
    with patch("services.attendance.get_current_bssid") as mock:
        mock.return_value = "aa:bb:cc:dd:ee:ff"
        yield mock


@pytest.fixture(autouse=True)
def mock_wifi_scan_api():
    """Avoid real network scans / BSSID queries from the /wifi API in tests."""
    devices = [
        {"ip": "192.168.1.10", "mac": "aa:bb:cc:dd:ee:ff"},
        {"ip": "192.168.1.20", "mac": "11:22:33:44:55:66"},
    ]
    with patch("routers.wifi.scan_network_arp") as mock, \
         patch("routers.wifi.get_current_bssid") as mock_bssid:
        mock.return_value = devices
        mock_bssid.return_value = "aa:bb:cc:dd:ee:ff"
        yield mock


@pytest.fixture(autouse=True)
def mock_is_match():
    with patch("services.face_recognition.is_match") as m1, \
         patch("services.attendance.is_match") as m2:
        m1.return_value = True
        m2.return_value = True
        yield m1