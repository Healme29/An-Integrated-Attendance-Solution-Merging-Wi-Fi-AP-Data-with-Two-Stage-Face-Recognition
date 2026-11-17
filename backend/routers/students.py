import csv
import io
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from typing import Optional
from models.schemas import StudentCreate, StudentResponse
from models.database import get_db
from services.wifi_scanner import normalize_mac

router = APIRouter(prefix="/students", tags=["students"])


def validate_sheet_date(value: str | None) -> str:
    if value is None:
        return datetime.now().strftime("%Y-%m-%d")
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be in YYYY-MM-DD format")
    return value


async def ensure_schedule(db, schedule_id: int):
    cursor = await db.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,))
    schedule = await cursor.fetchone()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


async def attendance_sheet_rows(db, schedule_id: int, sheet_date: str):
    cursor = await db.execute(
        """
        SELECT st.id, st.name, st.nim, st.mac_address, st.created_at,
               MIN(CASE WHEN a.check_type = 'start' THEN a.timestamp END) AS start_time,
               MAX(CASE WHEN a.check_type = 'end' THEN a.timestamp END) AS end_time,
               COUNT(a.id) > 0 AS attended,
               CASE
                   WHEN COUNT(a.id) = 0 THEN 'absent'
                   WHEN MAX(CASE WHEN a.check_type = 'end' AND a.status = 'verified' THEN 1 ELSE 0 END) = 1 THEN 'verified'
                   WHEN MAX(CASE WHEN a.status = 'face_only' THEN 1 ELSE 0 END) = 1 THEN 'face_only'
                   ELSE 'partial'
               END AS attendance_status
        FROM schedule_students ss
        JOIN students st ON st.id = ss.student_id
        LEFT JOIN attendance a
          ON a.student_id = st.id
         AND a.schedule_id = ss.schedule_id
         AND DATE(a.timestamp) = ?
        WHERE ss.schedule_id = ?
        GROUP BY st.id, st.name, st.nim, st.mac_address, st.created_at
        ORDER BY st.name
        """,
        (sheet_date, schedule_id),
    )
    records = []
    for row in await cursor.fetchall():
        record = dict(row)
        record["attended"] = bool(record["attended"])
        records.append(record)
    return records


async def find_mac_owner(db, mac: str, exclude_id: int | None = None):
    """Student (or None) already holding this normalized MAC."""
    cursor = await db.execute("SELECT * FROM students")
    rows = await cursor.fetchall()
    for row in rows:
        row_mac = (row["mac_address"] or "").strip()
        if not row_mac:
            continue
        if exclude_id is not None and row["id"] == exclude_id:
            continue
        if normalize_mac(row_mac) == normalize_mac(mac):
            return row
    return None


@router.get("/", response_model=list[StudentResponse])
async def list_students(nim: Optional[str] = None):
    """List students, or look up a single student by NIM (?nim=12345)."""
    db = await get_db()
    if nim:
        cursor = await db.execute("SELECT * FROM students WHERE nim = ?", (nim,))
    else:
        cursor = await db.execute("SELECT * FROM students ORDER BY name")
    rows = await cursor.fetchall()
    await db.close()
    return [dict(row) for row in rows]


@router.get("/attendance-sheet")
async def get_attendance_sheet(schedule_id: int, date: str | None = None):
    """Return the complete class roster with attendance status for one date."""
    sheet_date = validate_sheet_date(date)
    db = await get_db()
    try:
        schedule = await ensure_schedule(db, schedule_id)
        students = await attendance_sheet_rows(db, schedule_id, sheet_date)
        return {
            "schedule": dict(schedule),
            "date": sheet_date,
            "students": students,
            "total": len(students),
            "attended": sum(1 for student in students if student["attended"]),
        }
    finally:
        await db.close()


