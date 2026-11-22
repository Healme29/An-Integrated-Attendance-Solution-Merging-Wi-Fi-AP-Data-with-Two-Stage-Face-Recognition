"""QR session lifecycle tests: start/end, token rotation, grace period, subnet check."""
from datetime import datetime, timedelta

import pytest

from config import now_local
from services import qr_service


@pytest.mark.asyncio
async def test_start_and_end_session(test_db):
    session = await qr_service.create_session("Mathematics", room="101", created_by="teacher")
    assert session["is_active"] == 1
    assert session["class_name"] == "Mathematics"
    assert session["room"] == "101"
    assert len(session["token"]) == 6

    active = await qr_service.get_active_session()
    assert active and active["id"] == session["id"]

    ended = await qr_service.end_session(session["id"])
    assert ended["ended_at"] is not None
    assert ended["total_attendance"] == 0

    assert await qr_service.get_active_session() is None


@pytest.mark.asyncio
async def test_second_session_closes_first(test_db):
    first = await qr_service.create_session("Physics")
    second = await qr_service.create_session("Chemistry")
    assert first["id"] != second["id"]

    db = await test_db()
    cursor = await db.execute("SELECT is_active, ended_at FROM qr_sessions WHERE id = ?", (first["id"],))
    row = await cursor.fetchone()
    await db.close()
    assert row["is_active"] == 0
    assert row["ended_at"] is not None

    active = await qr_service.get_active_session()
    assert active["id"] == second["id"]


@pytest.mark.asyncio
async def test_validate_current_token(test_db):
    session = await qr_service.create_session("Mathematics", room="101")
    result = await qr_service.validate_token(session["token"])
    assert result["valid"] is True
    assert result["session_id"] == session["id"]
    assert result["class_name"] == "Mathematics"
    assert result["room"] == "101"


@pytest.mark.asyncio
async def test_validate_without_session(test_db):
    result = await qr_service.validate_token("ABC123")
    assert result["valid"] is False
    assert "No active class session" in result["message"]


@pytest.mark.asyncio
async def test_validate_rejects_unknown_token(test_db):
    await qr_service.create_session("Mathematics")
    result = await qr_service.validate_token("ZZZZZZ")
    assert result["valid"] is False


@pytest.mark.asyncio
async def test_token_rotation_keeps_previous_valid_in_grace(test_db):
    session = await qr_service.create_session("Mathematics")
    old_token = session["token"]

    # Force the rotation to be due.
    db = await test_db()
    stale = (now_local() - timedelta(seconds=60)).strftime("%Y-%m-%d %H:%M:%S")
    await db.execute("UPDATE qr_sessions SET token_rotated_at = ? WHERE id = ?", (stale, session["id"]))
    await db.commit()
    await db.close()

    refreshed = await qr_service.current_token(rotate=True)
    assert refreshed["token"] != old_token
    assert refreshed["prev_token"] == old_token

    # Grace period: the previous token is still accepted.
    result = await qr_service.validate_token(old_token)
    assert result["valid"] is True

    # Current token obviously valid.
    result = await qr_service.validate_token(refreshed["token"])
    assert result["valid"] is True


@pytest.mark.asyncio
async def test_grace_expires(test_db, monkeypatch):
    session = await qr_service.create_session("Mathematics")
    old_token = session["token"]

    db = await test_db()
    stale = (now_local() - timedelta(seconds=60)).strftime("%Y-%m-%d %H:%M:%S")
    await db.execute("UPDATE qr_sessions SET token_rotated_at = ? WHERE id = ?", (stale, session["id"]))
    await db.commit()
    await db.close()

    refreshed = await qr_service.current_token(rotate=True)

    # Pretend the rotation happened long ago: the grace window is over.
    db = await test_db()
    long_ago = (now_local() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    await db.execute("UPDATE qr_sessions SET token_rotated_at = ? WHERE id = ?", (long_ago, session["id"]))
    await db.commit()
    await db.close()

    result = await qr_service.validate_token(old_token)
    assert result["valid"] is False
    result = await qr_service.validate_token(refreshed["token"])
    assert result["valid"] is True


def test_is_school_subnet():
    assert qr_service.is_school_subnet("192.168.1.20") is True
    assert qr_service.is_school_subnet("192.168.137.5") is True
    assert qr_service.is_school_subnet("127.0.0.1") is True  # loopback / local demo
    assert qr_service.is_school_subnet("8.8.8.8") is False
    assert qr_service.is_school_subnet("not-an-ip") is False
    assert qr_service.is_school_subnet("") is False


def test_is_school_subnet_env_override(monkeypatch):
    monkeypatch.setattr(qr_service, "SCHOOL_SUBNET", "10.0.0.0/8")
    assert qr_service.is_school_subnet("10.1.2.3") is True
    assert qr_service.is_school_subnet("192.168.1.2") is False
    # Loopback stays accepted regardless of the configured subnet.
    assert qr_service.is_school_subnet("127.0.0.1") is True


def test_generate_token_shape():
    token = qr_service.generate_token()
    assert len(token) == 6
    assert token.isalnum() and token.isupper()
    tokens = {qr_service.generate_token() for _ in range(50)}
    assert len(tokens) > 40  # not degenerate


# ---- Router-level tests ----------------------------------------------------

def test_start_and_end_via_api(client):
    response = client.post("/qr-sessions/start", json={"class_name": "Mathematics", "room": "101"})
    assert response.status_code == 200
    body = response.json()
    assert body["class_name"] == "Mathematics"
    session_id = body["id"]

    active = client.get("/qr-sessions/active").json()
    assert active["active"] is True
    assert active["session_id"] == session_id

    token = client.get("/qr-sessions/active/token").json()
    assert token["active"] is True and token["token"]

    end = client.post("/qr-sessions/end", json={"session_id": session_id})
    assert end.status_code == 200
    assert end.json()["total_attendance"] == 0

    assert client.get("/qr-sessions/active").json() == {"active": False}


def test_validate_via_api(client):
    client.post("/qr-sessions/start", json={"class_name": "Biology"})
    token = client.get("/qr-sessions/active/token").json()["token"]

    ok = client.post("/qr-sessions/validate", json={"token": token})
    assert ok.status_code == 200
    assert ok.json()["valid"] is True

    bad = client.post("/qr-sessions/validate", json={"token": "WRONG1"})
    assert bad.status_code == 200
    assert bad.json()["valid"] is False

    none = client.post("/qr-sessions/validate", json={"token": "ABC123"})
    assert none.status_code == 200
    assert none.json()["valid"] is False


def test_qr_png_requires_active_session(client):
    response = client.get("/qr-sessions/active/qr.png")
    assert response.status_code == 404

    client.post("/qr-sessions/start", json={"class_name": "Mathematics"})
    response = client.get("/qr-sessions/active/qr.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_start_requires_class_name(client):
    response = client.post("/qr-sessions/start", json={"class_name": "   "})
    assert response.status_code == 400