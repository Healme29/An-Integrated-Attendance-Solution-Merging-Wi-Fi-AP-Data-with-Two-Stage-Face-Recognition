"""Tests for the auto check-in prompt endpoint (GET /me/prompt)."""
from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient


def active_schedule_payload(**overrides):
    """Schedule window spanning 'now' so the time check passes locally."""
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


def _create_student(client, nim="F25040126", mac="c4:23:60:49:97:79"):
    client.post("/students/", json={"name": "Buchari", "nim": nim, "mac_address": mac})
    return client.get("/students/", params={"nim": nim}).json()[0]["id"]


class TestPromptEndpoint:
    def test_student_not_found(self, client, setup_test_db):
        response = client.get("/me/prompt?student_id=999")
        assert response.status_code == 404

    def test_no_active_schedule(self, client, setup_test_db):
        student_id = _create_student(client)
        response = client.get(f"/me/prompt?student_id={student_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["prompt"] is False
        assert data["check_available"] is False
        assert data["reason"] == "no_active_schedule"

    def test_prompt_start_when_device_seen(self, client, setup_test_db):
        student_id = _create_student(client)
        client.post("/schedules/", json=active_schedule_payload())
        schedule_id = client.get("/schedules/").json()[0]["id"]
        with patch("routers.prompt.check_mac_on_network", return_value=True):
            response = client.get(f"/me/prompt?student_id={student_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["prompt"] is True
        assert data["check_available"] is True
        assert data["wifi_seen"] is True
        assert data["check_type"] == "start"
        assert data["schedule_id"] == schedule_id

    def test_no_prompt_when_device_not_seen(self, client, setup_test_db):
        student_id = _create_student(client)
        client.post("/schedules/", json=active_schedule_payload())
        with patch("routers.prompt.check_mac_on_network", return_value=False):
            response = client.get(f"/me/prompt?student_id={student_id}")
        data = response.json()
        assert data["prompt"] is False
        assert data["check_available"] is True
        assert data["reason"] == "device_not_seen_on_network"

    def test_student_without_mac_never_prompted(self, client, setup_test_db):
        student_id = _create_student(client, mac=None)
        client.post("/schedules/", json=active_schedule_payload())
        mock_check_result = True
        with patch("routers.prompt.check_mac_on_network", return_value=mock_check_result) as mock_check:
            response = client.get(f"/me/prompt?student_id={student_id}")
        data = response.json()
        assert data["prompt"] is False
        assert data["wifi_seen"] is False
        mock_check.assert_not_called()

    def test_prompt_end_after_start_exists(self, client, setup_test_db, fake_jpeg):
        student_id = _create_student(client)
        client.post("/schedules/", json=active_schedule_payload())
        schedule_id = client.get("/schedules/").json()[0]["id"]
        check = client.post(
            f"/attendance/check?schedule_id={schedule_id}&check_type=start",
            files={"file": ("a.jpg", fake_jpeg, "image/jpeg")},
        )
        assert check.status_code == 200
        response = client.get(f"/me/prompt?student_id={student_id}")
        data = response.json()
        assert data["check_type"] == "end"

    def test_check_in_complete(self, client, setup_test_db, fake_jpeg):
        student_id = _create_student(client)
        client.post("/schedules/", json=active_schedule_payload())
        schedule_id = client.get("/schedules/").json()[0]["id"]
        for stage in ("start", "end"):
            res = client.post(
                f"/attendance/check?schedule_id={schedule_id}&check_type={stage}",
                files={"file": ("a.jpg", fake_jpeg, "image/jpeg")},
            )
            assert res.status_code == 200
        response = client.get(f"/me/prompt?student_id={student_id}")
        data = response.json()
        assert data["prompt"] is False
        assert data["check_available"] is False
        assert data["reason"] == "check_in_complete"
