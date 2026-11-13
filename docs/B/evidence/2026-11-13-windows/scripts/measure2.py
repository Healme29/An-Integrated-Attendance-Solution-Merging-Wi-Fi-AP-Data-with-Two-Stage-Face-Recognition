"""Second measured run: hardening evidence on the Windows laptop (member B).

Covers: model presence, recognition error paths, upload-cap gap, SQLite
concurrency under parallel writes, backup/restore, and corrupt-DB startup.
Every printed number is measured; nothing is estimated.
"""
import concurrent.futures
import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import time

import httpx

ROOT = r"D:\NJUPT ( NANJING UNIVERSITY OF POSTS AND TELECOMMUNICATIONS )\STITP\An-Integrated-Attendance-Solution-Merging-Wi-Fi-AP-Data-with-Two-Stage-Face-Recognition"
TMP = r"C:\Users\nonia\AppData\Local\Temp\opencode\g1win\run2"
DB = os.path.join(TMP, "attendance.db")
DATA = os.path.join(TMP, "data")
PORT = 8013
BASE = f"http://127.0.0.1:{PORT}"
TZ = "Asia/Shanghai"

env = os.environ.copy()
env.update({
    "DATABASE_PATH": DB,
    "DATA_DIR": DATA,
    "TIMEZONE": TZ,
    "CORS_ORIGINS": f"http://127.0.0.1:{PORT}",
    "PYTHONUNBUFFERED": "1",
})

client = httpx.Client(timeout=120, trust_env=False)
OUT = []


def say(*parts):
    line = " ".join(str(p) for p in parts)
    OUT.append(line)
    print(line, flush=True)


def start_server(logname, wait_for_healthy_s=120):
    log_path = os.path.join(TMP, logname)
    log = open(log_path, "w", encoding="utf-8")
    started = time.perf_counter()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app",
         "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    deadline = time.time() + wait_for_healthy_s
    while time.time() < deadline:
        if proc.poll() is not None:
            return proc, None, (time.perf_counter() - started) * 1000, log_path
        try:
            r = httpx.get(f"{BASE}/health", timeout=1, trust_env=False)
            if r.status_code == 200:
                return proc, (time.perf_counter() - started) * 1000, None, log_path
            return proc, None, (time.perf_counter() - started) * 1000, log_path
        except Exception:
            pass
        time.sleep(0.05)
    return proc, None, None, log_path


def stop_server(proc, grace=20):
    if proc.poll() is not None:
        return proc.returncode, 0.0
    t0 = time.perf_counter()
    proc.terminate()
    try:
        proc.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)
    return proc.returncode, time.perf_counter() - t0


def log_tail(path, lines=6):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return json.dumps("".join(handle.readlines()[-lines:]).strip()[:600])
    except OSError:
        return "\"\""


