"""Run the project smoke test against a native server on this Windows laptop."""
import os
import shutil
import subprocess
import sys
import time

import httpx

ROOT = r"D:\NJUPT ( NANJING UNIVERSITY OF POSTS AND TELECOMMUNICATIONS )\STITP\An-Integrated-Attendance-Solution-Merging-Wi-Fi-AP-Data-with-Two-Stage-Face-Recognition"
TMP = r"C:\Users\nonia\AppData\Local\Temp\opencode\g1win\run4"
PORT = 8015
BASE = f"http://127.0.0.1:{PORT}"

env = os.environ.copy()
env.update({
    "DATABASE_PATH": os.path.join(TMP, "attendance.db"),
    "DATA_DIR": os.path.join(TMP, "data"),
    "TIMEZONE": "Asia/Shanghai",
    "REQUIRE_CLASSROOM_WIFI": "false",
    "PYTHONUNBUFFERED": "1",
})

os.makedirs(os.path.join(TMP, "data", "models"), exist_ok=True)
shutil.copyfile(os.path.join(ROOT, "backend", "data", "models", "yolov8m-face.pt"),
                os.path.join(TMP, "data", "models", "yolov8m-face.pt"))

log = open(os.path.join(TMP, "smoke_server.log"), "w", encoding="utf-8")
proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.main:app",
                         "--host", "127.0.0.1", "--port", str(PORT)],
                        cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
t0 = time.perf_counter()
while time.perf_counter() - t0 < 120:
    try:
        if httpx.get(BASE + "/health", timeout=1, trust_env=False).status_code == 200:
            break
    except Exception:
        pass
    time.sleep(0.1)
print(f"healthy_after_ms {(time.perf_counter()-t0)*1000:.0f}")

# Warm the detector so the smoke run measures behaviour, not model loading.
tiny = open(os.path.join(ROOT, "mobile", "android", "app", "src", "main", "res",
                        "mipmap-xxxhdpi", "ic_launcher.png"), "rb").read()
t0 = time.perf_counter()
r = httpx.post(BASE + "/faces/recognize", files={"file": ("i.png", tiny, "image/png")},
               timeout=180, trust_env=False)
print(f"warmup_recognize status={r.status_code} ms={(time.perf_counter()-t0)*1000:.0f}")

t0 = time.perf_counter()
smoke = subprocess.run([sys.executable, os.path.join(ROOT, "backend", "scripts", "smoke_test.py"),
                        "--base-url", BASE], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=300)
print(f"smoke_wall_s {time.perf_counter()-t0:.1f}")
print(smoke.stdout.strip())
print(smoke.stderr.strip()[:500])
print("smoke_exit", smoke.returncode)

proc.terminate()
try:
    proc.wait(timeout=20)
except subprocess.TimeoutExpired:
    proc.kill()
log.close()
print("server_stopped")