@router.post("/import/csv")
async def import_student_roster(
    schedule_id: int,
    file: UploadFile = File(...),
):
    """Import a class roster from CSV columns: name,nim,mac_address."""
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
    normalized = {name.strip().lower(): name for name in reader.fieldnames if name}
    if "name" not in normalized or "nim" not in normalized:
        raise HTTPException(status_code=400, detail="CSV must contain name and nim columns")

    db = await get_db()
    created = 0
    enrolled = 0
    skipped = 0
    errors: list[str] = []
    try:
        await ensure_schedule(db, schedule_id)
        for line_number, source in enumerate(reader, start=2):
            row = {key: (source.get(original) or "").strip() for key, original in normalized.items()}
            name = row.get("name", "")
            nim = row.get("nim", "")
            mac_address = row.get("mac_address") or None
            if not name or not nim:
                skipped += 1
                errors.append(f"Row {line_number}: name and nim are required")
                continue

            cursor = await db.execute("SELECT * FROM students WHERE nim = ?", (nim,))
            student = await cursor.fetchone()
            if student is None:
                if mac_address:
                    owner = await find_mac_owner(db, mac_address)
                    if owner:
                        skipped += 1
                        errors.append(f"Row {line_number}: MAC address belongs to {owner['name']}")
                        continue
                try:
                    cursor = await db.execute(
                        "INSERT INTO students (name, nim, mac_address) VALUES (?, ?, ?)",
                        (name, nim, mac_address),
                    )
                    student_id = cursor.lastrowid
                    created += 1
                except Exception as exc:
                    skipped += 1
                    errors.append(f"Row {line_number}: {exc}")
                    continue
            else:
                student_id = student["id"]

            cursor = await db.execute(
                "INSERT OR IGNORE INTO schedule_students (schedule_id, student_id) VALUES (?, ?)",
                (schedule_id, student_id),
            )
            if cursor.rowcount:
                enrolled += 1
        await db.commit()
    finally:
        await db.close()

    return {"created": created, "enrolled": enrolled, "skipped": skipped, "errors": errors}


