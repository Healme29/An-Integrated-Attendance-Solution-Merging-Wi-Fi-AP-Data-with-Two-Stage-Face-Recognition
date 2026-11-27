"""SQLite schema and small, additive-only migrations.

The v2 attendance model is session-based. A session belongs to one class and
moves through start -> end -> closed. Each student can have one start, one end,
and optional spot-check rows per session. Manual attendance is an audited row
written by the teacher after the session closes.

Policy: this build supports the current QR session schema only. Databases from
the removed schedule-based design are **not migrated** - they are refused at
startup so nobody loses data to a silent rebuild. Archive the old file and
start fresh (see AGENTS.md, "Database Schema").
"""
import aiosqlite
from config import DATABASE_PATH

# Tables that only existed before the rotating-QR redesign.
LEGACY_TABLES = ("schedules", "schedule_students", "ap_logs")


def _legacy_error(path, found: list[str]) -> RuntimeError:
    return RuntimeError(
        f"Legacy database detected at {path} ({', '.join(found)}).\n"
        "This build only supports the current QR session schema and does not "
        "migrate schedule-based data.\n"
        "Fix: stop the server, move the file to backups/, start again to get a "
        "fresh database, then restore the demo data with "
        "`python backend/scripts/seed_demo.py --reset` and re-enroll faces."
    )


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(str(DATABASE_PATH), timeout=5)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    await db.execute("PRAGMA busy_timeout = 5000")
    return db


async def _columns(db, table: str) -> set[str]:
    cursor = await db.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in await cursor.fetchall()}


async def _legacy_markers(db) -> list[str]:
    """Report evidence of the removed schedule-based design, if any."""
    cursor = await db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    tables = {row[0] for row in await cursor.fetchall()}
    found = [name for name in LEGACY_TABLES if name in tables]
    if "attendance" in tables:
        columns = await _columns(db, "attendance")
        if "schedule_id" in columns:
            found.append("attendance.schedule_id")
        elif "qr_session_id" not in columns:
            found.append("attendance (no qr_session_id)")
    return found


async def init_db():
    db = await aiosqlite.connect(str(DATABASE_PATH), timeout=5)
    try:
        await db.execute("PRAGMA journal_mode = WAL")

        # Refuse legacy databases instead of rebuilding them: a silent rebuild
        # dropped schedules/schedule_students/ap_logs and rewrote every
        # attendance row to qr_session_id=0. Archived files stay readable.
        legacy = await _legacy_markers(db)
        if legacy:
            raise _legacy_error(DATABASE_PATH, legacy)

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

            CREATE TABLE IF NOT EXISTS classes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_name TEXT NOT NULL,
                room TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS class_students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                UNIQUE(class_id, student_id)
            );

            CREATE TABLE IF NOT EXISTS qr_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT NOT NULL,
                prev_token TEXT,
                token_rotated_at TIMESTAMP NOT NULL,
                created_by TEXT,
                class_id INTEGER,
                class_name TEXT NOT NULL,
                room TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                is_active INTEGER NOT NULL DEFAULT 1,
                phase TEXT NOT NULL DEFAULT 'start',
                spot_round INTEGER NOT NULL DEFAULT 0,
                phase_started_at TIMESTAMP,
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                qr_session_id INTEGER NOT NULL,
                check_type TEXT NOT NULL DEFAULT 'start',
                spot_round INTEGER NOT NULL DEFAULT 0,
                confidence REAL,
                ip_address TEXT,
                status TEXT NOT NULL DEFAULT 'verified',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                faces_detected INTEGER DEFAULT 0,
                manual_by TEXT,
                manual_at TIMESTAMP,
                manual_reason TEXT,
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (qr_session_id) REFERENCES qr_sessions(id) ON DELETE CASCADE
            );

        """)

        # Add columns introduced after the first QR prototype without losing data.
        # These are additive only; anything older is rejected by the guard above.
        migrations = {
            "qr_sessions": {
                "class_id": "INTEGER",
                "phase": "TEXT NOT NULL DEFAULT 'start'",
                "spot_round": "INTEGER NOT NULL DEFAULT 0",
                "phase_started_at": "TIMESTAMP",
            },
            "attendance": {
                "check_type": "TEXT NOT NULL DEFAULT 'start'",
                "spot_round": "INTEGER NOT NULL DEFAULT 0",
                "manual_by": "TEXT",
                "manual_at": "TIMESTAMP",
                "manual_reason": "TEXT",
            },
        }
        for table, additions in migrations.items():
            existing = await _columns(db, table)
            for name, declaration in additions.items():
                if name not in existing:
                    await db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}")

        # Early QR rows used check_type='qr'. They are start evidence.
        await db.execute("UPDATE attendance SET check_type = 'start' WHERE check_type = 'qr'")
        await db.execute(
            "UPDATE qr_sessions SET phase_started_at = started_at WHERE phase_started_at IS NULL"
        )
        await db.executescript("""
            CREATE INDEX IF NOT EXISTS idx_attendance_session_student
                ON attendance(qr_session_id, student_id, check_type, spot_round);
            CREATE INDEX IF NOT EXISTS idx_class_students_class
                ON class_students(class_id, student_id);
        """)
        await db.commit()
    finally:
        await db.close()
