"""QR check-in flow tests: happy path, invalid token, identity binding,
duplicate rejection, and school-subnet enforcement."""
import pytest

from services import qr_service


@pytest.fixture
def student(client):
    response = client.post("/students/", json={"name": "Alice", "nim": "12345"})
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def session(client):
    response = client.post("/qr-sessions/start", json={"class_name": "Mathematics", "room": "101"})
    assert response.status_code == 200
    return response.json()


def _check_in(client, student_id, token, jpeg):
    return client.post(
        f"/attendance/check-qr?student_id={student_id}&token={token}",
        files={"file": ("selfie.jpg", jpeg, "image/jpeg")},
    )


def test_check_in_success(client, student, session, fake_jpeg):
    token = client.get("/qr-sessions/active/token").json()["token"]
    response = _check_in(client, student["id"], token, fake_jpeg)
    assert response.status_code == 200
    body = response.json()
    assert body["student_id"] == student["id"]
    assert body["student_name"] == "Alice"
    assert body["qr_session_id"] == session["id"]
    assert body["status"] == "verified"
    assert body["class_name"] == "Mathematics"
    assert 0.0 <= body["confidence"] <= 1.0


def test_check_in_duplicate_rejected(client, student, session, fake_jpeg):
    token = client.get("/qr-sessions/active/token").json()["token"]
    assert _check_in(client, student["id"], token, fake_jpeg).status_code == 200
    # The token rotated in between? Ask for the fresh one again.
    token = client.get("/qr-sessions/active/token").json()["token"]
    second = _check_in(client, student["id"], token, fake_jpeg)
    assert second.status_code == 409
    assert "Already checked in" in second.json()["detail"]


def test_check_in_unknown_student(client, session, fake_jpeg):
    token = client.get("/qr-sessions/active/token").json()["token"]
    response = _check_in(client, 9999, token, fake_jpeg)
    assert response.status_code == 404


def test_check_in_invalid_token(client, student, fake_jpeg):
    client.post("/qr-sessions/start", json={"class_name": "Mathematics"})
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
    from services import qr_service as _qr_unused  # noqa: F401  (router imports its own ref)

    import routers.attendance as attendance_router
    monkeypatch.setattr(attendance_router, "is_school_subnet", lambda ip: False)
    token = client.get("/qr-sessions/active/token").json()["token"]
    response = _check_in(client, student["id"], token, fake_jpeg)
    assert response.status_code == 403
    assert "school network" in response.json()["detail"]


def test_check_in_identity_binding(client, session, fake_jpeg):
    """The accepted face must belong to the logged-in student (403, no row
    written) when a friend's enrolled face is in front of their camera."""
    from unittest.mock import patch

    alice = client.post("/students/", json={"name": "Alice", "nim": "111"}).json()
    bob = client.post("/students/", json={"name": "Bob", "nim": "222"}).json()

    token = client.get("/qr-sessions/active/token").json()["token"]
    # Recognition resolves to Bob, but Alice is the logged-in account.
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
        response = client.post(
            f"/attendance/check-qr?student_id={alice['id']}&token={token}",
            files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")},
        )
    assert response.status_code == 403
    assert "Identity mismatch" in response.json()["detail"]

    # No attendance row was written for Alice.
    history = client.get(f"/attendance/student/{alice['id']}")
    assert history.headers["X-Total-Count"] == "0"


def test_today_and_export(client, student, session, fake_jpeg):
    token = client.get("/qr-sessions/active/token").json()["token"]
    assert _check_in(client, student["id"], token, fake_jpeg).status_code == 200

    today = client.get(f"/attendance/today?qr_session_id={session['id']}").json()
    assert len(today) == 1
    assert today[0]["student_name"] == "Alice"
    assert today[0]["class_name"] == "Mathematics"

    csv_export = client.get(f"/attendance/export/csv?qr_session_id={session['id']}")
    assert csv_export.status_code == 200
    assert "student_name" in csv_export.text
    assert "Alice" in csv_export.text

    history = client.get(f"/attendance/student/{student['id']}")
    assert history.status_code == 200
    assert history.headers["X-Total-Count"] == "1"


def test_student_history_filters(client, student, session, fake_jpeg):
    token = client.get("/qr-sessions/active/token").json()["token"]
    assert _check_in(client, student["id"], token, fake_jpeg).status_code == 200

    response = client.get(
        f"/attendance/student/{student['id']}?date_from=2099-01-01&date_to=2099-12-31"
    )
    assert response.status_code == 200
    assert response.headers["X-Total-Count"] == "0"
    assert response.json() == []


def test_students_crud(client):
    created = client.post("/students/", json={"name": "Cara", "nim": "333"})
    assert created.status_code == 200
    student_id = created.json()["id"]

    assert client.get(f"/students/{student_id}").json()["name"] == "Cara"

    lookup = client.get("/students/?nim=333").json()
    assert len(lookup) == 1 and lookup[0]["name"] == "Cara"

    duplicate = client.post("/students/", json={"name": "Cara2", "nim": "333"})
    assert duplicate.status_code == 400

    assert client.delete(f"/students/{student_id}").status_code == 200
    assert client.get(f"/students/{student_id}").status_code == 404


def test_face_enroll_hardening(client, student, fake_jpeg):
    """Magic-byte check rejects non-JPEG/PNG uploads; size cap rejects >4 MB."""
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

    response = client.post(
        f"/faces/enroll?student_id=999",
        files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")},
    )
    assert response.status_code == 404


def test_face_enroll_and_recognize(client, student, fake_jpeg):
    response = client.post(
        f"/faces/enroll?student_id={student['id']}",
        files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")},
    )
    assert response.status_code == 200
    assert response.json()["face_count"] == 1

    recognize = client.post(
        "/faces/recognize",
        files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")},
    )
    assert recognize.status_code == 200
    assert recognize.json()["recognized"] is True
    assert recognize.json()["student_id"] == student["id"]


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"