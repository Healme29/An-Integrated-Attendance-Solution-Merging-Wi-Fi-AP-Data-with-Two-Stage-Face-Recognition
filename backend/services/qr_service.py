"""Rotating QR session service.

A class session is opened by the teacher from the dashboard. While active, it
exposes a short-lived token that the dashboard renders as a QR code and
refreshes every QR_ROTATION_SECONDS. Students scan the QR in the classroom;
the scanned token is accepted for QR_GRACE_SECONDS after the rotation so slow
scans or network lag do not produce false rejections.

A check-in additionally requires the request to come from the school Wi-Fi
subnet (SCHOOL_SUBNET) - proof that the phone is on the school network.

Phase flow (S6):
  - 'start' : teacher pressed Start Class Session; QR rotates; students scan
              once for start selfie -> status 'partial' (yellow)
  - 'end'   : teacher pressed Start Final Attendance; QR rotates again; students
              scan again for end selfie -> status 'verified' (green)
  - 'closed': teacher pressed End Session; no more check-ins accepted.
"""
import ipaddress
import secrets
from datetime import datetime, timedelta

from config import (
    QR_TOKEN_LENGTH,
    QR_GRACE_SECONDS,
    QR_ROTATION_SECONDS,
    SCHOOL_SUBNET,
    now_local,
)
from models.database import get_db

_TOKEN_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no easy-to-confuse chars


def generate_token() -> str:
    """Random uppercase alphanumeric token (unambiguous characters)."""
    return "".join(secrets.choice(_TOKEN_ALPHABET) for _ in range(QR_TOKEN_LENGTH))


def is_school_subnet(ip_address_str: str) -> bool:
    """True when the client IP is inside the configured school subnet.

    Loopback is always accepted so local demos/tests on the same machine work.
    """
    if not ip_address_str:
        return False
    try:
        ip = ipaddress.ip_address(ip_address_str.split("%")[0])  # strip zone id
    except ValueError:
        return False
    if ip.is_loopback:
        return True
    try:
        network = ipaddress.ip_network(SCHOOL_SUBNET, strict=False)
    except ValueError:
        return ip.is_private
    return ip in network


def _parse_ts(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


async def create_session(class_name: str, room: str | None = None, created_by: str | None = None, class_id: int | None = None) -> dict:
    """Start a new class session in 'start' phase, closing any session still active."""
    db = await get_db()
    now = now_local()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    try:
        # One active session at a time: auto-close a forgotten session.
        await db.execute(
            """UPDATE qr_sessions
                  SET is_active = 0, ended_at = ?, phase = 'closed'
                WHERE is_active = 1 AND ended_at IS NULL""",
            (timestamp,),
        )
        await db.execute(
            """INSERT INTO qr_sessions
                   (token, token_rotated_at, created_by, class_id, class_name, room, started_at, is_active, phase)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, 'start')""",
            (generate_token(), timestamp, created_by, class_id, class_name, room, timestamp),
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT * FROM qr_sessions WHERE is_active = 1 ORDER BY id DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        return dict(row)
    finally:
        await db.close()


async def get_active_session() -> dict | None:
    """The single active session, or None."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM qr_sessions WHERE is_active = 1 AND ended_at IS NULL ORDER BY id DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def current_token(rotate: bool = True) -> dict | None:
    """Active session with a fresh token.

    Rotates the token when the last rotation is older than
    QR_ROTATION_SECONDS (unless rotate=False). The previous token is kept in
    prev_token so scans in flight stay valid for the grace period.
    """
    session = await get_active_session()
    if not session:
        return None
    if not rotate:
        return session

    rotated_at = _parse_ts(session["token_rotated_at"])
    if now_local() - rotated_at >= timedelta(seconds=QR_ROTATION_SECONDS):
        db = await get_db()
        try:
            timestamp = now_local().strftime("%Y-%m-%d %H:%M:%S")
            await db.execute(
                "UPDATE qr_sessions SET prev_token = ?, token = ?, token_rotated_at = ? WHERE id = ?",
                (session["token"], generate_token(), timestamp, session["id"]),
            )
            await db.commit()
        finally:
            await db.close()
        session = await get_active_session()
    return session


async def validate_token(token: str) -> dict:
    """Validate a scanned QR token against the active session.

    Accepts the current token, or the previous token while it is still inside
    the grace period after the rotation.
    """
    session = await current_token(rotate=False)
    if not session:
        return {"valid": False, "message": "No active class session"}
    if not token or token.strip() == "":
        return {"valid": False, "message": "Empty token"}

    token = token.strip()
    if token == session["token"]:
        return {
            "valid": True,
            "session_id": session["id"],
            "class_name": session["class_name"],
            "room": session["room"],
            "phase": session.get("phase", "start"),
        }

    # Grace window: the previous token stays valid shortly after rotating.
    if session["prev_token"] and token == session["prev_token"]:
        rotated_at = _parse_ts(session["token_rotated_at"])
        if now_local() - rotated_at <= timedelta(seconds=QR_GRACE_SECONDS):
            return {
                "valid": True,
                "session_id": session["id"],
                "class_name": session["class_name"],
                "room": session["room"],
                "phase": session.get("phase", "start"),
            }
    return {"valid": False, "message": "Invalid or expired QR code"}


async def set_phase(session_id: int, phase: str) -> dict | None:
    """Move a session to a new phase ('start' | 'end' | 'closed') and rotate its token."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM qr_sessions WHERE id = ?", (session_id,))
        session = await cursor.fetchone()
        if not session:
            return None
        timestamp = now_local().strftime("%Y-%m-%d %H:%M:%S")
        await db.execute(
            """UPDATE qr_sessions
                  SET phase = ?, token = ?, token_rotated_at = ?, prev_token = ?
                WHERE id = ?""",
            (phase, generate_token(), timestamp, None, session_id),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM qr_sessions WHERE id = ?", (session_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def end_session(session_id: int | None = None) -> dict | None:
    """Close the active (or given) session. Returns (session, attendance_count)."""
    db = await get_db()
    try:
        if session_id is not None:
            cursor = await db.execute("SELECT * FROM qr_sessions WHERE id = ?", (session_id,))
        else:
            cursor = await db.execute(
                "SELECT * FROM qr_sessions WHERE is_active = 1 AND ended_at IS NULL ORDER BY id DESC LIMIT 1"
            )
        session = await cursor.fetchone()
        if not session:
            return None
        session = dict(session)
        timestamp = now_local().strftime("%Y-%m-%d %H:%M:%S")
        await db.execute(
            "UPDATE qr_sessions SET is_active = 0, ended_at = ?, phase = 'closed' WHERE id = ?",
            (timestamp, session["id"]),
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT COUNT(*) FROM attendance WHERE qr_session_id = ?", (session["id"],)
        )
        session["total_attendance"] = (await cursor.fetchone())[0]
        session["ended_at"] = timestamp
        return session
    finally:
        await db.close()
