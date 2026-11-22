"""Class-session lifecycle, rotating QR tokens, phases, and subnet checks."""
from datetime import timedelta

import pytest

from config import now_local
from services import qr_service


@pytest.fixture
def class_id(client):
    created = client.post("/classes/", json={"class_name": "Mathematics", "room": "101"})
    assert created.status_code == 200
    cid = created.json()["id"]
    student = client.post("/students/", json={"name": "Alice", "nim": "12345"}).json()
    enrolled = client.post(f"/classes/{cid}/students", json={"student_id": student["id"]})
    assert enrolled.status_code == 200
    return cid


@pytest.mark.asyncio
async def test_start_and_end_session(test_db, class_id):
    session = await qr_service.create_session(class_id, created_by="teacher")
    assert session["is_active"] == 1
    assert session["class_id"] == class_id
    assert session["class_name"] == "Mathematics"
    assert session["phase"] == "start"
    assert len(session["token"]) == 6

    active = await qr_service.get_active_session()
    assert active and active["id"] == session["id"]

    ended = await qr_service.end_session(session["id"])
    assert ended["ended_at"] is not None
    assert ended["phase"] == "closed"
    assert ended["total_attendance"] == 0
    assert await qr_service.get_active_session() is None


@pytest.mark.asyncio
async def test_second_session_closes_first(test_db, class_id):
    first = await qr_service.create_session(class_id)
    second = await qr_service.create_session(class_id)
    assert first["id"] != second["id"]

    db = await test_db()
    cursor = await db.execute(
        "SELECT is_active, ended_at, phase FROM qr_sessions WHERE id = ?", (first["id"],)
    )
    row = await cursor.fetchone()
    await db.close()
    assert row["is_active"] == 0
    assert row["ended_at"] is not None
    assert row["phase"] == "closed"
    assert (await qr_service.get_active_session())["id"] == second["id"]


@pytest.mark.asyncio
async def test_validate_current_token(test_db, class_id):
    session = await qr_service.create_session(class_id)
    result = await qr_service.validate_token(session["token"])
    assert result["valid"] is True
    assert result["session_id"] == session["id"]
    assert result["phase"] == "start"


@pytest.mark.asyncio
async def test_validate_without_session(test_db):
    result = await qr_service.validate_token("ABC123")
    assert result["valid"] is False
    assert "No active class session" in result["message"]


@pytest.mark.asyncio
async def test_validate_rejects_unknown_token(test_db, class_id):
    await qr_service.create_session(class_id)
    assert (await qr_service.validate_token("ZZZZZZ"))["valid"] is False


@pytest.mark.asyncio
async def test_token_rotation_keeps_previous_valid_in_grace(test_db, class_id):
    session = await qr_service.create_session(class_id)
    old_token = session["token"]
    db = await test_db()
    stale = (now_local() - timedelta(seconds=60)).strftime("%Y-%m-%d %H:%M:%S")
    await db.execute("UPDATE qr_sessions SET token_rotated_at = ? WHERE id = ?", (stale, session["id"]))
    await db.commit()
    await db.close()

    refreshed = await qr_service.current_token(rotate=True)
    assert refreshed["token"] != old_token
    assert refreshed["prev_token"] == old_token
    assert (await qr_service.validate_token(old_token))["valid"] is True
    assert (await qr_service.validate_token(refreshed["token"]))["valid"] is True


