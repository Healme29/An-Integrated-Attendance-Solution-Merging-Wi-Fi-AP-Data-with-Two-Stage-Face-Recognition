# Demo Environment — G1 Evidence (M2 stage 1)

> **Owner:** member B · **Gate:** G1 "demo environment alive on the real machine" (due 2026-11-08)
> **Measured:** 2026-11-02 (Linux laptop) and 2026-11-13 (physical Windows 11 laptop).
> **Status:** the whole G1 table now has numbers on a physical Windows laptop (§7). What is
> still open is hardware/people-bound, not software: the hotspot scan with real phones and
> the confirmation that this laptop is the final demo machine (§6).

Everything below was executed, not predicted. Raw command output is quoted so anyone can
re-run it.

---

## 1. What G1 requires

| Requirement | Where it is proven here |
|---|---|
| `/health` returns ok | §2.1 |
| Data persists across a restart | §2.3 |
| `TIMEZONE` and the threshold from A are read correctly | §2.2, §2.4 |
| Smoke test passes | §2.5 |
| Settings are written down as the values actually used | §3 |

---

## 2. Measured results

Environment: Linux laptop, Python 3.12.3 (`venv`), native `uvicorn` (no Docker), isolated
`DATABASE_PATH` and `DATA_DIR` under `/tmp`, so the real `backend/attendance.db` was never
touched by the test.

```bash
export DATABASE_PATH=/tmp/opencode/g1/attendance.db DATA_DIR=/tmp/opencode/g1/data \
       TIMEZONE=Asia/Shanghai FACE_SIMILARITY_THRESHOLD=0.5 YOLO_IMG_SIZE=640 \
       CORS_ORIGINS=http://127.0.0.1:8011
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8011
```

### 2.1 Health and dashboard

| Check | Result |
|---|---|
| Cold start (process start → first healthy `/health`) | **5,926 ms** |
| `GET /health` | `{"status":"ok","database":"ok"}` |
| `GET /` | `{"message":"Face Attendance API is running",...}` |
| `GET /dashboard` | HTTP 200 in **81 ms** |

### 2.2 TIMEZONE is really applied

The schedule row is written with `now_local()` (configured timezone) while the student row
keeps SQLite's `CURRENT_TIMESTAMP` (UTC). The 8 h gap proves `TIMEZONE=Asia/Shanghai` was
read, not just accepted as an environment string:

```
POST /students/  -> {"created_at":"2026-11-02T09:46:30"}     # SQLite UTC
POST /schedules/ -> {"created_at":"2026-11-02T17:46:30"}     # Asia/Shanghai (UTC+8)
```

