import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from models.database import get_db, init_db
from models.schemas import StudentCreate, ScheduleCreate


class TestStudentAPI:
    def test_list_students_empty(self, client, setup_test_db):
        response = client.get("/students/")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_student(self, client, setup_test_db):
        response = client.post(
            "/students/",
            json={"name": "Alice Smith", "nim": "12345", "mac_address": "aa:bb:cc:dd:ee:ff"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Alice Smith"
        assert data["nim"] == "12345"
        assert data["mac_address"] == "aa:bb:cc:dd:ee:ff"

    def test_create_student_duplicate_nim(self, client, setup_test_db):
        client.post("/students/", json={"name": "Alice", "nim": "12345"})
        response = client.post("/students/", json={"name": "Bob", "nim": "12345"})
        assert response.status_code == 400

    def test_get_student_by_id(self, client, setup_test_db):
        client.post("/students/", json={"name": "Alice", "nim": "12345"})
        response = client.get("/students/1")
        assert response.status_code == 200
        assert response.json()["name"] == "Alice"

    def test_get_student_not_found(self, client, setup_test_db):
        response = client.get("/students/999")
        assert response.status_code == 404

    def test_delete_student(self, client, setup_test_db):
        client.post("/students/", json={"name": "Alice", "nim": "12345"})
        response = client.delete("/students/1")
        assert response.status_code == 200
        response = client.get("/students/1")
        assert response.status_code == 404

    def test_delete_student_not_found(self, client, setup_test_db):
        response = client.delete("/students/999")
        assert response.status_code == 404

    def test_update_mac_address(self, client, setup_test_db):
        client.post("/students/", json={"name": "Alice", "nim": "12345", "mac_address": "aa:bb:cc:dd:ee:ff"})
        response = client.put("/students/1/mac?mac_address=11:22:33:44:55:66")
        assert response.status_code == 200
        response = client.get("/students/1")
        assert response.json()["mac_address"] == "11:22:33:44:55:66"


class TestScheduleAPI:
    def test_list_schedules_empty(self, client, setup_test_db):
        response = client.get("/schedules/")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_schedule(self, client, setup_test_db):
        response = client.post(
            "/schedules/",
            json={
                "class_name": "Math 101",
                "day_of_week": 0,
                "start_time": "08:00",
                "end_time": "09:30",
                "ap_bssid": "AP_MATH_01",
                "room": "Room 201"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["class_name"] == "Math 101"
        assert data["day_of_week"] == 0
        assert data["room"] == "Room 201"

    def test_delete_schedule(self, client, setup_test_db):
        client.post("/schedules/", json={"class_name": "Math", "day_of_week": 0, "start_time": "08:00", "end_time": "09:30"})
        response = client.delete("/schedules/1")
        assert response.status_code == 200


class TestAttendanceAPI:
    def test_check_attendance_success(self, client, setup_test_db):
        client.post("/students/", json={"name": "Alice", "nim": "12345", "mac_address": "aa:bb:cc:dd:ee:ff"})
        client.post("/schedules/", json={"class_name": "Math", "day_of_week": 0, "start_time": "08:00", "end_time": "09:30"})

        response = client.post(
            "/attendance/check?schedule_id=1&check_type=start",
            files={"file": ("selfie.jpg", b"fake_image_data", "image/jpeg")}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["student_id"] == 1
        assert data["check_type"] == "start"
        assert data["wifi_verified"] is True
        assert data["status"] == "present"

    def test_check_attendance_invalid_check_type(self, client, setup_test_db):
        response = client.post(
            "/attendance/check?schedule_id=1&check_type=invalid",
            files={"file": ("selfie.jpg", b"fake", "image/jpeg")}
        )
        assert response.status_code == 400

    def test_check_attendance_no_face(self, client, setup_test_db, mock_face_detection):
        m1, m2, m3 = mock_face_detection
        m1.return_value = []
        m2.return_value = []
        m3.return_value = []

        client.post("/students/", json={"name": "Alice", "nim": "12345"})
        client.post("/schedules/", json={"class_name": "Math", "day_of_week": 0, "start_time": "08:00", "end_time": "09:30"})

        response = client.post(
            "/attendance/check?schedule_id=1&check_type=start",
            files={"file": ("selfie.jpg", b"fake_image_data", "image/jpeg")}
        )
        assert response.status_code == 400

    def test_get_today_attendance_empty(self, client, setup_test_db):
        response = client.get("/attendance/today")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_student_attendance(self, client, setup_test_db):
        client.post("/students/", json={"name": "Alice", "nim": "12345", "mac_address": "aa:bb:cc:dd:ee:ff"})
        client.post("/schedules/", json={"class_name": "Math", "day_of_week": 0, "start_time": "08:00", "end_time": "09:30"})
        client.post("/attendance/check?schedule_id=1&check_type=start", files={"file": ("selfie.jpg", b"fake", "image/jpeg")})

        response = client.get("/attendance/student/1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1


class TestFaceAPI:
    def test_enroll_face(self, client, setup_test_db):
        client.post("/students/", json={"name": "Alice", "nim": "12345"})

        response = client.post(
            "/faces/enroll?student_id=1",
            files={"file": ("selfie.jpg", b"fake_image_data", "image/jpeg")}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Face enrolled successfully"
        assert data["student_id"] == 1

    def test_enroll_face_student_not_found(self, client, setup_test_db):
        response = client.post(
            "/faces/enroll?student_id=999",
            files={"file": ("selfie.jpg", b"fake_image_data", "image/jpeg")}
        )
        assert response.status_code == 404

    def test_recognize_face(self, client, setup_test_db):
        client.post("/students/", json={"name": "Alice", "nim": "12345"})
        client.post("/faces/enroll?student_id=1", files={"file": ("selfie.jpg", b"fake", "image/jpeg")})

        response = client.post(
            "/faces/recognize",
            files={"file": ("selfie.jpg", b"fake_image_data", "image/jpeg")}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["recognized"] is True


class TestWiFiAPI:
    def test_scan_wifi(self, client, setup_test_db):
        response = client.get("/wifi/scan")
        assert response.status_code == 200
        data = response.json()
        assert "devices" in data
        assert data["count"] >= 0

    def test_check_mac(self, client, setup_test_db):
        response = client.get("/wifi/check/aa:bb:cc:dd:ee:ff")
        assert response.status_code == 200
        data = response.json()
        assert "mac_address" in data
        assert "on_network" in data


class TestRootEndpoint:
    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "docs" in data