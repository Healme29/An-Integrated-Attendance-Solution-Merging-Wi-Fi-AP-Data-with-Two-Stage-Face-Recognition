"""Probe: how does uvicorn behave when attendance.db is not a SQLite file?"""
import os
import subprocess
import sys
import time

import httpx

ROOT = r"D:\NJUPT ( NANJING UNIVERSITY OF POSTS AND TELECOMMUNICATIONS )\STITP\An-Integrated-Attendance-Solution-Merging-Wi-Fi-AP-Data-with-Two-Stage-Face-Recognition"
TMP = r"C:\Users\nonia\AppData\Local\Temp\opencode\g1win"
DB = os.path.join(TMP, "probe_corrupt.db")
PORT = 8012
BASE = f"http://127.0.0.1:{PORT}"

with open(DB, "wb") as handle:
    handle.write(b"this is not a sqlite database" * 1000)

env = os.environ.copy()
env.update({"DATABASE_PATH": DB, "DATA_DIR": os.path.join(TMP, "data"),
            "TIMEZONE": "Asia/Shanghai", "PYTHONUNBUFFERED": "1"})

log_path = os.path.join(TMP, "probe_corrupt.log")
log = open(log_path, "w", encoding="utf-8")
t0 = time.perf_counter()
proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.main:app",
                         "--host", "127.0.0.1", "--port", str(PORT)],
                        cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
print("started pid", proc.pid)
for i in range(600):
    code = proc.poll()
    if code is not None:
        print(f"process exited after {(time.perf_counter()-t0):.2f}s code={code}")
        break
    if i % 20 == 0:
        try:
            r = httpx.get(BASE + "/health", timeout=0.5, trust_env=False)
            print(f"t={(time.perf_counter()-t0):.1f}s health={r.status_code} {r.text[:120]}")
        except Exception as exc:
            print(f"t={(time.perf_counter()-t0):.1f}s no-response {type(exc).__name__}")
    time.sleep(0.1)
else:
    print("still alive after 60s -> terminating")
    proc.kill()
    proc.wait(timeout=10)
    print("killed, code", proc.returncode)
log.close()

with open(log_path, encoding="utf-8", errors="replace") as handle:
    lines = handle.readlines()
print("--- last 6 log lines ---")
print("".join(lines[-6:]))
os.remove(DB)
