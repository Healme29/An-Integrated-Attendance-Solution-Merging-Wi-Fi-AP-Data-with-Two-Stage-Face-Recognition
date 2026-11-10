"""Strict classroom mode (REQUIRE_CLASSROOM_WIFI) and the preflight endpoint.

The behaviour under test:
- GET /attendance/preflight reports whether a check-in could succeed before the
  app opens the camera (time window, classroom network, duplicates, pairing).
- With REQUIRE_CLASSROOM_WIFI=true, POST /attendance/check refuses a student
  whose device is not on the classroom network instead of degrading to
  face_only.
"""
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest


def active_schedule_payload(**overrides):
    """Schedule window spanning 'now' so time enforcement passes."""
    now = datetime.now()
    payload = {
        "class_name": "Math 101",
        "day_of_week": now.weekday(),
        "start_time": (now - timedelta(minutes=5)).strftime("%H:%M"),
        "end_time": (now + timedelta(minutes=5)).strftime("%H:%M"),
        "ap_bssid": None,
        "room": "Room 201",
    }
    payload.update(overrides)
    return payload


class TestPreflight:
    def test_allowed_inside_window_on_classroom_network(self, client, setup_test_db):
        client.post("/students/", json={"name": "Alice", "nim": "12345", "mac_address": "aa:bb:cc:dd:ee:ff"})
        client.post("/schedules/", json=active_schedule_payload())

        response = client.get("/attendance/preflight?student_id=1&schedule_id=1&check_type=start")
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is True
        assert data["reason"] is None
        assert data["in_window"] is True
        assert data["wifi_verified"] is True

    def test_outside_class_time(self, client, setup_test_db):
        client.post("/students/", json={"name": "Alice", "nim": "12345", "mac_address": "aa:bb:cc:dd:ee:ff"})
        client.post("/schedules/", json=active_schedule_payload(start_time="00:00", end_time="00:01"))

        response = client.get("/attendance/preflight?student_id=1&schedule_id=1")
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is False
        assert data["reason"] == "outside_class_time"
        assert data["in_window"] is False

    def test_wrong_day(self, client, setup_test_db):
        wrong_day = (datetime.now().weekday() + 1) % 7
        client.post("/students/", json={"name": "Alice", "nim": "12345"})
        client.post("/schedules/", json=active_schedule_payload(day_of_week=wrong_day))

        data = client.get("/attendance/preflight?student_id=1&schedule_id=1").json()
        assert data["allowed"] is False
        assert data["reason"] == "wrong_day"

    def test_strict_mode_blocks_when_device_not_seen(self, client, setup_test_db):
        client.post("/students/", json={"name": "Alice", "nim": "12345", "mac_address": "aa:bb:cc:dd:ee:ff"})
        client.post("/schedules/", json=active_schedule_payload())

        with patch("services.attendance.REQUIRE_CLASSROOM_WIFI", True), \
             patch("routers.attendance.REQUIRE_CLASSROOM_WIFI", True), \
             patch("services.attendance.check_mac_on_network", return_value=False):
            data = client.get("/attendance/preflight?student_id=1&schedule_id=1").json()

        assert data["allowed"] is False
        assert data["reason"] == "not_on_classroom_network"
        assert data["wifi_required"] is True

    def test_duplicate_check_in(self, client, setup_test_db, fake_jpeg):
        client.post("/students/", json={"name": "Alice", "nim": "12345", "mac_address": "aa:bb:cc:dd:ee:ff"})
        client.post("/schedules/", json=active_schedule_payload())
        client.post(
            "/attendance/check?student_id=1&schedule_id=1&check_type=start",
            files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")},
        )

        data = client.get("/attendance/preflight?student_id=1&schedule_id=1&check_type=start").json()
        assert data["allowed"] is False
        assert data["reason"] == "duplicate_check_in"

    def test_end_requires_start(self, client, setup_test_db):
        client.post("/students/", json={"name": "Alice", "nim": "12345", "mac_address": "aa:bb:cc:dd:ee:ff"})
        client.post("/schedules/", json=active_schedule_payload())

        data = client.get("/attendance/preflight?student_id=1&schedule_id=1&check_type=end").json()
        assert data["allowed"] is False
        assert data["reason"] == "missing_start_check"

    def test_unknown_student_or_schedule(self, client, setup_test_db):
        client.post("/students/", json={"name": "Alice", "nim": "12345"})
        client.post("/schedules/", json=active_schedule_payload())

        assert client.get("/attendance/preflight?student_id=999&schedule_id=1").status_code == 404
        assert client.get("/attendance/preflight?student_id=1&schedule_id=999").status_code == 404


class TestStrictCheckIn:
    def test_check_refused_without_classroom_network(self, client, setup_test_db, fake_jpeg):
        client.post("/students/", json={"name": "Alice", "nim": "12345", "mac_address": "aa:bb:cc:dd:ee:ff"})
        client.post("/schedules/", json=active_schedule_payload())

        with patch("services.attendance.REQUIRE_CLASSROOM_WIFI", True), \
             patch("services.attendance.check_mac_on_network", return_value=False):
            response = client.post(
                "/attendance/check?student_id=1&schedule_id=1&check_type=start",
                files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")},
            )

        assert response.status_code == 403
        assert "classroom network" in response.json()["detail"].lower()

    def test_check_accepted_when_network_visible(self, client, setup_test_db, fake_jpeg):
        client.post("/students/", json={"name": "Alice", "nim": "12345", "mac_address": "aa:bb:cc:dd:ee:ff"})
        client.post("/schedules/", json=active_schedule_payload())

        with patch("services.attendance.REQUIRE_CLASSROOM_WIFI", True), \
             patch("services.attendance.check_mac_on_network", return_value=True):
            response = client.post(
                "/attendance/check?student_id=1&schedule_id=1&check_type=start",
                files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")},
            )

        assert response.status_code == 200
        assert response.json()["wifi_verified"] is True


class TestActiveSchedules:
    def test_lists_only_schedules_inside_window(self, client, setup_test_db):
        client.post("/schedules/", json=active_schedule_payload(class_name="Active"))
        client.post("/schedules/", json=active_schedule_payload(
            class_name="Closed", start_time="00:00", end_time="00:01"
        ))

        response = client.get("/schedules/active")
        assert response.status_code == 200
        names = [s["class_name"] for s in response.json()]
        assert names == ["Active"]

    def test_empty_when_nothing_active(self, client, setup_test_db):
        client.post("/schedules/", json=active_schedule_payload(
            class_name="Closed", start_time="00:00", end_time="00:01"
        ))
        assert client.get("/schedules/active").json() == []
