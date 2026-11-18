# Offline Fallback — One Page (G5)

> **Purpose:** the demo must run with **no internet at all**: no Docker Hub, no model
> downloads, no campus DHCP surprises. This page is the fallback ladder. Read it on paper
> at the demo; it is also reproduced in `docs/B/demo_runbook.md`.
> **Owner:** B · **Gate:** G5 (2026-11-22)

---

## 0. The three things that need internet (prepare them the day before)

| Needs internet | Do this once, while online | Proof it is local afterwards |
|---|---|---|
| YOLO weights — **52,028,566 bytes** (≈ 49.6 MiB) | download to `backend/data/models/yolov8m-face.pt` | `Get-Item backend\data\models\yolov8m-face.pt` shows the size; `/faces/recognize` does not hit the network |
| InsightFace `buffalo_l` — **341,268,726 bytes unpacked**, 5 `.onnx` files | one warm-up `/faces/recognize` call; InsightFace downloads and caches it itself | `%USERPROFILE%\.insightface\models\buffalo_l` exists; a second call works with the Wi-Fi adapter disabled |
| Python packages / APK | `pip install -r backend/requirements.txt` + `pip install dill==0.3.8` (see the note below), APK already installed on the phone | `python -m uvicorn` starts, app opens |

Nothing else in the backend calls the internet. `TIMEZONE` needs the `tzdata` package
(installed by requirements), not a network lookup.

**The cache path is not `DATA_DIR`.** `insightface==2.1` hard-codes `~/.insightface`, so the
models live in `%USERPROFILE%\.insightface\models\buffalo_l` on Windows
(`~/.insightface/...` on Linux) no matter what `DATA_DIR` says. Back up **that** folder, not
only `backend/data/`. Decision: D-012.

**Both models load lazily on the first face request, not at startup.** Measured on the
Windows demo laptop (2026-11-13): cold `/faces/recognize` **13.4 s**, the same call warm
**1.5–1.6 s**, and the deliberate warm-up call the server makes for itself **8.3 s**. That is
why the pre-flight in §5 warms them before the audience arrives — a cold first selfie on
stage would look like a hang.

**`dill` is not in `backend/requirements.txt` yet** (A-owned file). Loading
`yolov8m-face.pt` fails with `ModuleNotFoundError: No module named 'dill'` without it, so the
install step above is two commands until A adds `dill==0.3.8` (hardening item 7).

---

## 1. Fallback ladder (use the first rung that works)

| Rung | Situation on stage | What you do | Time to switch |
|---|---|---|---|
| **1. Native backend, hotspot, no internet** | normal demo | phone + laptop on the same hotspot, server URL = laptop hotspot IP or `adb reverse` | — |
| **2. Native backend, Wi-Fi unusable** | `/wifi/scan` sees no phones, check-ins become `face_only` | keep going: `face_only` **is** the documented behaviour when the network isolates clients. Say the sentence in §4 and show the dashboard | 0 s |
| **3. Recognition fails** (no model, camera trouble) | check-in returns an error | switch to seeded data: `python backend/scripts/seed_demo.py --reset --students 5` (measured **0.7 s**), show dashboard + CSV export | ~10 s |
| **4. Backend will not start** | DB damaged, port taken, crash | `docs/B/deployment_guide.md` §8 (restore backup) — measured **13.9 s** from copy to healthy on the Windows laptop (6.2 s on the Linux one); if no backup, `seed_demo.py --reset` (measured **0.7 s**, 5 students) | < 1 min |
| **5. Laptop unusable** | hardware failure | D plays the 30–60 s backup video; slides already contain the screenshots | 0 s |

