import asyncio
import io
import pickle
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

import services.wifi_scanner as wifi_scanner
import services.face_recognition as face_recognition_module
from main import app
from config import now_local
from services.attendance import mark_attendance

# Conftest autouse fixtures patch these names during tests; capture the real
# implementations at collection time for the robustness tests below.
real_load_embeddings = face_recognition_module.load_embeddings
real_compare_faces = face_recognition_module.compare_faces
real_l2_normalize = face_recognition_module._l2_normalize


@pytest.fixture
def client():
    return TestClient(app)


async def seed_student_and_schedule(test_db, ap_bssid=None):
    db = await test_db()
    await db.execute(
        "INSERT INTO students (id, name, nim, mac_address) VALUES (?, ?, ?, ?)",
        (1, "Alice", "12345", "aa:bb:cc:dd:ee:ff")
    )
    await db.execute(
        "INSERT INTO schedules (id, class_name, day_of_week, start_time, end_time, ap_bssid, room)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (1, "Math", datetime.now().weekday(), "00:00", "23:59", ap_bssid, "Room 201")
    )
    await db.commit()
    await db.close()


class TestHealthEndpoint:
    def test_health_ok(self, client, setup_test_db):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "ok"

    def test_health_db_failure(self, client, setup_test_db):
        with patch("models.database.get_db", side_effect=OSError("db gone")):
            response = client.get("/health")
        assert response.status_code == 503
        assert response.json()["status"] == "error"


class TestTimezone:
    def test_now_local_system_default(self):
        before = datetime.now()
        value = now_local()
        after = datetime.now()
        assert before <= value <= after
        assert value.tzinfo is None

    def test_now_local_configured_timezone(self):
        import config
        original = config.TIMEZONE
        try:
            config.TIMEZONE = "Asia/Jakarta"
            value = now_local()
            utc_now = datetime.now(timezone.utc).replace(tzinfo=None)
            assert value.tzinfo is None
            assert abs((value - (utc_now + timedelta(hours=7))).total_seconds()) < 5
        finally:
            config.TIMEZONE = original

    def test_now_local_invalid_timezone_raises(self):
        import config
        original = config.TIMEZONE
        try:
            config.TIMEZONE = "Not/AZone"
            with pytest.raises(Exception):
                now_local()
        finally:
            config.TIMEZONE = original


class TestWifiScanApi:
    def test_scan_uses_resolved_subnet(self, client, setup_test_db):
        response = client.get("/wifi/scan")
        assert response.status_code == 200
        data = response.json()
        assert data["subnet"] == wifi_scanner.resolve_subnet()
        assert data["count"] == 2

    def test_scan_explicit_subnet_wins(self, client, setup_test_db):
        response = client.get("/wifi/scan?subnet=10.0.0.0/24")
        assert response.status_code == 200
        assert response.json()["subnet"] == "10.0.0.0/24"

    def test_scan_populates_ap_logs_with_dedupe(self, client, setup_test_db, test_db):
        client.get("/wifi/scan")
        client.get("/wifi/scan")

        async def _rows():
            db = await test_db()
            cursor = await db.execute("SELECT mac_address, ip_address FROM ap_logs")
            rows = await cursor.fetchall()
            await db.close()
            return [dict(r) for r in rows]

        rows = asyncio.run(_rows())
        assert len(rows) == 2
        assert {r["mac_address"] for r in rows} == {"aa:bb:cc:dd:ee:ff", "11:22:33:44:55:66"}

    def test_check_mac_logs_access(self, client, setup_test_db, test_db):
        response = client.get("/wifi/check/AA-BB-CC-DD-EE-FF")
        assert response.status_code == 200
        assert response.json()["on_network"] is True

        async def _rows():
            db = await test_db()
            cursor = await db.execute("SELECT mac_address, ip_address FROM ap_logs")
            rows = await cursor.fetchall()
            await db.close()
            return [dict(r) for r in rows]

        rows = asyncio.run(_rows())
        assert len(rows) == 1
        assert rows[0]["mac_address"] == "aa:bb:cc:dd:ee:ff"
        assert rows[0]["ip_address"] == "192.168.1.10"

    def test_check_mac_not_found_no_log(self, client, setup_test_db, test_db):
        response = client.get("/wifi/check/ff:ee:dd:cc:bb:aa")
        assert response.status_code == 200
        assert response.json()["on_network"] is False

        async def _count():
            db = await test_db()
            cursor = await db.execute("SELECT COUNT(*) FROM ap_logs")
            value = (await cursor.fetchone())[0]
            await db.close()
            return value

        assert asyncio.run(_count()) == 0


