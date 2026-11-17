import aiosqlite
from config import DATABASE_PATH


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(str(DATABASE_PATH))
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    db = await aiosqlite.connect(str(DATABASE_PATH))
    cursor = await db.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schedule_students'"
    )
    had_schedule_students = await cursor.fetchone() is not None
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            nim TEXT UNIQUE NOT NULL,
            mac_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS faces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            embedding BLOB NOT NULL,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT NOT NULL,
            day_of_week INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            ap_bssid TEXT,
            room TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            schedule_id INTEGER NOT NULL,
            check_type TEXT NOT NULL CHECK(check_type IN ('start', 'end')),
            confidence REAL,
            wifi_verified INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            faces_detected INTEGER DEFAULT 0,
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (schedule_id) REFERENCES schedules(id)
        );

        CREATE TABLE IF NOT EXISTS schedule_students (
            schedule_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (schedule_id, student_id),
            FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE CASCADE,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS ap_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mac_address TEXT NOT NULL,
            ip_address TEXT,
            bssid TEXT,
            ssid TEXT,
            scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    # Felix 22.0 migration: preserve the old global roster by enrolling every
    # existing student in every existing schedule once. New schedules remain
    # empty until the teacher adds or imports their class roster.
    if not had_schedule_students:
        await db.execute(
            """
            INSERT OR IGNORE INTO schedule_students (schedule_id, student_id)
            SELECT schedules.id, students.id FROM schedules CROSS JOIN students
            """
        )
        await db.commit()
    # Migration: very first schemas had no schedules.created_at; the dashboard
    # reads it, so add it for databases created before this change. The INSERT
    # path writes a CST (locale) timestamp explicitly.
    try:
        await db.execute("ALTER TABLE schedules ADD COLUMN created_at TIMESTAMP")
        await db.commit()
    except Exception:
        pass  # column already exists

    # Migration: attendance.faces_detected was added with the identity-binding
    # fix (D-003) so the detector box count is auditable per check-in.
    try:
        await db.execute("ALTER TABLE attendance ADD COLUMN faces_detected INTEGER DEFAULT 0")
        await db.commit()
    except Exception:
        pass  # column already exists
    await db.close()
