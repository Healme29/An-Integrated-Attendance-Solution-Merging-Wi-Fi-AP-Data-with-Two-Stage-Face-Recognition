"""Class-session lifecycle and rotating, phase-bound QR tokens.

start  -> students scan QR + selfie (partial)
spot   -> optional mid-class QR + selfie for students with a start row
end    -> students scan a NEW QR + selfie (verified)
closed -> no check-ins accepted
"""
import ipaddress
import secrets
from datetime import datetime, timedelta

from config import (
    FINAL_CHECK_GRACE_MINUTES,
    QR_GRACE_SECONDS,
    QR_ROTATION_SECONDS,
    QR_TOKEN_LENGTH,
    SCHOOL_SUBNET,
    now_local,
)
from models.database import get_db

_TOKEN_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_PHASES = {"start", "spot", "end", "closed"}


def generate_token() -> str:
    return "".join(secrets.choice(_TOKEN_ALPHABET) for _ in range(QR_TOKEN_LENGTH))


def is_school_subnet(ip_address_str: str) -> bool:
    if not ip_address_str:
        return False
    try:
        ip = ipaddress.ip_address(ip_address_str.split("%")[0])
    except ValueError:
        return False
    if ip.is_loopback:
        return True
    try:
        network = ipaddress.ip_network(SCHOOL_SUBNET, strict=False)
    except ValueError:
        return ip.is_private
    return ip in network


def _ts(value: str | datetime | None) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def _now_text() -> str:
    return now_local().strftime("%Y-%m-%d %H:%M:%S")


async def create_session(class_id: int, created_by: str | None = None) -> dict:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM classes WHERE id = ?", (class_id,))
        class_row = await cursor.fetchone()
        if not class_row:
            raise ValueError("Class not found")
        cursor = await db.execute(
            "SELECT COUNT(*) AS total FROM class_students WHERE class_id = ?", (class_id,)
        )
        if (await cursor.fetchone())["total"] == 0:
            raise ValueError("Add at least one student to the class before starting")

        timestamp = _now_text()
        await db.execute(
            """UPDATE qr_sessions
               SET is_active = 0, ended_at = ?, phase = 'closed'
               WHERE is_active = 1 AND ended_at IS NULL""",
            (timestamp,),
        )
        cursor = await db.execute(
            """INSERT INTO qr_sessions
               (token, token_rotated_at, created_by, class_id, class_name, room,
                started_at, phase_started_at, is_active, phase, spot_round)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 'start', 0)""",
            (
                generate_token(), timestamp, created_by, class_id,
                class_row["class_name"], class_row["room"], timestamp, timestamp,
            ),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM qr_sessions WHERE id = ?", (cursor.lastrowid,))
        return dict(await cursor.fetchone())
    finally:
        await db.close()


async def get_active_session() -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT * FROM qr_sessions
               WHERE is_active = 1 AND ended_at IS NULL
               ORDER BY id DESC LIMIT 1"""
        )
        row = await cursor.fetchone()
        if not row:
            return None
        session = dict(row)
        phase_started = _ts(session.get("phase_started_at") or session["started_at"])
        if (
            session.get("phase") == "end"
            and phase_started
            and now_local() - phase_started > timedelta(minutes=FINAL_CHECK_GRACE_MINUTES)
        ):
            timestamp = _now_text()
            await db.execute(
                """UPDATE qr_sessions
                   SET is_active = 0, ended_at = ?, phase = 'closed' WHERE id = ?""",
                (timestamp, session["id"]),
            )
            await db.commit()
            return None
        return session
    finally:
        await db.close()


async def get_session(session_id: int) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM qr_sessions WHERE id = ?", (session_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def list_sessions(limit: int = 10) -> list[dict]:
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT id, class_id, class_name, room, started_at, ended_at,
                      is_active, phase, created_by
               FROM qr_sessions ORDER BY id DESC LIMIT ?""",
            (max(1, min(limit, 50)),),
        )
        return [dict(row) for row in await cursor.fetchall()]
    finally:
        await db.close()


