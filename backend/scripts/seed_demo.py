"""Seed demo data for a presentation (offline fallback, Task B4).

Creates sample students, one schedule that is active **right now**, and sample
attendance rows, so the teacher dashboard and the app have something to show
even if the live demo fails or no real check-in has happened yet.

Runs directly against the SQLite file, so the API server does not have to be
running (stop it on Windows to avoid file locks).

Examples:
    python backend/scripts/seed_demo.py                 # add demo data
    python backend/scripts/seed_demo.py --reset         # wipe ALL data first
    python backend/scripts/seed_demo.py --students 5    # more sample students
    python backend/scripts/seed_demo.py --db some.db    # use another database

The demo schedule opens 5 minutes before "now" and closes 55 minutes after, in
the server's configured timezone (set TIMEZONE, e.g. Asia/Shanghai).

Note: demo students get locally-administered MAC addresses (02:00:00:00:00:NN)
that no phone actually uses, so the Wi-Fi prompt stays false for them. That is
fine for a dashboard-only fallback; for a live Wi-Fi demo register the real
phone MAC with `PUT /students/{id}/mac`.
"""
import argparse
import os
import sqlite3
import sys
from datetime import timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

DEMO_MAC_PREFIX = "02:00:00:00:00:"
MAX_DEMO_STUDENTS = 99


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true",
                        help="delete all existing students/schedules/attendance/ap_logs first")
    parser.add_argument("--students", type=int, default=3,
                        help="number of demo students to create (default: 3, max 99)")
    parser.add_argument("--db", default=None,
                        help="database path (default: value of DATABASE_PATH / backend/attendance.db)")
    return parser.parse_args()


def remove_stale_artifacts(student_ids: list[int]) -> int:
    """Delete embedding pickles and stored face images of deleted demo students.

    Without this a later demo of the same student id could match an old,
    unrelated face profile (the pickles and the database are separate files).
    """
    from config import EMBEDDINGS_DIR, DATA_DIR  # noqa: E402

    removed = 0
    for student_id in student_ids:
        pickle_path = Path(EMBEDDINGS_DIR) / f"student_{student_id}.pkl"
        if pickle_path.exists():
            pickle_path.unlink()
            removed += 1
        faces_dir = Path(DATA_DIR) / "faces"
        if faces_dir.exists():
            for image in faces_dir.glob(f"student_{student_id}_*"):
                image.unlink()
                removed += 1
    return removed


def main() -> int:
    args = parse_args()

    if args.db:
        os.environ["DATABASE_PATH"] = str(Path(args.db).resolve())

    # Import AFTER the database path is set, so config picks it up.
    from config import now_local  # noqa: E402  (import order is intentional)
    from models.database import DATABASE_PATH  # noqa: E402

    db_path = Path(DATABASE_PATH)
    print(f"database: {db_path}")

    # Make sure the schema exists even on a fresh machine.
    import asyncio
    from models.database import init_db  # noqa: E402
    asyncio.run(init_db())

    if not db_path.exists():
        print("database file was not created - check DATABASE_PATH permissions")
        return 1

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        if args.reset:
            old_ids = [row["id"] for row in cursor.execute("SELECT id FROM students")]
            removed_artifacts = remove_stale_artifacts(old_ids)
            cursor.execute("DELETE FROM attendance")
            cursor.execute("DELETE FROM ap_logs")
            cursor.execute("DELETE FROM faces")
            cursor.execute("DELETE FROM students")
            cursor.execute("DELETE FROM schedules")
            # Restart ids at 1 so screenshots stay tidy.
            for table in ("students", "schedules", "attendance", "ap_logs", "faces"):
                cursor.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table,))
            conn.commit()
            print("reset: all students, schedules, faces, attendance and ap_logs deleted")
            print(f"reset: stale embedding/face files removed: {removed_artifacts}")

        # --- students -------------------------------------------------------
        count = max(1, min(args.students, MAX_DEMO_STUDENTS))
        if count != args.students:
            print(f"students: clamped {args.students} to {count} (1..{MAX_DEMO_STUDENTS})")
        students = [
            (f"Demo Student {index}", f"DEMO{index:04d}")
            for index in range(1, count + 1)
        ]

        student_ids: list[tuple[int, str]] = []
        for index, (name, nim) in enumerate(students, start=1):
            mac = f"{DEMO_MAC_PREFIX}{index:02x}"
            row = cursor.execute("SELECT id FROM students WHERE nim = ?", (nim,)).fetchone()
            if row:
                cursor.execute("UPDATE students SET name = ?, mac_address = ? WHERE id = ?",
                               (name, mac, row["id"]))
                student_id = row["id"]
            else:
                cursor.execute(
                    "INSERT INTO students (name, nim, mac_address) VALUES (?, ?, ?)",
                    (name, nim, mac))
                student_id = cursor.lastrowid
            student_ids.append((student_id, name))
        conn.commit()
        print(f"students ready: {len(student_ids)}")

        # --- schedule active now -------------------------------------------
        now = now_local()
        start_dt = now - timedelta(minutes=5)
        end_dt = now + timedelta(minutes=55)
        start_time = start_dt.strftime("%H:%M")
        end_time = end_dt.strftime("%H:%M")
        if end_dt.date() != now.date():          # never cross midnight
            end_time = "23:59"
        cursor.execute(
            "INSERT INTO schedules (class_name, day_of_week, start_time, end_time, ap_bssid, room, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("Demo Class", now.weekday(), start_time, end_time, None, "Demo Room A",
             now.strftime("%Y-%m-%d %H:%M:%S")))
        schedule_id = cursor.lastrowid
        conn.commit()
        print(f"schedule created: id={schedule_id} 'Demo Class' {start_time}-{end_time} "
              f"(today, server timezone)")

        # --- sample attendance rows ---------------------------------------
        demo_times: dict[int, list[tuple[str, str, float]]] = {
            student_ids[0][0]: [("start", "verified", 0.86), ("end", "verified", 0.91)],
        }
        if len(student_ids) >= 2:
            demo_times[student_ids[1][0]] = [
                ("start", "verified", 0.81), ("end", "verified", 0.88)]
        if len(student_ids) >= 3:
            # Only a start row: shows the "waiting for end selfie" (face_only)
            # state on the dashboard.
            demo_times[student_ids[2][0]] = [("start", "face_only", 0.73)]

        rows_added = 0
        for student_id, timeline in demo_times.items():
            # START first (further in the past), then END closer to now.
            for offset_minutes, (check_type, status, confidence) in zip((6, 2), timeline):
                timestamp = (now - timedelta(minutes=offset_minutes)).strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    "INSERT INTO attendance (student_id, schedule_id, check_type, confidence, "
                    "wifi_verified, status, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (student_id, schedule_id, check_type, confidence,
                     1 if status == "verified" else 0, status, timestamp))
                rows_added += 1
        conn.commit()
        print(f"attendance rows created: {rows_added}")

        # --- summary --------------------------------------------------------
        print("\n--- demo data summary ---")
        for student_id, name in student_ids:
            print(f"  student id={student_id:<3} {name}")
        print(f"  schedule id={schedule_id:<3} Demo Class {start_time}-{end_time} "
              f"(server timezone: {os.getenv('TIMEZONE', 'system local')})")
        print("\nOpen the dashboard: http://127.0.0.1:8000/dashboard")
        print("Demo MACs are fake (02:00:00:00:00:NN): the Wi-Fi prompt stays false for")
        print("these students. For a live Wi-Fi demo set a real phone MAC with")
        print("PUT /students/{id}/mac, or use the real students instead.")
        print("Run with --reset to start from a clean database before the next demo.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
