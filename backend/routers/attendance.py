"""Attendance check-in, roster, manual override, history, and CSV export."""
import asyncio
import csv
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File

from config import MAX_CONCURRENT_RECOGNITIONS, MAX_UPLOAD_BYTES, now_local
from models.database import get_db
from models.schemas import AttendanceResponse, ManualAttendanceRequest, RosterStudent
from routers.teachers import require_teacher
from services.attendance import recognize_face
from services.photo_guard import assert_not_replayed, fingerprint, record as record_photo
from services.qr_service import get_session, is_school_subnet, validate_token

router = APIRouter(prefix="/attendance", tags=["attendance"])
_recognition_slots = asyncio.Semaphore(MAX_CONCURRENT_RECOGNITIONS)


def _student_status(att: dict, session: dict) -> str:
    if att["manual"] or att["end"]:
        return "verified"
    if att["start"]:
        return "partial"
    if session["is_active"] and session.get("phase") in ("start", "spot"):
        return "pending"
    return "absent"


async def _roster_rows(db, session_id: int) -> list[dict]:
    """One dictionary per enrolled student, always sorted by NIM."""
    cursor = await db.execute("SELECT * FROM qr_sessions WHERE id = ?", (session_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Class session not found")
    session = dict(row)
    class_id = session.get("class_id")

    if class_id is not None:
        cursor = await db.execute(
            """SELECT st.id AS student_id, st.name AS student_name, st.nim AS student_nim
               FROM class_students cs JOIN students st ON cs.student_id = st.id
               WHERE cs.class_id = ? ORDER BY st.nim""",
            (class_id,),
        )
    else:
        # Legacy sessions have no class. Preserve their data for history/export;
        # all newly created sessions always have a class roster.
        cursor = await db.execute(
            "SELECT id AS student_id, name AS student_name, nim AS student_nim FROM students ORDER BY nim"
        )
    students = [dict(row) for row in await cursor.fetchall()]

    cursor = await db.execute(
        """SELECT student_id, check_type, spot_round, status, timestamp, confidence,
                  faces_detected, manual_by, manual_at, manual_reason
           FROM attendance WHERE qr_session_id = ?""",
        (session_id,),
    )
    att_map: dict[int, dict] = {}
    for row in await cursor.fetchall():
        sid = row["student_id"]
        att = att_map.setdefault(
            sid, {"start": None, "end": None, "manual": None, "spots": []}
        )
        check_type = row["check_type"] or "start"
        if check_type in ("start", "end", "manual"):
            att[check_type] = dict(row)
        elif check_type == "spot":
            att["spots"].append(dict(row))

    roster = []
    for student in students:
        sid = student["student_id"]
        att = att_map.get(sid, {"start": None, "end": None, "manual": None, "spots": []})
        start = att["start"] or {}
        end = att["end"] or {}
        roster.append({
            "id": sid,
            "student_id": sid,
            "student_name": student["student_name"] or "",
            "student_nim": student["student_nim"] or "",
            "status": _student_status(att, session),
            "start_time": start.get("timestamp"),
            "end_time": end.get("timestamp"),
            "start_confidence": start.get("confidence"),
            "end_confidence": end.get("confidence"),
            "faces_detected_start": start.get("faces_detected") or 0,
            "faces_detected_end": end.get("faces_detected") or 0,
            "manual": att["manual"] is not None,
            "spot_checks": len(att["spots"]),
            "class_name": session["class_name"],
            "room": session["room"],
        })
    return roster


async def _recognize_with_limit(contents: bytes) -> dict:
    if _recognition_slots.locked():
        raise HTTPException(
            status_code=429,
            detail="Server is busy processing other selfies. Please try again in a few seconds.",
            headers={"Retry-After": "3"},
        )
    async with _recognition_slots:
        return await recognize_face(contents)


@router.post("/check-qr")
async def check_attendance_qr(
    request: Request,
    student_id: int,
    token: str,
    file: UploadFile = File(...),
):
    """Record one start, spot, or end check-in using QR + subnet + face proof."""
    client_ip = request.client.host if request.client else None
    if not is_school_subnet(client_ip):
        raise HTTPException(status_code=403, detail="You are not connected to the school network.")

    validation = await validate_token(token)
    if not validation.get("valid"):
        raise HTTPException(status_code=400, detail=validation.get("message") or "Invalid or expired QR code")
    session_id = validation["session_id"]
    phase = validation["phase"]
    spot_round = validation.get("spot_round", 0)

    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM students WHERE id = ?", (student_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Student not found")
        session = await get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Class session not found")
        class_id = session.get("class_id")
        if class_id is not None:
            cursor = await db.execute(
                "SELECT id FROM class_students WHERE class_id = ? AND student_id = ?",
                (class_id, student_id),
            )
            if not await cursor.fetchone():
                raise HTTPException(status_code=403, detail="You are not enrolled in this class")

        cursor = await db.execute(
            """SELECT id FROM attendance
               WHERE student_id = ? AND qr_session_id = ?
                 AND check_type = ? AND spot_round = ?""",
            (student_id, session_id, phase, spot_round if phase == "spot" else 0),
        )
        if await cursor.fetchone():
            label = "spot check" if phase == "spot" else f"{phase} check-in"
            raise HTTPException(status_code=409, detail=f"Already checked in for this {label}")

        if phase in ("spot", "end"):
            cursor = await db.execute(
                """SELECT id FROM attendance
                   WHERE student_id = ? AND qr_session_id = ? AND check_type = 'start'""",
                (student_id, session_id),
            )
            if not await cursor.fetchone():
                raise HTTPException(
                    status_code=409,
                    detail="Complete the start check-in before this QR phase",
                )
    finally:
        await db.close()

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image is too large")
    if not (
        contents.startswith(b"\xff\xd8\xff")
        or contents.startswith(b"\x89PNG\r\n\x1a\n")
    ):
        raise HTTPException(status_code=400, detail="Unsupported image format. Use JPEG or PNG")

    recognition = await _recognize_with_limit(contents)
    if not recognition["recognized"]:
        reason = recognition.get("reason", "unknown")
        messages = {
            "multiple_faces_detected": "Multiple faces detected. Take a selfie alone, with only your own face in frame.",
            "no_face_detected": "No face detected. Center your face in the camera and try again.",
            "liveness_failed": "The selfie did not pass the real-face check. Use the live camera, not a photo or screen.",
            "no_match": "Face not recognized. Ask the teacher to check your face enrollment.",
        }
        raise HTTPException(status_code=400, detail=messages.get(reason, f"Face not recognized: {reason}"))
    if recognition["student_id"] != student_id:
        raise HTTPException(
            status_code=403,
            detail="Identity mismatch: this face does not belong to the logged-in student",
        )

    sha = fingerprint(contents)
    try:
        assert_not_replayed(sha, student_id)
    except ValueError:
        raise HTTPException(
            status_code=409,
            detail="This exact photo was already used. Capture a fresh selfie in the app.",
        )

    timestamp = now_local().strftime("%Y-%m-%d %H:%M:%S")
    response_status = "verified" if phase == "end" else "partial"
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO attendance
               (student_id, qr_session_id, check_type, spot_round, confidence,
                ip_address, status, timestamp, faces_detected)
               VALUES (?, ?, ?, ?, ?, ?, 'verified', ?, ?)""",
            (
                student_id, session_id, phase,
                spot_round if phase == "spot" else 0,
                recognition["confidence"], client_ip, timestamp,
                recognition.get("faces_detected", 0),
            ),
        )
        await db.commit()
        att_id = cursor.lastrowid
        cursor = await db.execute(
            """SELECT st.name AS student_name, qs.class_name, qs.room
               FROM qr_sessions qs, students st WHERE qs.id = ? AND st.id = ?""",
            (session_id, student_id),
        )
        info = await cursor.fetchone()
    finally:
        await db.close()

    record_photo(sha, student_id, session_id, phase)
    return {
        "id": att_id,
        "student_id": student_id,
        "student_name": info["student_name"] if info else None,
        "qr_session_id": session_id,
        "check_type": phase,
        "spot_round": spot_round if phase == "spot" else 0,
        "confidence": recognition["confidence"],
        "ip_address": client_ip,
        "status": response_status,
        "timestamp": timestamp,
        "class_name": info["class_name"] if info else validation.get("class_name"),
        "room": info["room"] if info else validation.get("room"),
        "faces_detected": recognition.get("faces_detected", 0),
    }


@router.post("/manual")
async def manual_attendance(data: ManualAttendanceRequest, teacher: str = Depends(require_teacher)):
    """One-click teacher override after class. No prior attendance is required."""
    session = await get_session(data.qr_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Class session not found")
    if session["is_active"] and session.get("phase") != "closed":
        raise HTTPException(status_code=409, detail="End the class session before marking manual attendance")

    db = await get_db()
    try:
        class_id = session.get("class_id")
        if class_id is not None:
            cursor = await db.execute(
                """SELECT st.id FROM students st
                   JOIN class_students cs ON cs.student_id = st.id
                   WHERE cs.class_id = ? AND st.id = ?""",
                (class_id, data.student_id),
            )
        else:
            cursor = await db.execute("SELECT id FROM students WHERE id = ?", (data.student_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Student is not enrolled in this class")
        cursor = await db.execute(
            """SELECT id FROM attendance
               WHERE student_id = ? AND qr_session_id = ?
                 AND check_type IN ('end', 'manual')""",
            (data.student_id, data.qr_session_id),
        )
        if await cursor.fetchone():
            raise HTTPException(status_code=409, detail="Student is already verified for this session")

        timestamp = now_local().strftime("%Y-%m-%d %H:%M:%S")
        cursor = await db.execute(
            """INSERT INTO attendance
               (student_id, qr_session_id, check_type, confidence, ip_address,
                status, timestamp, manual_by, manual_at, manual_reason)
               VALUES (?, ?, 'manual', NULL, NULL, 'verified', ?, ?, ?, ?)""",
            (data.student_id, data.qr_session_id, timestamp, teacher, timestamp, data.reason),
        )
        await db.commit()
        return {
            "id": cursor.lastrowid,
            "student_id": data.student_id,
            "qr_session_id": data.qr_session_id,
            "check_type": "manual",
            "status": "verified",
            "timestamp": timestamp,
            "manual": True,
            "reason": data.reason,
        }
    finally:
        await db.close()


@router.get("/roster", response_model=list[RosterStudent])
async def get_roster(qr_session_id: int, teacher: str = Depends(require_teacher)):
    db = await get_db()
    try:
        return await _roster_rows(db, qr_session_id)
    finally:
        await db.close()


@router.get("/today", response_model=list[AttendanceResponse])
async def get_today_attendance(qr_session_id: Optional[int] = None):
    db = await get_db()
    today = now_local().strftime("%Y-%m-%d")
    query = """
        SELECT a.*, st.name AS student_name, qs.class_name, qs.room
        FROM attendance a
        LEFT JOIN students st ON a.student_id = st.id
        LEFT JOIN qr_sessions qs ON a.qr_session_id = qs.id
        WHERE DATE(a.timestamp) = ?
    """
    params: list = [today]
    if qr_session_id is not None:
        query += " AND a.qr_session_id = ?"
        params.append(qr_session_id)
    query += " ORDER BY a.timestamp DESC"
    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    await db.close()
    return [dict(row) for row in rows]


@router.get("/export/csv")
async def export_attendance_csv(date: str | None = None, qr_session_id: int | None = None):
    """Roster CSV for one session; raw check-in CSV when no session is supplied."""
    if date is None:
        date = now_local().strftime("%Y-%m-%d")
    else:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="date must be in YYYY-MM-DD format")

    output = io.StringIO()
    writer = csv.writer(output)
    db = await get_db()
    try:
        if qr_session_id is not None:
            rows = await _roster_rows(db, qr_session_id)
            headers = [
                "nim", "student_name", "class_name", "room",
                "start_time", "end_time", "start_confidence", "end_confidence",
                "status", "manual", "spot_checks",
                "faces_detected_start", "faces_detected_end",
            ]
            writer.writerow(headers)
            for r in rows:
                writer.writerow([
                    r["student_nim"], r["student_name"], r["class_name"], r["room"] or "",
                    r["start_time"] or "", r["end_time"] or "",
                    r["start_confidence"] if r["start_confidence"] is not None else "",
                    r["end_confidence"] if r["end_confidence"] is not None else "",
                    r["status"], "yes" if r["manual"] else "no", r["spot_checks"],
                    r["faces_detected_start"], r["faces_detected_end"],
                ])
            filename = f"attendance_roster_session{qr_session_id}.csv"
        else:
            cursor = await db.execute(
                """SELECT a.id, a.timestamp, a.check_type, a.spot_round,
                          a.student_id, st.name AS student_name, st.nim,
                          a.qr_session_id, qs.class_name, qs.room,
                          a.confidence, a.ip_address, a.status, a.faces_detected,
                          a.manual_by, a.manual_at, a.manual_reason
                   FROM attendance a
                   LEFT JOIN students st ON a.student_id = st.id
                   LEFT JOIN qr_sessions qs ON a.qr_session_id = qs.id
                   WHERE DATE(a.timestamp) = ? ORDER BY a.timestamp""",
                [date],
            )
            rows = await cursor.fetchall()
            headers = [
                "id", "timestamp", "check_type", "spot_round", "student_id",
                "student_name", "nim", "qr_session_id", "class_name", "room",
                "confidence", "ip_address", "status", "faces_detected",
                "manual_by", "manual_at", "manual_reason",
            ]
            writer.writerow(headers)
            for row in rows:
                record = dict(row)
                writer.writerow([record.get(col, "") if record.get(col) is not None else "" for col in headers])
            filename = f"attendance_{date}.csv"
    finally:
        await db.close()

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/student/{student_id}")
async def get_student_attendance(
    student_id: int,
    response: Response,
    limit: int = 100,
    offset: int = 0,
    date_from: str | None = None,
    date_to: str | None = None,
):
    if not 1 <= limit <= 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset must be >= 0")
    for name, value in (("date_from", date_from), ("date_to", date_to)):
        if value is not None:
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail=f"{name} must be in YYYY-MM-DD format")

    where = "a.student_id = ?"
    params: list = [student_id]
    if date_from is not None:
        where += " AND DATE(a.timestamp) >= ?"
        params.append(date_from)
    if date_to is not None:
        where += " AND DATE(a.timestamp) <= ?"
        params.append(date_to)

    db = await get_db()
    base = f"FROM attendance a LEFT JOIN qr_sessions qs ON a.qr_session_id = qs.id WHERE {where}"
    count_cursor = await db.execute(f"SELECT COUNT(*) {base}", params)
    total = (await count_cursor.fetchone())[0]
    cursor = await db.execute(
        f"SELECT a.*, qs.class_name, qs.room {base} ORDER BY a.timestamp DESC LIMIT ? OFFSET ?",
        params + [limit, offset],
    )
    rows = await cursor.fetchall()
    await db.close()
    response.headers["X-Total-Count"] = str(total)
    return [dict(row) for row in rows]
