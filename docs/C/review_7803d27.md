# Review of Auto Check-in Prompt Handover (commit `7803d27`, branch `a`)

Reviewed by C on 2026-10-26 on branch `task-c` (created from `a` @ `d17a46b`).

## Verdict

**Accepted.** The implementation follows `docs/A/auto_prompt_spec.md` exactly:

- `mobile/lib/services/prompt_service.dart` — polls `GET /me/prompt?student_id=`
  every 20 s (backend Wi-Fi scan cache is ~10 s, so this is safe), dedupes by
  `schedule_id:check_type` stage key so each stage banner shows exactly once,
  and stays silent on network errors (no crash).
- `mobile/lib/screens/home_screen.dart` — banner on `prompt == true`;
  "Check in now" reuses the manual camera flow (same `schedule_id`/`check_type`
  parameters) — no bypass of the camera. Polling pauses on app pause and
  restarts on resume (battery friendly). Settings still re-applies the toggle
  on return.
- `mobile/lib/screens/settings_screen.dart` — Auto check-in toggle, ON by
  default, persisted via `SessionService`.
- `mobile/lib/services/api_service.dart` — `getCheckInPrompt` matches the
  documented response contract field-by field; `pingServer()` probes `GET /`
  which exists in the backend (verified in `backend/main.py:50`).

## Findings fixed in this branch

| # | Finding | Fix | Commit |
|---|---------|-----|--------|
| 1 | `camera_screen.dart` had no error handling for camera init failure (permission denied etc.): `FutureBuilder` showed an infinite spinner, and `late CameraController` would throw `LateInitializationError` in `dispose()` if init never assigned it. Enroll screen already had the correct pattern. | Made the controller nullable, added an error state with a human message + "Retry" button and instructions to grant the permission manually. Mirrors `enroll_screen.dart`. | (this branch) |

## Notes (accepted as designed, no change)

- "Later" on the banner permanently hides that stage (dedupe key is never
  reset until Settings toggle is flipped). Manual check-in is still available
  from the schedule picker — matches spec ("each stage exactly once").
- `interval = 20 s` is at the slow end of the spec's 15–30 s range; fine for
  battery. If classroom tests feel sluggish we can go to 15 s.
- History screen relies on backend `class_name`/`room` join — verified present
  in `backend/routers/attendance.py` (student history query).

## Quality gates at review time

- `flutter analyze`: 0 issues
- `flutter test`: 1/1 passed
- `python -m pytest backend/tests -q`: 139 passed, 1 skipped (untouched backend)
