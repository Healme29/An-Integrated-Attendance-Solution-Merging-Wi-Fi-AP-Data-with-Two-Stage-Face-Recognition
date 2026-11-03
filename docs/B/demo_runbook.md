# Demo Runbook — printed copy (draft for G12–G16)

> **Status:** draft. Numbers marked *(measured)* were measured; everything else is a
> procedure to be executed and timed at dry run #1 (2027-01-09/10).
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
2. **Backend** (native — Docker cannot see the Wi-Fi LAN, decision D-002):
   ```powershell
   $env:TIMEZONE="Asia/Shanghai"; $env:FACE_SIMILARITY_THRESHOLD="0.5"; $env:YOLO_IMG_SIZE="640"
   $env:CORS_ORIGINS="http://127.0.0.1:8000"
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```
   Cold start to healthy: **5.9 s** *(measured 2026-11-02)*.
3. **Health + Wi-Fi** in a second terminal:
   ```powershell
   curl http://127.0.0.1:8000/health      # {"status":"ok","database":"ok"}
   curl http://127.0.0.1:8000/wifi/scan   # phone MAC must appear
   ```
4. **Backup the database now** (so a broken demo can be restored in ~6 s):
   ```powershell
   Copy-Item backend\attendance.db "backups\attendance-prerun.db"
   ```
5. **Warm the models** with one throwaway `/faces/recognize` call (first call may load
   YOLO + ArcFace; measured ~1 s per check-in afterwards).
6. **Phone**: `adb reverse tcp:8000 tcp:8000`, open the app, log in, confirm Settings →
   Test Connection is green.
7. **Dashboard** open in a browser tab, zoomed for the projector. Refresh once after the
   first check-in so the audience sees new rows appear.

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
| Backend does not answer `/health` | 2 attempts, 5 s apart | rung 4: restore backup (`deployment_guide.md` §8, 6.2 s measured) or `seed_demo.py --reset` |
| Check-in returns 403 `outside_class_time` | once | check clock/timezone first (`TIMEZONE` must be `Asia/Shanghai`), then fix the schedule window |
| Check-in returns 403 `identity mismatch` | once | wrong student logged in — C fixes the login, do not re-run blindly |
| `/wifi/scan` lists no phone | 1 scan | rung 2: continue, say the §4 sentence from `offline_fallback.md` |
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
if the previous run left a half-finished class.

---

## 6. Dry-run log (fill in at G13/G15)

| Item | Dry run #1 (Jan 9–10) | Dry run #2 (Jan 14–15) |
|---|---|---|
| Cold start → healthy (s) | | |
| `/wifi/scan` sees the phone (Y/N) | | |
| Start → `partial` (s) | | |
| End → `verified` (s) | | |
| Full run wall time (min) | | |
| Fallback used (which rung) | | |
| Surprises | | |
