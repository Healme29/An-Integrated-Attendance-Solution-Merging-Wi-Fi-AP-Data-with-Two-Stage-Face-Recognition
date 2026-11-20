"""Seed demo data for a presentation (offline fallback).

Creates sample students, one QR class session active **right now**, and sample
attendance rows, so the teacher dashboard and the app have something to show
even if the live demo fails or no real check-in has happened yet.

Runs directly against the SQLite file, so the API server does not have to be
running (stop it on Windows to avoid file locks).

Examples:
    python backend/scripts/seed_demo.py                 # add demo data
    python backend/scripts/seed_demo.py --reset         # wipe ALL data first
    python backend/scripts/seed_demo.py --students 5    # more sample students
    python backend/scripts/seed_demo.py --db some.db     # use another database

The seeded session is open now and rotates its QR token like a real one, so
the dashboard shows a live QR code immediately.
"""
import argparse
import os
import secrets
import sqlite3
import sys
from datetime import timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

TOKEN_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
MAX_DEMO_STUDENTS = 99


def demo_token() -> str:
    return "".join(secrets.choice(TOKEN_ALPHABET) for _ in range(6))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true",
                        help="delete all existing students/attendance first")
    parser.add_argument("--students", type=int, default=30,
                        help="number of demo students to create (default: 30, max 99)")
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
            cursor.execute("DELETE FROM faces")
            cursor.execute("DELETE FROM class_students")
            cursor.execute("DELETE FROM classes")
            cursor.execute("DELETE FROM students")
            cursor.execute("DELETE FROM qr_sessions")
            # Restart ids at 1 so screenshots stay tidy.
            for table in ("students", "attendance", "faces", "qr_sessions", "classes", "class_students"):
                cursor.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table,))
            conn.commit()
            print("reset: all students, faces, attendance and qr_sessions deleted")
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
        for name, nim in students:
            row = cursor.execute("SELECT id FROM students WHERE nim = ?", (nim,)).fetchone()
            if row:
                cursor.execute("UPDATE students SET name = ? WHERE id = ?", (name, row["id"]))
                student_id = row["id"]
            else:
                cursor.execute("INSERT INTO students (name, nim) VALUES (?, ?)", (name, nim))
                student_id = cursor.lastrowid
            student_ids.append((student_id, name))
        conn.commit()
        print(f"students ready: {len(student_ids)}")

        # --- class roster + QR session active now ---------------------------
        cursor.execute(
            "INSERT INTO classes (class_name, room, created_by) VALUES (?, ?, ?)",
            ("Demo Class", "Demo Room A", "demo"),
        )
        class_id = cursor.lastrowid
        for student_id, _name in student_ids:
            cursor.execute(
                "INSERT INTO class_students (class_id, student_id) VALUES (?, ?)",
                (class_id, student_id),
            )

        now = now_local()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "UPDATE qr_sessions SET is_active = 0, ended_at = ?, phase = 'closed' "
            "WHERE is_active = 1 AND ended_at IS NULL",
            (timestamp,))
        cursor.execute(
            "INSERT INTO qr_sessions (token, token_rotated_at, created_by, class_id, class_name, room, "
            "started_at, phase_started_at, is_active, phase, spot_round) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 'start', 0)",
            (demo_token(), timestamp, "demo", class_id, "Demo Class", "Demo Room A", timestamp, timestamp))
        session_id = cursor.lastrowid
        conn.commit()
        print(f"class created: id={class_id} with {len(student_ids)} enrolled students")
        print(f"qr session created: id={session_id} 'Demo Class' (START phase, rotating token)")

        # --- sample attendance rows ----------------------------------------
        demo_confidences = [0.86, 0.81, 0.73][: len(student_ids)]
        rows_added = 0
        for (student_id, _name), confidence in zip(student_ids, demo_confidences):
            check_time = (now - timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO attendance (student_id, qr_session_id, check_type, confidence, ip_address, "
                "status, timestamp, faces_detected) VALUES (?, ?, 'start', ?, ?, 'verified', ?, 1)",
                (student_id, session_id, confidence, "192.168.1.50", check_time))
            rows_added += 1
        conn.commit()
        print(f"attendance rows created: {rows_added}")

        # --- summary --------------------------------------------------------
        print("\n--- demo data summary ---")
        for student_id, name in student_ids:
            print(f"  student id={student_id:<3} {name}")
        print(f"  qr session id={session_id:<3} Demo Class (server timezone: "
              f"{os.getenv('TIMEZONE', 'system local')})")
        print("\nOpen the dashboard: http://127.0.0.1:8000/dashboard")
        print("Run with --reset to start from a clean database before the next demo.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())