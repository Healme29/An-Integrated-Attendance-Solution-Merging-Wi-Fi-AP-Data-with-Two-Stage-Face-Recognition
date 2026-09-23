from fastapi import APIRouter, HTTPException, UploadFile, File
from models.schemas import FaceEnrollResponse, RecognizeResponse
from models.database import get_db
from services.face_detection import detect_faces_from_bytes
from services.face_recognition import get_embedding, save_embeddings, load_embeddings
from utils.helpers import image_bytes_to_array
from datetime import datetime
import cv2
import pickle
from config import DATA_DIR

FACES_DIR = DATA_DIR / "faces"

router = APIRouter(prefix="/faces", tags=["faces"])


@router.post("/enroll", response_model=FaceEnrollResponse)
async def enroll_face(student_id: int, file: UploadFile = File(...)):
    contents = await file.read()
    image = image_bytes_to_array(contents)
    if image is None:
        raise HTTPException(status_code=400, detail="Invalid image data")

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
    saved_paths = []

    FACES_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for i, face in enumerate(faces):
        emb = get_embedding(image, face["bbox"])
        if emb is None:
            continue
        new_embeddings.append(emb)

        image_path = FACES_DIR / f"student_{student_id}_{timestamp}_{i}.jpg"
        x1, y1, x2, y2 = [int(v) for v in face["bbox"]]
        h, w = image.shape[:2]
        crop = image[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
        cv2.imwrite(str(image_path), crop)
        saved_paths.append(str(image_path))

    if not new_embeddings:
        await db.close()
        raise HTTPException(status_code=400, detail="Could not extract face embeddings")

    all_embeddings = existing + new_embeddings
    save_embeddings(student_id, all_embeddings)

    for emb, path in zip(new_embeddings, saved_paths):
        await db.execute(
            "INSERT INTO faces (student_id, embedding, image_path) VALUES (?, ?, ?)",
            (student_id, pickle.dumps(emb), path)
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
