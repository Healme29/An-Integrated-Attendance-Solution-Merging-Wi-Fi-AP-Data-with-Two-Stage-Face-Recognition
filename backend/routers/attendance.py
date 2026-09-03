from fastapi import APIRouter, HTTPException, UploadFile, File
from models.schemas import AttendanceRequest, AttendanceResponse
from models.database import get_db
from services.attendance import recognize_face, mark_attendance

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

    result = await mark_attendance(
        student_id=recognition["student_id"],
        schedule_id=schedule_id,
        check_type=check_type,
        confidence=recognition["confidence"]
    )
    return result


@router.get("/today", response_model=list[AttendanceResponse])
async def get_today_attendance():
    from datetime import datetime
    db = await get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor = await db.execute(
        "SELECT * FROM attendance WHERE DATE(timestamp) = ? ORDER BY timestamp DESC",
        (today,)
    )
    rows = await cursor.fetchall()
    await db.close()
    return rows


@router.get("/student/{student_id}")
async def get_student_attendance(student_id: int):
    db = await get_db()
    cursor = await db.execute(
        """SELECT a.*, s.class_name, s.room
           FROM attendance a
           JOIN schedules s ON a.schedule_id = s.id
           WHERE a.student_id = ?
           ORDER BY a.timestamp DESC""",
        (student_id,)
    )
    rows = await cursor.fetchall()
    await db.close()
    return [dict(row) for row in rows]
