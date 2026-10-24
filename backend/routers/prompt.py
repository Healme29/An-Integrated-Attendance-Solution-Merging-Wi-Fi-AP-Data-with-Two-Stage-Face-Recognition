"""Lightweight polling endpoint for the mobile app's auto check-in prompt.

The app (already logged in as a student) polls GET /me/prompt every ~15 s.
When ALL of these hold:
  1. a schedule is ACTIVE right now (same weekday, current time in window),
  2. the student has an unfinished stage for that schedule today
     (no 'start' yet -> start; 'start' exists but no 'end' -> end), and
  3. the student's device MAC is visible on the classroom network,
the response carries prompt=true so the app can offer the camera check-in
screen automatically.

This endpoint READS existing services only (get_schedules_for_now,
get_existing_check, check_mac_on_network) — no attendance rule is changed.
Check-ins still go through POST /attendance/check with all its enforcement.
"""
from fastapi import APIRouter, HTTPException
from models.database import get_db
from services.attendance import get_schedules_for_now, get_existing_check
from services.wifi_scanner import check_mac_on_network, get_current_bssid

router = APIRouter(tags=["auto-prompt"])


@router.get("/me/prompt")
async def check_in_prompt(student_id: int):
    """Tell the app whether/when to surface the automatic check-in flow."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    student = await cursor.fetchone()
    await db.close()
    if not student:
        raise HTTPException(status_code=404, detail="student_not_found")
    student = dict(student)

    mac = (student.get("mac_address") or "").strip()
    wifi_seen = bool(mac) and check_mac_on_network(mac)
    bssid = get_current_bssid()

    schedules = await get_schedules_for_now()
    if not schedules:
        return _to_dto(student_id, None, None, wifi_seen, bssid, "no_active_schedule")

    for schedule in schedules:
        schedule_id = schedule["id"]
        if not await get_existing_check(student_id, schedule_id, "start"):
            return _to_dto(student_id, schedule, "start", wifi_seen, bssid)
        if not await get_existing_check(student_id, schedule_id, "end"):
            return _to_dto(student_id, schedule, "end", wifi_seen, bssid)

    # Start AND end exist for every schedule active right now.
    return _to_dto(student_id, None, None, wifi_seen, bssid, "check_in_complete")


def _to_dto(student_id: int, schedule: dict | None, check_type: str | None,
            wifi_seen: bool, bssid: str | None, reason: str | None = None) -> dict:
    """Build the prompt response. prompt=true only when a stage is actionable
    AND the device was seen on the network (the auto-trigger premise)."""
    if schedule:
        return {
            "student_id": student_id,
            "prompt": wifi_seen,
            "check_available": True,
            "wifi_seen": wifi_seen,
            "reason": None if wifi_seen else "device_not_seen_on_network",
            "schedule_id": schedule["id"],
            "class_name": schedule["class_name"],
            "room": schedule["room"],
            "check_type": check_type,
            "bssid": bssid,
        }
    return {
        "student_id": student_id,
        "prompt": False,
        "check_available": False,
        "wifi_seen": wifi_seen,
        "reason": reason or "no_active_schedule",
        "schedule_id": None,
        "class_name": None,
        "room": None,
        "check_type": None,
        "bssid": bssid,
    }
