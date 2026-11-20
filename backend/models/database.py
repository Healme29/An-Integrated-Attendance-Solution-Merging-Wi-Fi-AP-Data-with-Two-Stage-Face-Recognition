import aiosqlite
from config import DATABASE_PATH


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(str(DATABASE_PATH))
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    db = await aiosqlite.connect(str(DATABASE_PATH))
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

        -- One teacher-driven class session at a time. The teacher starts the
        -- session from the dashboard; a rotating QR token is projected on the
        -- classroom LCD and refreshed every QR_ROTATION_SECONDS.
        CREATE TABLE IF NOT EXISTS qr_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT NOT NULL,
            prev_token TEXT,
            token_rotated_at TIMESTAMP NOT NULL,
            created_by TEXT,
            class_name TEXT NOT NULL,
            room TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP,
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            qr_session_id INTEGER NOT NULL,
            confidence REAL,
            ip_address TEXT,
            status TEXT NOT NULL DEFAULT 'verified',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            faces_detected INTEGER DEFAULT 0,
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (qr_session_id) REFERENCES qr_sessions(id) ON DELETE CASCADE
        );
    """)
    # Migration: the pre-QR attendance table was schedule-based (schedule_id,
    # check_type, wifi_verified). SQLite cannot drop old columns portably, so
    # an outdated table is rebuilt: student_id / confidence / status /
    # timestamp / faces_detected survive with qr_session_id = 0 and NULL ip.
    cursor = await db.execute("PRAGMA table_info(attendance)")
    columns = {row[1] for row in await cursor.fetchall()}
    if "schedule_id" in columns:
        await db.executescript("""
            DROP TABLE IF EXISTS attendance_legacy;
            ALTER TABLE attendance RENAME TO attendance_legacy;
            CREATE TABLE attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                qr_session_id INTEGER NOT NULL,
                confidence REAL,
                ip_address TEXT,
                status TEXT NOT NULL DEFAULT 'verified',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                faces_detected INTEGER DEFAULT 0,
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (qr_session_id) REFERENCES qr_sessions(id) ON DELETE CASCADE
            );
            INSERT INTO attendance (student_id, qr_session_id, confidence, status, timestamp, faces_detected)
            SELECT student_id, 0, confidence, status, timestamp, faces_detected
            FROM attendance_legacy;
            DROP TABLE attendance_legacy;
        """)
    # Legacy schedule-based tables are no longer part of the attendance flow;
    # drop them so stale rosters/AP logs cannot be mistaken for live data.
    await db.executescript("""
        DROP TABLE IF EXISTS schedule_students;
        DROP TABLE IF EXISTS schedules;
        DROP TABLE IF EXISTS ap_logs;
    """)
    await db.commit()
    await db.close()