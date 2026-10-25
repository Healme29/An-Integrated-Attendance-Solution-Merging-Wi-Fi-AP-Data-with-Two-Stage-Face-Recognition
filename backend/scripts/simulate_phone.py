"""Local PHONE SIMULATOR (headless) — auto check-in prompt, tier 1 polling.

Plays the mobile app's part of the loop against a running backend. Flow
mirrors docs/A/auto_prompt_spec.md and mobile/lib/services/prompt_service.dart:

    poll GET /me/prompt every N seconds
      -> prompt=true -> show banner -> (auto) tap "Check in now"
      -> POST /attendance/check with the next held-out photo
      -> next poll offers the following stage (start -> end)
      -> reason check_in_complete stops the loop.

Purpose: end-to-end test + local demo without a Flutter build (Windows
desktop build currently blocked by the Developer-Mode symlink requirement;
APK build works for real devices).

Usage (backend running on 127.0.0.1:8000):
    python backend/scripts/simulate_phone.py --student-id 8
    python backend/scripts/simulate_phone.py --student-id 8 --photo-start <path> --photo-end <path>
"""
import argparse
import glob
import json
import mimetypes
import os
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo(os.environ.get("TIMEZONE", "Asia/Shanghai"))


def request(path, method="GET", body=None, headers=None, timeout=60):
    req = urllib.request.Request(
        "http://127.0.0.1:8000" + path, data=body, method=method,
        headers=headers or {},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def get(path):
    return request(path)


def post_multipart(path, file_path: Path):
    boundary = "----sim" + uuid.uuid4().hex
    ctype = mimetypes.guess_type(file_path.name)[0] or "image/jpeg"
    data = file_path.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"file\"; filename=\"{file_path.name}\"\r\n"
        f"Content-Type: {ctype}\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    return request(
        path, method="POST", body=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )


def banner(p: dict, stage: str) -> None:
    print("\n" + "=" * 62)
    print(f"  [PHONE BANNER]  {p['class_name']} ({p['room']}) detected!")
    print(f"  {stage.upper()} check-in available | BSSID {p.get('bssid')}")
    print("  [auto-taps 'Check in now' in 3s] / [Later]")


def find_photo(folder: str, name_hint: str) -> Path:
    matches = glob.glob(str(Path(folder) / f"{name_hint}*.jpg"))
    if not matches:
        raise SystemExit(f"Photo not found: {name_hint}*.jpg in {folder}")
    return Path(matches[0])


def find_or_create_schedule(student_id: int) -> dict:
    """Always create a FRESH demo schedule for this run (unique room name
    sidesteps the same-room overlap rule) so the prompt loop starts from
    'start' even if an older active schedule is already complete."""
    now = datetime.now(TZ)
    start = (now - timedelta(minutes=5)).strftime("%H:%M")
    # Keep the window on the same day so start < end always holds;
    # end clamps to 23:59 when the +90 min window would cross midnight.
    end_dt = now + timedelta(minutes=90)
    end = end_dt.date().isoformat() == now.date().isoformat() and end_dt.strftime("%H:%M") or "23:59"
    room = f"Ruang Sim {student_id} {now.strftime('%H%M')}"
    payload = {
        "class_name": "Demo Auto Prompt",
        "day_of_week": now.weekday(),
        "start_time": start,
        "end_time": end,
        "room": room,
    }
    created = request(
        "/schedules/", method="POST",
        body=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    print(f"[jadwal] dibuat: id={created['id']} {created['class_name']} "
          f"{start}-{end} ({room})")
    return created


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--student-id", type=int, default=8)
    ap.add_argument("--poll", type=float, default=8.0, help="poll interval, s")
    ap.add_argument("--tap-delay", type=float, default=3.0,
                    help="seconds between banner and the simulated tap")
    ap.add_argument("--photo-dir", default="gambar_percobaan/orang_1")
    ap.add_argument("--photo-start", default="e7d8152e",
                    help="held-out photo name hint for the START check")
    ap.add_argument("--photo-end", default="709040f3",
                    help="held-out photo name hint for the END check")
    args = ap.parse_args()

    student = get(f"/students/{args.student_id}")
    print(f"[SIM] login: {student['name']} (NIM {student['nim'] or '-'}) "
          f"| registered MAC: {student['mac_address'] or '-'}")

    schedule = find_or_create_schedule(args.student_id)
    print(f"[SIM] heartbeat GET /me/prompt every {args.poll:.0f} s ...\n")

    tapped_stage = None
    for cycle in range(1, 200):
        p = get(f"/me/prompt?student_id={args.student_id}")
        stamp = datetime.now(TZ).strftime("%H:%M:%S")
        if p["prompt"]:
            stage = p["check_type"]
            banner(p, stage)
            if tapped_stage == p["schedule_id"]:
                pass  # next stage banner — fine
            time.sleep(args.tap_delay)
            print(f"  [{stamp}] STUDENT TAPPED 'Check in now' -> camera...")
            held = args.photo_start if stage == "start" else args.photo_end
            photo = find_photo(args.photo_dir, held)
            print(f"  [camera] sending held-out photo: {photo.name}")
            result = post_multipart(
                f"/attendance/check?schedule_id={p['schedule_id']}&check_type={stage}",
                photo,
            )
            print(f"  [RESULT] {result['student_name']} | {result['check_type'].upper()} "
                  f"| confidence {(result['confidence'] * 100):.1f}% "
                  f"| wifi={result['wifi_verified']} | status={result['status']}")
            tapped_stage = p["schedule_id"]
            time.sleep(args.poll)
        else:
            reason = p.get("reason")
            if reason == "check_in_complete":
                print(f"\n[{stamp}] reason=check_in_complete -> banner stops.")
                print(f"[DONE] {student['name']}'s attendance today is complete "
                      f"(start + end verified). Simulation succeeded.\n")
                return
            hint = {
                "no_active_schedule": "no active class right now",
                "device_not_seen_on_network":
                    "class active but device NOT seen on the network (banner must NOT appear)",
            }.get(reason, reason)
            print(f"[{stamp}] poll: prompt=false ({hint})")
            time.sleep(args.poll)
    print(f"[STOP] 200-poll limit reached.")


if __name__ == "__main__":
    main()
