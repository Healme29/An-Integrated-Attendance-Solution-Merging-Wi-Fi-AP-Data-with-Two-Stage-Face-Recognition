from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response, UploadFile, File
from models.schemas import (
    AttendanceResponse,
    ManualAttendanceRequest,
    RosterStudent,
)
from models.database import get_db
from services.attendance import recognize_face
from services.qr_service import validate_token, is_school_subnet
from config import now_local

router = APIRouter(prefix="/attendance", tags=["attendance"])


# ---------------------------------------------------------------------------
# Helper: fetch all students with their latest attendance for a session
# ---------------------------------------------------------------------------
async def _build_roster(db, session_id: int) -> list[RosterStudent]:
    """Return every student in the session's class with their attendance status."""
    # Find the class_id for this session
    cursor = await db.execute(
        "SELECT class_id FROM qr_sessions WHERE id = ?", (session_id,)
    )
    row = await cursor.fetchone()
    class_id = row["class_id"] if row else None

    if class_id is None:
        # Fallback: no class -> empty roster
        return []

    # All students enrolled in this class
    cursor = await db.execute(
        """
        SELECT cs.student_id AS student_id, st.name AS student_name, st.nim AS student_nim
        FROM class_students cs
        JOIN students st ON cs.student_id = st.id
        WHERE cs.class_id = ?
        ORDER BY st.nim
        """,
        (class_id,),
    )
    students = await cursor.fetchall()

    # Attendance for this session
    cursor = await db.execute(
        """
        SELECT student_id, check_type, status, timestamp, confidence,
               faces_detected, manual_by, manual_at, manual_reason
        FROM attendance
        WHERE qr_session_id = ?
        """,
        (session_id,),
    )
    att_rows = await cursor.fetchall()
    att_map: dict[int, dict] = {}
    for r in att_rows:
        sid = r["student_id"]
        if sid not in att_map:
            att_map[sid] = {
                "start": None,
                "end": None,
                "manual": None,
            }
        ct = r["check_type"] or "qr"
        if ct == "manual":
            att_map[sid]["manual"] = dict(r)
        elif ct == "start":
            att_map[sid]["start"] = dict(r)
        elif ct == "end":
            att_map[sid]["end"] = dict(r)

    roster: list[RosterStudent] = []
    for s in students:
        sid = s["student_id"]
        att = att_map.get(sid, {"start": None, "end": None, "manual": None})

        status = "absent"
        start_time = None
        end_time = None
        start_confidence = None
        end_confidence = None
        faces_detected_start = 0
        faces_detected_end = 0
        manual = False

        if att["manual"]:
            status = "verified"
            manual = True
        elif att["end"]:
            status = "verified"
            end_time = att["end"]["timestamp"]
            end_confidence = att["end"]["confidence"]
            faces_detected_end = att["end"]["faces_detected"] or 0
        elif att["start"]:
            status = "partial"
            start_time = att["start"]["timestamp"]
            start_confidence = att["start"]["confidence"]
            faces_detected_start = att["start"]["faces_detected"] or 0

        roster.append(
            RosterStudent(
                id=sid,
                student_id=sid,
                student_name=s["student_name"] or "",
                student_nim=s["student_nim"] or "",
                status=status,
                start_time=start_time,
                end_time=end_time,
                start_confidence=start_confidence,
                end_confidence=end_confidence,
                faces_detected_start=faces_detected_start,
                faces_detected_end=faces_detected_end,
                manual=manual,
            )
        )

    return roster


