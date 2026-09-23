from datetime import datetime, time, timedelta
from models.database import get_db
from services.face_recognition import get_embedding, compare_faces, is_match, load_embeddings
from services.face_detection import detect_faces_from_bytes
from services.wifi_scanner import check_mac_on_network
from config import ATTENDANCE_CHECK_WINDOW_MINUTES


async def get_schedules_for_now() -> list[dict]:
    """Get active schedules based on current time and day."""
    now = datetime.now()
    current_day = now.weekday()
    current_time = now.strftime("%H:%M")

    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM schedules WHERE day_of_week = ? AND start_time <= ? AND end_time >= ?",
        (current_day, current_time, current_time)
    )
    rows = await cursor.fetchall()
    await db.close()
    return [dict(row) for row in rows]


async def validate_schedule_time(schedule_id: int) -> dict:
    """Validate a schedule exists and now is within its class window.

    Returns the schedule dict. Raises ValueError with one of:
    'schedule_not_found', 'wrong_day', 'outside_class_time'.
    """
    db = await get_db()
    cursor = await db.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,))
    schedule = await cursor.fetchone()
    await db.close()

    if not schedule:
        raise ValueError("schedule_not_found")
    schedule = dict(schedule)

    now = datetime.now()
    if schedule["day_of_week"] != now.weekday():
        raise ValueError("wrong_day")

    grace = timedelta(minutes=ATTENDANCE_CHECK_WINDOW_MINUTES)
    window_start = (datetime.combine(now.date(), datetime.strptime(schedule["start_time"], "%H:%M").time()) - grace).time()
    window_end = (datetime.combine(now.date(), datetime.strptime(schedule["end_time"], "%H:%M").time()) + grace).time()
    now_time = now.time()

    if window_start <= window_end:
        in_window = window_start <= now_time <= window_end
    else:
        # class window crosses midnight (e.g. 23:30 - 00:30)
        in_window = now_time >= window_start or now_time <= window_end
    if not in_window:
        raise ValueError("outside_class_time")

    return schedule


async def get_existing_check(student_id: int, schedule_id: int, check_type: str) -> dict | None:
    """Return an existing attendance record for this student/schedule/stage, if any."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM attendance WHERE student_id = ? AND schedule_id = ? AND check_type = ?",
        (student_id, schedule_id, check_type)
    )
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def recognize_face(image_bytes: bytes) -> dict:
    """Detect and recognize a face from image bytes."""
    from utils.helpers import image_bytes_to_array

    image = image_bytes_to_array(image_bytes)
    if image is None:
        return {"recognized": False, "reason": "invalid_image"}

    faces = detect_faces_from_bytes(image_bytes)
    if not faces:
        return {"recognized": False, "reason": "no_face_detected"}

    best_face = max(faces, key=lambda f: f["confidence"])
    embedding = get_embedding(image, best_face["bbox"])
    if embedding is None:
        return {"recognized": False, "reason": "embedding_extraction_failed"}

    from models.database import get_db
    db = await get_db()
    cursor = await db.execute("SELECT id, name FROM students")
    students = await cursor.fetchall()

    best_match = None
    best_score = 0.0

    for student in students:
        stored = load_embeddings(student["id"])
        if not stored:
            continue
        idx, score = compare_faces(embedding, stored)
        if score > best_score:
            best_score = score
            best_match = student

    await db.close()

    if best_match and is_match(best_score):
        return {
            "recognized": True,
            "student_id": best_match["id"],
            "student_name": best_match["name"],
            "confidence": best_score
        }
    return {"recognized": False, "reason": "no_match"}


async def mark_attendance(student_id: int, schedule_id: int, check_type: str, confidence: float) -> dict:
    """Mark attendance with two-stage (start/end) pairing.

    Rules:
    - Duplicate check-in for the same stage is rejected ('duplicate_check_in').
    - 'end' requires a prior 'start' check-in ('missing_start_check').
    - 'start' is recorded with status 'partial' until the 'end' check arrives.
    - 'end' finalizes the pair: 'verified' when Wi-Fi is confirmed on both,
      otherwise 'face_only'. The start row is updated to the final status.
    """
    duplicate = await get_existing_check(student_id, schedule_id, check_type)
    if duplicate:
        raise ValueError("duplicate_check_in")

    start_check = None
    if check_type == "end":
        start_check = await get_existing_check(student_id, schedule_id, "start")
        if not start_check:
            raise ValueError("missing_start_check")

    db = await get_db()

    cursor = await db.execute(
        "SELECT mac_address FROM students WHERE id = ?", (student_id,)
    )
    student = await cursor.fetchone()

    wifi_verified = False
    if student and student["mac_address"]:
        wifi_verified = check_mac_on_network(student["mac_address"])

    if check_type == "start":
        status = "partial"
    else:
        start_wifi = bool(start_check["wifi_verified"])
        status = "verified" if (wifi_verified and start_wifi) else "face_only"

    await db.execute(
        """INSERT INTO attendance (student_id, schedule_id, check_type, confidence, wifi_verified, status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (student_id, schedule_id, check_type, confidence, int(wifi_verified), status)
    )

    if check_type == "end":
        await db.execute(
            """UPDATE attendance SET status = ?
               WHERE student_id = ? AND schedule_id = ? AND check_type = 'start'""",
            (status, student_id, schedule_id)
        )

    await db.commit()

    cursor = await db.execute("SELECT last_insert_rowid()")
    att_id = (await cursor.fetchone())[0]

    cursor = await db.execute("SELECT name FROM students WHERE id = ?", (student_id,))
    name_row = await cursor.fetchone()
    await db.close()

    return {
        "id": att_id,
        "student_id": student_id,
        "student_name": name_row["name"] if name_row else None,
        "schedule_id": schedule_id,
        "check_type": check_type,
        "confidence": confidence,
        "wifi_verified": wifi_verified,
        "status": status,
        "timestamp": datetime.now()
    }
