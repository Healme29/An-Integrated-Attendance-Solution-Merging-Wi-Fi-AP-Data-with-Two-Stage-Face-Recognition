# Pilot plan — real classroom, Dec 7–13 2026

> Deliverable for M2 stage 4 (gate **G7**, then **G9/G10**). Owner: A (lead).
> Backup window: **Dec 14–20, 2026**. This plan is a draft until **G4** (teacher-confirmed
> date + roster, owner D) is written in `docs/D/teacher_requirements.md`.
>
> **Status: draft.** The roster, room and AP BSSID are placeholders until D and the teacher
> confirm them. Nothing in this file is a result — results belong in `docs/A/pilot_report.md`.

## 1. What the pilot is for

Prove, in a real class with real students, that the integrated flow works end to end:
Wi-Fi AP presence + two-stage face check-in + teacher dashboard/CSV. The pilot is not a
feature demo; it is a measurement with a small, controlled group. It produces the numbers
for the final report and the fix list before the Jan 18 demo.

In scope:

- one real class session (one schedule row, one room, one AP);
- 5–10 students who volunteered, each enrolled and carrying a phone with the app;
- start check-in and end check-in, Wi-Fi verification, dashboard and CSV export.

Out of scope (do not claim in the report):

- mask support (measured separately in `docs/A/robustness_test.md`, not promised);
- anti-spoofing (no liveness detection; draft only in `docs/A/anti_spoofing.md`);
- authenticated sessions (`student_id` is claimed today; M3 work, recorded in D-003);
- multi-room or multi-AP scheduling, iOS devices, and any class larger than 10 students.

## 2. Dates and gates

| Date | Gate | What must be true |
|---|---|---|
| **Nov 22** | **G4** (owner D) | Teacher confirms the date, class, room and student roster in writing |
| Nov 29 | **G7** | ≥ 5 pilot students enrolled **in the real classroom**, 5 embeddings each, classroom lighting |
| Dec 6 | **G8** | Rehearsal passed: server on the pilot machine, phones on the pilot network, forms printed, one full start→end simulation with 2 people |
| **Dec 7–13** | **G9** | Pilot executed; raw attendance rows, AP logs, server log, timing sheet and forms stored |
| Dec 20 | **G10** | `docs/A/pilot_report.md` with real numbers; every finding has an owner and a fix-or-dismiss decision |
| Jan 3 | G11 | Pilot fixes merged, tests green |

If G4 slips, every later gate slips the same amount (critical chain). The backup week
Dec 14–20 exists for weather, illness, room conflicts and server failures — not for missing
preparation.

## 3. Class and participants

- One class session of a course whose teacher agrees. Schedule row must already exist in the
  app with the correct `day_of_week`, `start_time`, `end_time`, `room` and `ap_bssid`.
- 5–10 volunteer students. Each one:
  1. installs the app (C provides the APK and a 1-page install/help sheet);
  2. logs in with their NIM;
  3. is enrolled in the classroom at G7 (5 photos, one face per photo, `bright` condition);
  4. has their phone's **actual MAC** for the classroom SSID registered on their student
     record. Warn about MAC randomisation: either disable it for that SSID or read the MAC
     the router/DHCP shows and register that exact value. This is the most common reason a
     real student will show `face_only` instead of `verified`.
- The teacher is told what the dashboard shows and that attendance rows are experimental for
  this session; the pilot does not replace the official attendance record unless the teacher
  chooses to use it.

## 4. Pre-pilot checklist

### G7 — enrollment in the real classroom (Nov 29)

| # | Item | Owner | Evidence |
|---|---|---|---|
| 1 | Room/date confirmed for enrollment visit | D | `docs/D/teacher_requirements.md` |
| 2 | Server running on the pilot machine with `YOLO_IMG_SIZE=640`, `TIMEZONE` set to the campus zone | B | `/health` output + env dump |
| 3 | 5–10 students enrolled **in the room**, 5 embeddings each, one face per photo | A | per-student `total_embeddings=5` log |
| 4 | Re-run `evaluate_threshold.py` on the new profiles | A | `docs/threshold_report.md` numbers still separate at 0.5 |
| 5 | Check-in works from a phone **on the classroom Wi-Fi**, not just localhost | C + B | one real start check-in (test schedule), screenshot |
| 6 | Classroom AP BSSID and subnet recorded | B | router/DHCP screenshot in `docs/B/` |
| 7 | Each pilot student's MAC registered; `GET /wifi/check/<mac>` returns `present` for at least 3 of them during the visit | B | log excerpt |

### G8 — rehearsal (Dec 6)

| # | Item | Owner | Evidence |
|---|---|---|---|
| 1 | Full flow with 2 people: login → start → wait → end → history | A + C | timing sheet from rehearsal |
| 2 | Dashboard + CSV export for the test schedule | B | exported CSV |
| 3 | Offline fallback proven (hotspot, no internet) | B | `docs/B/` fallback note |
| 4 | Phones charged, app installed, NIM login works on each pilot phone | C | checklist signed |
| 5 | Printed forms: consent, teacher feedback, student exit, timing sheet | A | files in `docs/A/pilot/` |
| 6 | Server log redirected to a file and rotated for the pilot day | B | log path in runbook |
| 7 | Backup plan agreed: backup date, backup room, who calls it off | A | this file, §8 |

