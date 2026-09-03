from fastapi import APIRouter, HTTPException, UploadFile, File
from models.schemas import FaceEnrollResponse, RecognizeResponse
from models.database import get_db
from services.face_detection import detect_faces_from_bytes
from services.face_recognition import get_embedding, save_embeddings, load_embeddings
from pathlib import Path
from config import DATA_DIR

router = APIRouter(prefix="/faces", tags=["faces"])


@router.post("/enroll", response_model=FaceEnrollResponse)
async def enroll_face(student_id: int, file: UploadFile = File(...)):
    contents = await file.read()
    faces = detect_faces_from_bytes(contents)
    if not faces:
        raise HTTPException(status_code=400, detail="No face detected in image")

    db = await get_db()
    cursor = await db.execute("SELECT id FROM students WHERE id = ?", (student_id,))
    if not await cursor.fetchone():
        await db.close()
        raise HTTPException(status_code=404, detail="Student not found")

    existing = load_embeddings(student_id)
    new_embeddings = []

    for face in faces:
        emb = get_embedding(face["crop"])
        if emb is not None:
            new_embeddings.append(emb)

    if not new_embeddings:
        await db.close()
        raise HTTPException(status_code=400, detail="Could not extract face embeddings")

    all_embeddings = existing + new_embeddings
    save_embeddings(student_id, all_embeddings)

    await db.execute(
        "INSERT INTO faces (student_id, embedding, image_path) VALUES (?, ?, ?)",
        (student_id, b"blob", str(DATA_DIR / "faces" / f"{student_id}_{len(all_embeddings)}.jpg"))
    )
    await db.commit()
    await db.close()

    return FaceEnrollResponse(
        message="Face enrolled successfully",
        student_id=student_id,
        face_count=len(all_embeddings)
    )


@router.post("/recognize", response_model=RecognizeResponse)
async def recognize_face(file: UploadFile = File(...)):
    from services.attendance import recognize_face
    contents = await file.read()
    result = await recognize_face(contents)
    return RecognizeResponse(**result)