@pytest.mark.asyncio
async def test_grace_expires(test_db, class_id):
    session = await qr_service.create_session(class_id)
    old_token = session["token"]
    db = await test_db()
    stale = (now_local() - timedelta(seconds=60)).strftime("%Y-%m-%d %H:%M:%S")
    await db.execute("UPDATE qr_sessions SET token_rotated_at = ? WHERE id = ?", (stale, session["id"]))
    await db.commit()
    await db.close()
    refreshed = await qr_service.current_token(rotate=True)

    db = await test_db()
    long_ago = (now_local() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    await db.execute("UPDATE qr_sessions SET token_rotated_at = ? WHERE id = ?", (long_ago, session["id"]))
    await db.commit()
    await db.close()

    assert (await qr_service.validate_token(old_token))["valid"] is False
    assert (await qr_service.validate_token(refreshed["token"]))["valid"] is True


@pytest.mark.asyncio
async def test_phase_change_rotates_and_invalidates_start_token(test_db, class_id):
    session = await qr_service.create_session(class_id)
    start_token = session["token"]
    ended = await qr_service.set_phase(session["id"], "end", "teacher")
    assert ended["phase"] == "end"
    assert ended["token"] != start_token
    assert (await qr_service.validate_token(start_token))["valid"] is False
    result = await qr_service.validate_token(ended["token"])
    assert result["valid"] is True and result["phase"] == "end"


@pytest.mark.asyncio
async def test_spot_check_round_and_resume(test_db, class_id):
    session = await qr_service.create_session(class_id)
    spot = await qr_service.set_phase(session["id"], "spot", "teacher")
    assert spot["phase"] == "spot" and spot["spot_round"] == 1
    resumed = await qr_service.set_phase(session["id"], "start", "teacher")
    assert resumed["phase"] == "start" and resumed["spot_round"] == 1
    final = await qr_service.set_phase(session["id"], "end", "teacher")
    assert final["phase"] == "end"


def test_is_school_subnet():
    assert qr_service.is_school_subnet("192.168.1.20") is True
    assert qr_service.is_school_subnet("192.168.137.5") is True
    assert qr_service.is_school_subnet("127.0.0.1") is True
    assert qr_service.is_school_subnet("8.8.8.8") is False
    assert qr_service.is_school_subnet("not-an-ip") is False
    assert qr_service.is_school_subnet("") is False


def test_is_school_subnet_env_override(monkeypatch):
    monkeypatch.setattr(qr_service, "SCHOOL_SUBNET", "10.0.0.0/8")
    assert qr_service.is_school_subnet("10.1.2.3") is True
    assert qr_service.is_school_subnet("192.168.1.2") is False
    assert qr_service.is_school_subnet("127.0.0.1") is True


def test_generate_token_shape():
    token = qr_service.generate_token()
    assert len(token) == 6
    assert token.isalnum() and token.isupper()
    assert len({qr_service.generate_token() for _ in range(50)}) > 40


def test_start_and_end_via_api(client, class_id):
    response = client.post("/qr-sessions/start", json={"class_id": class_id})
    assert response.status_code == 200
    body = response.json()
    assert body["class_name"] == "Mathematics"
    assert body["phase"] == "start"
    session_id = body["id"]

    active = client.get("/qr-sessions/active").json()
    assert active["active"] is True and active["session_id"] == session_id
    token = client.get("/qr-sessions/active/token").json()
    assert token["active"] is True and token["token"]

    end = client.post("/qr-sessions/end", json={"session_id": session_id})
    assert end.status_code == 200
    assert end.json()["total_attendance"] == 0
    assert client.get("/qr-sessions/active").json() == {"active": False}


def test_validate_via_api(client, class_id):
    client.post("/qr-sessions/start", json={"class_id": class_id})
    token = client.get("/qr-sessions/active/token").json()["token"]
    assert client.post("/qr-sessions/validate", json={"token": token}).json()["valid"] is True
    assert client.post("/qr-sessions/validate", json={"token": "WRONG1"}).json()["valid"] is False


def test_qr_png_requires_active_session(client, class_id):
    assert client.get("/qr-sessions/active/qr.png").status_code == 404
    client.post("/qr-sessions/start", json={"class_id": class_id})
    response = client.get("/qr-sessions/active/qr.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_start_requires_class_and_enrollment(client):
    missing = client.post("/qr-sessions/start", json={"class_id": 999})
    assert missing.status_code == 400
    empty = client.post("/classes/", json={"class_name": "Empty"}).json()
    response = client.post("/qr-sessions/start", json={"class_id": empty["id"]})
    assert response.status_code == 400
    assert "at least one student" in response.json()["detail"]


def test_history_returns_sessions(client, class_id):
    started = client.post("/qr-sessions/start", json={"class_id": class_id}).json()
    history = client.get("/qr-sessions/history").json()
    assert history[0]["id"] == started["id"]
    assert history[0]["class_name"] == "Mathematics"


def test_teacher_login_and_protected_actions(unauthenticated_client, class_id):
    unauthenticated_client.post("/qr-sessions/end")
    bad = unauthenticated_client.post(
        "/teachers/login", json={"username": "teacher", "password": "wrong"}
    )
    assert bad.status_code == 401
    login = unauthenticated_client.post(
        "/teachers/login", json={"username": "teacher", "password": "attendance2026"}
    )
    assert login.status_code == 200
    token = login.json()["token"]
    assert unauthenticated_client.post("/teachers/verify", json={"token": token}).json()["valid"] is True
    headers = {"Authorization": f"Bearer {token}"}
    started = unauthenticated_client.post(
        "/qr-sessions/start", json={"class_id": class_id}, headers=headers
    )
    assert started.status_code == 200
