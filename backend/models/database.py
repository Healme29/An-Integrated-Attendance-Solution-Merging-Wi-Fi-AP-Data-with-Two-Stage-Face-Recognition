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

        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT NOT NULL,
            day_of_week INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            ap_bssid TEXT,
            room TEXT
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
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (schedule_id) REFERENCES schedules(id)
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
    await db.commit()
    await db.close()
