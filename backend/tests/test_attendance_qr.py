"""End-to-end attendance rules: two stages, enrollment, identity, roster, CSV."""
from unittest.mock import patch

import pytest


@pytest.fixture
def student(client):
    response = client.post("/students/", json={"name": "Alice", "nim": "12345"})
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def session(client, student):
    created = client.post("/classes/", json={"class_name": "Mathematics", "room": "101"})
    class_id = created.json()["id"]
    client.post(f"/classes/{class_id}/students", json={"student_id": student["id"]})
    response = client.post("/qr-sessions/start", json={"class_id": class_id})
    assert response.status_code == 200
    return response.json()


def _check_in(client, student_id, token, jpeg):
    return client.post(
        f"/attendance/check-qr?student_id={student_id}&token={token}",
        files={"file": ("selfie.jpg", jpeg, "image/jpeg")},
    )


def _token(client):
    return client.get("/qr-sessions/active/token").json()["token"]


def test_start_check_in_is_partial(client, student, session, fake_jpeg):
    response = _check_in(client, student["id"], _token(client), fake_jpeg)
    assert response.status_code == 200
    body = response.json()
    assert body["student_id"] == student["id"]
    assert body["student_name"] == "Alice"
    assert body["qr_session_id"] == session["id"]
    assert body["check_type"] == "start"
    assert body["status"] == "partial"
    assert body["class_name"] == "Mathematics"
    assert 0.0 <= body["confidence"] <= 1.0


def test_full_two_stage_flow_and_roster(client, student, session, fake_jpeg):
    started = _check_in(client, student["id"], _token(client), fake_jpeg)
    assert started.status_code == 200 and started.json()["status"] == "partial"

    roster = client.get(f"/attendance/roster?qr_session_id={session['id']}").json()
    assert roster[0]["status"] == "partial"
    assert roster[0]["student_nim"] == "12345"

    changed = client.post("/qr-sessions/phase", json={"phase": "end"})
    assert changed.status_code == 200
    assert changed.json()["phase"] == "end"

    # A different file represents the second live capture.
    finished = _check_in(client, student["id"], _token(client), fake_jpeg + b"end")
    assert finished.status_code == 200
    assert finished.json()["check_type"] == "end"
    assert finished.json()["status"] == "verified"

    roster = client.get(f"/attendance/roster?qr_session_id={session['id']}").json()
    assert roster[0]["status"] == "verified"
    assert roster[0]["start_time"]
    assert roster[0]["end_time"]


def test_duplicate_start_rejected(client, student, session, fake_jpeg):
    assert _check_in(client, student["id"], _token(client), fake_jpeg).status_code == 200
    second = _check_in(client, student["id"], _token(client), fake_jpeg)
    assert second.status_code == 409
    assert "Already checked in" in second.json()["detail"]


def test_end_requires_start(client, student, session, fake_jpeg):
    client.post("/qr-sessions/phase", json={"phase": "end"})
    response = _check_in(client, student["id"], _token(client), fake_jpeg)
    assert response.status_code == 409
    assert "Complete the start check-in" in response.json()["detail"]


def test_end_rejects_same_photo_file(client, student, session, fake_jpeg):
    assert _check_in(client, student["id"], _token(client), fake_jpeg).status_code == 200
    client.post("/qr-sessions/phase", json={"phase": "end"})
    response = _check_in(client, student["id"], _token(client), fake_jpeg)
    assert response.status_code == 409
    assert "fresh selfie" in response.json()["detail"]


def test_spot_check_optional_round(client, student, session, fake_jpeg):
    assert _check_in(client, student["id"], _token(client), fake_jpeg).status_code == 200
    response = client.post("/qr-sessions/phase", json={"phase": "spot"})
    assert response.status_code == 200 and response.json()["spot_round"] == 1
    spot = _check_in(client, student["id"], _token(client), fake_jpeg + b"spot")
    assert spot.status_code == 200 and spot.json()["check_type"] == "spot"
    duplicate = _check_in(client, student["id"], _token(client), fake_jpeg + b"spot2")
    assert duplicate.status_code == 409
    client.post("/qr-sessions/phase", json={"phase": "start"})
    client.post("/qr-sessions/phase", json={"phase": "end"})
    assert _check_in(client, student["id"], _token(client), fake_jpeg + b"end").status_code == 200


def test_check_in_unknown_student(client, session, fake_jpeg):
    response = _check_in(client, 9999, _token(client), fake_jpeg)
    assert response.status_code == 404


def test_student_must_be_enrolled(client, session, fake_jpeg):
    outsider = client.post("/students/", json={"name": "Outsider", "nim": "999"}).json()
    response = _check_in(client, outsider["id"], _token(client), fake_jpeg)
    assert response.status_code == 403
    assert "not enrolled" in response.json()["detail"]


def test_check_in_invalid_token(client, student, session, fake_jpeg):
    response = _check_in(client, student["id"], "WRONG1", fake_jpeg)
    assert response.status_code == 400
    assert "Invalid or expired QR code" in response.json()["detail"]


def test_check_in_without_active_session(client, student, fake_jpeg):
    response = _check_in(client, student["id"], "ABC123", fake_jpeg)
    assert response.status_code == 400
    assert "No active class session" in response.json()["detail"]


