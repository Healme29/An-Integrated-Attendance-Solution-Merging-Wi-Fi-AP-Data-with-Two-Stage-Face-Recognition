import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch
from models.database import get_db, init_db
from models.schemas import StudentCreate, ScheduleCreate


def active_schedule_payload(**overrides):
    """Schedule window spanning 'now' so time enforcement passes."""
    now = datetime.now()
    payload = {
        "class_name": "Math 101",
        "day_of_week": now.weekday(),
        "start_time": (now - timedelta(minutes=5)).strftime("%H:%M"),
        "end_time": (now + timedelta(minutes=5)).strftime("%H:%M"),
        "ap_bssid": "AP_MATH_01",
        "room": "Room 201"
    }
    payload.update(overrides)
    return payload


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

    def test_search_student_by_nim(self, client, setup_test_db):
        client.post("/students/", json={"name": "Alice", "nim": "12345"})
        client.post("/students/", json={"name": "Bob", "nim": "67890"})

        response = client.get("/students/?nim=67890")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Bob"

    def test_search_student_by_nim_not_found(self, client, setup_test_db):
        response = client.get("/students/?nim=99999")
        assert response.status_code == 200
        assert response.json() == []


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

    def test_delete_schedule_not_found(self, client, setup_test_db):
        response = client.delete("/schedules/999")
        assert response.status_code == 404

    def test_get_schedule_by_id(self, client, setup_test_db):
        client.post("/schedules/", json={"class_name": "Math", "day_of_week": 0, "start_time": "08:00", "end_time": "09:30"})
        response = client.get("/schedules/1")
        assert response.status_code == 200
        assert response.json()["class_name"] == "Math"

    def test_get_schedule_not_found(self, client, setup_test_db):
        response = client.get("/schedules/999")
        assert response.status_code == 404

    def test_update_schedule(self, client, setup_test_db):
        client.post("/schedules/", json={"class_name": "Math", "day_of_week": 0, "start_time": "08:00", "end_time": "09:30"})
        response = client.put("/schedules/1", json={
            "class_name": "Physics", "day_of_week": 2, "start_time": "10:00", "end_time": "11:30"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["class_name"] == "Physics"
        assert data["day_of_week"] == 2

    def test_update_schedule_not_found(self, client, setup_test_db):
        response = client.put("/schedules/999", json={
            "class_name": "Physics", "day_of_week": 2, "start_time": "10:00", "end_time": "11:30"
        })
        assert response.status_code == 404

    def test_create_schedule_invalid_day(self, client, setup_test_db):
        response = client.post("/schedules/", json={
            "class_name": "Math", "day_of_week": 7, "start_time": "08:00", "end_time": "09:30"
        })
        assert response.status_code == 400

    def test_create_schedule_invalid_time_format(self, client, setup_test_db):
        response = client.post("/schedules/", json={
            "class_name": "Math", "day_of_week": 0, "start_time": "8am", "end_time": "09:30"
        })
        assert response.status_code == 400

    def test_create_schedule_end_before_start(self, client, setup_test_db):
        response = client.post("/schedules/", json={
            "class_name": "Math", "day_of_week": 0, "start_time": "10:00", "end_time": "09:00"
        })
        assert response.status_code == 400

    def test_create_schedule_empty_class_name(self, client, setup_test_db):
        response = client.post("/schedules/", json={
            "class_name": "  ", "day_of_week": 0, "start_time": "08:00", "end_time": "09:30"
        })
        assert response.status_code == 400


class TestAttendanceAPI:
    def test_check_attendance_success(self, client, setup_test_db, fake_jpeg):
        client.post("/students/", json={"name": "Alice", "nim": "12345", "mac_address": "aa:bb:cc:dd:ee:ff"})
        client.post("/schedules/", json=active_schedule_payload())

        response = client.post(
            "/attendance/check?schedule_id=1&check_type=start",
            files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["student_id"] == 1
        assert data["student_name"] == "Alice"
        assert data["check_type"] == "start"
        assert data["wifi_verified"] is True
        assert data["status"] == "partial"

    def test_check_attendance_invalid_check_type(self, client, setup_test_db, fake_jpeg):
        response = client.post(
            "/attendance/check?schedule_id=1&check_type=invalid",
            files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")}
        )
        assert response.status_code == 400

    def test_check_attendance_no_face(self, client, setup_test_db, fake_jpeg, mock_face_detection):
        m1, m2, m3 = mock_face_detection
        m1.return_value = []
        m2.return_value = []
        m3.return_value = []

        client.post("/students/", json={"name": "Alice", "nim": "12345"})
        client.post("/schedules/", json=active_schedule_payload())

        response = client.post(
            "/attendance/check?schedule_id=1&check_type=start",
            files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")}
        )
        assert response.status_code == 400

    def test_check_attendance_schedule_not_found(self, client, setup_test_db, fake_jpeg):
        client.post("/students/", json={"name": "Alice", "nim": "12345"})

        response = client.post(
            "/attendance/check?schedule_id=999&check_type=start",
            files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")}
        )
        assert response.status_code == 404

    def test_check_attendance_outside_class_time(self, client, setup_test_db, fake_jpeg):
        client.post("/students/", json={"name": "Alice", "nim": "12345"})
        client.post("/schedules/", json=active_schedule_payload(
            start_time="00:00", end_time="00:01"
        ))

        response = client.post(
            "/attendance/check?schedule_id=1&check_type=start",
            files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")}
        )
        assert response.status_code == 403

    def test_check_attendance_wrong_day(self, client, setup_test_db, fake_jpeg):
        wrong_day = (datetime.now().weekday() + 1) % 7
        client.post("/students/", json={"name": "Alice", "nim": "12345"})
        client.post("/schedules/", json=active_schedule_payload(day_of_week=wrong_day))

        response = client.post(
            "/attendance/check?schedule_id=1&check_type=start",
            files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")}
        )
        assert response.status_code == 403

    def test_check_attendance_duplicate_check_in(self, client, setup_test_db, fake_jpeg):
        client.post("/students/", json={"name": "Alice", "nim": "12345", "mac_address": "aa:bb:cc:dd:ee:ff"})
        client.post("/schedules/", json=active_schedule_payload())
        client.post("/attendance/check?schedule_id=1&check_type=start", files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")})

        response = client.post(
            "/attendance/check?schedule_id=1&check_type=start",
            files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")}
        )
        assert response.status_code == 409

    def test_check_attendance_end_without_start(self, client, setup_test_db, fake_jpeg):
        client.post("/students/", json={"name": "Alice", "nim": "12345", "mac_address": "aa:bb:cc:dd:ee:ff"})
        client.post("/schedules/", json=active_schedule_payload())

        response = client.post(
            "/attendance/check?schedule_id=1&check_type=end",
            files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")}
        )
        assert response.status_code == 409

    def test_two_stage_check_in_verified(self, client, setup_test_db, fake_jpeg):
        client.post("/students/", json={"name": "Alice", "nim": "12345", "mac_address": "aa:bb:cc:dd:ee:ff"})
        client.post("/schedules/", json=active_schedule_payload())

        start_resp = client.post(
            "/attendance/check?schedule_id=1&check_type=start",
            files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")}
        )
        assert start_resp.status_code == 200
        assert start_resp.json()["status"] == "partial"

        end_resp = client.post(
            "/attendance/check?schedule_id=1&check_type=end",
            files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")}
        )
        assert end_resp.status_code == 200
        end_data = end_resp.json()
        assert end_data["status"] == "verified"

        # start row should also be finalized
        history = client.get("/attendance/student/1").json()
        statuses = {row["check_type"]: row["status"] for row in history}
        assert statuses["start"] == "verified"
        assert statuses["end"] == "verified"

    def test_two_stage_check_in_no_wifi_face_only(self, client, setup_test_db, fake_jpeg, mock_wifi_scanner):
        mock_wifi_scanner.return_value = False
        client.post("/students/", json={"name": "Alice", "nim": "12345", "mac_address": "aa:bb:cc:dd:ee:ff"})
        client.post("/schedules/", json=active_schedule_payload())

        client.post("/attendance/check?schedule_id=1&check_type=start", files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")})
        end_resp = client.post(
            "/attendance/check?schedule_id=1&check_type=end",
            files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")}
        )
        assert end_resp.status_code == 200
        assert end_resp.json()["status"] == "face_only"

    def test_get_today_attendance_empty(self, client, setup_test_db):
        response = client.get("/attendance/today")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_today_attendance_with_data(self, client, setup_test_db, fake_jpeg):
        client.post("/students/", json={"name": "Alice", "nim": "12345", "mac_address": "aa:bb:cc:dd:ee:ff"})
        client.post("/schedules/", json=active_schedule_payload())
        client.post("/attendance/check?schedule_id=1&check_type=start", files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")})

        response = client.get("/attendance/today")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["student_name"] == "Alice"
        assert data[0]["class_name"] == "Math 101"

    def test_get_today_attendance_schedule_filter(self, client, setup_test_db, fake_jpeg):
        client.post("/students/", json={"name": "Alice", "nim": "12345", "mac_address": "aa:bb:cc:dd:ee:ff"})
        client.post("/schedules/", json=active_schedule_payload())
        client.post("/schedules/", json=active_schedule_payload(class_name="Physics"))
        client.post("/attendance/check?schedule_id=1&check_type=start", files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")})

        response = client.get("/attendance/today?schedule_id=2")
        assert response.status_code == 200
        assert response.json() == []

        response = client.get("/attendance/today?schedule_id=1")
        assert len(response.json()) == 1

    def test_export_csv_with_data(self, client, setup_test_db, fake_jpeg):
        client.post("/students/", json={"name": "Alice", "nim": "12345", "mac_address": "aa:bb:cc:dd:ee:ff"})
        client.post("/schedules/", json=active_schedule_payload())
        client.post("/attendance/check?schedule_id=1&check_type=start", files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")})

        response = client.get("/attendance/export/csv")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment" in response.headers["content-disposition"]
        body = response.text
        assert body.splitlines()[0].startswith("id,timestamp,check_type")
        assert "Alice" in body
        assert "12345" in body

    def test_export_csv_empty(self, client, setup_test_db):
        response = client.get("/attendance/export/csv")
        assert response.status_code == 200
        lines = response.text.strip().splitlines()
        assert len(lines) == 1  # header only

    def test_export_csv_invalid_date(self, client, setup_test_db):
        response = client.get("/attendance/export/csv?date=not-a-date")
        assert response.status_code == 400

    def test_get_student_attendance(self, client, setup_test_db, fake_jpeg):
        client.post("/students/", json={"name": "Alice", "nim": "12345", "mac_address": "aa:bb:cc:dd:ee:ff"})
        client.post("/schedules/", json=active_schedule_payload())
        client.post("/attendance/check?schedule_id=1&check_type=start", files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")})

        response = client.get("/attendance/student/1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1


class TestFaceAPI:
    def test_enroll_face(self, client, setup_test_db, fake_jpeg):
        client.post("/students/", json={"name": "Alice", "nim": "12345"})

        response = client.post(
            "/faces/enroll?student_id=1",
            files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Face enrolled successfully"
        assert data["student_id"] == 1

    def test_enroll_face_invalid_image(self, client, setup_test_db):
        client.post("/students/", json={"name": "Alice", "nim": "12345"})

        response = client.post(
            "/faces/enroll?student_id=1",
            files={"file": ("selfie.jpg", b"not_an_image", "image/jpeg")}
        )
        assert response.status_code == 400

    def test_enroll_face_student_not_found(self, client, setup_test_db, fake_jpeg):
        response = client.post(
            "/faces/enroll?student_id=999",
            files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")}
        )
        assert response.status_code == 404

    def test_recognize_face(self, client, setup_test_db, fake_jpeg):
        client.post("/students/", json={"name": "Alice", "nim": "12345"})
        client.post("/faces/enroll?student_id=1", files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")})

        response = client.post(
            "/faces/recognize",
            files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")}
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

    def test_dashboard_served(self, client):
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Teacher Dashboard" in response.text