async def current_token(rotate: bool = True) -> dict | None:
    session = await get_active_session()
    if not session or not rotate:
        return session
    rotated_at = _ts(session["token_rotated_at"])
    if now_local() - rotated_at >= timedelta(seconds=QR_ROTATION_SECONDS):
        db = await get_db()
        try:
            timestamp = _now_text()
            await db.execute(
                """UPDATE qr_sessions
                   SET prev_token = token, token = ?, token_rotated_at = ? WHERE id = ?""",
                (generate_token(), timestamp, session["id"]),
            )
            await db.commit()
        finally:
            await db.close()
        session = await get_active_session()
    return session


def _session_payload(session: dict) -> dict:
    return {
        "valid": True,
        "session_id": session["id"],
        "class_name": session["class_name"],
        "room": session["room"],
        "phase": session.get("phase", "start"),
        "spot_round": session.get("spot_round", 0),
    }


async def validate_token(token: str) -> dict:
    session = await current_token(rotate=False)
    if not session:
        return {"valid": False, "message": "No active class session"}
    if not token or not token.strip():
        return {"valid": False, "message": "Empty token"}
    token = token.strip()
    if secrets.compare_digest(token, session["token"]):
        return _session_payload(session)
    if session["prev_token"] and secrets.compare_digest(token, session["prev_token"]):
        rotated_at = _ts(session["token_rotated_at"])
        if now_local() - rotated_at <= timedelta(seconds=QR_GRACE_SECONDS):
            return _session_payload(session)
    return {"valid": False, "message": "Invalid or expired QR code"}


async def set_phase(session_id: int, phase: str, teacher: str | None = None) -> dict | None:
    if phase not in _PHASES:
        raise ValueError("phase must be start, spot, end, or closed")
    session = await get_session(session_id)
    if not session or not session["is_active"]:
        return None
    current = session.get("phase", "start")
    allowed = {
        "start": {"spot", "end", "closed"},
        "spot": {"start", "end", "closed"},
        "end": {"closed"},
    }
    if phase not in allowed.get(current, set()):
        raise ValueError(f"Cannot move from {current} to {phase}")
    if phase == "closed":
        return await end_session(session_id)

    timestamp = _now_text()
    spot_round = session.get("spot_round", 0) + (1 if phase == "spot" else 0)
    db = await get_db()
    try:
        await db.execute(
            """UPDATE qr_sessions
               SET phase = ?, spot_round = ?, phase_started_at = ?,
                   prev_token = NULL, token = ?, token_rotated_at = ?
               WHERE id = ?""",
            (phase, spot_round, timestamp, generate_token(), timestamp, session_id),
        )
        await db.commit()
    finally:
        await db.close()
    return await get_session(session_id)


async def end_session(session_id: int | None = None) -> dict | None:
    db = await get_db()
    try:
        if session_id is not None:
            cursor = await db.execute("SELECT * FROM qr_sessions WHERE id = ?", (session_id,))
        else:
            cursor = await db.execute(
                """SELECT * FROM qr_sessions
                   WHERE is_active = 1 AND ended_at IS NULL ORDER BY id DESC LIMIT 1"""
            )
        row = await cursor.fetchone()
        if not row:
            return None
        session = dict(row)
        timestamp = _now_text()
        await db.execute(
            """UPDATE qr_sessions
               SET is_active = 0, ended_at = ?, phase = 'closed' WHERE id = ?""",
            (timestamp, session["id"]),
        )
        await db.commit()
        cursor = await db.execute(
            """SELECT COUNT(DISTINCT student_id) AS total FROM attendance
               WHERE qr_session_id = ? AND check_type IN ('start', 'end', 'manual')""",
            (session["id"],),
        )
        session["total_attendance"] = (await cursor.fetchone())["total"]
        session["ended_at"] = timestamp
        session["phase"] = "closed"
        session["is_active"] = 0
        return session
    finally:
        await db.close()