@router.get("/export/xlsx")
async def export_attendance_sheet(schedule_id: int, date: str | None = None):
    """Download the full roster and its attendance result as an Excel file."""
    sheet_date = validate_sheet_date(date)
    db = await get_db()
    try:
        schedule = await ensure_schedule(db, schedule_id)
        students = await attendance_sheet_rows(db, schedule_id, sheet_date)
    finally:
        await db.close()

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Attendance Sheet"
    sheet.append(["Felix 22.1 Attendance Sheet"])
    sheet.merge_cells("A1:I1")
    sheet["A1"].font = Font(size=16, bold=True, color="FFFFFF")
    sheet["A1"].fill = PatternFill("solid", fgColor="1A56DB")
    sheet["A1"].alignment = Alignment(horizontal="center")
    sheet.append(["Class / Subject", schedule["class_name"], "Date", sheet_date, "Room", schedule["room"] or "-"])
    sheet.append([])
    headers = ["No.", "NIM", "Student Name", "Attendance", "Status", "Start Time", "End Time", "Class / Subject", "Date"]
    sheet.append(headers)
    for cell in sheet[4]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="0E9F6E")
        cell.alignment = Alignment(horizontal="center")

    for index, student in enumerate(students, start=1):
        sheet.append([
            index,
            student["nim"],
            student["name"],
            "Present" if student["attended"] else "Absent",
            student["attendance_status"].replace("_", " ").title(),
            student["start_time"] or "-",
            student["end_time"] or "-",
            schedule["class_name"],
            sheet_date,
        ])
        fill_color = "E6F7F0" if student["attended"] else "FCE8E6"
        for cell in sheet[sheet.max_row]:
            cell.fill = PatternFill("solid", fgColor=fill_color)

    widths = [7, 16, 28, 14, 16, 22, 22, 28, 14]
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.freeze_panes = "A5"
    sheet.auto_filter.ref = f"A4:I{max(sheet.max_row, 4)}"

    output = io.BytesIO()
    workbook.save(output)
    safe_class = "".join(char if char.isalnum() else "_" for char in schedule["class_name"]).strip("_")
    filename = f"attendance_sheet_{safe_class}_{sheet_date}.xlsx"
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/", response_model=StudentResponse)
async def create_student(data: StudentCreate, schedule_id: int | None = None):
    db = await get_db()
    if schedule_id is not None:
        await ensure_schedule(db, schedule_id)
    if data.mac_address:
        owner = await find_mac_owner(db, data.mac_address)
        if owner:
            await db.close()
            raise HTTPException(
                status_code=409,
                detail=f"MAC address already registered to {owner['name']} (id {owner['id']}) — "
                       "one device belongs to one student"
            )
    try:
        await db.execute(
            "INSERT INTO students (name, nim, mac_address) VALUES (?, ?, ?)",
            (data.name, data.nim, data.mac_address)
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM students WHERE nim = ?", (data.nim,))
        student = await cursor.fetchone()
        if schedule_id is not None:
            await db.execute(
                "INSERT OR IGNORE INTO schedule_students (schedule_id, student_id) VALUES (?, ?)",
                (schedule_id, student["id"]),
            )
            await db.commit()
    except Exception:
        await db.close()
        raise HTTPException(status_code=400, detail="Student with this NIM already exists")
    await db.close()
    return dict(student)


@router.post("/{student_id}/schedules/{schedule_id}")
async def enroll_student_in_schedule(student_id: int, schedule_id: int):
    db = await get_db()
    try:
        await ensure_schedule(db, schedule_id)
        cursor = await db.execute("SELECT id FROM students WHERE id = ?", (student_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Student not found")
        await db.execute(
            "INSERT OR IGNORE INTO schedule_students (schedule_id, student_id) VALUES (?, ?)",
            (schedule_id, student_id),
        )
        await db.commit()
    finally:
        await db.close()
    return {"message": "Student enrolled in class"}


@router.delete("/{student_id}/schedules/{schedule_id}")
async def remove_student_from_schedule(student_id: int, schedule_id: int):
    db = await get_db()
    try:
        cursor = await db.execute(
            "DELETE FROM schedule_students WHERE schedule_id = ? AND student_id = ?",
            (schedule_id, student_id),
        )
        if not cursor.rowcount:
            raise HTTPException(status_code=404, detail="Student is not enrolled in this class")
        await db.commit()
    finally:
        await db.close()
    return {"message": "Student removed from class roster"}


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(student_id: int):
    db = await get_db()
    cursor = await db.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    student = await cursor.fetchone()
    await db.close()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return dict(student)


@router.delete("/{student_id}")
async def delete_student(student_id: int):
    db = await get_db()
    cursor = await db.execute("SELECT id FROM students WHERE id = ?", (student_id,))
    if not await cursor.fetchone():
        await db.close()
        raise HTTPException(status_code=404, detail="Student not found")
    await db.execute("DELETE FROM schedule_students WHERE student_id = ?", (student_id,))
    await db.execute("DELETE FROM students WHERE id = ?", (student_id,))
    await db.commit()
    await db.close()
    return {"message": "Student deleted"}


@router.put("/{student_id}/mac")
async def update_mac(student_id: int, mac_address: str):
    db = await get_db()
    cursor = await db.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    if not await cursor.fetchone():
        await db.close()
        raise HTTPException(status_code=404, detail="Student not found")
    owner = await find_mac_owner(db, mac_address, exclude_id=student_id)
    if owner:
        await db.close()
        raise HTTPException(
            status_code=409,
            detail=f"MAC address already registered to {owner['name']} (id {owner['id']}) — "
                   "one device belongs to one student"
        )
    await db.execute(
        "UPDATE students SET mac_address = ? WHERE id = ?",
        (mac_address, student_id)
    )
    await db.commit()
    await db.close()
    return {"message": "MAC address updated"}
