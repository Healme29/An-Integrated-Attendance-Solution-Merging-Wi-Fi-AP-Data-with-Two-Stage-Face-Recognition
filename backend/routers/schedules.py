from fastapi import APIRouter, HTTPException
from models.schemas import ScheduleCreate, ScheduleResponse
from models.database import get_db

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("/", response_model=list[ScheduleResponse])
async def list_schedules():
    db = await get_db()
    cursor = await db.execute("SELECT * FROM schedules ORDER BY day_of_week, start_time")
    rows = await cursor.fetchall()
    await db.close()
    return rows


@router.post("/", response_model=ScheduleResponse)
async def create_schedule(data: ScheduleCreate):
    db = await get_db()
    await db.execute(
        "INSERT INTO schedules (class_name, day_of_week, start_time, end_time, ap_bssid, room) VALUES (?, ?, ?, ?, ?, ?)",
        (data.class_name, data.day_of_week, data.start_time, data.end_time, data.ap_bssid, data.room)
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM schedules ORDER BY id DESC LIMIT 1")
    schedule = await cursor.fetchone()
    await db.close()
    return schedule


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: int):
    db = await get_db()
    await db.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    await db.commit()
    await db.close()
    return {"message": "Schedule deleted"}