Consequence for the demo: schedule windows, `outside_class_time` decisions and stored
attendance timestamps all follow `TIMEZONE`. A wrong zone on the demo laptop is the most
likely cause of unexplained 403s (it already happened once during C's device testing).

### 2.3 Persistence across a restart

```text
1. POST /students/ {"name":"G1 Persistence Check","nim":"G1CHECK01"}  -> id 1
2. kill the uvicorn process, start it again with the same DATABASE_PATH
3. GET /students/?nim=G1CHECK01
   -> [{"id":1,"name":"G1 Persistence Check","nim":"G1CHECK01", ...}]
```

The SQLite file (32 KB) survived, and so did the schedule and one `ap_logs` row.

### 2.4 Wi-Fi path (native)

```json
GET /wifi/scan
{"devices":[{"ip":"10.163.255.254","mac":"70:c6:dd:09:b0:02"}],
 "subnet":"10.163.216.0/24","count":1,"bssid":"50:98:b8:c9:2b:e2",
 "timestamp":"2026-11-02T17:46:36"}
```

- Interface: `wlo1` `10.163.216.151/17`, SSID `NJUPT-CMCC`, AP `50:98:B8:C9:2B:E2`.
- `subnet` equals the range that was **actually swept** (see the scanner fix in
  `docs/B/network_validation.md` §6).
- Only the gateway is visible — the same client-isolation/VLAN behaviour measured on the
  campus network before. Expected on campus, not a regression.

### 2.5 Smoke test

```
14/14 checks passed
Smoke test OK - backend is testable end-to-end.
```

The 15th check (own-MAC lookup) is Windows-only because it reads the host MAC with
`getmac`; on this Linux machine it is skipped by design.

### 2.6 Offline demo data (fallback input)

```
python backend/scripts/seed_demo.py --reset --students 5
students ready: 5
schedule created: id=1 'Demo Class' 17:42-18:42 (today, server timezone)
attendance rows created: 5
```

Served by the same server without restart: `/attendance/today` returned the five rows with
joined names, `/attendance/export/csv` returned the header plus rows, and
`/me/prompt?student_id=1` answered `check_in_complete` (already both stages),
`/me/prompt?student_id=5` answered `check_available: true, reason: device_not_seen_on_network`
(fake demo MAC, as documented).

### 2.7 Recovery if the database is damaged

| Step | Measured |
|---|---|
| Random bytes written over the DB → start server | startup fails: `sqlite3.DatabaseError: file is not a database`, connection refused |
| Copy backup over the DB → start server → `/health` ok | **6,172 ms** total (5.9 s startup + ~0.3 s copy) |

The full procedure is in `docs/B/deployment_guide.md` §8, and the demo-day sequence is in
`docs/B/demo_runbook.md`.

---

## 3. Values locked for the demo machine

| Variable | Value | Source |
|---|---|---|
| `TIMEZONE` | `Asia/Shanghai` | schedule windows on the demo machine |
| `FACE_SIMILARITY_THRESHOLD` | `0.5` | A's measured threshold (`docs/threshold_report.md`) |
| `YOLO_IMG_SIZE` | `640` | A's G3 measurement (3.8× faster, same recall) |
| `YOLO_CONF_THRESHOLD` | `0.25` (default) | A's G3 measurement |
| `ATTENDANCE_CHECK_WINDOW_MINUTES` | `15` (default) | project rule |
| `CORS_ORIGINS` | `http://127.0.0.1:8000` | only the dashboard needs it; no wildcard for the demo |
| `WI_FI_SUBNET` | unset on a flat hotspot; classroom /24 on campus | see network validation |
| Run mode | **native `uvicorn`**, not Docker | D-002 in `docs/B/DECISIONS.md` |

---

## 4. Automated regression baseline

```
python -m pytest backend/tests -q   ->   171 passed, 1 skipped   (23.8 s)   # 2026-11-02, Linux
python -m pytest backend/tests -q   ->   209 passed              (38.7 s)   # 2026-11-13, Windows
```

Two platform-dependent tests were fixed on the way (they never failed on Windows, so the
team baseline looked green while a Linux machine was red):

- `test_scan_cache_reuses_result` asserted against the Windows scan path without pinning
  the platform; it now patches `platform.system` so the same assertions run everywhere.
- The three `test_prompt.py` failures were the same root cause as the scanner bug below:
  scapy raises `PermissionError` without raw-socket privileges. The scanner now falls back
  to ping + `ip neigh`, so the prompt tests pass unprivileged.

---

## 5. What changed in the code because of this work

| File | Change | Why |
|---|---|---|
| `backend/services/wifi_scanner.py` | real netmask detection; bounded sweep; platform-correct ping flags; unprivileged Linux fallback | F1/F2 findings, see `network_validation.md` §6 |
| `backend/scripts/seed_demo.py` | N students (1–99), id sequence reset, scoped cleanup of stale embeddings/crops, honest MAC note | offline fallback must be repeatable and clean |
| `backend/tests/test_wifi_subnet.py` | 19 new tests for detection, sweep bounds, `ip neigh` parsing, fallback | the scanner is now testable without a network |
| `backend/tests/test_services.py` | cache test pinned to the Windows path | portable suite |

---

## 6. Still open (do not mark G1 done until these are done)

| # | Item | Status on 2026-11-13 | How to close it |
|---|---|---|---|
| 1 | Run this table on the **physical demo laptop** (Windows) | ✅ measured on a physical Windows 11 laptop — §7. **Still to confirm:** that this machine is the one used on stage (team decision) | if the demo laptop changes, repeat §7 there; the scripts are in `docs/B/evidence/2026-11-13-windows/scripts/` |
| 2 | Re-measure a scan with **1–2 real phones** on the demo network (hotspot with isolation off) | ❌ **not measured yet** — needs a second phone | `GET /wifi/scan` must list the phone MACs; record seconds per scan |
| 3 | Confirm model warm-up on the demo laptop | ✅ measured on Windows — §7.5: YOLO cold 13.4 s → warm 1.5 s, ArcFace load 2.8–3.0 s, 341 MB of model files, 1,001 MB RSS. **Not measured:** matching latency on a real face (no face photo on this machine) | one real enrolled face + one live check-in, timed |
| 4 | Docker on the demo laptop | ⏸ **not measured yet** — daemon not running; optional per D-002 | only needed if the dashboard is demoed while native Wi-Fi is not |
| 5 | **Timed, full `pip install -r backend/requirements.txt` on a clean machine** | ✅ measured on Windows — **577 s** (9 min 37 s), Python 3.12.10 venv, Tsinghua mirror (§7.1) | — |

### 6.1 Why item 5 was not done on the Linux machine (2026-11-02), and how it was closed

The install was **not** run end-to-end on the Linux laptop: its root filesystem had 6.2 GB
free (`df -h /`), and `ultralytics` pulls `torch` plus the `nvidia-*` CUDA wheels — 2–3 GB of
downloads and more unpacked. Filling the disk to measure the timer would have destroyed the
working environment.

Closed on 2026-11-13 on the Windows laptop instead (the measurement that matters): **577 s**
for the full pinned set (§7.1). The install log with the start/finish stamps is
`.venv/pip_install.log`; it is git-ignored, so the numbers are also copied into
`docs/B/evidence/2026-11-13-windows/README.md`.

### 6.2 Closed on 2026-11-03 (was a risk, not an open measurement)

| Item | Status |
|---|---|
| BSSID unreadable because only `iwconfig` was supported | ✅ fixed — probe chain `iw` → `nmcli` → `iwconfig`, warning when none work; proven on a host **without** `iw` (`network_validation.md` §7, D-009) |
| macOS `ping` flags wrong | ✅ fixed — plain `-c 1` on Darwin (`network_validation.md` §6.2, D-010) |

---

## 7. Measured on 2026-11-13 — physical Windows 11 laptop

Second G1 session, this time on the machine class the demo will use. OS `Windows 11
10.0.22621`, AMD64 (Intel64 Family 6 Model 140), Python **3.12.10** in a project-local
`.venv`, native `uvicorn`, isolated `DATABASE_PATH`/`DATA_DIR` under `%TEMP%` so the real
`backend/attendance.db` was never touched. Campus Wi-Fi `10.163.158.239/17`, gateway
`10.163.255.254`, AP BSSID `78:2c:29:09:e2:f2`.

Raw output: `docs/B/evidence/2026-11-13-windows/` (scripts included).

### 7.1 Clean install (item 5 of §6, now closed)

```text
INSTALL_STARTED=2026-11-13 12:09:36
INSTALL_FINISHED=2026-11-13 12:19:13 exit=0        -> 577 s (9 min 37 s)
Successfully installed ... torch-2.15.0+cpu numpy-1.26.4 onnxruntime-1.18.1 ...
```

- Python **3.13.5** (the system interpreter) cannot install the pinned set: no cp313 wheels
  for `numpy==1.26.4` / `onnxruntime==1.18.1` / `opencv-python==4.10.0.84`. Python 3.12.10
  works (D-012).
- `torch` resolved to the **CPU** wheel (126.7 MB) on Windows, not the CUDA bundle, so the
  Windows install is far smaller than the Linux one feared in §6.1.
- The install alone is **not** enough: the YOLO checkpoint is dill-pickled and `dill` is not
  in `backend/requirements.txt`, so `/faces/recognize` returned **500**
  (`ModuleNotFoundError: No module named 'dill'`). After `pip install dill==0.3.8` the same
  call returns 200. D-012 records the decision and the one-line change requested from A.

### 7.2 G1 table, repeated on Windows

| Check | Measured value | Verdict |
|---|---|---|
| Cold start → first healthy `/health` | **17,313 ms** | ✅ |
| Restart with the same DB → healthy | **25,260 ms** | ✅ |
| `GET /health` / `/` / `/dashboard` (warm, median of 3) | **5.4 ms** / **1.7 ms** / **6.2 ms** | ✅ |
| `TIMEZONE=Asia/Shanghai` applied | student `created_at` 04:21:07 (SQLite UTC) vs schedule 12:21:07 → **+8.0 h** | ✅ |
| Data persists across stop/start | student `G1WIN01` returned with the same id | ✅ |
| Smoke test | **12/15** before `dill` → **15/15** after (`measurements-smoke.txt`) | ✅ |
| `seed_demo.py --reset --students 5` | **695 ms**, exit 0; `/attendance/today` 5 rows, CSV 6 lines, `/me/prompt` `check_in_complete` | ✅ |
| Backup copy (server stopped) | **1.2 ms**, 40,960 bytes | ✅ |
| Restore backup → healthy | **13,912 ms** (copy 2.9 ms) | ✅ |
| Fresh start with no DB file | **14,715 ms**, 0 students, DB created | ✅ |
| Server started against a corrupt DB | startup fails with `sqlite3.DatabaseError: file is not a database`; the **process does not exit** (killed after 87 s) | ⚠️ see §7.6 |

The Windows cold start (17–25 s) is ~3× the Linux number (5.9 s). It is dominated by
importing `torch`/`ultralytics` on a cold page cache; it is still well inside the runbook's
T−30 min window, so no change was made.

### 7.3 Wi-Fi path on the campus network (Windows)

```json
GET /wifi/scan
{"devices":[{"ip":"10.163.255.254","mac":"70:c6:dd:09:b0:02"}],
 "subnet":"10.163.158.0/24","count":1,"bssid":"78:2c:29:09:e2:f2"}
```

| Measurement | Value |
|---|---|
| Fresh scan (ARP sweep of 254 hosts) | **4,281 ms** |
| Second scan inside the 10 s cache window | **29 ms** |
| `ap_logs` rows after two scans (dedupe) | 0 → **1** → **1** |
| Interface network detected from `ipconfig` mask | `10.163.128.0/17` (server log), sweep capped to the host's /24 |
| BSSID read with `netsh` | `78:2c:29:09:e2:f2`, stable |

Only the gateway is visible — the same client-isolation/VLAN behaviour as on Linux
(`network_validation.md` F2), not a Windows regression. The reported `subnet` is exactly the
range that was swept (D-004). See `network_validation.md` §8 for the Windows-specific parser
work (D-011).

### 7.4 Face pipeline (model load measured, matching not measured)

| Measurement | Value |
|---|---|
| First `/faces/recognize` after a cold start (YOLO load + inference) | **13,435 ms** |
| Second / third call (warm) | **1,637 ms** / **1,535 ms** |
| Warm-up call on a freshly started server (page cache warm) | **8,282 ms** |
| InsightFace `buffalo_l` load (5 models) | **2.83–2.98 s**, RSS delta **+533 MB** |
| Backend RSS with **both** models resident | **1,001 MB** |
| `yolov8m-face.pt` | 52,028,566 bytes, sha256 `219f490a…be93`, downloaded in ~70 s |
| `buffalo_l` unpacked | 341,268,726 bytes in 5 `.onnx` files |
| `/faces/enroll` with no face in the photo | 400 `No face detected in image` (1,419 ms) |
| `/attendance/check` with no face in the photo | 400 `Face not recognized: no_face_detected` (1,400 ms) |

No real face photo was available (none may be committed, and no face image was reachable
from this network), so the **matching** latency on a real face is **not measured yet** —
recorded, not estimated.

### 7.5 Upload cap on the recognition path (hardening finding, measured)

| Request | Limit | Result |
|---|---|---|
| `POST /faces/enroll` with an 11 MB body | 10 MB | **413** `Image too large (max 10 MB)` in 88 ms |
| `POST /faces/recognize` with an 11 MB body | 10 MB | **200**, body read fully, 145 ms |
| `POST /attendance/check` with an 11 MB body | 10 MB | **400** `Face not recognized: invalid_image`, 155 ms |

`/faces/enroll` checks `MAX_UPLOAD_BYTES` before reading; the other two read the whole
upload first. On a trusted LAN this is a nuisance, not a breach; it is logged as gap 1 in
`hardening_checklist.md` §2.1 for A.

### 7.6 Corrupt DB: clear error, but the process lingers

Measured twice (`measurements-g1.txt` §7 aborted with a 120 s timeout;
`measurements-corrupt-db.txt` polled the process for 87 s):

- the server logs `sqlite3.DatabaseError: file is not a database` and
  `ERROR: Application startup failed. Exiting.`;
- but `uvicorn` never actually exits and never binds the port, so an operator who "starts it
  again" accumulates processes. `models/database.py` is A-owned and the likely cause is the
  `aiosqlite` connection opened in `init_db()` not being closed on failure, so B recorded the
  observation and handed it to A instead of patching it.

Recovery is unaffected: stop the process, copy the backup over the DB, start again
(**13.9 s** measured, §7.2).

### 7.7 What this session changed in the code

| File | Change | Why |
|---|---|---|
| `backend/services/wifi_scanner.py` | locale-independent Windows netmask parsing; non-contiguous masks rejected | D-011 |
| `backend/tests/test_wifi_subnet.py` | +4 locale/format tests (Chinese, French, `(Preferred)`, invalid mask) | D-011; suite **209 passed** |

Nothing else outside B's allowed files was modified for this measurement run.