Every rung was chosen so the **claim** of the project ("three conditions, two-stage
verification") stays honest: we never fake a `verified` row during a live demo.

**Rung 4 trap, measured 2026-11-13:** with a corrupt `attendance.db` the server logs
`sqlite3.DatabaseError: file is not a database` and `Application startup failed. Exiting.`,
but the **process keeps running and never binds port 8000** — `/health` just times out. Do not
wait for it to die and do not assume port 8000 is free: kill that window first, then restore.

---

## 2. Hotspot setup (no internet required)

1. Windows → Settings → Network & Internet → **Mobile hotspot** → share the Wi-Fi adapter,
   band 2.4 GHz, name `Attendance-Demo`, password given in the runbook.
2. Turn **off** "Private network / client isolation" if the hotspot offers it (Windows
   Mobile Hotspot does not isolate clients; a phone hotspot may).
3. Laptop IP on the hotspot is printed by `ipconfig` (usually `192.168.137.1`).
4. Phone → join `Attendance-Demo`.
5. Verify the scanner sees the phone **before** the demo:

```powershell
curl.exe http://127.0.0.1:8000/wifi/scan
# the phone's MAC must appear; the phone must have "Private/random MAC" turned OFF
# for this network, otherwise the MAC changes on every join and the check fails
```

> **Measured so far:** the hotspot rung itself is **not measured yet** (no second phone +
> hotspot session on this machine). The campus-network numbers (only the gateway visible)
> are in `docs/B/network_validation.md` — Linux §2 and Windows §8. Record the hotspot result
> there when it is run: devices found, seconds per scan, whether the phone MAC stays stable
> across rejoins.
>
> On Windows the scanner does **not** need Npcap: it ping-sweeps and reads the ARP table
> (`arp -a`), which the 2026-11-13 run confirmed on the campus LAN. A fresh 254-host sweep
> measured **4.3 s**; a repeat within 10 s is cached at **29 ms**. If a scan takes longer
> than ~10 s on stage, the sweep is touching more than one /24 — check `"subnet"` in the
> response.

---

## 3. Phone ↔ laptop connectivity, in order of preference

| Option | When | Notes |
|---|---|---|
| Same hotspot / same LAN, `http://<laptop-ip>:8000` (on the Windows hotspot that is `http://192.168.137.1:8000`, the app's built-in default) | demo room, network we control | needs firewall port 8000 open |
| `adb reverse tcp:8000 tcp:8000` + app URL `http://127.0.0.1:8000` | campus Wi-Fi blocks phone→PC (already observed) | proven path from C's device testing; requires USB debugging |
| Phone hotspot + laptop as client | no other network | laptop IP differs each time; check with `ipconfig` |

The app side (server URL, `adb reverse`) is C's checklist; B only guarantees the backend
answers on port 8000.

---

## 4. The sentence to say when the Wi-Fi check fails live

> "The face check passed; the Wi-Fi check did not, because this network isolates clients
> so the server cannot see the phone on the LAN. That is the documented `face_only` state —
> the system records that it could not verify Wi-Fi instead of pretending it did. On a
> flat classroom network the same check returns `verified`; we measured that on
> 25 October."

Why this is honest, not an excuse: `face_only` is a real row in the database with
`wifi_verified = 0` (`docs/B/network_validation.md` §3 F2, `docs/PROJECT_CONTEXT.md` §2).

> **Only valid with `REQUIRE_CLASSROOM_WIFI=false`.** With strict mode on (the demo setting,
> D-006) the same failure is refused before the camera opens, so no `face_only` row exists.
> In that case say instead: *"The system refused the check-in because the phone is not
> visible on the classroom network — that is the gate working, not a failure. We can repeat
> the same check on a flat network to show the accepted path."*

### 4b. If the server cannot read its own BSSID

A second, different reason for `face_only`: the laptop cannot tell which AP it is on, so a
pinned `schedules.ap_bssid` can never match. Since 2026-11-03 this is **visible**, not
silent — the server log shows one line:

```
WARNING services.wifi_scanner: Cannot read the current BSSID: none of 'iw', 'nmcli' or
'iwconfig' is available on this Linux host. ... Install 'iw' (package: iw) or set the
schedule ap_bssid to NULL.
```

What to do, in order:

1. `curl.exe http://127.0.0.1:8000/wifi/scan` — if `"bssid": null`, the check cannot pass.
2. Quick fix on stage: set that schedule's `ap_bssid` to NULL (`PUT /schedules/{id}`), which
   means "do not pin the AP" — the Wi-Fi presence check still runs, only the room check is
   skipped. Say that out loud, do not hide it.
3. Do **not** hand-type a BSSID you copied from a phone. A wrong pin is worse than no pin.

Measured: on the Linux laptop reading the BSSID works through `nmcli` even though `iw` is not
installed (`docs/B/network_validation.md` §7); on the Windows laptop it works through
`netsh wlan show interfaces` (`78:2c:29:09:e2:f2`, §8). macOS has no probe at all
(D-010), so there `ap_bssid` must be NULL.

---

## 5. Pre-demo checklist (10 minutes, offline)

| # | Check | Command / action | Expected |
|---|---|---|---|
| 1 | Backend starts | `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000` | `Uvicorn running on http://0.0.0.0:8000` (cold start measured **17.3 s**) |
| 2 | Health | `curl.exe http://127.0.0.1:8000/health` | `{"status":"ok","database":"ok"}` |
| 3 | Models on disk | the two `Get-Item` checks below, with the network already off | both sizes match, 5 `.onnx` files present |
| 4 | Models warm | `curl.exe -F "file=@<a phone photo>" http://127.0.0.1:8000/faces/recognize` | answer in **13.4 s** the first time, **1.5 s** the second; no download log |
| 5 | Data present | `curl.exe http://127.0.0.1:8000/attendance/today` | rows (seeded or real) |
| 6 | Dashboard | open `/dashboard` | table + status colours render |
| 7 | CSV | `/attendance/export/csv` | downloads, header `id,timestamp,...` |
| 8 | Wi-Fi | `/wifi/scan` | phone MAC visible (or the §4 sentence ready) **and** `"bssid"` is not null (§4b) |
| 9 | Backup | copy `attendance.db` to `backups\` + USB | file exists (40 KB copy measured **1.2 ms**) |
| 10 | Clock | compare `/attendance/today` timestamps to the wall clock | same timezone (`Asia/Shanghai`); a wrong `TIMEZONE` shifts them by 8 h |
| 11 | Strict mode agreed | is `REQUIRE_CLASSROOM_WIFI` `true` or `false`? | decided **before** the first check-in; say which on stage |

The model pre-flight (step 3), offline, in one block:

```powershell
Get-Item backend\data\models\yolov8m-face.pt | Select-Object Length   # 52028566
Get-ChildItem "$env:USERPROFILE\.insightface\models\buffalo_l"        # 5 .onnx files
Get-ChildItem "$env:USERPROFILE\.insightface\models\buffalo_l" | Measure-Object Length -Sum
# Sum ≈ 341268726
```

If either is missing, do not improvise on stage: the face path is rung 3 (§1), seeded data
plus the dashboard. A missing `.pt` fails loudly at check-in
(`FileNotFoundError: YOLOv8-face model not found at ...`); a missing `buffalo_l` only fails
once the network is gone, which is why step 3 exists.

Print this page. Do not rely on reading it from the laptop that is running the demo.
