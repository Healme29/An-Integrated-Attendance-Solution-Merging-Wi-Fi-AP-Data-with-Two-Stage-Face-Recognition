"""Schema contract tests: fresh databases, additive migrations, legacy refusal.

The project policy is "current schema only": databases from the removed
schedule-based design are refused with a clear message instead of being
rebuilt (the old rebuild dropped tables and rewrote every attendance row).
"""
import asyncio
import sqlite3
from pathlib import Path

import pytest

from models import database

EXPECTED_COLUMNS = {
    "students": {"id", "name", "nim", "mac_address", "created_at"},
    "faces": {"id", "student_id", "embedding", "image_path", "created_at"},
    "classes": {"id", "class_name", "room", "created_by", "created_at"},
    "class_students": {"id", "class_id", "student_id", "added_at"},
    "qr_sessions": {
        "id", "token", "prev_token", "token_rotated_at", "created_by", "class_id",
        "class_name", "room", "started_at", "ended_at", "is_active", "phase",
        "spot_round", "phase_started_at",
    },
    "attendance": {
        "id", "student_id", "qr_session_id", "check_type", "spot_round",
        "confidence", "ip_address", "status", "timestamp", "faces_detected",
        "manual_by", "manual_at", "manual_reason",
    },
}


def _use_db(monkeypatch, path: Path) -> Path:
    monkeypatch.setattr(database, "DATABASE_PATH", path)
    return path


def _columns(path: Path, table: str) -> set[str]:
    con = sqlite3.connect(str(path))
    try:
        return {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
    finally:
        con.close()


def _table_names(path: Path) -> set[str]:
    con = sqlite3.connect(str(path))
    try:
        return {
            row[0]
            for row in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
    finally:
        con.close()


def test_fresh_db_has_current_schema(monkeypatch, tmp_path):
    db_path = _use_db(monkeypatch, tmp_path / "fresh.db")

    asyncio.run(database.init_db())

    tables = _table_names(db_path)
    for table, expected in EXPECTED_COLUMNS.items():
        assert table in tables, f"missing table {table}"
        assert _columns(db_path, table) == expected, f"column drift in {table}"


def test_init_db_is_idempotent(monkeypatch, tmp_path):
    db_path = _use_db(monkeypatch, tmp_path / "twice.db")

    asyncio.run(database.init_db())
    asyncio.run(database.init_db())

    assert _columns(db_path, "attendance") == EXPECTED_COLUMNS["attendance"]


def test_legacy_schedule_db_is_refused_without_touching_data(monkeypatch, tmp_path):
    db_path = _use_db(monkeypatch, tmp_path / "legacy.db")
    con = sqlite3.connect(str(db_path))
    con.executescript(
        """
        CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT, nim TEXT, mac_address TEXT);
        CREATE TABLE schedules (id INTEGER PRIMARY KEY, class_name TEXT, room TEXT);
        CREATE TABLE attendance (
            id INTEGER PRIMARY KEY,
            student_id INTEGER NOT NULL,
            schedule_id INTEGER,
            check_type TEXT,
            confidence REAL,
            status TEXT,
            timestamp TIMESTAMP
        );
        INSERT INTO students (id, name, nim) VALUES (1, 'Demo', 'F0001');
        INSERT INTO schedules (id, class_name, room) VALUES (1, 'Algorithms', 'Lab 1');
        INSERT INTO attendance (student_id, schedule_id, check_type, confidence, status, timestamp)
        VALUES (1, 1, 'start', 0.91, 'verified', '2026-10-24 21:32:13');
        """
    )
    con.commit()
    con.close()

    with pytest.raises(RuntimeError) as excinfo:
        asyncio.run(database.init_db())

    message = str(excinfo.value)
    assert "Legacy database detected" in message
    assert "schedules" in message

    # The refused file keeps its original tables and rows.
    tables = _table_names(db_path)
    assert {"schedules", "attendance"} <= tables
    con = sqlite3.connect(str(db_path))
    try:
        assert con.execute("SELECT COUNT(*) FROM attendance").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM schedules").fetchone()[0] == 1
    finally:
        con.close()


def test_qr_v2_db_gains_new_columns_and_keeps_rows(monkeypatch, tmp_path):
    """A previous QR database is upgraded additively: no row is changed."""
    db_path = _use_db(monkeypatch, tmp_path / "qr_v2.db")
    con = sqlite3.connect(str(db_path))
    con.executescript(
        """
        CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT, nim TEXT, mac_address TEXT);
        CREATE TABLE qr_sessions (
            id INTEGER PRIMARY KEY, token TEXT NOT NULL, prev_token TEXT,
            token_rotated_at TIMESTAMP NOT NULL, created_by TEXT,
            class_name TEXT NOT NULL, room TEXT, started_at TIMESTAMP,
            ended_at TIMESTAMP, is_active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE attendance (
            id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL,
            qr_session_id INTEGER NOT NULL, confidence REAL, ip_address TEXT,
            status TEXT NOT NULL DEFAULT 'verified', timestamp TIMESTAMP,
            faces_detected INTEGER DEFAULT 0
        );
        INSERT INTO students (id, name, nim) VALUES (1, 'Demo', 'F0001');
        INSERT INTO qr_sessions (id, token, token_rotated_at, class_name, started_at, is_active)
        VALUES (1, 'ABC234', '2026-11-19 08:00:00', 'Demo Class', '2026-11-19 08:00:00', 1);
        INSERT INTO attendance (student_id, qr_session_id, confidence, status, timestamp)
        VALUES (1, 1, 0.88, 'verified', '2026-11-19 08:01:00');
        """
    )
    con.commit()
    con.close()

    asyncio.run(database.init_db())

    assert _columns(db_path, "qr_sessions") == EXPECTED_COLUMNS["qr_sessions"]
    assert _columns(db_path, "attendance") == EXPECTED_COLUMNS["attendance"]
    con = sqlite3.connect(str(db_path))
    try:
        assert con.execute("SELECT COUNT(*) FROM attendance").fetchone()[0] == 1
        assert con.execute("SELECT qr_session_id FROM attendance").fetchone()[0] == 1
        assert con.execute("SELECT phase FROM qr_sessions").fetchone()[0] == "start"
        assert con.execute(
            "SELECT phase_started_at FROM qr_sessions"
        ).fetchone()[0] == "2026-11-19 08:00:00"
    finally:
        con.close()
