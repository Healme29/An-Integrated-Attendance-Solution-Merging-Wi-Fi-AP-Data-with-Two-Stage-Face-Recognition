"""Measured G1 evidence run on the Windows laptop (member B, M2 stage 1).

Runs entirely outside the repo, against an isolated DATABASE_PATH/DATA_DIR.
Every number printed here is a real measurement; nothing is estimated.
"""
import json
import os
import platform
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

ROOT = r"D:\NJUPT ( NANJING UNIVERSITY OF POSTS AND TELECOMMUNICATIONS )\STITP\An-Integrated-Attendance-Solution-Merging-Wi-Fi-AP-Data-with-Two-Stage-Face-Recognition"
TMP = r"C:\Users\nonia\AppData\Local\Temp\opencode\g1win"
DB = os.path.join(TMP, "attendance.db")
DATA = os.path.join(TMP, "data")
PORT = 8011
BASE = f"http://127.0.0.1:{PORT}"
TZ = "Asia/Shanghai"

env = os.environ.copy()
env.update({
    "DATABASE_PATH": DB,
    "DATA_DIR": DATA,
    "TIMEZONE": TZ,
    "FACE_SIMILARITY_THRESHOLD": "0.5",
    "YOLO_IMG_SIZE": "640",
    "CORS_ORIGINS": f"http://127.0.0.1:{PORT}",
    "PYTHONUNBUFFERED": "1",
})

client = httpx.Client(timeout=60, trust_env=False)
OUT = []


def say(*parts):
    line = " ".join(str(p) for p in parts)
    OUT.append(line)
    print(line, flush=True)


def start_server(logname):
    log_path = os.path.join(TMP, logname)
    log = open(log_path, "w", encoding="utf-8")
    started = time.perf_counter()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app",
         "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    deadline = time.time() + 120
    while time.time() < deadline:
        if proc.poll() is not None:
            log.close()
            return proc, None, log_path
        try:
            r = httpx.get(f"{BASE}/health", timeout=1, trust_env=False)
            if r.status_code == 200:
                return proc, (time.perf_counter() - started) * 1000, log_path
        except Exception:
            pass
        time.sleep(0.05)
    proc.terminate()
    log.close()
    raise RuntimeError("server did not become healthy within 120 s")


def stop_server(proc):
    proc.terminate()
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)


def log_tail(path, lines=8):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return "".join(handle.readlines()[-lines:])
    except OSError:
        return ""


def ap_log_count():
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        return conn.execute("SELECT COUNT(*) FROM ap_logs").fetchone()[0]
    finally:
        conn.close()


