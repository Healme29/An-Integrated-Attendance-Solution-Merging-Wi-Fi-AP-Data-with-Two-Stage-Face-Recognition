# Demo Runbook — printed copy (draft for G12–G16)

> **Status:** draft. Numbers marked *(measured)* were measured; everything else is a
> procedure to be executed and timed at dry run #1 (2027-01-09/10).
> **Owner:** B · **Used by:** A (backend), C (phone), D (narration), B (fallback).
> **Updated 2026-11-10:** strict classroom mode (`REQUIRE_CLASSROOM_WIFI=true`, D-006) and
> the check-in preflight are now part of the demo path, and the app only lists schedules
> whose window is open. The dry-run dates above predate the accelerated timeline (D-005);
> the dates will be re-cut, the procedures below will not.

---

## 0. Roles and who to call

| Person | Owns during the demo | If their part breaks |
|---|---|---|
| **A** | backend process, face recognition, threshold questions | decides "keep going" vs "use fallback"; B executes |
| **C** | phone, app, `adb reverse`, camera framing | swaps to the backup phone; if both fail → rung 5 |
| **D** | narration, timing, slides, backup video | keeps talking, plays the video |
| **B** | Wi-Fi check, database, fallback ladder | calls the rung, does the restore |

B and A sit next to each other: only B touches the database, only A touches the ML config.

---

## 1. Ports and addresses

| Thing | Value |
|---|---|
| Backend (host) | `http://127.0.0.1:8000` |
| Backend (phones) | `http://192.168.137.1:8000` — the Windows Mobile Hotspot host, and the app's built-in default |
| Dashboard | `http://127.0.0.1:8000/dashboard` |
| API docs (only if asked) | `http://127.0.0.1:8000/docs` |
| Hotspot | SSID `Attendance-Demo`, 2.4 GHz, password on the printed sheet (not in git) |
| Phone connection | join `Attendance-Demo`; no cable needed |
| Alternative (USB only) | `adb reverse tcp:8000 tcp:8000`, then set the app URL to `http://127.0.0.1:8000` in Settings |

---

## 2. Startup order (T−30 min)

1. **Hotspot first.** Turn on the Windows Mobile Hotspot: SSID `Attendance-Demo`, band
   2.4 GHz. Windows assigns the host address `192.168.137.1`; write it on the printed sheet.
   A phone hotspot or a small travel router works too — what matters is that the server and
   the student phones share one flat network with **client isolation off**, which campus
   Wi-Fi does not give us (`network_validation.md` F2).
2. **Backend** (native — Docker cannot see the Wi-Fi LAN, decision D-002):
   ```powershell
   $env:TIMEZONE="Asia/Shanghai"; $env:FACE_SIMILARITY_THRESHOLD="0.5"; $env:YOLO_IMG_SIZE="640"
   $env:WI_FI_SUBNET="192.168.137.0/24"; $env:REQUIRE_CLASSROOM_WIFI="true"
   $env:CORS_ORIGINS="http://127.0.0.1:8000"
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```
   Cold start to healthy: **5.9 s** *(measured 2026-11-02)*. Keep
   `REQUIRE_CLASSROOM_WIFI=true` for the demo: it turns the Wi-Fi condition into a visible
   gate (403, no row) instead of a silent downgrade to `face_only`.
3. **Health + Wi-Fi** in a second terminal:
   ```powershell
   curl.exe http://127.0.0.1:8000/health      # {"status":"ok","database":"ok"}
   curl.exe http://127.0.0.1:8000/wifi/scan   # the phone MAC must appear in "devices"
   ```
   The response also carries `bssid` — that is the **hotspot's** BSSID and the value the
   schedule will pin in step 5. (In Windows PowerShell `curl` is an alias for
   `Invoke-WebRequest`; the commands below use `curl.exe` so you see the raw JSON.)
4. **Replace the seeded MACs with the real phones.** `seed_demo.py` deliberately gives demo
   students fake local MACs (`02:00:00:00:00:NN`), so with strict mode on **every check-in
   from a seeded student is rejected with 403**. Register the real Wi-Fi MAC of each demo
   phone (and switch off "private/random MAC" for `Attendance-Demo` on that phone):
   ```powershell
   curl.exe -X PUT "http://127.0.0.1:8000/students/1/mac?mac_address=aa:bb:cc:dd:ee:ff"
   ```
   Note the query parameter — this endpoint takes no JSON body.
