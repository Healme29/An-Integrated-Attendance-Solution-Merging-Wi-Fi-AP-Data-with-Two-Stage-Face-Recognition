from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Response
from models.schemas import AttendanceRequest, AttendanceResponse
from models.database import get_db
from services.attendance import recognize_face, mark_attendance, validate_schedule_time
from config import ATTENDANCE_CHECK_WINDOW_MINUTES, now_local

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/check", response_model=AttendanceResponse)
async def check_attendance(
    schedule_id: int,
    check_type: str,
    file: UploadFile = File(...)
):
    if check_type not in ("start", "end"):
        raise HTTPException(status_code=400, detail="check_type must be 'start' or 'end'")

    contents = await file.read()
    recognition = await recognize_face(contents)

    if not recognition["recognized"]:
        raise HTTPException(
            status_code=400,
            detail=f"Face not recognized: {recognition.get('reason', 'unknown')}"
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
            student_id=recognition["student_id"],
            schedule_id=schedule_id,
            check_type=check_type,
            confidence=recognition["confidence"]
        )
    except ValueError as e:
        reason = str(e)
        if reason == "duplicate_check_in":
            raise HTTPException(status_code=409, detail=f"Already checked in ({check_type}) for this schedule")
        if reason == "missing_start_check":
            raise HTTPException(status_code=409, detail="End check-in requires a prior start check-in")
        raise
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
               a.schedule_id, s.class_name, s.room
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
        "student_id", "student_name", "nim", "schedule_id", "class_name", "room"
    ])
    for row in rows:
        record = dict(row)
        record["wifi_verified"] = "yes" if record["wifi_verified"] else "no"
        writer.writerow([record.get(col, "") for col in [
            "id", "timestamp", "check_type", "confidence", "wifi_verified", "status",
            "student_id", "student_name", "nim", "schedule_id", "class_name", "room"
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
