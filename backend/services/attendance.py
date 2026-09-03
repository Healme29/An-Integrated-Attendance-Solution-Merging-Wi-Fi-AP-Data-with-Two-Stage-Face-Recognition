from datetime import datetime, time
from models.database import get_db
from services.face_recognition import get_embedding, compare_faces, is_match, load_embeddings
from services.face_detection import detect_faces_from_bytes
from services.wifi_scanner import check_mac_on_network


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


async def recognize_face(image_bytes: bytes) -> dict:
    """Detect and recognize a face from image bytes."""
    faces = detect_faces_from_bytes(image_bytes)
    if not faces:
        return {"recognized": False, "reason": "no_face_detected"}

    best_face = max(faces, key=lambda f: f["confidence"])
    embedding = get_embedding(best_face["crop"])
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
    """Mark attendance if all conditions are met."""
    db = await get_db()

    cursor = await db.execute(
        "SELECT mac_address FROM students WHERE id = ?", (student_id,)
    )
    student = await cursor.fetchone()

    wifi_verified = False
    if student and student["mac_address"]:
        wifi_verified = check_mac_on_network(student["mac_address"])

    status = "present" if wifi_verified else "face_only"

    await db.execute(
        """INSERT INTO attendance (student_id, schedule_id, check_type, confidence, wifi_verified, status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (student_id, schedule_id, check_type, confidence, int(wifi_verified), status)
    )
    await db.commit()

    cursor = await db.execute("SELECT last_insert_rowid()")
    att_id = (await cursor.fetchone())[0]
    await db.close()

    return {
        "id": att_id,
        "student_id": student_id,
        "schedule_id": schedule_id,
        "check_type": check_type,
        "confidence": confidence,
        "wifi_verified": wifi_verified,
        "status": status
    }
