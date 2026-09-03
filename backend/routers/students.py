from fastapi import APIRouter, HTTPException
from models.schemas import StudentCreate, StudentResponse
from models.database import get_db

router = APIRouter(prefix="/students", tags=["students"])


@router.get("/", response_model=list[StudentResponse])
async def list_students():
    db = await get_db()
    cursor = await db.execute("SELECT * FROM students ORDER BY name")
    rows = await cursor.fetchall()
    await db.close()
    return rows


@router.post("/", response_model=StudentResponse)
async def create_student(data: StudentCreate):
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO students (name, nim, mac_address) VALUES (?, ?, ?)",
            (data.name, data.nim, data.mac_address)
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM students WHERE nim = ?", (data.nim,))
        student = await cursor.fetchone()
    except Exception:
        await db.close()
        raise HTTPException(status_code=400, detail="Student with this NIM already exists")
    await db.close()
    return student


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(student_id: int):
    db = await get_db()
    cursor = await db.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    student = await cursor.fetchone()
    await db.close()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.delete("/{student_id}")
async def delete_student(student_id: int):
    db = await get_db()
    cursor = await db.execute("SELECT id FROM students WHERE id = ?", (student_id,))
    if not await cursor.fetchone():
        await db.close()
        raise HTTPException(status_code=404, detail="Student not found")
    await db.execute("DELETE FROM students WHERE id = ?", (student_id,))
    await db.commit()
    await db.close()
    return {"message": "Student deleted"}


@router.put("/{student_id}/mac")
async def update_mac(student_id: int, mac_address: str):
    db = await get_db()
    await db.execute(
        "UPDATE students SET mac_address = ? WHERE id = ?",
        (mac_address, student_id)
    )
    await db.commit()
    await db.close()
    return {"message": "MAC address updated"}
