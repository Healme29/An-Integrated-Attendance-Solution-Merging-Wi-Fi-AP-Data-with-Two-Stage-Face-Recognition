"""Core attendance helpers: single-face recognition over enrolled embeddings.

The schedule / Wi-Fi-AP layers of the old design were replaced by the QR
session flow (see services/qr_service.py): presence is proven by scanning the
teacher's rotating QR in the room, and network membership by the request
originating from the school subnet.
"""
from services.face_recognition import get_embedding, compare_faces, is_match, load_embeddings
from services.face_detection import detect_faces_from_bytes, dedupe_faces, distinct_people


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
    from models.database import get_db

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