"""Third measured run: face-path behaviour after installing the missing dill.

The YOLO checkpoint is loaded for real here (warm-up), so timings are measured
from an actual model load; ArcFace is not reached because no real face photo is
available on this machine (recorded as not measured, not estimated).
"""
import json
import os
import shutil
import subprocess
import sys
import time

import httpx

ROOT = r"D:\NJUPT ( NANJING UNIVERSITY OF POSTS AND TELECOMMUNICATIONS )\STITP\An-Integrated-Attendance-Solution-Merging-Wi-Fi-AP-Data-with-Two-Stage-Face-Recognition"
TMP = r"C:\Users\nonia\AppData\Local\Temp\opencode\g1win\run3"
DB = os.path.join(TMP, "attendance.db")
DATA = os.path.join(TMP, "data")
PORT = 8014
BASE = f"http://127.0.0.1:{PORT}"

env = os.environ.copy()
env.update({
    "DATABASE_PATH": DB, "DATA_DIR": DATA, "TIMEZONE": "Asia/Shanghai",
    "CORS_ORIGINS": f"http://127.0.0.1:{PORT}", "PYTHONUNBUFFERED": "1",
})
client = httpx.Client(timeout=180, trust_env=False)
OUT = []


def say(*parts):
    line = " ".join(str(p) for p in parts)
    OUT.append(line)
    print(line, flush=True)


def start_server(logname):
    log = open(os.path.join(TMP, logname), "w", encoding="utf-8")
    t0 = time.perf_counter()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app",
         "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    while time.perf_counter() - t0 < 120:
        if proc.poll() is not None:
            return proc, None, os.path.join(TMP, logname)
        try:
            if httpx.get(f"{BASE}/health", timeout=1, trust_env=False).status_code == 200:
                return proc, (time.perf_counter() - t0) * 1000, os.path.join(TMP, logname)
        except Exception:
            pass
        time.sleep(0.05)
    raise RuntimeError("not healthy")


def stop(proc):
    proc.terminate()
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)


def main():
    shutil.rmtree(TMP, ignore_errors=True)
    os.makedirs(os.path.join(DATA, "models"), exist_ok=True)
    shutil.copyfile(os.path.join(ROOT, "backend", "data", "models", "yolov8m-face.pt"),
                    os.path.join(DATA, "models", "yolov8m-face.pt"))

    say("=== environment ===")
    say("python", sys.version.split()[0])
    try:
        import dill
        say("dill_installed", dill.__version__)
    except Exception as exc:  # noqa: BLE001
        say("dill_missing", repr(exc))

    proc, cold_ms, log_path = start_server("s1.log")
    say(f"cold_start_to_healthy_ms {cold_ms:.0f}")
    r = client.post(BASE + "/students/", json={"name": "Face Path", "nim": "FACE01", "mac_address": None})
    student_id = r.json()["id"]
    say("student_id", student_id)

    png = open(os.path.join(ROOT, "mobile", "android", "app", "src", "main", "res",
                            "mipmap-xxxhdpi", "ic_launcher.png"), "rb").read()

    say("\n=== 1. YOLO cold load and warm inference (no-face image) ===")
    for attempt in (1, 2, 3):
        t0 = time.perf_counter()
        r = client.post(BASE + "/faces/recognize", files={"file": ("icon.png", png, "image/png")})
        ms = (time.perf_counter() - t0) * 1000
        say(f"recognize_no_face_{attempt} status={r.status_code} ms={ms:.0f}", r.text[:160])

    say("\n=== 2. enroll without a face ===")
    t0 = time.perf_counter()
    r = client.post(BASE + f"/faces/enroll?student_id={student_id}",
                    files={"file": ("icon.png", png, "image/png")})
    say("enroll_no_face status", r.status_code, "ms", f"{(time.perf_counter()-t0)*1000:.0f}", r.text[:160])

    say("\n=== 3. check-in without a face (valid student) ===")
    t0 = time.perf_counter()
    r = client.post(BASE + f"/attendance/check?student_id={student_id}&schedule_id=1&check_type=start",
                    files={"file": ("icon.png", png, "image/png")})
    say("attendance_check_no_face status", r.status_code,
        "ms", f"{(time.perf_counter()-t0)*1000:.0f}", r.text[:200].replace("\n", " "))

    say("\n=== 4. upload cap: 11 MB body (limit is 10 MB) ===")
    big = b"\xff\xd8\xff" + os.urandom(11 * 1024 * 1024)
    for label, url in (
        ("recognize", "/faces/recognize"),
        ("attendance_check", f"/attendance/check?student_id={student_id}&schedule_id=1&check_type=start"),
        ("enroll", f"/faces/enroll?student_id={student_id}"),
    ):
        t0 = time.perf_counter()
        r = client.post(BASE + url, files={"file": ("big.jpg", big, "image/jpeg")})
        say(f"oversized_11MB_{label} status={r.status_code} ms={(time.perf_counter()-t0)*1000:.0f}", r.text[:160].replace("\n", " "))
    del big

    say("\n=== 5. image decode edge cases ===")
    corrupt = b"\xff\xd8\xff" + b"garbage" * 200
    r = client.post(BASE + "/faces/recognize", files={"file": ("bad.jpg", corrupt, "image/jpeg")})
    say("truncated_jpeg status", r.status_code, r.text[:160])
    gray = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000100000001008000000003a7e9b55"
        "0000000a49444154789c6360000002000154a24f6c0000000049454e44ae426082")
    r = client.post(BASE + "/faces/recognize", files={"file": ("tiny.png", gray, "image/png")})
    say("tiny_valid_png status", r.status_code, r.text[:160])

    say("\n=== 6. shutdown ===")
    t0 = time.perf_counter()
    stop(proc)
    say("shutdown_s", f"{time.perf_counter()-t0:.2f}")
    with open(log_path, encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    say("log_500_count", text.count(" 500 Internal Server Error"))
    say("log_traceback_count", text.count("Traceback (most recent call last)"))

    with open(os.path.join(TMP, "measurements.txt"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(OUT) + "\n")
    say("\nwrote", os.path.join(TMP, "measurements.txt"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
