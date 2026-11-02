# Deployment Guide — Running the Backend with Docker

> **Audience:** anyone on the team, including non-technical members (D, teachers).
> **Time needed:** 20–30 minutes the first time (most of it is image download/build).
> **Output:** backend reachable at `http://<machine-ip>:8000`, teacher dashboard at
> `http://<machine-ip>:8000/dashboard`.

---

## 0. What you are deploying

One container runs the whole backend (FastAPI + SQLite + face models):

```
your machine
└── docker compose
    └── backend container  ── port 8000 ──▶ phone app / teacher browser
        ├── /app/data/models/yolov8m-face.pt   (baked into the image, 50 MB)
        └── /app/data/dbdata  ◀── named volume (persistent)
            ├── attendance.db                  (database)
            └── insightface/                   (ArcFace models, ~330 MB, downloaded on first use)
```

> **Demo rule (measured):** Wi-Fi presence scanning only works from the **host's**
> network stack. On Docker Desktop (Windows/macOS) the container cannot see the
> host Wi-Fi LAN — for any demo/pilot that must show `/wifi/scan` finding real
> phones or BSSID pinning working, **run natively** with `uvicorn`. See §6.

---

## 1. Prerequisites

| Item | Notes |
|---|---|
| Docker Desktop | Windows/macOS. On Windows: WSL2 backend, 8 GB RAM recommended |
| Repo checkout | `git clone <repo>` (or the zip the team shared) |
| Free port 8000 | if taken, use `BACKEND_PORT` (see §4) |

---

## 2. China network note — configure a registry mirror FIRST

Docker Hub is usually unreachable from campus/home networks in mainland China
(`failed to fetch anonymous token ... auth.docker.io`). Add a mirror to the Docker
daemon **before** building:

1. Open `%USERPROFILE%\.docker\daemon.json` (Windows) or `~/.docker/daemon.json` (macOS)
   and add `registry-mirrors`:

```json
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://dockerproxy.com"
  ]
}
```

2. Restart the engine so the mirrors apply:

```powershell
docker desktop restart
docker info --format "{{.RegistryConfig.Mirrors}}"   # must list your mirrors
```

Mirrors go down from time to time; if a pull still fails, test a few candidate mirror
`/v2/` URLs from a browser and use whichever answers (HTTP 200/401 = reachable).

---

## 3. Start the backend

From the **repository root** (where `docker-compose.yml` lives):

```powershell
docker compose up -d --build
```

First run: builds the image (several minutes; `insightface` compiles native code) and
starts the container.

Check it is running:

```powershell
docker compose ps
docker compose logs -f backend        # Ctrl+C to stop watching
```

You should see `Uvicorn running on http://0.0.0.0:8000`.

---

## 4. Settings (optional `.env` in the repo root)

| Variable | Default | Meaning |
|---|---|---|
| `BACKEND_PORT` | `8000` | host port to publish |
| `TIMEZONE` | `Asia/Shanghai` | server timezone — **schedule windows and stored timestamps follow this** |
| `CORS_ORIGINS` | `*` | comma-separated allowed origins; set the school dashboard URL in production |
| `WI_FI_SUBNET` | `192.168.1.0/24` | subnet the Wi-Fi scanner sweeps (see limitation §6) |
| `FACE_SIMILARITY_THRESHOLD` | `0.5` | recognition threshold (final value from A) |
| `ATTENDANCE_CHECK_WINDOW_MINUTES` | `15` | grace minutes around the class window |

Example `.env`:

```ini
BACKEND_PORT=8000
TIMEZONE=Asia/Shanghai
CORS_ORIGINS=http://10.163.235.210:8000
FACE_SIMILARITY_THRESHOLD=0.5
WI_FI_SUBNET=10.163.235.0/24
```

Then re-create the container: `docker compose up -d`.

---

## 5. Verify

Run these in **PowerShell**. Two Windows traps are already handled below: `curl` is an alias
for `Invoke-WebRequest` (always write `curl.exe`), and JSON bodies must be single-quoted.

