from fastapi import APIRouter, HTTPException
from datetime import datetime
from models.schemas import ScheduleCreate, ScheduleResponse
from models.database import get_db

router = APIRouter(prefix="/schedules", tags=["schedules"])


def validate_schedule_payload(data: ScheduleCreate) -> None:
    """Validate schedule fields and normalize HH:MM times.

    Raises HTTPException(400) on invalid input. Normalizes times to
    zero-padded HH:MM so string comparisons stay reliable.
    """
    if not data.class_name.strip():
        raise HTTPException(status_code=400, detail="class_name cannot be empty")
    if not 0 <= data.day_of_week <= 6:
        raise HTTPException(status_code=400, detail="day_of_week must be 0 (Monday) to 6 (Sunday)")
    try:
        start = datetime.strptime(data.start_time, "%H:%M")
        end = datetime.strptime(data.end_time, "%H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="start_time and end_time must be in HH:MM format")
    if start >= end:
        raise HTTPException(status_code=400, detail="start_time must be before end_time")
    data.start_time = start.strftime("%H:%M")
    data.end_time = end.strftime("%H:%M")


def _times_overlap(start_a: str, end_a: str, start_b: str, end_b: str) -> bool:
    """True if [start_a, end_a) intersects [start_b, end_b) (HH:MM strings)."""
    return start_a < end_b and end_a > start_b


async def check_room_overlap(db, data: ScheduleCreate, exclude_id: int | None = None):
    """Reject two classes booked in the same room at overlapping times."""
    cursor = await db.execute("SELECT * FROM schedules WHERE day_of_week = ?", (data.day_of_week,))
    rows = await cursor.fetchall()
    for row in rows:
        if exclude_id is not None and row["id"] == exclude_id:
            continue
        if (row["room"] or None) != (data.room or None):
            continue
        if _times_overlap(data.start_time, data.end_time, row["start_time"], row["end_time"]):
            room_label = data.room or "the same room"
            raise HTTPException(
                status_code=409,
                detail=f"Time slot conflicts with '{row['class_name']}' in {room_label}"
            )


@router.get("/", response_model=list[ScheduleResponse])
async def list_schedules():
    db = await get_db()
    cursor = await db.execute("SELECT * FROM schedules ORDER BY day_of_week, start_time")
    rows = await cursor.fetchall()
    await db.close()
    return [dict(row) for row in rows]


@router.post("/", response_model=ScheduleResponse)
async def create_schedule(data: ScheduleCreate):
    validate_schedule_payload(data)
    db = await get_db()
    try:
        await check_room_overlap(db, data)
        await db.execute(
            "INSERT INTO schedules (class_name, day_of_week, start_time, end_time, ap_bssid, room) VALUES (?, ?, ?, ?, ?, ?)",
            (data.class_name, data.day_of_week, data.start_time, data.end_time, data.ap_bssid, data.room)
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM schedules ORDER BY id DESC LIMIT 1")
        schedule = await cursor.fetchone()
    finally:
        await db.close()
    return dict(schedule)


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(schedule_id: int):
    db = await get_db()
    cursor = await db.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,))
    schedule = await cursor.fetchone()
    await db.close()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return dict(schedule)


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(schedule_id: int, data: ScheduleCreate):
    validate_schedule_payload(data)
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM schedules WHERE id = ?", (schedule_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Schedule not found")
        await check_room_overlap(db, data, exclude_id=schedule_id)
        await db.execute(
            "UPDATE schedules SET class_name = ?, day_of_week = ?, start_time = ?, end_time = ?, ap_bssid = ?, room = ? WHERE id = ?",
            (data.class_name, data.day_of_week, data.start_time, data.end_time, data.ap_bssid, data.room, schedule_id)
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,))
        schedule = await cursor.fetchone()
    finally:
        await db.close()
    return dict(schedule)


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: int):
    db = await get_db()
    cursor = await db.execute("SELECT id FROM schedules WHERE id = ?", (schedule_id,))
    if not await cursor.fetchone():
        await db.close()
        raise HTTPException(status_code=404, detail="Schedule not found")
    await db.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    await db.commit()
    await db.close()
    return {"message": "Schedule deleted"}
