"""End-to-end smoke test against a running backend.

Usage:
    python backend/scripts/smoke_test.py [--base-url http://127.0.0.1:8000]

Exercises every endpoint that does not require a real face photo:
health, dashboard, students + NIM login, QR session lifecycle (start,
rotating token, validate, QR PNG), attendance flow (face pipeline responds
correctly to a faceless image), today list, and CSV export.
"""
import argparse
import io
import sys
from datetime import datetime

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
    check("GET /dashboard",
          r.status_code == 200
          and "Teacher Dashboard" in r.text
          and "QR Code" in r.text)

    # 2. Student create + login by NIM
    nim = f"smoke{int(datetime.now().timestamp()) % 100000000}"
    r = client.post("/students/", json={"name": "Smoke Tester", "nim": nim, "mac_address": None})
    check("POST /students/", r.status_code == 200, f"nim={nim}")
    student = r.json()

    r = client.get(f"/students/?nim={nim}")
    check("GET /students/?nim= (login)", r.status_code == 200 and len(r.json()) == 1)

    # 3. QR session lifecycle: start -> active info -> rotating token -> QR image
    client.post("/qr-sessions/end")  # clear any session left over from a previous run
    r = client.post("/qr-sessions/start", json={
        "class_name": "Smoke Test Class",
        "room": "Smoke Room",
        "created_by": "smoke",
    })
    check("POST /qr-sessions/start", r.status_code == 200, str(r.json())[:80])
    session = r.json()

    r = client.get("/qr-sessions/active")
    check("GET /qr-sessions/active",
          r.status_code == 200
          and r.json().get("active") is True
          and r.json().get("session_id") == session["id"])

    r = client.get("/qr-sessions/active/token")
    token = r.json().get("token")
    check("GET /qr-sessions/active/token", r.status_code == 200 and bool(token), f"token={token}")

    r = client.post("/qr-sessions/validate", json={"token": token})
    check("POST /qr-sessions/validate (current token)",
          r.status_code == 200 and r.json().get("valid") is True)

    r = client.post("/qr-sessions/validate", json={"token": "ZZZZZZ"})
    check("POST /qr-sessions/validate (wrong token rejected)",
          r.status_code == 200 and r.json().get("valid") is False)

    r = client.get("/qr-sessions/active/qr.png")
    check("GET /qr-sessions/active/qr.png",
          r.status_code == 200 and r.headers.get("content-type") == "image/png")

    # 4. Face pipeline: faceless image must be rejected cleanly
    import cv2
    import numpy as np
    ok, buf = cv2.imencode(".jpg", np.full((480, 640, 3), 128, dtype=np.uint8))
    blank_jpeg = buf.tobytes()

    r = client.post("/faces/recognize", files={"file": ("blank.jpg", blank_jpeg, "image/jpeg")})
    check("POST /faces/recognize (no face -> not recognized)",
          r.status_code == 200 and r.json().get("recognized") is False,
          str(r.json())[:80] if r.status_code == 200 else r.text[:80])

    r = client.post(
        f"/attendance/check-qr?student_id={student['id']}&token={token}",
        files={"file": ("blank.jpg", blank_jpeg, "image/jpeg")},
    )
    check("POST /attendance/check-qr (no face -> 400)",
          r.status_code == 400 and "no_face_detected" in r.text, r.text[:80])

    r = client.post(
        f"/attendance/check-qr?student_id={student['id']}&token=WRONG1",
        files={"file": ("blank.jpg", blank_jpeg, "image/jpeg")},
    )
    check("POST /attendance/check-qr (invalid token -> 400)",
          r.status_code == 400 and "Invalid or expired QR code" in r.text, r.text[:80])

    # 5. Attendance listing + CSV export
    r = client.get(f"/attendance/today?qr_session_id={session['id']}")
    check("GET /attendance/today", r.status_code == 200 and isinstance(r.json(), list))

    r = client.get(f"/attendance/export/csv?qr_session_id={session['id']}")
    check("GET /attendance/export/csv",
          r.status_code == 200 and r.text.startswith("id,timestamp"), "CSV header OK")

    # 6. End session -> no more check-ins
    r = client.post("/qr-sessions/end", json={"session_id": session["id"]})
    check("POST /qr-sessions/end",
          r.status_code == 200 and r.json().get("total_attendance") == 0)

    r = client.get("/qr-sessions/active")
    check("GET /qr-sessions/active (after end -> inactive)",
          r.status_code == 200 and r.json().get("active") is False)

    # 7. Cleanup smoke-test data
    r = client.delete(f"/students/{student['id']}")
    check("Cleanup (delete smoke student)", r.status_code == 200)

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