```powershell
# 1. health
curl.exe http://127.0.0.1:8000/health
# {"status":"ok","database":"ok"}

# 2. teacher dashboard
Start-Process http://127.0.0.1:8000/dashboard

# 3. API docs
Start-Process http://127.0.0.1:8000/docs

# 4. persistence: create a student, restart, confirm it is still there
Invoke-RestMethod -Uri http://127.0.0.1:8000/students/ -Method Post `
  -ContentType 'application/json' -Body '{"name":"Deploy Check","nim":"DEPLOY01","mac_address":null}'
docker compose restart backend
Invoke-RestMethod -Uri "http://127.0.0.1:8000/students/?nim=DEPLOY01"
# the student must still be returned -> the named volume works

# 5. smoke test (host Python, no face photo needed)
python backend/scripts/smoke_test.py --base-url http://127.0.0.1:8000

# 6. stop / start later
docker compose stop          # stop; data stays in the volume
docker compose up -d         # start again (no rebuild)
```

**A fresh clone has no database file.** The server creates `backend/attendance.db` (or the
container volume) on the first start — that is expected, not an error.

**Phone access over Wi-Fi:** allow port 8000 in Windows Defender Firewall when prompted,
then set the app's server URL to `http://<machine-ip>:8000`.

---

## 5b. Native run (required when the demo must show Wi-Fi presence)

Use this mode on the demo/pilot machine. Measured on 2026-11-02: a cold start is
**~5.9 s** to `{"status":"ok","database":"ok"}` and `/wifi/scan` finds devices that
Docker cannot see (details in `docs/B/demo_environment.md`).

```powershell
# 0. once: Python 3.11+ and the dependencies
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt

# 1. once: YOLO weights (52 MB, not in git)
#    the folder does NOT exist in a fresh clone - create it first (measured: the
#    download fails with "cannot find path" if backend\data\models is missing)
New-Item -ItemType Directory -Force backend\data\models | Out-Null
curl.exe -L -o backend\data\models\yolov8m-face.pt https://github.com/YapaLab/yolo-face/releases/download/1.0.0/yolov8m-face.pt
# sanity check: the file must be ~52 MB
Get-Item backend\data\models\yolov8m-face.pt | Select-Object Length

# 2. every demo: set the environment (values locked at G1/G3)
$env:TIMEZONE                 = "Asia/Shanghai"   # schedules follow this
$env:FACE_SIMILARITY_THRESHOLD = "0.5"            # final value from A
$env:YOLO_IMG_SIZE            = "640"             # measured: 3.8x faster, same recall
$env:CORS_ORIGINS             = "http://127.0.0.1:8000"

# 3. start from the repository root (Ctrl+C stops it)
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 4. verify (second terminal, same PowerShell window settings not needed)
curl.exe http://127.0.0.1:8000/health
curl.exe http://127.0.0.1:8000/wifi/scan      # phones + BSSID must be visible
python backend\scripts\smoke_test.py --base-url http://127.0.0.1:8000
```

Opening the port for the phone (once, as administrator):

```powershell
New-NetFirewallRule -DisplayName "Attendance backend 8000" -Direction Inbound `
  -Protocol TCP -LocalPort 8000 -Action Allow
# find the machine IP the phone must use (the Wi-Fi adapter's IPv4 address)
Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -like "*Wi-Fi*"} |
  Select-Object IPAddress, PrefixLength
