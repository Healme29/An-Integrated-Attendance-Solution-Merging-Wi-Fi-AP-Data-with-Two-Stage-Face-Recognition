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

```powershell
# 1. health
curl http://127.0.0.1:8000/health
# {"status":"ok","database":"ok"}

# 2. teacher dashboard
start http://127.0.0.1:8000/dashboard

# 3. API docs
start http://127.0.0.1:8000/docs

# 4. persistence: create a student, restart, confirm it is still there
curl -X POST http://127.0.0.1:8000/students/ -H "Content-Type: application/json" -d "{\"name\":\"Deploy Check\",\"nim\":\"DEPLOY01\",\"mac_address\":null}"
docker compose restart backend
curl "http://127.0.0.1:8000/students/?nim=DEPLOY01"
# the student must still be returned -> the named volume works

# 5. smoke test (host Python, no face photo needed)
python backend/scripts/smoke_test.py --base-url http://127.0.0.1:8000
```

**Phone access over Wi-Fi:** allow port 8000 in Windows Defender Firewall when prompted,
then set the app's server URL to `http://<machine-ip>:8000`.

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
(`/app/data/dbdata/insightface`). Do one warm-up call before a live demo so the download
does not happen in front of the audience:

```powershell
# upload any photo to /faces/recognize once, wait for the download to finish
```

After the first download the volume keeps the models across restarts and rebuilds.

---

## 8. Backup and restore the database

```powershell
# backup (runs inside the container, writes into the current folder)
docker compose exec backend python -c "import shutil; shutil.copy('/app/data/dbdata/attendance.db', '/app/data/dbdata/attendance.backup.db')"
docker compose cp backend:/app/data/dbdata/attendance.backup.db ./attendance-backup.db

# restore
docker compose cp ./attendance-backup.db backend:/app/data/dbdata/attendance.db
docker compose restart backend
```

---

## 9. Troubleshooting

| Symptom | Fix |
|---|---|
| `failed to fetch anonymous token` / registry timeout | configure mirrors (§2) |
| `port is already allocated` | another process uses 8000; set `BACKEND_PORT=8001` or stop the local server |
| Dashboard opens but all data empty | fresh volume — seed demo data (script planned under `backend/scripts/`) |
| `/wifi/scan` returns Docker-internal addresses | expected in Docker Desktop; see §6 |
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

