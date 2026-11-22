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
            class_id INTEGER,
            class_name TEXT NOT NULL,
            room TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP,
            is_active INTEGER NOT NULL DEFAULT 1,
            phase TEXT NOT NULL DEFAULT 'start',
            FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE SET NULL
        );

        -- Class roster: one class groups students; one student belongs to at
        -- most one class (enforced in UI). This is what the teacher sees on
        -- the dashboard roster — never students from other classes.
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

        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            qr_session_id INTEGER NOT NULL,
            check_type TEXT NOT NULL DEFAULT 'qr',
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
    # Migration: rebuild qr_sessions if it lacks class_id/phase columns.
    cursor = await db.execute("PRAGMA table_info(qr_sessions)")
    columns = {row[1] for row in await cursor.fetchall()}
    if "class_id" not in columns or "phase" not in columns:
        await db.executescript("""
            DROP TABLE IF EXISTS qr_sessions_legacy;
            ALTER TABLE qr_sessions RENAME TO qr_sessions_legacy;
            CREATE TABLE qr_sessions (
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
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE SET NULL
            );
            INSERT INTO qr_sessions (id, token, prev_token, token_rotated_at, created_by, class_id, class_name, room, started_at, ended_at, is_active, phase)
            SELECT id, token, prev_token, token_rotated_at, created_by, NULL, class_name, room, started_at, ended_at, is_active, 'start'
            FROM qr_sessions_legacy;
            DROP TABLE qr_sessions_legacy;
        """)

    # Migration: rebuild attendance if it lacks manual columns.
    cursor = await db.execute("PRAGMA table_info(attendance)")
    columns = {row[1] for row in await cursor.fetchall()}
    if "manual_by" not in columns:
        await db.executescript("""
            DROP TABLE IF EXISTS attendance_legacy;
            ALTER TABLE attendance RENAME TO attendance_legacy;
            CREATE TABLE attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                qr_session_id INTEGER NOT NULL,
                check_type TEXT NOT NULL DEFAULT 'qr',
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
            INSERT INTO attendance (id, student_id, qr_session_id, check_type, confidence, ip_address, status, timestamp, faces_detected, manual_by, manual_at, manual_reason)
            SELECT id, student_id, qr_session_id, 'qr', confidence, ip_address, status, timestamp, faces_detected, NULL, NULL, NULL
            FROM attendance_legacy;
            DROP TABLE attendance_legacy;
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
                check_type TEXT NOT NULL DEFAULT 'qr',
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