```

Notes:

- `TIMEZONE` is what makes schedule windows and stored timestamps correct. If check-ins
  fail with `outside_class_time` on a machine whose clock "looks right", compare
  `GET /attendance/today` timestamps with your watch before touching the schedule.
- `WI_FI_SUBNET` is optional. Unset → auto-detected from the interface; the value shown by
  `/wifi/scan` is **exactly the /24 that was swept**. On a network wider than /24 set the
  classroom /24 explicitly.
- Windows does **not** need Npcap for the scan path (ping sweep + `arp -a`).

---

## 6. Important limitation — Wi-Fi scanning inside Docker on Windows/macOS

The Wi-Fi presence check depends on the **host's** ARP table and wireless adapter.
On Docker Desktop (Windows/macOS) the container runs inside a Linux VM with its own
network namespace, so scanning inside the container sees the Docker bridge — **not** the
campus Wi-Fi clients. Consequences:

| Goal | How to run |
|---|---|
| Dashboard demo, API demo, seeded demo data | Docker is fine |
| **Real Wi-Fi presence check (classroom/pilot)** | Run the backend **natively** on the classroom machine (`python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000`) or use Docker on a **Linux** host with `network_mode: host` |

This is a property of container networking, not a bug in our code.

---

## 7. First attendance check downloads models (~330 MB)

The ArcFace models land in the persistent volume on the first recognition call
(`/app/data/dbdata/insightface`), or in `DATA_DIR` when running natively. Do one warm-up call
before a live demo so the download does not happen in front of the audience:

```powershell
# any JPEG works - the point is to trigger the model load/download, not a match
curl.exe -X POST http://127.0.0.1:8000/faces/recognize -F "file=@C:\path\to\any\photo.jpg"
# expect a JSON answer within seconds-to-a-minute the first time:
#   {"recognized":false,...} or {"recognized":true,...}  -> models are warm
# a second identical call must be fast (measured ~1 s per check-in afterwards)
```

After the first download the volume (or `DATA_DIR`) keeps the models across restarts and
rebuilds. Verify the second call is fast — if it is slow, the models were not cached where
you think they are.

---

## 8. Backup and restore the database

Two modes, pick the one matching how the backend runs.

**Docker:**

```powershell
# backup (runs inside the container, writes into the current folder)
docker compose exec backend python -c "import shutil; shutil.copy('/app/data/dbdata/attendance.db', '/app/data/dbdata/attendance.backup.db')"
docker compose cp backend:/app/data/dbdata/attendance.backup.db ./attendance-backup.db

# restore
docker compose cp ./attendance-backup.db backend:/app/data/dbdata/attendance.db
docker compose restart backend
```

**Native (recommended for the demo machine):**

```powershell
# backup: stop the server first (SQLite locks the file on Windows), then copy
Copy-Item backend\attendance.db "backups\attendance-$(Get-Date -Format yyyyMMdd-HHmm).db"

# restore: copy the backup over the live file and start the server again
Copy-Item backups\attendance-20270118-0900.db backend\attendance.db -Force
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**Measured recovery time (2026-11-02, seeded DB, this repo):** a corrupted database makes
startup fail immediately (`sqlite3.DatabaseError: file is not a database`, connection
refused). Copying the backup over it and starting the server reached
`{"status":"ok","database":"ok"}` in **6.2 s** — 5.9 s of that is the interpreter +
FastAPI startup, 0.3 s the file copy. So the honest demo-day number is **under 10 s plus
the time to notice**, provided a backup file exists. Make a backup right before the demo
and keep it on a USB stick/phone as well.

---

## 9. Troubleshooting

| Symptom | Fix |
|---|---|
| `failed to fetch anonymous token` / registry timeout | configure mirrors (§2) |
| `port is already allocated` | another process uses 8000; set `BACKEND_PORT=8001` or stop the local server |
| Dashboard opens but all data empty | run `python backend\scripts\seed_demo.py --students 5` (§11) |
| `/wifi/scan` returns Docker-internal addresses | expected in Docker Desktop; see §6 |
| `/wifi/scan` shows a /24 although the network is wider | expected: only one /24 is swept; set `WI_FI_SUBNET` to the classroom /24 |
| `/wifi/scan` returns `devices: []` on Linux as a normal user | raw sockets are unavailable; the scanner falls back to ping + `ip neigh` automatically (log line `scapy ARP scan failed`) |
| Server refuses connections and the log ends with `sqlite3.DatabaseError: file is not a database` | the DB file is damaged: restore a backup (§8) |
| Phone cannot connect | firewall port 8000; same Wi-Fi; use the machine's LAN IP, or USB `adb reverse` for a phone |

---

## 10. Verified on 2026-10-25 — actual results

Setup used for the verification: Windows 10.0.26200, Docker Desktop 28.4.0 (WSL2),
registry mirrors `docker.m.daocloud.io` + `dockerproxy.com`, host port `8001`.

