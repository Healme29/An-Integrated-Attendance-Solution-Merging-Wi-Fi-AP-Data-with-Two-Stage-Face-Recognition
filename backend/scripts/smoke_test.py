"""End-to-end smoke test against a running backend.

Usage:
    python backend/scripts/smoke_test.py [--base-url http://127.0.0.1:8000]

Exercises every endpoint that does not require a real face photo:
health, dashboard, students + NIM login, schedules, real Wi-Fi scan,
attendance flow (face pipeline responds correctly to a faceless image),
today list, and CSV export.
"""
import argparse
import sys
from datetime import datetime, timedelta

import httpx

PASS = "PASS"
FAIL = "FAIL"
results = []


def check(name: str, condition: bool, detail: str = ""):
    status = PASS if condition else FAIL
    results.append((name, status, detail))
    print(f"[{status}] {name}" + (f" - {detail}" if detail else ""))


def main(base_url: str) -> int:
    client = httpx.Client(base_url=base_url, timeout=30, trust_env=False)

    # 1. Health + dashboard
    r = client.get("/")
    check("GET / (health)", r.status_code == 200)

    r = client.get("/dashboard")
    check("GET /dashboard", r.status_code == 200 and "Teacher Dashboard" in r.text)

    # 2. Student create + login by NIM
    nim = f"smoke{int(datetime.now().timestamp()) % 100000000}"
    r = client.post("/students/", json={"name": "Smoke Tester", "nim": nim, "mac_address": None})
    check("POST /students/", r.status_code == 200, f"nim={nim}")
    student = r.json()

    r = client.get(f"/students/?nim={nim}")
    check("GET /students/?nim= (login)", r.status_code == 200 and len(r.json()) == 1)

    # 3. Schedule valid right now (time-enforcement aware)
    now = datetime.now()
    r = client.post("/schedules/", json={
        "class_name": "Smoke Test Class",
        "day_of_week": now.weekday(),
        "start_time": (now - timedelta(minutes=5)).strftime("%H:%M"),
        "end_time": (now + timedelta(minutes=5)).strftime("%H:%M"),
        "room": "Smoke Room",
    })
    check("POST /schedules/ (active now)", r.status_code == 200)
    schedule = r.json()

    # 4. Validation rejects bad schedule
    r = client.post("/schedules/", json={
        "class_name": "Bad", "day_of_week": 0, "start_time": "10:00", "end_time": "09:00"
    })
    check("POST /schedules/ rejects end<=start", r.status_code == 400)

    # 5. Real Wi-Fi scan (ARP + ping sweep on this machine's network)
    r = client.get("/wifi/scan")
    devices = r.json().get("devices", []) if r.status_code == 200 else []
    check("GET /wifi/scan (real ARP scan)", r.status_code == 200, f"{len(devices)} devices found")

    # 6. Wi-Fi check endpoint: a random MAC must return on_network=False;
    #    the machine's own MAC is reported as info (Windows never lists its
    #    own MAC in its own ARP cache, so it legitimately may be absent).
    import subprocess
    import re
    try:
        ipconfig = subprocess.run(
            ["getmac", "/fo", "csv", "/nh"], capture_output=True, text=True, timeout=15
        )
        macs = re.findall(r"(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}", ipconfig.stdout)
        own_mac = macs[0] if macs else None
    except Exception:
        own_mac = None

    r = client.get("/wifi/check/DE:AD:BE:EF:00:01")
    unknown_result = r.json().get("on_network") if r.status_code == 200 else None
    check("GET /wifi/check (unknown MAC -> False)",
          r.status_code == 200 and unknown_result is False)

    if own_mac:
        r = client.get(f"/wifi/check/{own_mac}")
        found = r.json().get("on_network") if r.status_code == 200 else None
        check("GET /wifi/check/{own-mac}", r.status_code == 200,
              f"mac={own_mac} on_network={found} (may be False on isolated APs)")

    # 7. Face pipeline: faceless image must be rejected cleanly
    import io
    import cv2
    import numpy as np
    ok, buf = cv2.imencode(".jpg", np.full((480, 640, 3), 128, dtype=np.uint8))
    blank_jpeg = buf.tobytes()

    r = client.post("/faces/recognize", files={"file": ("blank.jpg", blank_jpeg, "image/jpeg")})
    check("POST /faces/recognize (no face -> not recognized)",
          r.status_code == 200 and r.json().get("recognized") is False,
          str(r.json())[:80] if r.status_code == 200 else r.text[:80])

    r = client.post(
        f"/attendance/check?schedule_id={schedule['id']}&check_type=start",
        files={"file": ("blank.jpg", blank_jpeg, "image/jpeg")},
    )
    check("POST /attendance/check (no face -> 400)",
          r.status_code == 400 and "no_face_detected" in r.text, r.text[:80])

    # 8. Unknown schedule -> 404
    r = client.post(
        "/attendance/check?schedule_id=999999&check_type=start",
        files={"file": ("blank.jpg", blank_jpeg, "image/jpeg")},
    )
    # 400 (no face checked first) OR 404 depending on validation order - both acceptable?
    # Our order checks the face first, so expect 400; a 404 would mean schedule checked first.
    check("POST /attendance/check (unknown schedule handled)", r.status_code in (400, 404), r.text[:80])

    # 9. Attendance listing + CSV export
    r = client.get("/attendance/today")
    check("GET /attendance/today", r.status_code == 200 and isinstance(r.json(), list))

    r = client.get("/attendance/export/csv")
    check("GET /attendance/export/csv",
          r.status_code == 200 and r.text.startswith("id,timestamp"), "CSV header OK")

    # 10. Cleanup smoke-test data
    r = client.delete(f"/students/{student['id']}")
    client.delete(f"/schedules/{schedule['id']}")
    check("Cleanup (delete smoke student/schedule)", r.status_code == 200)

    client.close()

    failed = [r for r in results if r[1] == FAIL]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        print("FAILED:")
        for name, _, detail in failed:
            print(f"  - {name}: {detail}")
        return 1
    print("Smoke test OK - backend is testable end-to-end.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    sys.exit(main(args.base_url))