5. **Check the active schedule and pin the AP.** The app lists only `/schedules/active`, so
   the demo class must be inside its window *and* on today's weekday:
   ```powershell
   curl.exe http://127.0.0.1:8000/schedules/active     # must not be []
   ```
   If it is empty, re-run `seed_demo.py` (it opens a class 5 min before now and closes 55 min
   after) or fix the window. Then pin the hotspot BSSID from step 3:
   ```powershell
   curl.exe http://127.0.0.1:8000/schedules/1     # copy day_of_week/start_time/end_time/room
   ```
   `PUT /schedules/{id}` replaces **every** field, so copy the current window from that GET
   and add only the BSSID — do not retype the times, or the class window breaks:
   ```powershell
   curl.exe -X PUT http://127.0.0.1:8000/schedules/1 -H "Content-Type: application/json" `
     -d '{"class_name":"<from GET>","day_of_week":<from GET>,"start_time":"<from GET>","end_time":"<from GET>","ap_bssid":"<bssid from step 3>","room":"<from GET>"}'
   ```
   `day_of_week` is 0 = Monday. Leaving `ap_bssid` empty is allowed — the MAC layer still
   applies — but then the BSSID half of the story is not demonstrated.
6. **Preflight must be green before the audience arrives:**
   ```powershell
   curl.exe "http://127.0.0.1:8000/attendance/preflight?student_id=1&schedule_id=1&check_type=start"
   ```
   Expect `"allowed": true`, `"wifi_verified": true`, and `schedule_bssid` equal to
   `server_bssid`. If `wifi_verified` is false, do **not** start with strict mode: go to the
   fallback table (§4).
7. **Backup the database now** (so a broken demo can be restored in ~6 s):
   ```powershell
   Copy-Item backend\attendance.db "backups\attendance-prerun.db"
   ```
8. **Warm the models** with one throwaway `/faces/recognize` call (first call may load
   YOLO + ArcFace; measured ~1 s per check-in afterwards).
9. **Phone**: join `Attendance-Demo`, open the app, log in, confirm Settings → Test
   Connection is green. **Dashboard** open in a browser tab, zoomed for the projector.
   Refresh once after the first check-in so the audience sees new rows appear.

---

## 3. On-stage sequence (what the audience sees)

| Time | Who | Action | Expected visible result |
|---|---|---|---|
| 0:00 | D | problem + three-condition rule | slide |
| 1:00 | C | student logs in with NIM | home screen lists **only** the class whose window is open |
| 1:15 | C | tap check-in — the app calls preflight first | camera opens only because the server answered `allowed: true` |
| 1:30 | C | **start** selfie | `partial` row, dashboard row appears (refresh) |
| 2:30 | A | explain face match confidence on the dashboard | confidence ≈ 0.7–0.95 |
| 3:00 | C | **end** selfie | row becomes `verified`; with strict mode the Wi-Fi was confirmed on both stages |
| 3:30 | B | `/wifi/scan` + `ap_logs` evidence | phone MAC logged, `bssid` = the hotspot, matching `schedule_bssid` |
| 3:45 | C | *optional negative test*: leave the hotspot (mobile data only), tap check-in | app refuses **before** the camera: "not connected to the classroom Wi-Fi", no row written |
| 4:15 | D | CSV export / history | spreadsheet opens with the rows |
| 5:00 | D | limitations + future work | slides |

---

## 4. Fallback triggers (B decides, A confirms)

| Trigger | Threshold | Action |
|---|---|---|
| Backend does not answer `/health` | 2 attempts, 5 s apart | rung 4: restore backup (`deployment_guide.md` §8, 6.2 s measured) or `seed_demo.py --reset` |
| Check-in returns 403 `outside_class_time` | once | check clock/timezone first (`TIMEZONE` must be `Asia/Shanghai`), then fix the schedule window |
| Check-in returns 403 `not_on_classroom_network` | first occurrence | the student's MAC is not visible on the hotspot: wrong MAC registered, phone using a private/random MAC, or the phone is on another network. Check `/wifi/scan`, fix with `PUT /students/{id}/mac`. If the network itself is unreliable, restart the backend with `REQUIRE_CLASSROOM_WIFI=false` — rows then degrade to `face_only`; say that on stage instead of hiding it |
| App shows "No active class right now" | before going on stage | `/schedules/active` is empty: the schedule is outside its window or on another weekday. Re-run `seed_demo.py` or correct start/end |
| Preflight says `wifi_verified: false` while `/wifi/scan` sees the phone | before going on stage | `schedule_bssid` ≠ `server_bssid`. Clear `ap_bssid` or set it to the value preflight reports |
| Check-in returns 403 `identity mismatch` | once | wrong student logged in — C fixes the login, do not re-run blindly |
| `/wifi/scan` lists no phone | 1 scan | with strict mode on this blocks every check-in, so do not "continue": restart with `REQUIRE_CLASSROOM_WIFI=false`, demo the face path, and say the §4 sentence from `offline_fallback.md` |
| Recognition error twice | 2 attempts | rung 3: seeded dashboard + CSV, explain the flow with real rows from the pilot |
| Laptop dies | — | rung 5: backup video (D) |

---

## 5. Shutdown / reset after the demo

```powershell
# copy the demo database somewhere for the report's evidence
Copy-Item backend\attendance.db "backups\attendance-after-demo.db"
# stop the server with Ctrl+C in its terminal; then:
adb reverse --remove tcp:8000
```

Before the **next** demo run: `python backend/scripts/seed_demo.py --reset --students 5`
if the previous run left a half-finished class. **A reset puts the fake demo MACs back**
(`02:00:00:00:00:NN`), so repeat step 4 of §2 and re-pin the BSSID (step 5) before the next
run — with strict mode on, otherwise every check-in is rejected.

---

## 6. Dry-run log (fill in at G13/G15)

| Item | Dry run #1 (Jan 9–10) | Dry run #2 (Jan 14–15) |
|---|---|---|
| Strict mode on (`REQUIRE_CLASSROOM_WIFI=true`) | | |
| Preflight `allowed: true` before the first selfie | | |
| Negative test: off-hotspot check-in refused | | |
| Cold start → healthy (s) | | |
| `/wifi/scan` sees the phone (Y/N) | | |
| Start → `partial` (s) | | |
| End → `verified` (s) | | |
| Full run wall time (min) | | |
| Fallback used (which rung) | | |
| Surprises | | |
