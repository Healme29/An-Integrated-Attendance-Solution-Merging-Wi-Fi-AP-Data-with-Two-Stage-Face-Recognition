from datetime import datetime, time, timedelta
from models.database import get_db
from services.face_recognition import get_embedding, compare_faces, is_match, load_embeddings
from services.face_detection import detect_faces_from_bytes, dedupe_faces, distinct_people
from services.wifi_scanner import check_mac_on_network, get_current_bssid, is_same_bssid
from config import ATTENDANCE_CHECK_WINDOW_MINUTES, REQUIRE_CLASSROOM_WIFI, now_local


def schedule_window(schedule: dict, now: datetime | None = None) -> tuple[time, time]:
    """Attendance window for a schedule: start-grace .. end+grace (HH:MM)."""
    now = now or now_local()
    grace = timedelta(minutes=ATTENDANCE_CHECK_WINDOW_MINUTES)
    start = (
        datetime.combine(now.date(), datetime.strptime(schedule["start_time"], "%H:%M").time())
        - grace
    ).time()
    end = (
        datetime.combine(now.date(), datetime.strptime(schedule["end_time"], "%H:%M").time())
        + grace
    ).time()
    return start, end


def is_within_window(schedule: dict, now: datetime | None = None) -> bool:
    """True when `now` is inside the schedule's day and attendance window."""
    now = now or now_local()
    if schedule["day_of_week"] != now.weekday():
        return False
    window_start, window_end = schedule_window(schedule, now)
    now_time = now.time()
    if window_start <= window_end:
        return window_start <= now_time <= window_end
    # class window crosses midnight (e.g. 23:30 - 00:30)
    return now_time >= window_start or now_time <= window_end


async def get_active_schedules() -> list[dict]:
    """Schedules whose attendance window currently includes `now`."""
    now = now_local()
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM schedules WHERE day_of_week = ? ORDER BY start_time",
        (now.weekday(),),
    )
    rows = await cursor.fetchall()
    await db.close()
    return [dict(row) for row in rows if is_within_window(dict(row), now)]


async def get_schedules_for_now() -> list[dict]:
    """Schedules the attendance window currently allows (legacy name)."""
    return await get_active_schedules()


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

    now = now_local()
    if schedule["day_of_week"] != now.weekday():
        raise ValueError("wrong_day")

    if not is_within_window(schedule, now):
        raise ValueError("outside_class_time")

    return schedule


async def classroom_wifi_verified(student_id: int, schedule_id: int) -> bool:
    """True when the student's device is on the network the schedule expects.

    Layer 1: the student's registered MAC is visible in the server's ARP table.
    Layer 2 (only when the schedule pins an AP): the server itself must be
    associated with that BSSID. A single campus SSID spans many APs, so the
    server's own AP is the only location fact this machine can verify.
    """
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT mac_address FROM students WHERE id = ?", (student_id,)
        )
        student = await cursor.fetchone()
        cursor = await db.execute(
            "SELECT ap_bssid FROM schedules WHERE id = ?", (schedule_id,)
        )
        schedule_row = await cursor.fetchone()
    finally:
        await db.close()

    if not student or not student["mac_address"]:
        return False
    if not check_mac_on_network(student["mac_address"]):
        return False
    if schedule_row and schedule_row["ap_bssid"]:
        return is_same_bssid(get_current_bssid(), schedule_row["ap_bssid"])
    return True


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


async def recognize_face(image_bytes: bytes, enforce_single_face: bool = True) -> dict:
    """Detect and recognize one face from image bytes.

    The photo must contain exactly one person. Multiple detector boxes for the
    same face (nested boxes) are merged first; a genuinely different second
    face is rejected with `multiple_faces_detected` so a photo of a friend can
    never be used to check someone else in. When several faces are present the
    largest box is used, not the most confident one: a face close to the
    camera is the person taking the selfie.

    Returns `faces_detected` (raw detector boxes) so callers can audit what the
    model saw.
    """
    from utils.helpers import image_bytes_to_array

    image = image_bytes_to_array(image_bytes)
    if image is None:
        return {"recognized": False, "reason": "invalid_image"}

    detected = detect_faces_from_bytes(image_bytes)
    if not detected:
        return {"recognized": False, "reason": "no_face_detected"}

    faces = dedupe_faces(detected)
    people = distinct_people(faces)
    if enforce_single_face and len(people) > 1:
        return {
            "recognized": False,
            "reason": "multiple_faces_detected",
            "faces_detected": len(detected),
        }

    primary = faces[0]
    embedding = get_embedding(image, primary["bbox"])
    if embedding is None:
        return {
            "recognized": False,
            "reason": "embedding_extraction_failed",
            "faces_detected": len(detected),
        }

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
            "confidence": best_score,
            "faces_detected": len(detected),
        }
    return {
        "recognized": False,
        "reason": "no_match",
        "faces_detected": len(detected),
    }


async def mark_attendance(
    student_id: int,
    schedule_id: int,
    check_type: str,
    confidence: float,
    faces_detected: int = 0,
) -> dict:
    """Mark attendance with two-stage (start/end) pairing.

    Rules:
    - Duplicate check-in for the same stage is rejected ('duplicate_check_in').
    - 'end' requires a prior 'start' check-in ('missing_start_check').
    - 'start' is recorded with status 'partial' until the 'end' check arrives.
    - 'end' finalizes the pair: 'verified' when Wi-Fi is confirmed on both,
      otherwise 'face_only'. The start row is updated to the final status.
    - `faces_detected` is the raw detector box count, stored for audit.
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

    wifi_verified = await classroom_wifi_verified(student_id, schedule_id)

    if REQUIRE_CLASSROOM_WIFI and not wifi_verified:
        await db.close()
        raise ValueError("not_on_classroom_network")

    if check_type == "start":
        status = "partial"
    else:
        start_wifi = bool(start_check["wifi_verified"])
        status = "verified" if (wifi_verified and start_wifi) else "face_only"

    # Store an explicit local timestamp (SQLite's CURRENT_TIMESTAMP is UTC,
    # which would break DATE() comparisons against local class days).
    timestamp = now_local().strftime("%Y-%m-%d %H:%M:%S")
    await db.execute(
        """INSERT INTO attendance (student_id, schedule_id, check_type, confidence, wifi_verified, status, timestamp, faces_detected)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (student_id, schedule_id, check_type, confidence, int(wifi_verified), status, timestamp, faces_detected)
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
        "faces_detected": faces_detected,
        "timestamp": timestamp
    }