## 5. Runbook — pilot day

Times are relative to the class start (`T`). The observer writes every timestamp on the
timing sheet; the server log is the source of truth afterwards.

| Time | Step | Owner | Notes |
|---|---|---|---|
| T−90 | Arrive, power the server laptop, start `uvicorn`, redirect log | B | do not use `--reload`; verify `/health` + `/docs` |
| T−75 | Connect server to the classroom network, confirm subnet and AP BSSID | B | `GET /wifi/scan` should list the AP and some phones |
| T−60 | Verify the schedule row for today (room, AP BSSID, window ± grace) | A | screenshots of `/schedules/` |
| T−45 | Phones: app open, logged in, camera permission granted, battery > 50% | C | fix NIM/MAC issues now |
| T−30 | `GET /wifi/check/<mac>` for every pilot phone; record present/absent | B | absent MAC → fix before start, not during |
| T−10 | Consent forms collected; students told what to do and that they may opt out | A | no photo/data without consent |
| **T+0–10** | **START check-in window**; students take the start selfie | C supports | observer records attempts, retries, duration |
| T+10 | Quick check: start rows exist for all expected students | A | dashboard or `GET /attendance/today?schedule_id=` |
| T+45–60 | **END check-in window** | C supports | same observation |
| T+60 | Confirm start rows were finalised (status `verified` / `face_only`) | A | `GET /attendance/today` |
| T+70 | Export CSV, screenshot dashboard, copy DB + log to the evidence folder | B | no edits to the CSV |
| T+80 | Teacher feedback form; 2-minute student exit form | D + A | forms in `docs/A/pilot/` |
| T+90 | Stop server, take a final backup of `attendance.db` and `ap_logs` | B | keep the file, do not prune |

Rules during the pilot:

- **No live fixes to the ML code or thresholds.** If something breaks, record it and use the
  fallback. A changed threshold invalidates the measurement.
- Every failed attempt gets a one-line note (student, stage, error, retry, time). The server
  log alone does not explain a student walking away.
- If more than half the group cannot check in, stop the pilot and reschedule to the backup
  week; partial data is still useful but must be labelled incomplete.

## 6. Data collection

| Data | Where | Owner | Purpose |
|---|---|---|---|
| `attendance` rows | `attendance.db` + CSV export | B | statuses, confidence, `faces_detected`, timestamps |
| `ap_logs` / `/wifi/scan` | `attendance.db` | B | presence evidence, AP BSSID, IP |
| Server log | file on the pilot machine | B | 400/403/409 counts, stack traces, request timings |
| Timing sheet | paper → `docs/A/pilot/` (photos/scans, no student faces) | A | check-in duration per attempt |
| Teacher feedback | printed form → transcribed into `pilot_report.md` | D | usability and trust |
| Student exit form | 3 questions, anonymous | A | friction points, privacy comfort |
| Screenshots | dashboard + app states | C | evidence for the report/slides |

Names and NIMs are replaced with `S1..S10` in the report; the mapping stays local. Face
photos and raw selfies are not copied into the report, slides or git.

## 7. Success metrics (fixed before the pilot)

Let `started` = students with a start row, `ended` = students with an end row for the same
schedule, `pairs` = students with both.

| Metric | Formula | Target | Why this target |
|---|---|---|---|
| Start→end linkage | `pairs / started` | ≥ 90% | A student who starts but never ends gets no verdict |
| Verified share | `end rows with wifi_verified=1 / end rows` | ≥ 80% | The classroom AP is the premise of the project |
| `face_only` share | `end rows with status='face_only' / end rows` | ≤ 20% | Each one is a Wi-Fi or MAC registration failure to explain |
| Identity errors | rows recorded for a student whose face was rejected | **0** | The system must never grant the wrong person |
| Retry rate | `(400 + 403 responses) / check-in attempts` | ≤ 15% | Too high means capture guidance or enrollment is wrong |
| Check-in duration | phone-side seconds per attempt, p50 / p95 | p50 ≤ 5 s, p95 ≤ 10 s | Keeps the two-stage flow usable between classes |
| Data completeness | CSV rows == expected check-ins | 100% | Export must be trustworthy for the teacher |
| Crash-free sessions | app sessions without a fatal error | ≥ 95% | One crash in a 10-student class is already disruptive |

These are targets, not pass/fail for G9 (G9 passes when the data is collected). Missed
targets become G10 findings with an owner.

## 8. Failure and fallback

