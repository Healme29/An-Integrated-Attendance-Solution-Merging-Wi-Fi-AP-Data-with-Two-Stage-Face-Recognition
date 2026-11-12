# Demo Environment — G1 Evidence (M2 stage 1)

> **Owner:** member B · **Gate:** G1 "demo environment alive on the real machine" (due 2026-11-08)
> **Measured:** 2026-11-02 · **Status:** environment verified on the development laptop;
> the repeat on the physical demo laptop is still open (see §6).

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
python -m pytest backend/tests -q   ->   171 passed, 1 skipped   (23.8 s)
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

| # | Item | How to close it |
|---|---|---|
| 1 | Run this table on the **physical demo laptop** (Windows) | §5b of the deployment guide, paste the numbers here |
| 2 | Re-measure a scan with **1–2 real phones** on the demo network (hotspot with isolation off) | `GET /wifi/scan` must list the phone MACs; record seconds per scan |
| 3 | Confirm model warm-up on the demo laptop (first recognition downloads `buffalo_l`, ~330 MB) | one `/faces/recognize` call before the demo, then time a real check-in |
| 4 | Docker on the demo laptop | optional — only needed if the dashboard is demoed while native Wi-Fi is not |
| 5 | **Timed, full `pip install -r backend/requirements.txt` on a clean machine** | `time pip install -r backend/requirements.txt` in a fresh venv, paste the wall time |

### 6.1 Why item 5 is not already done here

The install was **not** run end-to-end on this machine: the root filesystem had 6.2 GB free on
2026-11-02 and only **1.1 GB free on 2026-11-12** (`df -h /`); `ultralytics` pulls `torch`
plus the `nvidia-*` CUDA wheels, which is 2–3 GB of downloads and more than that unpacked. Filling the disk to measure the timer would
destroy the working environment, so the step is left to the demo laptop, where the disk is
empty and the measurement is the one that actually matters. Recorded honestly rather than
estimated: `pip install` time is **not measured yet**.

### 6.2 Closed on 2026-11-03 (was a risk, not an open measurement)

| Item | Status |
|---|---|
| BSSID unreadable because only `iwconfig` was supported | ✅ fixed — probe chain `iw` → `nmcli` → `iwconfig`, warning when none work; proven on a host **without** `iw` (`network_validation.md` §7, D-009) |
| macOS `ping` flags wrong | ✅ fixed — plain `-c 1` on Darwin (`network_validation.md` §6.2, D-010) |
