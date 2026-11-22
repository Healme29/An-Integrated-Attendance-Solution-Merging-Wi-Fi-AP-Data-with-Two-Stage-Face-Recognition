from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response, UploadFile, File
from models.schemas import AttendanceResponse
from models.database import get_db
from services.attendance import recognize_face
from services.photo_guard import fingerprint, assert_not_replayed, record as record_photo
from services.qr_service import validate_token, is_school_subnet
from config import now_local

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/check-qr", response_model=AttendanceResponse)
async def check_attendance_qr(
    request: Request,
    student_id: int,
    token: str,
    file: UploadFile = File(...),
):
    """QR-based check-in for the logged-in student.

    Attendance is granted only when ALL conditions hold:
    1. The phone reaches this server from the school Wi-Fi subnet.
    2. The scanned QR token matches the active session (grace included).
    3. The uploaded selfie matches the face enrolled for `student_id`
       (identity binding - a friend holding the phone cannot check in).
    4. The student has not already checked into this session.
    """
    db = await get_db()
    cursor = await db.execute("SELECT id FROM students WHERE id = ?", (student_id,))
    student_row = await cursor.fetchone()
    await db.close()
    if not student_row:
        raise HTTPException(status_code=404, detail="Student not found")

    # 1. School network proof: the request must originate from the school subnet.
    client_ip = request.client.host if request.client else None
    if not is_school_subnet(client_ip):
        raise HTTPException(
            status_code=403,
            detail="You are not connected to the school network.",
        )

    # 2. QR token must belong to the active session (rotation grace applies).
    validation = await validate_token(token)
    if not validation.get("valid"):
        raise HTTPException(status_code=400, detail=validation.get("message") or "Invalid or expired QR code")
    session_id = validation["session_id"]

    # 3. Face recognition with identity binding.
    contents = await file.read()
    sha = fingerprint(contents)
    recognition = await recognize_face(contents)

    if not recognition["recognized"]:
        reason = recognition.get("reason", "unknown")
        if reason == "multiple_faces_detected":
            raise HTTPException(
                status_code=400,
                detail="Multiple faces detected. Take a selfie alone, with only "
                       "your own face in frame."
            )
        raise HTTPException(status_code=400, detail=f"Face not recognized: {reason}")

    if recognition["student_id"] != student_id:
        raise HTTPException(
            status_code=403,
            detail="Identity mismatch: the face in this photo does not belong "
                   "to the logged-in student. Refusing to record attendance."
        )

    # Capture-replay tripwire: the exact same photo file may only be accepted
    # once per day per student (blocks shared-file identity swaps).
    try:
        assert_not_replayed(sha, student_id)
    except ValueError:
        raise HTTPException(
            status_code=409,
            detail="This exact photo was already used for a check-in today — "
                   "capture a fresh selfie in the app."
        )

    # 4. One check-in per session.
    db = await get_db()
    cursor = await db.execute(
        "SELECT id FROM attendance WHERE student_id = ? AND qr_session_id = ?",
        (student_id, session_id),
    )
    duplicate = await cursor.fetchone()
    if duplicate:
        await db.close()
        raise HTTPException(status_code=409, detail="Already checked in for this class session")

    # Store an explicit local timestamp (SQLite's CURRENT_TIMESTAMP is UTC,
    # which would break DATE() comparisons against local class days).
    timestamp = now_local().strftime("%Y-%m-%d %H:%M:%S")
    await db.execute(
        """INSERT INTO attendance
               (student_id, qr_session_id, confidence, ip_address, status, timestamp, faces_detected)
           VALUES (?, ?, ?, ?, 'verified', ?, ?)""",
        (
            student_id,
            session_id,
            recognition["confidence"],
            client_ip,
            timestamp,
            recognition.get("faces_detected", 0),
        ),
    )
    await db.commit()

    cursor = await db.execute("SELECT last_insert_rowid()")
    att_id = (await cursor.fetchone())[0]
    cursor = await db.execute(
        """SELECT st.name AS student_name, qs.class_name, qs.room
             FROM qr_sessions qs, students st
            WHERE qs.id = ? AND st.id = ?""",
        (session_id, student_id),
    )
    info = await cursor.fetchone()
    await db.close()

    record_photo(sha, student_id, session_id, "qr")
    return {
        "id": att_id,
        "student_id": student_id,
        "student_name": info["student_name"] if info else None,
        "qr_session_id": session_id,
        "confidence": recognition["confidence"],
        "ip_address": client_ip,
        "status": "verified",
        "timestamp": timestamp,
        "class_name": info["class_name"] if info else validation.get("class_name"),
        "room": info["room"] if info else validation.get("room"),
        "faces_detected": recognition.get("faces_detected", 0),
    }


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
    """Export attendance records as CSV. Filters: ?date=YYYY-MM-DD&qr_session_id=N"""
    import csv
    import io

    if date is None:
        date = now_local().strftime("%Y-%m-%d")
    else:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="date must be in YYYY-MM-DD format")

    db = await get_db()
    query = """
        SELECT a.id, a.timestamp, a.confidence, a.ip_address, a.status,
               a.student_id, st.name AS student_name, st.nim,
               a.qr_session_id, qs.class_name, qs.room, a.faces_detected
        FROM attendance a
        LEFT JOIN students st ON a.student_id = st.id
        LEFT JOIN qr_sessions qs ON a.qr_session_id = qs.id
        WHERE DATE(a.timestamp) = ?
    """
    params: list = [date]
    if qr_session_id is not None:
        query += " AND a.qr_session_id = ?"
        params.append(qr_session_id)
    query += " ORDER BY a.timestamp"

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    await db.close()

    output = io.StringIO()
    writer = csv.writer(output)
    headers = [
        "id", "timestamp", "student_id", "student_name", "nim",
        "qr_session_id", "class_name", "room",
        "confidence", "ip_address", "status", "faces_detected",
    ]
    writer.writerow(headers)
    for row in rows:
        record = dict(row)
        record["faces_detected"] = record.get("faces_detected") or 0
        writer.writerow([record.get(col, "") for col in headers])

    filename = f"attendance_{date}" + (f"_session{qr_session_id}" if qr_session_id is not None else "") + ".csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
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
    """Student attendance history.

    Optional filters: ?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD
    Pagination: ?limit=1..500&offset=N (total count returned in X-Total-Count).
    """
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
    base = f"FROM attendance a JOIN qr_sessions qs ON a.qr_session_id = qs.id WHERE {where}"

    count_cursor = await db.execute(f"SELECT COUNT(*) {base}", params)
    total = (await count_cursor.fetchone())[0]

    cursor = await db.execute(
        f"SELECT a.*, qs.class_name, qs.room {base} ORDER BY a.timestamp DESC LIMIT ? OFFSET ?",
        params + [limit, offset]
    )
    rows = await cursor.fetchall()
    await db.close()

    response.headers["X-Total-Count"] = str(total)
    return [dict(row) for row in rows]