def test_check_in_after_session_closed(client, student, session, fake_jpeg):
    client.post("/qr-sessions/end", json={"session_id": session["id"]})
    response = _check_in(client, student["id"], session["token"], fake_jpeg)
    assert response.status_code == 400
    assert "No active class session" in response.json()["detail"]


def test_check_in_rejects_outside_school_subnet(client, student, session, fake_jpeg, monkeypatch):
    import routers.attendance as attendance_router
    monkeypatch.setattr(attendance_router, "is_school_subnet", lambda ip: False)
    response = _check_in(client, student["id"], _token(client), fake_jpeg)
    assert response.status_code == 403
    assert "school network" in response.json()["detail"]


def test_check_in_identity_binding(client, student, session, fake_jpeg):
    bob = client.post("/students/", json={"name": "Bob", "nim": "222"}).json()
    with patch(
        "routers.attendance.recognize_face",
        return_value={
            "recognized": True,
            "student_id": bob["id"],
            "student_name": "Bob",
            "confidence": 0.9,
            "faces_detected": 1,
        },
    ):
        response = _check_in(client, student["id"], _token(client), fake_jpeg)
    assert response.status_code == 403
    assert "Identity mismatch" in response.json()["detail"]
    history = client.get(f"/attendance/student/{student['id']}")
    assert history.headers["X-Total-Count"] == "0"


def test_manual_attendance_only_after_close(client, student, session):
    response = client.post(
        "/attendance/manual",
        json={"student_id": student["id"], "qr_session_id": session["id"]},
    )
    assert response.status_code == 409
    assert "End the class session" in response.json()["detail"]

    client.post("/qr-sessions/end", json={"session_id": session["id"]})
    marked = client.post(
        "/attendance/manual",
        json={"student_id": student["id"], "qr_session_id": session["id"]},
    )
    assert marked.status_code == 200
    assert marked.json()["status"] == "verified"
    assert marked.json()["manual"] is True

    roster = client.get(f"/attendance/roster?qr_session_id={session['id']}").json()
    assert roster[0]["status"] == "verified"
    assert roster[0]["manual"] is True


def test_today_and_export(client, student, session, fake_jpeg):
    assert _check_in(client, student["id"], _token(client), fake_jpeg).status_code == 200
    today = client.get(f"/attendance/today?qr_session_id={session['id']}").json()
    assert len(today) == 1
    assert today[0]["student_name"] == "Alice"
    assert today[0]["check_type"] == "start"

    csv_export = client.get(f"/attendance/export/csv?qr_session_id={session['id']}")
    assert csv_export.status_code == 200
    assert "student_name" in csv_export.text
    assert "Alice" in csv_export.text
    assert "partial" in csv_export.text

    history = client.get(f"/attendance/student/{student['id']}")
    assert history.status_code == 200
    assert history.headers["X-Total-Count"] == "1"


def test_student_history_filters(client, student, session, fake_jpeg):
    assert _check_in(client, student["id"], _token(client), fake_jpeg).status_code == 200
    response = client.get(
        f"/attendance/student/{student['id']}?date_from=2099-01-01&date_to=2099-12-31"
    )
    assert response.status_code == 200
    assert response.headers["X-Total-Count"] == "0"
    assert response.json() == []


def test_students_crud_and_single_class_membership(client):
    cara = client.post("/students/", json={"name": "Cara", "nim": "333"}).json()
    first = client.post("/classes/", json={"class_name": "First"}).json()
    second = client.post("/classes/", json={"class_name": "Second"}).json()
    client.post(f"/classes/{first['id']}/students", json={"student_id": cara["id"]})
    client.post(f"/classes/{second['id']}/students", json={"student_id": cara["id"]})
    assert client.get(f"/classes/{first['id']}/students").json() == []
    assert len(client.get(f"/classes/{second['id']}/students").json()) == 1

    duplicate = client.post("/students/", json={"name": "Cara2", "nim": "333"})
    assert duplicate.status_code == 400
    assert client.delete(f"/students/{cara['id']}").status_code == 200
    assert client.get(f"/students/{cara['id']}").status_code == 404


def test_face_enroll_hardening(client, student, fake_jpeg):
    response = client.post(
        f"/faces/enroll?student_id={student['id']}",
        files={"file": ("evil.txt", b"not an image at all", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported image format" in response.json()["detail"]

    big = b"\xff\xd8\xff" + b"\x00" * (11 * 1024 * 1024)
    response = client.post(
        f"/faces/enroll?student_id={student['id']}",
        files={"file": ("big.jpg", big, "image/jpeg")},
    )
    assert response.status_code == 413
    assert client.post(
        "/faces/enroll?student_id=999",
        files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")},
    ).status_code == 404


def test_face_enroll_and_recognize(client, student, fake_jpeg):
    response = client.post(
        f"/faces/enroll?student_id={student['id']}",
        files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")},
    )
    assert response.status_code == 200
    assert response.json()["face_count"] == 1

    recognize = client.post(
        "/faces/recognize", files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")}
    )
    assert recognize.status_code == 200
    assert recognize.json()["recognized"] is True
    assert recognize.json()["student_id"] == student["id"]


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
