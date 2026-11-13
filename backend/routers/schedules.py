import csv
import io

from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from datetime import datetime
from models.schemas import ScheduleCreate, ScheduleResponse
from models.database import get_db
from config import now_local

router = APIRouter(prefix="/schedules", tags=["schedules"])

DAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


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


@router.get("/export/csv")
async def export_schedules_csv():
    """Export every class schedule as a reusable UTF-8 CSV file."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM schedules ORDER BY day_of_week, start_time, class_name")
    rows = await cursor.fetchall()
    await db.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["class_name", "day_of_week", "day", "start_time", "end_time", "room", "ap_bssid"])
    day_names = list(DAYS)
    for row in rows:
        writer.writerow([
            row["class_name"],
            row["day_of_week"],
            day_names[row["day_of_week"]].title(),
            row["start_time"],
            row["end_time"],
            row["room"] or "",
            row["ap_bssid"] or "",
        ])
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="schedules.csv"'},
    )


@router.post("/import/csv")
async def import_schedules_csv(file: UploadFile = File(...)):
    """Import schedules from CSV, accepting a day name or day_of_week 0-6."""
    if file.filename and not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV file")
    contents = await file.read()
    if len(contents) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="CSV file must be 2 MB or smaller")
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV must use UTF-8 encoding")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV is empty")
    columns = {name.strip().lower(): name for name in reader.fieldnames if name}
    required = {"class_name", "start_time", "end_time"}
    if not required.issubset(columns) or not ({"day", "day_of_week"} & set(columns)):
        raise HTTPException(
            status_code=400,
            detail="CSV requires class_name, day or day_of_week, start_time, and end_time columns",
        )

    db = await get_db()
    imported = 0
    skipped = 0
    errors: list[str] = []
    try:
        for line_number, source in enumerate(reader, start=2):
            row = {key: (source.get(original) or "").strip() for key, original in columns.items()}
            day_value = row.get("day_of_week") or row.get("day", "")
            try:
                if day_value.lower() in DAYS:
                    day_of_week = DAYS[day_value.lower()]
                else:
                    day_of_week = int(day_value)
                data = ScheduleCreate(
                    class_name=row.get("class_name", ""),
                    day_of_week=day_of_week,
                    start_time=row.get("start_time", ""),
                    end_time=row.get("end_time", ""),
                    room=row.get("room") or None,
                    ap_bssid=row.get("ap_bssid") or None,
                )
                validate_schedule_payload(data)
            except Exception as exc:
                skipped += 1
                detail = getattr(exc, "detail", str(exc))
                errors.append(f"Row {line_number}: {detail}")
                continue

            duplicate = await db.execute(
                """
                SELECT id FROM schedules
                WHERE class_name = ? AND day_of_week = ? AND start_time = ? AND end_time = ?
                  AND COALESCE(room, '') = COALESCE(?, '')
                """,
                (data.class_name, data.day_of_week, data.start_time, data.end_time, data.room),
            )
            if await duplicate.fetchone():
                skipped += 1
                errors.append(f"Row {line_number}: duplicate schedule skipped")
                continue

            try:
                await check_room_overlap(db, data)
                await db.execute(
                    """
                    INSERT INTO schedules
                        (class_name, day_of_week, start_time, end_time, ap_bssid, room, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        data.class_name,
                        data.day_of_week,
                        data.start_time,
                        data.end_time,
                        data.ap_bssid,
                        data.room,
                        now_local().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                imported += 1
            except HTTPException as exc:
                skipped += 1
                errors.append(f"Row {line_number}: {exc.detail}")
        await db.commit()
    finally:
        await db.close()

    return {"imported": imported, "skipped": skipped, "errors": errors}


@router.post("/", response_model=ScheduleResponse)
async def create_schedule(data: ScheduleCreate):
    validate_schedule_payload(data)
    db = await get_db()
    try:
        await check_room_overlap(db, data)
        # Explicit local (CST) timestamp: SQLite's CURRENT_TIMESTAMP default
        # is UTC, which was showing a shifted time on the teacher dashboard.
        await db.execute(
            "INSERT INTO schedules (class_name, day_of_week, start_time, end_time, ap_bssid, room, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (data.class_name, data.day_of_week, data.start_time, data.end_time, data.ap_bssid, data.room,
             now_local().strftime("%Y-%m-%d %H:%M:%S"))
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM schedules ORDER BY id DESC LIMIT 1")
        schedule = await cursor.fetchone()
    finally:
        await db.close()
    return dict(schedule)


@router.get("/active", response_model=list[ScheduleResponse])
async def list_active_schedules():
    """Schedules whose attendance window includes right now (grace applied)."""
    from services.attendance import get_active_schedules
    return await get_active_schedules()


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
    await db.execute("DELETE FROM schedule_students WHERE schedule_id = ?", (schedule_id,))
    await db.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    await db.commit()
    await db.close()
    return {"message": "Schedule deleted"}