def main():
    os.makedirs(TMP, exist_ok=True)
    os.makedirs(DATA, exist_ok=True)
    for name in ("attendance.db", "attendance.db-journal", "attendance.backup.db"):
        path = os.path.join(TMP, name)
        if os.path.exists(path):
            os.remove(path)

    say("=== environment ===")
    say("python", sys.version.split()[0])
    say("platform", platform.platform())
    say("machine", platform.machine(), "processor", platform.processor())
    say("timezone_setting", TZ, "| system", datetime.now().astimezone().tzinfo)
    say("database", DB)
    say("data_dir", DATA)

    say("\n=== 1. cold start and core endpoints ===")
    proc, cold_ms, log_path = start_server("server1.log")
    if cold_ms is None:
        say("COLD START FAILED")
        say(log_tail(log_path, 20))
        return 1
    say(f"cold_start_to_healthy_ms {cold_ms:.0f}")

    for path in ("/health", "/", "/dashboard"):
        samples = []
        for _ in range(3):
            t0 = time.perf_counter()
            r = client.get(BASE + path)
            samples.append((time.perf_counter() - t0) * 1000)
        say(f"GET {path} status={r.status_code} median_ms={sorted(samples)[1]:.1f}")
    say("health_body", client.get(BASE + "/health").json())

    say("\n=== 2. TIMEZONE applied ===")
    nim = "G1WIN01"
    r = client.post(BASE + "/students/", json={
        "name": "G1 Windows Persistence Check", "nim": nim, "mac_address": None,
    })
    student = r.json()
    say("POST /students/ status", r.status_code, "created_at", student.get("created_at"))
    now_local = datetime.now(ZoneInfo(TZ))
    r = client.post(BASE + "/schedules/", json={
        "class_name": "G1 Windows Class",
        "day_of_week": now_local.weekday(),
        "start_time": (now_local - timedelta(minutes=5)).strftime("%H:%M"),
        "end_time": (now_local + timedelta(minutes=30)).strftime("%H:%M"),
        "room": "Windows Lab",
    })
    schedule = r.json()
    say("POST /schedules/ status", r.status_code, "created_at", schedule.get("created_at"))
    try:
        utc_dt = datetime.fromisoformat(student["created_at"])
        local_dt = datetime.fromisoformat(schedule["created_at"])
        say("created_at delta hours", round((local_dt - utc_dt).total_seconds() / 3600, 2))
    except Exception as exc:  # noqa: BLE001
        say("delta calculation failed", repr(exc))

    say("\n=== 3. Wi-Fi scan on the real campus network ===")
    before = ap_log_count()
    t0 = time.perf_counter()
    scan1 = client.get(BASE + "/wifi/scan")
    fresh_ms = (time.perf_counter() - t0) * 1000
    after_first = ap_log_count()
    t0 = time.perf_counter()
    scan2 = client.get(BASE + "/wifi/scan")
    cached_ms = (time.perf_counter() - t0) * 1000
    after_second = ap_log_count()
    scan_json = scan1.json()
    say("scan_status", scan1.status_code, "fresh_ms", f"{fresh_ms:.0f}", "cached_ms", f"{cached_ms:.0f}")
    say("scan_body", json.dumps({k: scan_json[k] for k in ("devices", "subnet", "count", "bssid")}))
    say("ap_logs_rows before", before, "after_first", after_first, "after_second", after_second)

    say("\n=== 4. persistence across a restart ===")
    stop_server(proc)
    proc, warm_ms, log_path = start_server("server2.log")
    say(f"restart_to_healthy_ms {warm_ms:.0f}" if warm_ms else "RESTART FAILED")
    r = client.get(BASE + f"/students/?nim={nim}")
    say("GET /students/?nim status", r.status_code, "rows", len(r.json()),
        "id", r.json()[0]["id"] if r.json() else None)

    say("\n=== 5. end-to-end smoke test (native, Windows) ===")
    smoke = subprocess.run(
        [sys.executable, os.path.join(ROOT, "backend", "scripts", "smoke_test.py"),
         "--base-url", BASE],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=300,
    )
    for line in (smoke.stdout + smoke.stderr).strip().splitlines():
        say("smoke:", line)
    say("smoke_exit_code", smoke.returncode)

    say("\n=== 6. offline seed data (server stopped) ===")
    stop_server(proc)
    t0 = time.perf_counter()
    seed = subprocess.run(
        [sys.executable, os.path.join(ROOT, "backend", "scripts", "seed_demo.py"),
         "--reset", "--students", "5"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=300,
    )
    seed_ms = (time.perf_counter() - t0) * 1000
    for line in (seed.stdout + seed.stderr).strip().splitlines():
        say("seed:", line)
    say("seed_wall_ms", f"{seed_ms:.0f}", "exit", seed.returncode)

    proc, seed_start_ms, log_path = start_server("server3.log")
    say(f"post_seed_start_to_healthy_ms {seed_start_ms:.0f}" if seed_start_ms else "START FAILED")
    r = client.get(BASE + "/attendance/today")
    today = r.json()
    say("GET /attendance/today status", r.status_code, "rows", len(today))
    if today:
        say("first_row", json.dumps(today[0]))
    r = client.get(BASE + "/attendance/export/csv")
    say("GET /attendance/export/csv status", r.status_code, "lines", len(r.text.splitlines()),
        "header", r.text.splitlines()[0] if r.text else "")
    r = client.get(BASE + "/me/prompt?student_id=1")
    say("GET /me/prompt student 1 status", r.status_code, "body", json.dumps(r.json())[:200])
    stop_server(proc)

    say("\n=== 7. backup, corruption and restore ===")
    backup = os.path.join(TMP, "attendance.backup.db")
    t0 = time.perf_counter()
    shutil.copyfile(DB, backup)
    backup_ms = (time.perf_counter() - t0) * 1000
    say("backup_copy_ms", f"{backup_ms:.1f}", "size_bytes", os.path.getsize(backup))

    with open(DB, "wb") as handle:
        handle.write(b"this is not a sqlite database" * 1000)
    proc, _, bad_log = start_server("server_corrupt.log")
    time.sleep(2)
    failed_ok = proc.poll() is not None
    say("corrupt_start_failed", failed_ok, "exit_code", proc.poll())
    say("corrupt_log_tail", json.dumps(log_tail(bad_log, 4).strip()[:400]))
    if proc.poll() is None:
        stop_server(proc)

    t0 = time.perf_counter()
    shutil.copyfile(backup, DB)
    restore_copy_ms = (time.perf_counter() - t0) * 1000
    t_total = time.perf_counter()
    proc, restore_ms, log_path = start_server("server4.log")
    total_ms = (time.perf_counter() - t_total) * 1000
    say("restore_copy_ms", f"{restore_copy_ms:.1f}",
        "start_to_healthy_ms", f"{restore_ms:.0f}" if restore_ms else "FAILED",
        "total_ms", f"{total_ms:.0f}")
    if restore_ms is not None:
        r = client.get(BASE + "/health")
        say("health_after_restore", r.status_code, json.dumps(r.json()))
        stop_server(proc)

    say("\n=== 8. model files present? ===")
    for path in (
        os.path.join(ROOT, "backend", "data", "models", "yolov8m-face.pt"),
        os.path.join(DATA, "models", "yolov8m-face.pt"),
        os.path.join(DATA, "insightface"),
    ):
        say("exists", os.path.exists(path), path)

    with open(os.path.join(TMP, "measurements.txt"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(OUT) + "\n")
    say("\nwrote", os.path.join(TMP, "measurements.txt"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