| Failure | Symptom | Immediate action | Follow-up |
|---|---|---|---|
| AP not in `ap_logs` / wrong BSSID | everyone `face_only` | B checks router DHCP/ARP, corrects the schedule row only if the row is wrong (record the change) | B writes the cause in `pilot_report.md` |
| Phone cannot reach the server | request timeout / connection refused | switch to the G5 hotspot + `adb reverse` procedure | C documents which path worked |
| MAC randomised / wrong | `wifi_verified=0` for one student | read the real MAC from DHCP, update the student record, retry within the window | add a warning to the install sheet |
| Server crash / laptop sleep | app errors | restart `uvicorn`, keep the same DB, ask students to retry; note the gap | B checks power settings before the demo |
| Model slow (> 10 s) | timeouts | confirm `YOLO_IMG_SIZE=640`, close other apps, retry once | A records p95 in the report |
| Duplicate check-in | 409 | expected; tell the student not to resend | count 409s, they are not errors |
| Student not enrolled / face rejected repeatedly | 403/404 | remove from the pilot group for that session, record the reason; do not enroll on the spot | re-enroll at G7 with better photos |
| Teacher cancels | no session | use the backup window Dec 14–20; notify the group same day | update G9 date in the progress log |
| Room Wi-Fi down | no network at all | pilot cannot measure `verified`; reschedule rather than run a face-only class | B investigates with campus IT |

## 9. Roles

| Person | During preparation | During the pilot |
|---|---|---|
| **A** | Owns this plan, G7 enrollment, metrics, analysis | Runbook lead, timing sheet, decides stop/continue |
| **B** | Server, network, AP/BSSID, dashboard, CSV, backups | Runs the server, fixes network, exports data |
| **C** | App install, phone compatibility, capture guidance | Helps students one by one, records app errors |
| **D** | Teacher communication, date/roster (G4), forms | Collects teacher feedback, handles consent paperwork |

One person must be free to watch the clock and write notes — that is A. A does not debug
phones during the start window.

## 10. Ethics and privacy

- Participation is voluntary. A student may decline or withdraw at any point, including
  after the session; their rows are deleted on request. No academic consequence.
- The teacher knows what is stored and who can see the dashboard. The pilot does not replace
  the official attendance record unless the teacher explicitly chooses it.
- Raw selfies and face crops are stored only on the pilot machine, never in git, the group
  chat, slides or the report. The anonymised rows and score tables are what gets published.
- Delete raw pilot photos and unpublished logs after `pilot_report.md` is finalised
  (target Jan 10, 2027), keeping only the anonymised tables and the CSV with NIMs removed.
- No face data of anyone who did not consent, including bystanders in the background; photos
  with a second person are rejected by design (D-003), but do not keep them either.

## 11. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| G4 date/roster late (D/teacher) | medium | high — moves G7–G16 | D confirms by Nov 22; backup week reserved; A starts G7 paperwork before the date |
| Classroom AP not visible from the server | medium | high — no `verified` rows | B tests from the room at G7, not on the pilot day |
| MAC randomisation breaks Wi-Fi match | high | medium — `face_only` rows | register the DHCP MAC, disable randomisation for the SSID, test at T−30 |
| Students forget the app/login | medium | medium — lost attempts | C sends a reminder the day before; spare phone with the app installed |
| Threshold too strict in classroom light | low–medium | high — mass 403 | robustness test before G7; retry guidance; fix list at G10, no live tuning |
| One phone model behaves differently | medium | medium — one student blocked | C tests the app on each pilot phone at G8 |
| Raw data lost after the session | low | high — no report numbers | B copies DB + log + CSV immediately at T+70 and keeps a second copy |

## 12. After the pilot — analysis and reporting (G10, Dec 20)

1. Freeze the data: copy the DB, log and timing sheet into one evidence folder; compute the
   metrics from the copy, never from a live server.
2. Fill `docs/A/pilot_report.md`: linkage, verified vs `face_only`, retry rate, duration
   p50/p95, identity errors, per-student notes, failure list, teacher/student feedback.
3. Write the decision entries: is 0.5 still right (D-001 revisit), is the 0.10 multi-face
   ratio right (D-003 revisit), is 640 still the right `imgsz` under classroom light
   (D-002 revisit). Use the pilot numbers, not opinions.
4. Every failure gets an owner and a fix-or-dismiss reason; fixes land before **G11**
   (Jan 3). Anything that cannot be fixed becomes a written limitation in the report and the
   demo scope (G12).
5. Update the progress log in `docs/PLAN_TIMELINE.md` with the gate result the same day.

## 13. Open items (blockers)

| # | Item | Owner | Needed by |
|---|---|---|---|
| 1 | Teacher-confirmed date, class, room, roster (G4) | D | Nov 22 |
| 2 | Two extra robustness volunteers (P4, P5) | A | Nov 22 |
| 3 | Classroom AP BSSID + subnet + access to the router/DHCP page | B | Nov 29 |
| 4 | Printed forms and consent text (English, 1 page) | A + D | Dec 6 |
| 5 | Spare phone with the app for the pilot day | C | Dec 6 |
