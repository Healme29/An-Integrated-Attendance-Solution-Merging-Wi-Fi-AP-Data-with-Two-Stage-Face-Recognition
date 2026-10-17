# TASK B — Attendance Orchestrator + Schedule Logic

## Summary
You are responsible for the **core business logic of the system**: connecting face recognition, Wi-Fi check, and schedule validation into one correct attendance flow. You also manage attendance endpoints and schedule CRUD.

---

## FILES TO WORK ON

### 1. `backend/services/attendance.py` ⭐ MOST IMPORTANT
**What already exists:** `get_schedules_for_now()`, `recognize_face()`, `mark_attendance()`. Basic flow: detect → recognize → check Wi-Fi → insert record.

**What you must do & fix:**

#### ⚠️ CRITICAL — Two-Stage Attendance Logic (Priority 1, Blocker #2) [EST: 5 hours]
This is the **core feature of the project**: attendance is only valid if there is a "start" AND "end" check-in for the same student + schedule.

- [ ] **Create function `get_existing_check(student_id, schedule_id, check_type)`:**
  ```python
  async def get_existing_check(student_id: int, schedule_id: int, check_type: str) -> dict | None:
      """Find an existing attendance record for a student+schedule+check_type."""
  ```
- [ ] **Create function `is_start_end_paired(student_id, schedule_id) -> bool`:**
  ```python
  async def is_start_end_paired(student_id: int, schedule_id: int) -> bool:
      """Check if student already has 'start' AND 'end' for this schedule. Return True if both exist."""
  ```
- [ ] **Update `mark_attendance()`** — after inserting a new check-in, check if the start/end pair is complete:
  - If check_type = "start" → status = "partial" (waiting for end)
  - If check_type = "end" → find matching "start". If found → update BOTH records to status = "verified"
  - If check_type = "end" but no "start" exists → reject with error "Must check in at start of class first"
- [ ] **Add new status values in DB check constraint:** `CHECK(check_type IN ('start', 'end'))` already exists. For status, you need new values: `partial`, `verified`. But `status` has no CHECK constraint, so you can use new values directly without migration.
- [ ] **Prevent duplicate check-in:** If student already checked in "start" for the same schedule today, reject a second "start". Same for "end". The `get_existing_check()` function above will help with this.

#### ⚠️ HIGH — Schedule Time Enforcement (Priority 1, Blocker #3) [EST: 2 hours]
- [ ] **In `routers/attendance.py` endpoint `check_attendance()`:** Before processing the photo, call `get_schedules_for_now()`.
- [ ] **Validation:** If the `schedule_id` sent is not in `get_schedules_for_now()` → reject 400 "Attendance outside class hours".
  ```python
  schedules = await get_schedules_for_now()
  if not any(s["id"] == schedule_id for s in schedules):
      raise HTTPException(status_code=400, detail="Attendance outside class hours. Current time does not match any active schedule.")
  ```
- [ ] **Grace period:** There is `ATTENDANCE_CHECK_WINDOW_MINUTES = 15` in `config.py`. Modify `get_schedules_for_now()` to add a window: start_time minus 15 minutes, end_time plus 15 minutes.
- [ ] **Timezone handling:** Add timezone configuration in `config.py` (default `Asia/Jakarta`). Use `pytz` or `zoneinfo` for consistency.

#### HIGH — Fix `recognize_face()` [EST: 1 hour]
- [ ] **Coordinate with A:** After A fixes `get_embedding()` signature, update the call here. This code needs to change from:
  ```python
  embedding = get_embedding(best_face["crop"])  # OLD
  ```
  to:
  ```python
  embedding = get_embedding(full_image, best_face["bbox"])  # NEW
  ```
  So you need to pass `full_image` (not `image_bytes`) to `recognize_face()`.
- [ ] **Or restructure:** Change `recognize_face()` to accept `np.ndarray` (image array) + `bytes` (raw) for flexibility.

### 2. `backend/routers/attendance.py`
**What already exists:** `POST /attendance/check`, `GET /attendance/today`, `GET /attendance/student/{id}`.

**What must be fixed:**
- [ ] **Schedule time validation** — integrate as described above.
- [ ] **Response model:** Currently `AttendanceResponse` does not match the real response from `mark_attendance()`. Check if all fields match. Example: `AttendanceResponse` has field `wifi_verified: bool`, but in the DB it's stored as integer (0/1). This needs casting.
- [ ] **Student attendance history:** Add fields `class_name`, `room`, `status` already joined with schedules in the query.
- [ ] **Pagination:** Add `limit` (default 50) and `offset` parameters for the attendance history endpoint.
- [ ] **Date filter:** Add `start_date` and `end_date` parameters for `GET /attendance/today` to make it more flexible (rename to `GET /attendance/date-range` or add query params).

### 3. `backend/routers/schedules.py`
**What already exists:** Almost complete. Full CRUD.

**What's needed:**
- [ ] **Update schedule:** Add `PUT /schedules/{id}` to update a schedule.
- [ ] **Get schedule by ID:** Add `GET /schedules/{id}`.
- [ ] **Input validation:** Check that `start_time < end_time`. Check `day_of_week` is between 0-6.
- [ ] **Overlap detection:** Check if a new schedule overlaps with existing schedules in the same room on the same day.
  ```sql
  SELECT * FROM schedules WHERE day_of_week = ? AND room = ? AND start_time < ? AND end_time > ?
  ```
  If overlap → reject with error.

### 4. `backend/models/schemas.py`
**What's needed:**
- [ ] **Update `AttendanceResponse`:** Ensure fields exactly match the response from `mark_attendance()`. Add fields `student_name`, `class_name`, `room` for history.
- [ ] **Add `AttendanceHistoryResponse`:** Special model for history endpoint (join with schedule).
- [ ] **Add `ScheduleUpdate`:** Pydantic model for schedule update.

### 5. `backend/config.py`
**What's needed:**
- [ ] Add `TIMEZONE = "Asia/Jakarta"`
- [ ] Review `ATTENDANCE_CHECK_WINDOW_MINUTES = 15` — should it be longer (30 minutes)?

---

## DEPENDENCIES
- Module A: Functions `detect_faces_from_bytes()`, `get_embedding()`, `compare_faces()`, `is_match()`
- Module D: Function `check_mac_on_network()`
- Database: tables `students`, `schedules`, `attendance`
- No new external dependencies (all via other modules)

---

## TEAM INTEGRATION
| Module | Depends on | What to coordinate |
|-------|---------------|---------------------------|
| attendance.py | A (face_recognition) | `get_embedding()` signature — ask A if it's fixed |
| attendance.py | D (wifi_scanner) | Function `check_mac_on_network()` — should be stable |
| routers/attendance.py | services/attendance.py | Yourself — ensure async functions are called with `await` |
| routers/schedules.py | database.py | No changes, already stable |

---

## TIME ESTIMATES
| Sub-task | Estimate |
|----------|----------|
| Two-stage logic (start + end pairing) | 5-6 hours |
| Schedule time enforcement + grace period | 2-3 hours |
| Fix recognize_face (coordinate with A) | 1-2 hours |
| Fix response models & schemas | 1-2 hours |
| Additional schedule CRUD features | 2-3 hours |
| **Total** | **11-16 hours** |

---

## PRIORITIES
1. ⚠️ **CRITICAL** — Two-stage attendance logic (start → partial → end → verified)
2. ⚠️ **HIGH** — Schedule time enforcement
3. **HIGH** — Coordinate with A for recognize_face() fix
4. **MEDIUM** — Fix Pydantic response models
5. **LOW** — Pagination, date filter, overlap detection