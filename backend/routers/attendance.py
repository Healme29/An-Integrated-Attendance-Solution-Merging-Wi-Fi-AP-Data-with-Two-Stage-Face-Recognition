from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Response
from models.schemas import AttendanceRequest, AttendanceResponse
from models.database import get_db
from services.attendance import recognize_face, mark_attendance, validate_schedule_time
from services.photo_guard import fingerprint, assert_not_replayed, record as record_photo
from config import ATTENDANCE_CHECK_WINDOW_MINUTES, now_local

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/check", response_model=AttendanceResponse)
async def check_attendance(
    student_id: int,
    schedule_id: int,
    check_type: str,
    file: UploadFile = File(...)
):
    """Two-stage check-in for the logged-in student.

    `student_id` is the account that is signed in on the phone. It is not
    trusted on its own: the uploaded selfie must match that same student. This
    closes the "friend's face in front of my camera" hole (see D-003).
    """
    if check_type not in ("start", "end"):
        raise HTTPException(status_code=400, detail="check_type must be 'start' or 'end'")

    db = await get_db()
    cursor = await db.execute("SELECT id FROM students WHERE id = ?", (student_id,))
    student_row = await cursor.fetchone()
    await db.close()
    if not student_row:
        raise HTTPException(status_code=404, detail="Student not found")

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
        raise HTTPException(
            status_code=400,
            detail=f"Face not recognized: {reason}"
        )

    # Identity binding: the face must belong to the account that is logged in.
    # Without this, the endpoint would happily mark the person the camera sees
    # (a friend holding the phone), not the student who signed in.
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

    try:
        await validate_schedule_time(schedule_id)
    except ValueError as e:
        reason = str(e)
        if reason == "schedule_not_found":
            raise HTTPException(status_code=404, detail="Schedule not found")
        if reason == "wrong_day":
            raise HTTPException(status_code=403, detail="No class scheduled today for this schedule")
        if reason == "outside_class_time":
            raise HTTPException(
                status_code=403,
                detail=f"Attendance only allowed within class time (+/- {ATTENDANCE_CHECK_WINDOW_MINUTES} minutes)"
            )
        raise

    try:
        result = await mark_attendance(
            student_id=student_id,
            schedule_id=schedule_id,
            check_type=check_type,
            confidence=recognition["confidence"],
            faces_detected=recognition.get("faces_detected", 0),
        )
    except ValueError as e:
        reason = str(e)
        if reason == "duplicate_check_in":
            raise HTTPException(status_code=409, detail=f"Already checked in ({check_type}) for this schedule")
        if reason == "missing_start_check":
            raise HTTPException(status_code=409, detail="End check-in requires a prior start check-in")
        raise
    record_photo(sha, result["student_id"], schedule_id, check_type)
    return result


@router.get("/today", response_model=list[AttendanceResponse])
async def get_today_attendance(schedule_id: int | None = None):
    db = await get_db()
    today = now_local().strftime("%Y-%m-%d")

    query = """
        SELECT a.*, st.name AS student_name, s.class_name
        FROM attendance a
        LEFT JOIN students st ON a.student_id = st.id
        LEFT JOIN schedules s ON a.schedule_id = s.id
        WHERE DATE(a.timestamp) = ?
    """
    params: list = [today]
    if schedule_id is not None:
        query += " AND a.schedule_id = ?"
        params.append(schedule_id)
    query += " ORDER BY a.timestamp DESC"

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    await db.close()
    return [dict(row) for row in rows]


@router.get("/export/csv")
async def export_attendance_csv(date: str | None = None, schedule_id: int | None = None):
    """Export attendance records as CSV. Filters: ?date=YYYY-MM-DD&schedule_id=N"""
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
        SELECT a.id, a.timestamp, a.check_type, a.confidence, a.wifi_verified, a.status,
               a.student_id, st.name AS student_name, st.nim,
               a.schedule_id, s.class_name, s.room, a.faces_detected
        FROM attendance a
        LEFT JOIN students st ON a.student_id = st.id
        LEFT JOIN schedules s ON a.schedule_id = s.id
        WHERE DATE(a.timestamp) = ?
    """
    params: list = [date]
    if schedule_id is not None:
        query += " AND a.schedule_id = ?"
        params.append(schedule_id)
    query += " ORDER BY a.timestamp"

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    await db.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "timestamp", "check_type", "confidence", "wifi_verified", "status",
        "student_id", "student_name", "nim", "schedule_id", "class_name", "room",
        "faces_detected"
    ])
    for row in rows:
        record = dict(row)
        record["wifi_verified"] = "yes" if record["wifi_verified"] else "no"
        record["faces_detected"] = record.get("faces_detected") or 0
        writer.writerow([record.get(col, "") for col in [
            "id", "timestamp", "check_type", "confidence", "wifi_verified", "status",
            "student_id", "student_name", "nim", "schedule_id", "class_name", "room",
            "faces_detected"
        ]])

    filename = f"attendance_{date}" + (f"_schedule{schedule_id}" if schedule_id is not None else "") + ".csv"
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
    base = f"FROM attendance a JOIN schedules s ON a.schedule_id = s.id WHERE {where}"

    count_cursor = await db.execute(f"SELECT COUNT(*) {base}", params)
    total = (await count_cursor.fetchone())[0]

    cursor = await db.execute(
        f"SELECT a.*, s.class_name, s.room {base} ORDER BY a.timestamp DESC LIMIT ? OFFSET ?",
        params + [limit, offset]
    )
    rows = await cursor.fetchall()
    await db.close()

    response.headers["X-Total-Count"] = str(total)
    return [dict(row) for row in rows]