def main():
    shutil.rmtree(TMP, ignore_errors=True)
    os.makedirs(os.path.join(DATA, "models"), exist_ok=True)
    os.makedirs(TMP, exist_ok=True)

    say("=== environment ===")
    say("python", sys.version.split()[0], "| cwd", ROOT)
    say("database", DB)
    say("data_dir", DATA)

    say("\n=== 0. model files ===")
    src_model = os.path.join(ROOT, "backend", "data", "models", "yolov8m-face.pt")
    dst_model = os.path.join(DATA, "models", "yolov8m-face.pt")
    t0 = time.perf_counter()
    shutil.copyfile(src_model, dst_model)
    copy_ms = (time.perf_counter() - t0) * 1000
    digest = hashlib.sha256(open(dst_model, "rb").read()).hexdigest()
    say("yolo_model_bytes", os.path.getsize(dst_model), "copy_ms", f"{copy_ms:.0f}")
    say("yolo_model_sha256", digest)
    insight_home = os.path.join(os.path.expanduser("~"), ".insightface")
    buffalo = os.path.join(insight_home, "models", "buffalo_l")
    say("insightface_home", insight_home, "buffalo_l_present", os.path.isdir(buffalo))
    if os.path.isdir(buffalo):
        files = sorted(os.listdir(buffalo))
        total = sum(os.path.getsize(os.path.join(buffalo, f)) for f in files
                    if os.path.isfile(os.path.join(buffalo, f)))
        say("buffalo_l_files", json.dumps(files), "total_bytes", total)

    say("\n=== 1. cold start ===")
    proc, cold_ms, early_ms, log_path = start_server("s1.log")
    if cold_ms is None:
        say("COLD START FAILED early_ms", early_ms, "exit", proc.poll())
        say("log_tail", log_tail(log_path, 12))
        return 1
    say(f"cold_start_to_healthy_ms {cold_ms:.0f}")

    say("\n=== 2. recognition error paths (YOLO model present) ===")
    png = open(os.path.join(ROOT, "mobile", "android", "app", "src", "main", "res",
                            "mipmap-xxxhdpi", "ic_launcher.png"), "rb").read()
    say("no_face_png_bytes", len(png))
    for attempt in (1, 2):
        t0 = time.perf_counter()
        r = client.post(BASE + "/faces/recognize", files={"file": ("icon.png", png, "image/png")})
        elapsed = (time.perf_counter() - t0) * 1000
        try:
            body = r.json()
        except Exception:
            body = r.text[:200]
        say(f"recognize_no_face_attempt{attempt} status={r.status_code} ms={elapsed:.0f}", json.dumps(body)[:220])

    corrupt_png = b"\x89PNG\r\n\x1a\n" + b"not a real png" * 100
    r = client.post(BASE + "/faces/recognize", files={"file": ("x.png", corrupt_png, "image/png")})
    say("recognize_corrupt_png status", r.status_code, json.dumps(r.json())[:160] if r.headers.get("content-type", "").startswith("application/json") else r.text[:160])

    say("\n=== 3. upload cap gap on /faces/recognize and /attendance/check ===")
    big = b"\xff\xd8\xff" + os.urandom(11 * 1024 * 1024)
    t0 = time.perf_counter()
    r = client.post(BASE + "/faces/recognize", files={"file": ("big.jpg", big, "image/jpeg")})
    big_ms = (time.perf_counter() - t0) * 1000
    say("oversized_11MB_recognize status", r.status_code, "ms", f"{big_ms:.0f}", "body", r.text[:200].replace("\n", " "))
    t0 = time.perf_counter()
    r = client.post(BASE + f"/faces/enroll?student_id=1", files={"file": ("big.jpg", big, "image/jpeg")})
    big_enroll_ms = (time.perf_counter() - t0) * 1000
    say("oversized_11MB_enroll status", r.status_code, "ms", f"{big_enroll_ms:.0f}", "body", r.text[:160].replace("\n", " "))
    r = client.post(BASE + f"/attendance/check?student_id=1&schedule_id=1&check_type=start",
                    files={"file": ("big.jpg", big, "image/jpeg")})
    say("oversized_11MB_attendance_check status", r.status_code, "body", r.text[:160].replace("\n", " "))
    del big

    say("\n=== 4. face path without a face image ===")
    r = client.post(BASE + f"/attendance/check?student_id=1&schedule_id=1&check_type=start",
                    files={"file": ("icon.png", png, "image/png")})
    say("attendance_check_no_face status", r.status_code, "body", r.text[:200].replace("\n", " "))

    say("\n=== 5. SQLite concurrency: parallel writes and reads ===")
    def write_one(i):
        t0 = time.perf_counter()
        try:
            r = client.post(BASE + "/students/", json={
                "name": f"Conc {i}", "nim": f"CONC{i:03d}", "mac_address": None,
            })
            return r.status_code, (time.perf_counter() - t0) * 1000, r.text[:120]
        except Exception as exc:  # noqa: BLE001
            return 0, (time.perf_counter() - t0) * 1000, repr(exc)[:120]

    def read_one(_):
        t0 = time.perf_counter()
        try:
            r = client.get(BASE + "/students/")
            return r.status_code, (time.perf_counter() - t0) * 1000, len(r.json())
        except Exception as exc:  # noqa: BLE001
            return 0, (time.perf_counter() - t0) * 1000, repr(exc)[:120]

    for label, fn, n in (("write", write_one, 24), ("read", read_one, 24)):
        t0 = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=n) as pool:
            results = list(pool.map(fn, range(n)))
        wall = (time.perf_counter() - t0) * 1000
        codes = {}
        for code, _, _ in results:
            codes[code] = codes.get(code, 0) + 1
        lat = sorted(r[1] for r in results)
        errs = [r[2] for r in results if r[0] != 200][:4]
        say(f"concurrent_{label}_n={n} wall_ms={wall:.0f} codes={json.dumps(codes)} "
            f"p50_ms={statistics.median(lat):.0f} max_ms={max(lat):.0f}")
        if errs:
            say(f"concurrent_{label}_sample_errors", json.dumps(errs))

    r = client.get(BASE + "/students/")
    say("students_rows_after_concurrency", len(r.json()) if r.status_code == 200 else r.status_code)
    lock_events = 0
    with open(log_path, encoding="utf-8", errors="replace") as handle:
        lock_events = sum("database is locked" in line for line in handle)
    say("log_lines_with_database_is_locked", lock_events)

    say("\n=== 6. clean shutdown time ===")
    code, shutdown_s = stop_server(proc)
    say("shutdown_exit_code", code, "shutdown_s", f"{shutdown_s:.2f}")

    say("\n=== 7. backup and restore ===")
    backup = os.path.join(TMP, "attendance.backup.db")
    t0 = time.perf_counter()
    shutil.copyfile(DB, backup)
    say("backup_copy_ms", f"{(time.perf_counter()-t0)*1000:.1f}", "size_bytes", os.path.getsize(backup))
    os.remove(DB)
    t0 = time.perf_counter()
    proc, healthy_ms, _, log_path = start_server("s2.log")
    say("start_without_db_healthy_ms", f"{healthy_ms:.0f}" if healthy_ms else "FAILED", "exit", proc.returncode if healthy_ms is None else None)
    if healthy_ms:
        r = client.get(BASE + "/students/")
        say("students_after_fresh_db", len(r.json()) if r.status_code == 200 else r.status_code)
        stop_server(proc)
    t0 = time.perf_counter()
    shutil.copyfile(backup, DB)
    restore_copy_ms = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter()
    proc, restore_ms, _, log_path = start_server("s3.log")
    say("restore_copy_ms", f"{restore_copy_ms:.1f}", "start_to_healthy_ms", f"{restore_ms:.0f}" if restore_ms else "FAILED")
    if restore_ms:
        r = client.get(BASE + "/students/?nim=CONC000")
        say("restored_row_nim_CONC000 status", r.status_code, "rows", len(r.json()))
        stop_server(proc)

    say("\n=== 8. corrupt database at startup ===")
    with open(DB, "wb") as handle:
        handle.write(b"this is not a sqlite database" * 1000)
    proc, healthy, boot_ms, log_path = start_server("s4.log", wait_for_healthy_s=20)
    say("corrupt_exit_after_ms", f"{boot_ms:.0f}" if boot_ms else "none", "poll", proc.poll())
    if proc.poll() is None:
        say("still_alive_after_20s True -> killing")
        code, _ = stop_server(proc, grace=1)
        say("killed_exit_code", code)
    say("corrupt_log_tail", log_tail(log_path, 3))

    with open(os.path.join(TMP, "measurements.txt"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(OUT) + "\n")
    say("\nwrote", os.path.join(TMP, "measurements.txt"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