| Check | Result |
|---|---|
| Build (after base image + torch CPU cached) | ✅ ~4 min; image **3.4 GB** |
| Base image `python:3.11-slim` via mirror | ✅ 2.4 MB/s–16 MB/s downloads |
| Container state | ✅ `Up`, `0.0.0.0:8001->8000/tcp` |
| `GET /health` | ✅ `{"status":"ok","database":"ok"}` |
| `TIMEZONE` env applied | ✅ `Asia/Shanghai` (container timestamps in CST) |
| `DATABASE_PATH` | ✅ `/app/data/dbdata/attendance.db` |
| YOLO weights baked into the image | ✅ `/app/data/models/yolov8m-face.pt` (52 MB) **visible at runtime** — the `/app/data/dbdata` volume layout fixed the shadowing problem |
| Persistence across `docker compose restart` | ✅ student `DEPLOY01` still present afterwards |
| Smoke test against the container | ✅ **15/15 checks passed** |
| Smoke test against the native dev server | ✅ **15/15 checks passed** |
| `GET /wifi/scan` **inside the container** | ⚠️ `{"devices":[],"subnet":"192.168.1.0/24","count":0,"bssid":null}` — confirms §6: the container cannot see the host's Wi-Fi clients |

**Conclusion for the team:** Docker is the right vehicle for the dashboard/API demo and for
seeded offline data, but the **Wi-Fi presence feature must run natively** (or on a Linux
host with `network_mode: host`) for the classroom pilot.

---

## 11. Demo data (offline fallback)

`backend/scripts/seed_demo.py` writes demo students, a class that is **open right now**
(start = now − 5 min, end = now + 55 min, never crossing midnight) and sample attendance
rows directly into the SQLite file. Run it with the server **stopped** on Windows.

```powershell
# clean slate, 5 demo students, dashboard immediately has something to show
python backend\scripts\seed_demo.py --reset --students 5

# more students (max 99), or a different database file
python backend\scripts\seed_demo.py --students 8 --db C:\demo\attendance.db
```

What it produces (measured 2026-11-02, `TIMEZONE=Asia/Shanghai`):

| Item | Result |
|---|---|
| Students | `Demo Student 1..N`, NIM `DEMO0001..`, MAC `02:00:00:00:00:01..` |
| Schedule | `Demo Class`, today's weekday, active window around "now" |
| Attendance | 5 rows for 3+ students: two complete `verified` pairs and one `face_only` start |
| Dashboard | `/attendance/today` and `/attendance/export/csv` serve the seeded rows immediately |

`--reset` also deletes the embedding pickles and stored face crops **of the deleted
students only** (so a reused student id cannot match an old face) and restarts the id
sequences at 1. Real enrolled profiles are left untouched.

The fake MACs mean the Wi-Fi prompt stays `false` for demo students — correct, because no
phone has that address. For a live Wi-Fi demo register a real phone MAC with
`PUT /students/{id}/mac`, or demo with the real students.

---

## 12. Verified on 2026-11-02 — native run (G1 evidence)

Setup: Linux 6.x laptop, Python 3.12.3 in `venv`, `python -m uvicorn backend.main:app
--host 0.0.0.0 --port 8011`, isolated `DATABASE_PATH`, `TIMEZONE=Asia/Shanghai`,
`FACE_SIMILARITY_THRESHOLD=0.5`, `YOLO_IMG_SIZE=640`, `CORS_ORIGINS=http://127.0.0.1:8011`.

| Check | Result |
|---|---|
| Cold start → `/health` ok | ✅ **5.9 s** |
| `TIMEZONE` applied | ✅ schedule `created_at` 17:46:30 (CST) vs SQLite UTC 09:46:30 → +8 h |
| Data persists across stop/start | ✅ student `G1CHECK01` returned after restart |
| `/wifi/scan` native | ✅ 1 device (gateway `10.163.255.254`), BSSID `50:98:b8:c9:2b:e2` |
| Subnet auto-detect on a /17 interface | ✅ interface `10.163.128.0/17` → sweeps and reports `10.163.216.0/24` |
| Smoke test | ✅ **14/14** (the 15th check is Windows-only: it reads the host MAC with `getmac`) |
| `seed_demo.py --reset` | ✅ 5 students, 1 open class, 5 attendance rows, served by the dashboard |
| Recovery from a corrupted DB | ✅ restore + start = **6.2 s** to healthy (see §8) |
| Docker in this environment | ⏸ not measured — no Docker daemon on this machine; last Docker run 2026-10-25 (§10) |

G1 on the **actual demo laptop** (Windows) is still open: install, run §5b, repeat this
table there and paste the numbers into `docs/B/demo_environment.md`.