# ---------------------------------------------------------------------------
# QR check-in with phase awareness (start / end)
# ---------------------------------------------------------------------------
@router.post("/check-qr")
async def check_attendance_qr(
    request: Request,
    student_id: int,
    token: str,
    file: UploadFile = File(...),
):
    """QR-based check-in for the logged-in student.

    Phase rules:
      - 'start' phase: first selfie -> inserts check_type='start', status='partial'
      - 'end' phase:   requires a prior 'start' row for this student/session;
                       inserts check_type='end', status='verified'
      - 'closed' phase: rejected

    Attendance is granted only when ALL conditions hold:
    1. The phone reaches this server from the school Wi-Fi subnet.
    2. The scanned QR token matches the active session (grace included).
    3. The uploaded selfie matches the face enrolled for `student_id`
       (identity binding).
    4. The student has not already checked into this phase/session.
    """
    db = await get_db()
    cursor = await db.execute("SELECT id FROM students WHERE id = ?", (student_id,))
    student_row = await cursor.fetchone()
    await db.close()
    if not student_row:
        raise HTTPException(status_code=404, detail="Student not found")

    # 1. School network proof.
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
    phase = validation.get("phase", "start")

    if phase == "closed":
        raise HTTPException(status_code=400, detail="Class session has ended. No more check-ins accepted.")

    # 3. Face recognition with identity binding.
    contents = await file.read()
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

    # 4. Duplicate check per phase/session.
    db = await get_db()
    cursor = await db.execute(
        """SELECT id FROM attendance
           WHERE student_id = ? AND qr_session_id = ?
             AND (check_type = ? OR (check_type = 'qr' AND ? = 'start'))""",
        (student_id, session_id, phase if phase in ("start", "end") else "start", phase),
    )
    duplicate = await cursor.fetchone()
    if duplicate:
        await db.close()
        raise HTTPException(status_code=409, detail=f"Already checked in for this {phase} phase")

    # In 'end' phase, require a prior start check-in.
    if phase == "end":
        cursor = await db.execute(
            """SELECT id FROM attendance
               WHERE student_id = ? AND qr_session_id = ?
                 AND (check_type = 'start' OR check_type = 'qr')""",
            (student_id, session_id),
        )
        has_start = await cursor.fetchone()
        if not has_start:
            await db.close()
            raise HTTPException(
                status_code=409,
                detail="No start check-in found for this session. Scan the start QR first.",
            )

    # Store an explicit local timestamp.
    # Attendance record status is always 'verified' for a successful check-in;
    # the roster view computes 'partial' vs 'verified' from check_type combos.
    timestamp = now_local().strftime("%Y-%m-%d %H:%M:%S")
    await db.execute(
        """INSERT INTO attendance
               (student_id, qr_session_id, check_type, confidence, ip_address, status, timestamp, faces_detected)
            VALUES (?, ?, ?, ?, ?, 'verified', ?, ?)""",
        (
            student_id,
            session_id,
            phase,
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

    return {
        "id": att_id,
        "student_id": student_id,
        "student_name": info["student_name"] if info else None,
        "qr_session_id": session_id,
        "check_type": phase,
        "confidence": recognition["confidence"],
        "ip_address": client_ip,
        "status": "verified",
        "timestamp": timestamp,
        "class_name": info["class_name"] if info else validation.get("class_name"),
        "room": info["room"] if info else validation.get("room"),
        "faces_detected": recognition.get("faces_detected", 0),
    }


# ---------------------------------------------------------------------------
# Manual attendance (S6) — teacher marks a student verified
# ---------------------------------------------------------------------------
@router.post("/manual")
async def manual_attendance(
    data: ManualAttendanceRequest,
    teacher: str = "teacher",  # TODO: replace with real auth from S5
):
    """Teacher manually marks a student as verified (verified status, no selfie).

    Only usable after class or when the student cannot self-check-in.
    Creates a check_type='manual' row with status='verified'.
    """
    db = await get_db()
    # Verify student exists
    cursor = await db.execute("SELECT id FROM students WHERE id = ?", (data.student_id,))
    if not await cursor.fetchone():
        await db.close()
        raise HTTPException(status_code=404, detail="Student not found")

    # Find the latest session for this student (any session)
    cursor = await db.execute(
        """SELECT qs.id AS session_id, qs.class_name, qs.room
             FROM attendance a
             JOIN qr_sessions qs ON a.qr_session_id = qs.id
            WHERE a.student_id = ?
            ORDER BY a.timestamp DESC
            LIMIT 1""",
        (data.student_id,),
    )
    row = await cursor.fetchone()
    if not row:
        await db.close()
        raise HTTPException(status_code=404, detail="Student has no attendance record to attach manual mark to")
    session_id = row["session_id"]

    # Prevent duplicate manual marks for same session
    cursor = await db.execute(
        """SELECT id FROM attendance
           WHERE student_id = ? AND qr_session_id = ? AND check_type = 'manual'""",
        (data.student_id, session_id),
    )
    if await cursor.fetchone():
        await db.close()
        raise HTTPException(status_code=409, detail="Manual attendance already recorded for this student/session")

    timestamp = now_local().strftime("%Y-%m-%d %H:%M:%S")
    await db.execute(
        """INSERT INTO attendance
               (student_id, qr_session_id, check_type, confidence, ip_address, status, timestamp,
                manual_by, manual_at, manual_reason)
            VALUES (?, ?, 'manual', NULL, NULL, 'verified', ?, ?, ?, ?)""",
        (
            data.student_id,
            session_id,
            timestamp,
            teacher,
            timestamp,
            data.reason,
        ),
    )
    await db.commit()
    cursor = await db.execute("SELECT last_insert_rowid()")
    att_id = (await cursor.fetchone())[0]
    await db.close()

    return {
        "id": att_id,
        "student_id": data.student_id,
        "qr_session_id": session_id,
        "status": "verified",
        "timestamp": timestamp,
        "manual": True,
        "reason": data.reason,
    }


# ---------------------------------------------------------------------------
# Roster (S3) — one row per student in the session's class
# ---------------------------------------------------------------------------
@router.get("/roster", response_model=list[RosterStudent])
async def get_roster(qr_session_id: int):
    """Return every student in the session's class with their attendance status."""
    db = await get_db()
    try:
        roster = await _build_roster(db, qr_session_id)
        return [r.model_dump() for r in roster]
    finally:
        await db.close()


# ---------------------------------------------------------------------------
# Today's attendance (unchanged)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Export CSV (S10) — roster-based: one row per student
# ---------------------------------------------------------------------------
@router.get("/export/csv")
async def export_attendance_csv(date: str | None = None, qr_session_id: int | None = None):
    """Export attendance records as CSV.

    If qr_session_id is given: one row per enrolled student in that session
    (start + end times, confidences, status). Otherwise: raw attendance rows.
    """
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

    if qr_session_id is not None:
        # Roster-based export: one row per student in the session's class
        cursor = await db.execute(
            "SELECT class_id FROM qr_sessions WHERE id = ?", (qr_session_id,)
        )
        class_row = await cursor.fetchone()
        class_id = class_row["class_id"] if class_row else None

        if class_id is not None:
            query = """
                SELECT st.nim, st.name,
                       MAX(CASE WHEN a.check_type IN ('start','qr') THEN a.timestamp END) AS start_time,
                       MAX(CASE WHEN a.check_type = 'end' THEN a.timestamp END) AS end_time,
                       MAX(CASE WHEN a.check_type IN ('start','qr') THEN a.confidence END) AS start_confidence,
                       MAX(CASE WHEN a.check_type = 'end' THEN a.confidence END) AS end_confidence,
                       MAX(CASE WHEN a.check_type = 'manual' THEN 'manual'
                                WHEN MAX(CASE WHEN a.check_type = 'end' THEN 1 END) = 1 THEN 'verified'
                                WHEN MAX(CASE WHEN a.check_type IN ('start','qr') THEN 1 END) = 1 THEN 'partial'
                                ELSE 'absent' END) AS status,
                       MAX(CASE WHEN a.check_type = 'manual' THEN 1 ELSE 0 END) AS is_manual,
                       MAX(CASE WHEN a.check_type IN ('start','qr') THEN a.faces_detected END) AS faces_start,
                       MAX(CASE WHEN a.check_type = 'end' THEN a.faces_detected END) AS faces_end
                FROM class_students cs
                JOIN students st ON cs.student_id = st.id
                LEFT JOIN attendance a ON a.student_id = st.id AND a.qr_session_id = ?
                WHERE cs.class_id = ?
                GROUP BY st.id, st.nim, st.name
                ORDER BY st.nim
            """
            cursor = await db.execute(query, (qr_session_id, class_id))
        else:
            cursor = await db.execute(
                """SELECT st.nim, st.name, NULL AS start_time, NULL AS end_time,
                          NULL AS start_confidence, NULL AS end_confidence,
                          'absent' AS status, 0 AS is_manual,
                          0 AS faces_start, 0 AS faces_end
                   FROM students st ORDER BY st.nim"""
            )
        rows = await cursor.fetchall()
        await db.close()

        output = io.StringIO()
        writer = csv.writer(output)
        headers = [
            "nim", "student_name", "start_time", "end_time",
            "start_confidence", "end_confidence", "status",
            "manual", "faces_detected_start", "faces_detected_end",
        ]
        writer.writerow(headers)
        for r in rows:
            writer.writerow([
                r["nim"], r["name"],
                r["start_time"] or "", r["end_time"] or "",
                r["start_confidence"] or "", r["end_confidence"] or "",
                r["status"],
                "yes" if r["is_manual"] else "no",
                r["faces_start"] or 0, r["faces_end"] or 0,
            ])

        filename = f"attendance_roster_{date}_session{qr_session_id}.csv"
    else:
        # Raw attendance rows export
        query = """
            SELECT a.id, a.timestamp, a.check_type, a.student_id, st.name AS student_name, st.nim,
                   a.qr_session_id, qs.class_name, qs.room,
                   a.confidence, a.ip_address, a.status, a.faces_detected,
                   a.manual_by, a.manual_reason
            FROM attendance a
            LEFT JOIN students st ON a.student_id = st.id
            LEFT JOIN qr_sessions qs ON a.qr_session_id = qs.id
            WHERE DATE(a.timestamp) = ?
            ORDER BY a.timestamp
        """
        cursor = await db.execute(query, [date])
        rows = await cursor.fetchall()
        await db.close()

        output = io.StringIO()
        writer = csv.writer(output)
        headers = [
            "id", "timestamp", "check_type", "student_id", "student_name", "nim",
            "qr_session_id", "class_name", "room",
            "confidence", "ip_address", "status", "faces_detected",
            "manual_by", "manual_reason",
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


# ---------------------------------------------------------------------------
# Student attendance history (unchanged)
# ---------------------------------------------------------------------------
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