class TestEnrollHardening:
    def test_oversized_upload_rejected(self, client, setup_test_db, fake_jpeg):
        client.post("/students/", json={"name": "Alice", "nim": "12345"})
        with patch("routers.faces.MAX_UPLOAD_BYTES", 64):
            response = client.post(
                "/faces/enroll?student_id=1",
                files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")}
            )
        assert response.status_code == 413

    def test_unsupported_format_rejected(self, client, setup_test_db):
        client.post("/students/", json={"name": "Alice", "nim": "12345"})
        response = client.post(
            "/faces/enroll?student_id=1",
            files={"file": ("selfie.gif", b"GIF89a" + b"x" * 32, "image/gif")}
        )
        assert response.status_code == 400
        assert "Unsupported image format" in response.json()["detail"]

    def test_valid_jpeg_magic_accepted(self, client, setup_test_db, fake_jpeg):
        client.post("/students/", json={"name": "Alice", "nim": "12345"})
        response = client.post(
            "/faces/enroll?student_id=1",
            files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")}
        )
        assert response.status_code == 200

    def test_tiny_face_rejected(self, client, setup_test_db, fake_jpeg, mock_face_detection):
        m1, m2, m3 = mock_face_detection
        tiny = [{"bbox": (10, 10, 30, 30), "confidence": 0.9, "crop": None}]
        m2.return_value = tiny
        client.post("/students/", json={"name": "Alice", "nim": "12345"})

        response = client.post(
            "/faces/enroll?student_id=1",
            files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")}
        )
        assert response.status_code == 400
        assert "too small" in response.json()["detail"]

    def test_max_embeddings_limit(self, client, setup_test_db, fake_jpeg):
        client.post("/students/", json={"name": "Alice", "nim": "12345"})
        full = [np.random.randn(512).astype(np.float32) for _ in range(5)]
        with patch("routers.faces.load_embeddings", return_value=full):
            response = client.post(
                "/faces/enroll?student_id=1",
                files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")}
            )
        assert response.status_code == 400
        assert "limit" in response.json()["detail"]

    def test_enroll_response_reports_counts(self, client, setup_test_db, fake_jpeg):
        client.post("/students/", json={"name": "Alice", "nim": "12345"})
        response = client.post(
            "/faces/enroll?student_id=1",
            files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["faces_detected"] == 1
        assert data["face_count"] == 1
        assert data["total_embeddings"] >= 1


class TestScheduleOverlap:
    def _payload(self, **overrides):
        payload = {
            "class_name": "Math",
            "day_of_week": 0,
            "start_time": "08:00",
            "end_time": "09:30",
            "room": "Room 201",
        }
        payload.update(overrides)
        return payload

    def test_overlapping_same_room_rejected(self, client, setup_test_db):
        client.post("/schedules/", json=self._payload())
        response = client.post("/schedules/", json=self._payload(class_name="Physics"))
        assert response.status_code == 409
        assert "conflicts" in response.json()["detail"]

    def test_overlapping_different_room_allowed(self, client, setup_test_db):
        client.post("/schedules/", json=self._payload())
        response = client.post("/schedules/", json=self._payload(class_name="Physics", room="Room 202"))
        assert response.status_code == 200

    def test_adjacent_slot_same_room_allowed(self, client, setup_test_db):
        client.post("/schedules/", json=self._payload())
        response = client.post("/schedules/", json=self._payload(
            class_name="Physics", start_time="09:30", end_time="11:00"
        ))
        assert response.status_code == 200

    def test_overlapping_other_day_allowed(self, client, setup_test_db):
        client.post("/schedules/", json=self._payload())
        response = client.post("/schedules/", json=self._payload(class_name="Physics", day_of_week=2))
        assert response.status_code == 200

    def test_update_excludes_itself(self, client, setup_test_db):
        client.post("/schedules/", json=self._payload())
        response = client.put("/schedules/1", json=self._payload(
            class_name="Math Advanced", start_time="08:30", end_time="10:00"
        ))
        assert response.status_code == 200
        assert response.json()["start_time"] == "08:30"

    def test_update_conflicts_with_other_schedule(self, client, setup_test_db):
        client.post("/schedules/", json=self._payload())
        response = client.post("/schedules/", json=self._payload(
            class_name="Physics", room="Room 202", start_time="11:00", end_time="12:00"
        ))
        assert response.status_code == 200
        response = client.put("/schedules/2", json=self._payload(
            class_name="Physics", room="Room 201", start_time="09:00", end_time="10:00"
        ))
        assert response.status_code == 409

    def test_time_normalization(self, client, setup_test_db):
        response = client.post("/schedules/", json=self._payload(start_time="8:00", end_time="9:30"))
        assert response.status_code == 200
        assert response.json()["start_time"] == "08:00"
        assert response.json()["end_time"] == "09:30"


class TestHistoryPagination:
    def _seed(self, client, fake_jpeg, n_schedules=3):
        client.post("/students/", json={"name": "Alice", "nim": "12345", "mac_address": "aa:bb:cc:dd:ee:ff"})
        now = datetime.now()
        for i in range(n_schedules):
            client.post("/schedules/", json={
                "class_name": f"Class {i}",
                "day_of_week": now.weekday(),
                "start_time": (now - timedelta(minutes=5 + i)).strftime("%H:%M"),
                "end_time": (now + timedelta(minutes=5 - i)).strftime("%H:%M"),
                "room": f"Room {100 + i}",
            })
            client.post(
                f"/attendance/check?schedule_id={i + 1}&check_type=start",
                files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")}
            )

    def test_limit_and_total_header(self, client, setup_test_db, fake_jpeg):
        self._seed(client, fake_jpeg)
        response = client.get("/attendance/student/1?limit=2")
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert response.headers["X-Total-Count"] == "3"

    def test_offset(self, client, setup_test_db, fake_jpeg):
        self._seed(client, fake_jpeg)
        response = client.get("/attendance/student/1?limit=2&offset=2")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.headers["X-Total-Count"] == "3"

    def test_date_range_filter(self, client, setup_test_db, fake_jpeg):
        self._seed(client, fake_jpeg)
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        response = client.get(f"/attendance/student/1?date_from={yesterday}")
        assert len(response.json()) == 3
        response = client.get(f"/attendance/student/1?date_from={today}&date_to={today}")
        assert len(response.json()) == 3
        response = client.get(f"/attendance/student/1?date_to={yesterday}")
        assert response.json() == []
        assert response.headers["X-Total-Count"] == "0"

    def test_invalid_limit(self, client, setup_test_db):
        response = client.get("/attendance/student/1?limit=0")
        assert response.status_code == 400
        response = client.get("/attendance/student/1?limit=501")
        assert response.status_code == 400

    def test_invalid_date_filter(self, client, setup_test_db):
        response = client.get("/attendance/student/1?date_from=bad")
        assert response.status_code == 400


class TestFaceRecognitionRobustness:
    def test_load_embeddings_corrupt_file(self, tmp_path):
        with patch("services.face_recognition.EMBEDDINGS_DIR", tmp_path):
            (tmp_path / "student_77.pkl").write_bytes(b"corrupt garbage not a pickle")
            assert real_load_embeddings(77) == []

    def test_load_embeddings_truncated_pickle(self, tmp_path):
        with patch("services.face_recognition.EMBEDDINGS_DIR", tmp_path):
            emb = [np.random.randn(512).astype(np.float32)]
            data = pickle.dumps(emb)
            (tmp_path / "student_78.pkl").write_bytes(data[: len(data) // 2])
            assert real_load_embeddings(78) == []

    def test_load_all_embeddings_skips_corrupt(self, tmp_path):
        from services.face_recognition import load_all_embeddings, save_embeddings
        with patch("services.face_recognition.EMBEDDINGS_DIR", tmp_path):
            save_embeddings(1, [np.random.randn(512).astype(np.float32)])
            (tmp_path / "student_2.pkl").write_bytes(b"broken")
            all_embs = load_all_embeddings()
            assert 1 in all_embs
            assert 2 not in all_embs

    def test_save_leaves_no_tmp_file(self, tmp_path):
        from services.face_recognition import save_embeddings
        with patch("services.face_recognition.EMBEDDINGS_DIR", tmp_path):
            save_embeddings(5, [np.random.randn(512).astype(np.float32)])
            assert list(tmp_path.glob("*.tmp")) == []
            assert (tmp_path / "student_5.pkl").exists()

    def test_compare_faces_skips_zero_norm(self):
        emb = np.random.randn(512).astype(np.float32)
        idx, score = real_compare_faces(emb, [np.zeros(512, dtype=np.float32)])
        assert idx == -1
        assert score == 0.0

    def test_compare_faces_returns_original_index(self):
        target = np.zeros(512, dtype=np.float32)
        target[0] = 1.0
        other = np.zeros(512, dtype=np.float32)
        other[1] = 1.0
        zero = np.zeros(512, dtype=np.float32)
        idx, score = real_compare_faces(target, [zero, other, target.copy()])
        assert idx == 2
        assert score == pytest.approx(1.0)

    def test_l2_normalize(self):
        v = np.array([3.0, 4.0], dtype=np.float32)
        normalized = real_l2_normalize(v)
        assert normalized.dtype == np.float32
        assert float(np.linalg.norm(normalized)) == pytest.approx(1.0, abs=1e-6)
        zero = real_l2_normalize(np.zeros(3, dtype=np.float32))
        assert float(np.linalg.norm(zero)) == 0.0


class TestBssidVerification:
    @pytest.mark.asyncio
    async def test_matching_bssid_verifies_wifi(self, test_db, setup_test_db):
        await seed_student_and_schedule(test_db, ap_bssid="aa:bb:cc:dd:ee:ff")
        with patch("services.attendance.get_current_bssid", return_value="aa:bb:cc:dd:ee:ff"):
            result = await mark_attendance(student_id=1, schedule_id=1, check_type="start", confidence=0.9)
        assert result["wifi_verified"] is True
        assert result["status"] == "partial"

    @pytest.mark.asyncio
    async def test_wrong_bssid_fails_wifi(self, test_db, setup_test_db):
        await seed_student_and_schedule(test_db, ap_bssid="aa:bb:cc:dd:ee:ff")
        with patch("services.attendance.get_current_bssid", return_value="11:22:33:44:55:66"):
            result = await mark_attendance(student_id=1, schedule_id=1, check_type="start", confidence=0.9)
        assert result["wifi_verified"] is False

    @pytest.mark.asyncio
    async def test_server_off_wifi_fails_bssid_check(self, test_db, setup_test_db):
        await seed_student_and_schedule(test_db, ap_bssid="aa:bb:cc:dd:ee:ff")
        with patch("services.attendance.get_current_bssid", return_value=None):
            result = await mark_attendance(student_id=1, schedule_id=1, check_type="start", confidence=0.9)
        assert result["wifi_verified"] is False

    @pytest.mark.asyncio
    async def test_bssid_format_agnostic(self, test_db, setup_test_db):
        await seed_student_and_schedule(test_db, ap_bssid="AA-BB-CC-DD-EE-FF")
        with patch("services.attendance.get_current_bssid", return_value="aabbccddeeff"):
            result = await mark_attendance(student_id=1, schedule_id=1, check_type="start", confidence=0.9)
        assert result["wifi_verified"] is True

    @pytest.mark.asyncio
    async def test_no_pinned_bssid_skips_check(self, test_db, setup_test_db):
        await seed_student_and_schedule(test_db, ap_bssid=None)
        with patch("services.attendance.get_current_bssid", side_effect=AssertionError("must not be called")):
            result = await mark_attendance(student_id=1, schedule_id=1, check_type="start", confidence=0.9)
        assert result["wifi_verified"] is True

    @pytest.mark.asyncio
    async def test_end_check_bssid_mismatch_yields_face_only(self, test_db, setup_test_db):
        await seed_student_and_schedule(test_db, ap_bssid="aa:bb:cc:dd:ee:ff")
        with patch("services.attendance.get_current_bssid", return_value="11:22:33:44:55:66"):
            await mark_attendance(student_id=1, schedule_id=1, check_type="start", confidence=0.9)
            result = await mark_attendance(student_id=1, schedule_id=1, check_type="end", confidence=0.85)
        assert result["wifi_verified"] is False
        assert result["status"] == "face_only"


class TestBssidParsers:
    NETSH_SAMPLE = (
        "There is 1 interface on the system:\n\n"
        "    Name                   : Wi-Fi\n"
        "    Description            : Intel(R) Wi-Fi 6 AX201 160MHz\n"
        "    GUID                   : 12345678-1234-1234-1234-123456789012\n"
        "    MAC address            : 8c:55:4a:11:22:33\n"
        "    State                  : connected\n"
        "    SSID                   : ClassroomAP\n"
        "    BSSID                  : a4:2b:b0:12:34:56\n"
        "    Authentication         : WPA2-Personal\n"
    )

    def test_parse_netsh_bssid(self):
        assert wifi_scanner.parse_netsh_bssid(self.NETSH_SAMPLE) == "a4:2b:b0:12:34:56"

    def test_parse_netsh_bssid_missing(self):
        assert wifi_scanner.parse_netsh_bssid("No interfaces") is None

    def test_parse_iwconfig_bssid(self):
        output = (
            'wlan0     IEEE 802.11  ESSID:"ClassroomAP"\n'
            "          Mode:Managed  Frequency:5.18 GHz  Access Point: A4:2B:B0:12:34:56\n"
        )
        assert wifi_scanner.parse_iwconfig_bssid(output) == "a4:2b:b0:12:34:56"

    def test_parse_iwconfig_not_associated(self):
        output = (
            'wlan0     IEEE 802.11  ESSID:off/any\n'
            "          Mode:Managed  Access Point: Not-Associated   Sensitivity:0/0\n"
        )
        assert wifi_scanner.parse_iwconfig_bssid(output) is None

    def test_is_same_bssid(self):
        assert wifi_scanner.is_same_bssid("AA:BB:CC:DD:EE:FF", "aabbccddeeff") is True
        assert wifi_scanner.is_same_bssid("aa:bb:cc:dd:ee:ff", "11:22:33:44:55:66") is False
        assert wifi_scanner.is_same_bssid(None, "aa:bb:cc:dd:ee:ff") is False
        assert wifi_scanner.is_same_bssid("aa:bb:cc:dd:ee:ff", None) is False
        assert wifi_scanner.is_same_bssid(None, None) is False

    def test_scan_response_includes_bssid(self, client, setup_test_db):
        response = client.get("/wifi/scan")
        assert response.status_code == 200
        assert response.json()["bssid"] == "aa:bb:cc:dd:ee:ff"

    def test_scan_logs_bssid_to_ap_logs(self, client, setup_test_db, test_db):
        client.get("/wifi/scan")

        async def _rows():
            db = await test_db()
            cursor = await db.execute("SELECT mac_address, bssid FROM ap_logs")
            rows = await cursor.fetchall()
            await db.close()
            return [dict(r) for r in rows]

        rows = asyncio.run(_rows())
        assert rows
        assert all(r["bssid"] == "aa:bb:cc:dd:ee:ff" for r in rows)
