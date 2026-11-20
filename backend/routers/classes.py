"""Class & enrollment management (S3).

One class groups students. One student belongs to at most one class (enforced
in the UI). The dashboard roster shows only students enrolled in the session's
class — never students from other classes.
"""
from fastapi import APIRouter, HTTPException
from models.database import get_db
from models.schemas import (
    ClassCreate,
    ClassResponse,
    ClassStudentAdd,
    ClassStudentResponse,
)

router = APIRouter(prefix="/classes", tags=["classes"])


@router.post("/", response_model=ClassResponse)
async def create_class(data: ClassCreate, created_by: str = "teacher"):
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO classes (class_name, room, created_by) VALUES (?, ?, ?)",
            (data.class_name.strip(), data.room, created_by),
        )
        await db.commit()
        class_id = cursor.lastrowid
        cursor = await db.execute("SELECT * FROM classes WHERE id = ?", (class_id,))
        row = await cursor.fetchone()
        return dict(row)
    finally:
        await db.close()


@router.get("/", response_model=list[ClassResponse])
async def list_classes():
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM classes ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


@router.get("/{class_id}/students", response_model=list[ClassStudentResponse])
async def list_class_students(class_id: int):
    db = await get_db()
    try:
        cursor = await db.execute(
            """
            SELECT cs.id, cs.student_id, st.name AS student_name,
                   st.nim AS student_nim, cs.added_at
            FROM class_students cs
            JOIN students st ON cs.student_id = st.id
            WHERE cs.class_id = ?
            ORDER BY st.nim
            """,
            (class_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


@router.post("/{class_id}/students", response_model=ClassStudentResponse)
async def add_student_to_class(class_id: int, data: ClassStudentAdd):
    db = await get_db()
    try:
        # Verify class exists
        cursor = await db.execute("SELECT id FROM classes WHERE id = ?", (class_id,))
        if not await cursor.fetchone():
            await db.close()
            raise HTTPException(status_code=404, detail="Class not found")

        # Verify student exists
        cursor = await db.execute("SELECT id FROM students WHERE id = ?", (data.student_id,))
        if not await cursor.fetchone():
            await db.close()
            raise HTTPException(status_code=404, detail="Student not found")

        # One student = one class: remove from any other class first
        await db.execute(
            "DELETE FROM class_students WHERE student_id = ?", (data.student_id,)
        )

        cursor = await db.execute(
            """INSERT INTO class_students (class_id, student_id)
               VALUES (?, ?)""",
            (class_id, data.student_id),
        )
        await db.commit()
        link_id = cursor.lastrowid

        cursor = await db.execute(
            """
            SELECT cs.id, cs.student_id, st.name AS student_name,
                   st.nim AS student_nim, cs.added_at
            FROM class_students cs
            JOIN students st ON cs.student_id = st.id
            WHERE cs.id = ?
            """,
            (link_id,),
        )
        row = await cursor.fetchone()
        return dict(row)
    finally:
        await db.close()


@router.delete("/{class_id}/students/{student_id}")
async def remove_student_from_class(class_id: int, student_id: int):
    db = await get_db()
    try:
        cursor = await db.execute(
            "DELETE FROM class_students WHERE class_id = ? AND student_id = ?",
            (class_id, student_id),
        )
        await db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Enrollment not found")
        return {"message": "Student removed from class"}
    finally:
        await db.close()
