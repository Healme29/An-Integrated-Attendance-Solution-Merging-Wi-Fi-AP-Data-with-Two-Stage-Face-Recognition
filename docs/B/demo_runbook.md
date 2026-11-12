# Demo Runbook — printed copy (draft for G12–G16)

> **Status:** draft. Numbers marked *(measured)* were measured; everything else is a
> procedure to be timed at dry run #1, now **before the assessment (presentation ≈
> 2026-11-23)**; the former 2027-01-09/10 slots were superseded by A's D-005 (2026-11-09).
> **Owner:** B · **Used by:** A (backend), C (phone), D (narration), B (fallback).

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
| Backend | `http://127.0.0.1:8000` (host), `http://<laptop-ip>:8000` (LAN) |
| Dashboard | `http://127.0.0.1:8000/dashboard` |
| API docs (only if asked) | `http://127.0.0.1:8000/docs` |
| Phone connection | `adb reverse tcp:8000 tcp:8000`, app URL `http://127.0.0.1:8000` |
| Hotspot | SSID `Attendance-Demo`, password on the printed sheet (not in git) |

---

## 2. Startup order (T−30 min)

1. **Laptop network first.** Join the demo network or start the Mobile hotspot. Write the
   laptop IP on the printed sheet.
2. **Backend** (native — Docker cannot see the Wi-Fi LAN, decision D-002) **with the log
   captured to a file** (the "CCTV" record — see §2b):
   ```powershell
   $env:TIMEZONE="Asia/Shanghai"; $env:FACE_SIMILARITY_THRESHOLD="0.5"; $env:YOLO_IMG_SIZE="640"
   $env:CORS_ORIGINS="http://127.0.0.1:8000"
   $log = "backend\server_$(Get-Date -Format 'yyyyMMdd-HHmm').log"
   cmd /c "python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > `"$log`" 2>&1"
   ```
   In a **second** PowerShell window, follow the file live (use the filename printed above;
   the `$log` variable only exists in the first window):
   ```powershell
   Get-Content backend\server-20261123-0900.log -Wait -Tail 20
   ```
   Cold start to healthy: **5.9 s** *(2026-11-02)*, **6.1–9.1 s** *(2026-11-11/12, same
   host, cold page cache — the reason the runbook starts at T−30 min, not T−5)*.
3. **Health + Wi-Fi** in another terminal:
   ```powershell
   curl http://127.0.0.1:8000/health      # {"status":"ok","database":"ok"}
   curl http://127.0.0.1:8000/wifi/scan   # phone MAC must appear
   ```
4. **Backup the database now** (so a broken demo can be restored in ~6 s):
   ```powershell
   Copy-Item backend\attendance.db "backups\attendance-prerun.db"
   ```
5. **Warm the models** with one `/faces/recognize` call **using a photo that contains a
   face** — a faceless image stops after YOLO and leaves ArcFace cold, so it warms nothing.
   Then confirm the cache exists: `dir %USERPROFILE%\.insightface\models\buffalo_l` must list
   five `.onnx` files (~326 MB). With the cache present, loading took 3.1–4.2 s here (D-014);
   afterwards a check-in is ~1 s. Missing cache + no internet = a failed check-in
   (`ProxyError`), **not** `face_only`.
6. **Phone**: `adb reverse tcp:8000 tcp:8000`, open the app, log in, confirm Settings →
   Test Connection is green.
7. **Dashboard** open in a browser tab, zoomed for the projector. Refresh once after the
   first check-in so the audience sees new rows appear.

---

## 2b. Log capture — the "CCTV" file (decision D-012)

Why: if the terminal is closed, scrolled away, or the laptop reboots, a demo whose output
only ever existed on screen has no record. The log file is the evidence that a disputed
check-in was (or was not) served, and when.

**One command, no code change.** The backend has no file-handler configuration and B does not
own `backend/main.py`, so capture is done by the shell. `cmd /c` is used instead of
PowerShell's `2>&1 | Tee-Object` because PowerShell 5.1 wraps native stderr in
`ErrorRecord`s and writes formatting noise into the file; `cmd /c` writes the raw lines.

What the file contains *(measured 2026-11-11 on port 8098)*:

```
INFO:     Started server process [11320]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8098 (Press CTRL+C to quit)
INFO:     127.0.0.1:34112 - "GET /health HTTP/1.1" 200 OK
Interface network 10.163.128.0/17 is wider than /24; sweeping only 10.163.167.0/24. ...
scapy ARP scan failed ([Errno 1] Operation not permitted); using ping + neighbour fallback
INFO:     127.0.0.1:34128 - "GET /wifi/scan HTTP/1.1" 200 OK
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [11320]
```

So the log proves: start time, every HTTP request with status code, scanner warnings (why a
scan degraded), tracebacks, and clean versus unclean shutdown. It does **not** contain face
images, embeddings, or similarity scores — those are not logged anywhere.

Housekeeping for the demo day:

| When | Action |
|---|---|
| Before the demo | `Remove-Item backend\server_*.log -ErrorAction SilentlyContinue` so the file of the day is unambiguous |
| During | Leave the tail window open; the file is the authority if the screen is scrolled |
| After | `Copy-Item $log "backups\server-demo.log"` next to `attendance-after-demo.db` |
| Never | `git add` the log — `backend/server_*.log` is already in `.gitignore` (verified with `git check-ignore`) |

Privacy: access lines include the request path, so a check-in line contains
`student_id=…`. That is a student number, not biometric data, but it is still personal — keep
the logs on the demo laptop and the USB backup only, and delete them once the report is
written.

---

## 3. On-stage sequence (what the audience sees)

| Time | Who | Action | Expected visible result |
|---|---|---|---|
| 0:00 | D | problem + three-condition rule | slide |
| 1:00 | C | student logs in with NIM | app home with the class banner |
| 1:30 | C | **start** selfie | `partial` row, dashboard row appears (refresh) |
| 2:30 | A | explain face match confidence on the dashboard | confidence ≈ 0.7–0.95 |
| 3:00 | C | **end** selfie | row becomes `verified` (or `face_only`) |
| 3:30 | B | `/wifi/scan` + `ap_logs` evidence | phone MAC logged on the classroom AP |
| 4:00 | D | CSV export / history | spreadsheet opens with the rows |
| 5:00 | D | limitations + future work | slides |

---

## 4. Fallback triggers (B decides, A confirms)

| Trigger | Threshold | Action |
|---|---|---|
| Backend does not answer `/health` | 2 attempts, 5 s apart | rung 4: restore backup (`deployment_guide.md` §8, 6.1–6.2 s re-measured 2026-11-12) or `seed_demo.py --reset` |
| Check-in returns 403 `outside_class_time` | once | check clock/timezone first (`TIMEZONE` must be `Asia/Shanghai`), then fix the schedule window |
| Check-in returns 403 `identity mismatch` | once | wrong student logged in — C fixes the login, do not re-run blindly |
| `/wifi/scan` lists no phone | 1 scan | rung 2: continue, say the §4 sentence from `offline_fallback.md` |
| Recognition error twice | 2 attempts | rung 3: seeded dashboard + CSV, explain the flow with real rows from the pilot |
| Laptop dies | — | rung 5: backup video (D) |

---

## 5. Shutdown / reset after the demo

```powershell
# copy the demo database and the day's log somewhere for the report's evidence
# (use the actual filename; $log only exists in the window that started the server)
Copy-Item backend\attendance.db "backups\attendance-after-demo.db"
Copy-Item backend\server-20261123-0900.log "backups\server-demo.log"
# stop the server with Ctrl+C in its terminal; the log ends with
#   "Application shutdown complete." + "Finished server process"  ← confirms a clean stop
# then:
adb reverse --remove tcp:8000
```

Before the **next** demo run: `python backend/scripts/seed_demo.py --reset --students 5`
if the previous run left a half-finished class.

---

## 6. Dry-run log (fill in at G13/G15)

**Run #0 — 2026-11-12, seeded path only, on the Linux host.** Executed and measured:
seed 5 students → 5 attendance rows, cold start 8.2 s, smoke test 14/14, `/attendance/today`
and CSV correct, dashboard title correct, log capture verified, restore 6.2 s + 6.1 s with
data intact. Full table in `dry_run_2026-11-12.md`. It does **not** cover a real face
check-in, a real phone, Windows, or the hotspot — those are the rows below.

| Item | Dry run #1 (before 2026-11-23) | Dry run #2 (December pilot) |
|---|---|---|
| Cold start → healthy (s) | | |
| `/wifi/scan` sees the phone (Y/N) | | |
| Start → `partial` (s) | | |
| End → `verified` (s) | | |
| Full run wall time (min) | | |
| Log file written + clean shutdown line (Y/N) | | |
| Fallback used (which rung) | | |
| Surprises | | |
