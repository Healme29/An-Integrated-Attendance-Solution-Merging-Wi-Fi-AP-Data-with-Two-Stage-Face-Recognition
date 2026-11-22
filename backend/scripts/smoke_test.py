"""End-to-end smoke test for the two-stage QR attendance server.

Usage:
    python backend/scripts/smoke_test.py --base-url http://127.0.0.1:8000
    python backend/scripts/smoke_test.py --load 30

No real face photo is needed. The test creates one temporary class/student,
checks both QR phases, closes the session, exercises manual attendance, and
exports the roster CSV. --load additionally sends N concurrent faceless uploads
to measure how the real YOLO pipeline behaves under a class-sized burst.
"""
import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import cv2
import httpx
import numpy as np

results = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append((name, status, detail))
    print(f"[{status}] {name}" + (f" - {detail}" if detail else ""))


def main(base_url: str, load: int) -> int:
    client = httpx.Client(base_url=base_url, timeout=90, trust_env=False)
    check("GET /health", client.get("/health").status_code == 200)
    dashboard = client.get("/dashboard")
    check(
        "GET /dashboard (two-stage UI)",
        dashboard.status_code == 200
        and "Start Final Attendance" in dashboard.text
        and "Teacher Dashboard" in dashboard.text,
    )

    login = client.post(
        "/teachers/login", json={"username": "teacher", "password": "attendance2026"}
    )
    check("Teacher login", login.status_code == 200)
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    client.post("/qr-sessions/end", headers=headers)  # clear a previous demo session
    suffix = int(datetime.now().timestamp()) % 100000000
    created_class = client.post(
        "/classes/", json={"class_name": "Smoke Test Class", "room": "Smoke Room"}, headers=headers
    )
    check("Create class", created_class.status_code == 200)
    class_id = created_class.json()["id"]
    created_student = client.post(
        "/students/", json={"name": "Smoke Tester", "nim": f"smoke{suffix}"}, headers=headers
    )
    check("Create student", created_student.status_code == 200)
    student = created_student.json()
    enrolled = client.post(
        f"/classes/{class_id}/students", json={"student_id": student["id"]}, headers=headers
    )
    check("Enroll student (one class)", enrolled.status_code == 200)

    started = client.post("/qr-sessions/start", json={"class_id": class_id}, headers=headers)
    check("Start session (START phase)", started.status_code == 200 and started.json()["phase"] == "start")
    session = started.json()

    active = client.get("/qr-sessions/active").json()
    check("Active session info", active.get("active") is True and active.get("phase") == "start")
    token = client.get("/qr-sessions/active/token").json()["token"]
    check("Rotating token exists", bool(token))
    valid = client.post("/qr-sessions/validate", json={"token": token}).json()
    check("Validate current token + phase", valid.get("valid") is True and valid.get("phase") == "start")
    check("Reject unknown token", client.post("/qr-sessions/validate", json={"token": "ZZZZZZ"}).json()["valid"] is False)
    qr = client.get("/qr-sessions/active/qr.png")
    check("QR PNG", qr.status_code == 200 and qr.headers.get("content-type") == "image/png")

    ok, buf = cv2.imencode(".jpg", np.full((480, 640, 3), 128, dtype=np.uint8))
    blank_jpeg = buf.tobytes()
    recognized = client.post("/faces/recognize", files={"file": ("blank.jpg", blank_jpeg, "image/jpeg")})
    check("Faceless image rejected cleanly", recognized.status_code == 200 and recognized.json()["recognized"] is False)
    no_face = client.post(
        f"/attendance/check-qr?student_id={student['id']}&token={token}",
        files={"file": ("blank.jpg", blank_jpeg, "image/jpeg")},
    )
    check("Check-in without a face -> 400", no_face.status_code == 400 and "No face detected" in no_face.text)
    bad_token = client.post(
        f"/attendance/check-qr?student_id={student['id']}&token=WRONG1",
        files={"file": ("blank.jpg", blank_jpeg, "image/jpeg")},
    )
    check("Invalid token -> 400", bad_token.status_code == 400)

    roster = client.get(f"/attendance/roster?qr_session_id={session['id']}", headers=headers)
    check("Roster contains enrolled student", roster.status_code == 200 and roster.json()[0]["status"] == "pending")
    csv_start = client.get(f"/attendance/export/csv?qr_session_id={session['id']}")
    check("Roster CSV header", csv_start.status_code == 200 and csv_start.text.startswith("nim,student_name"))

    changed = client.post("/qr-sessions/phase", json={"phase": "end"}, headers=headers)
    check("Start Final Attendance (END phase)", changed.status_code == 200 and changed.json()["phase"] == "end")
    new_token = changed.json()["token"]
    check("Final QR token differs", new_token != token)
    check("Start token invalid in final phase", client.post("/qr-sessions/validate", json={"token": token}).json()["valid"] is False)
    end_without_start = client.post(
        f"/attendance/check-qr?student_id={student['id']}&token={new_token}",
        files={"file": ("blank.jpg", blank_jpeg, "image/jpeg")},
    )
    check("Final check-in requires start", end_without_start.status_code == 409)

    if load > 0:
        def send_faceless(_):
            response = client.post(
                f"/attendance/check-qr?student_id={student['id']}&token={new_token}",
                files={"file": ("blank.jpg", blank_jpeg, "image/jpeg")},
            )
            return response.status_code

        began = time.monotonic()
        with ThreadPoolExecutor(max_workers=load) as pool:
            codes = list(pool.map(send_faceless, range(load)))
        elapsed = time.monotonic() - began
        check(
            f"Concurrent load ({load} requests)",
            all(code in (400, 409, 429) for code in codes),
            f"{elapsed:.2f}s; codes={{{', '.join(f'{c}:{codes.count(c)}' for c in sorted(set(codes)))}}}",
        )

    ended = client.post("/qr-sessions/end", json={"session_id": session["id"]}, headers=headers)
    check("End session", ended.status_code == 200)
    manual = client.post(
        "/attendance/manual",
        json={"student_id": student["id"], "qr_session_id": session["id"]},
        headers=headers,
    )
    check("One-click manual attendance after class", manual.status_code == 200 and manual.json()["status"] == "verified")
    final_roster = client.get(f"/attendance/roster?qr_session_id={session['id']}", headers=headers).json()
    check("Final roster is verified + manual", final_roster[0]["status"] == "verified" and final_roster[0]["manual"] is True)
    final_csv = client.get(f"/attendance/export/csv?qr_session_id={session['id']}")
    check("Final CSV includes verified", "verified" in final_csv.text and "yes" in final_csv.text)

    cleanup = client.delete(f"/students/{student['id']}", headers=headers)
    check("Cleanup temporary student", cleanup.status_code == 200)
    client.close()

    failed = [r for r in results if r[1] == "FAIL"]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        for name, _, detail in failed:
            print(f"  FAILED: {name}: {detail}")
        return 1
    print("Smoke test OK — the NEW two-stage flow is running.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--load", type=int, default=0, help="number of concurrent faceless uploads")
    args = parser.parse_args()
    sys.exit(main(args.base_url, max(0, args.load)))
