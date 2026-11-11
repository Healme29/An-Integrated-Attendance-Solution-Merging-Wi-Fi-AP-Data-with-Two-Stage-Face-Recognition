# Offline Fallback — One Page (G5)

> **Purpose:** the demo must run with **no internet at all**: no Docker Hub, no model
> downloads, no campus DHCP surprises. This page is the fallback ladder. Read it on paper
> at the demo; it is also reproduced in `docs/B/demo_runbook.md`.
> **Owner:** B · **Gate:** G5 (2026-11-22)

---

## 0. The three things that need internet (prepare them the day before)

| Needs internet | Do this once, while online | Proof it is local afterwards |
|---|---|---|
| YOLO weights (52 MB) | `backend/data/models/yolov8m-face.pt` exists | `ls -lh` shows the file; `/faces/recognize` does not hit the network |
| InsightFace `buffalo_l` (~330 MB) | one warm-up `/faces/recognize` call, models cached in `DATA_DIR` | second call works with the Wi-Fi adapter disabled |
| Python packages / APK | `pip install -r backend/requirements.txt`, APK already installed on the phone | `python -m uvicorn` starts, app opens |

Nothing else in the backend calls the internet. `TIMEZONE` needs the `tzdata` package
(installed by requirements), not a network lookup.

---

## 1. Fallback ladder (use the first rung that works)

| Rung | Situation on stage | What you do | Time to switch |
|---|---|---|---|
| **1. Native backend, hotspot, no internet** | normal demo | phone + laptop on the same hotspot, server URL = laptop hotspot IP or `adb reverse` | — |
| **2. Native backend, Wi-Fi unusable** | `/wifi/scan` sees no phones, check-ins become `face_only` | keep going: `face_only` **is** the documented behaviour when the network isolates clients. Say the sentence in §4 and show the dashboard | 0 s |
| **3. Recognition fails** (no model, camera trouble) | check-in returns an error | switch to seeded data: `python backend/scripts/seed_demo.py --reset --students 5`, show dashboard + CSV export | ~10 s |
| **4. Backend will not start** | DB damaged, port taken, crash | `docs/B/deployment_guide.md` §8 (restore backup) — measured **6.2 s** to healthy; if no backup, `seed_demo.py --reset` | < 1 min |
| **5. Laptop unusable** | hardware failure | D plays the 30–60 s backup video; slides already contain the screenshots | 0 s |

Every rung was chosen so the **claim** of the project ("three conditions, two-stage
verification") stays honest: we never fake a `verified` row during a live demo.

---

## 2. Hotspot setup (no internet required)

> **Approved by the lecturer (2026-11-11, D-013):** demonstrating on a network we control is
> acceptable ("Either should be fine"). That is what this section builds, and it is why the
> room check is exact here: one AP, one room.

1. Windows → Settings → Network & Internet → **Mobile hotspot** → share the Wi-Fi adapter,
   band 2.4 GHz, name `Attendance-Demo`, password given in the runbook.
2. Turn **off** "Private network / client isolation" if the hotspot offers it (Windows
   Mobile Hotspot does not isolate clients; a phone hotspot may).
3. Laptop IP on the hotspot is printed by `ipconfig` (usually `192.168.137.1`).
4. Phone → join `Attendance-Demo`.
5. Verify the scanner sees the phone **before** the demo:

```powershell
curl http://127.0.0.1:8000/wifi/scan
# the phone's MAC must appear; the phone must have "Private/random MAC" turned OFF
# for this network, otherwise the MAC changes on every join and the check fails
```

> **Measured so far:** the hotspot rung itself is **not measured yet** (no second phone +
> hotspot session on this machine). The campus-network numbers (only the gateway visible)
> are in `docs/B/network_validation.md`. Record the hotspot result there when it is run:
> devices found, seconds per scan, whether the phone MAC stays stable across rejoins.

---

## 3. Phone ↔ laptop connectivity, in order of preference

| Option | When | Notes |
|---|---|---|
| Same hotspot / same LAN, `http://<laptop-ip>:8000` | demo room, network we control | needs firewall port 8000 open |
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

1. `curl http://127.0.0.1:8000/wifi/scan` — if `"bssid": null`, the check cannot pass.
2. Quick fix on stage: set that schedule's `ap_bssid` to NULL (`PUT /schedules/{id}`), which
   means "do not pin the AP" — the Wi-Fi presence check still runs, only the room check is
   skipped. Say that out loud, do not hide it.
3. Do **not** hand-type a BSSID you copied from a phone. A wrong pin is worse than no pin.

Measured on this laptop: reading the BSSID works through `nmcli` even though `iw` is not
installed (`docs/B/network_validation.md` §7).

---

## 4c. The sentence to say when the Wi-Fi check **passes**

The failure case in §4 is one half. The success case has its own approved wording, because
saying more than this is overclaiming:

> "The check-in was made within the coverage area of the scheduled AP: the student's device
> was reachable on the classroom network, and this machine was associated with the AP pinned
> to the room. We do not claim to know which AP a phone is attached to, and on a shared
> campus network that is the limit of what the Wi-Fi condition proves."

The lecturer accepted this claim on 2026-11-11 provided the limitation is stated honestly,
and noted that in practice an AP covers one classroom and cannot hold all the students
anyway (`DECISIONS.md` D-013, `threat_model.md` §3.1). On the demo network the claim is
stronger than on campus — one AP, one room — but the sentence stays the same; the report
explains why.

Do **not** say "the system proves the student was in the room" or "the system cannot be
gamed". Both are false and both are contradicted by `threat_model.md` T1–T6.

---

## 5. Pre-demo checklist (10 minutes, offline)

| # | Check | Command / action | Expected |
|---|---|---|---|
| 1 | Backend starts | `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000` | `Uvicorn running on http://0.0.0.0:8000` |
| 2 | Health | `curl http://127.0.0.1:8000/health` | `{"status":"ok","database":"ok"}` |
| 3 | Models local | `/faces/recognize` with any photo | answer arrives in seconds, no download log |
| 4 | Data present | `curl http://127.0.0.1:8000/attendance/today` | rows (seeded or real) |
| 5 | Dashboard | open `/dashboard` | table + status colours render |
| 6 | CSV | `/attendance/export/csv` | downloads, header `id,timestamp,...` |
| 7 | Wi-Fi | `/wifi/scan` | phone MAC visible (or the §4 sentence ready) **and** `"bssid"` is not null (§4b) |
| 8 | Backup | copy `attendance.db` to `backups\` + USB | file exists |
| 9 | Clock | compare `/attendance/today` timestamps to the wall clock | same timezone (`Asia/Shanghai`) |
| 10 | Log file | server started through `cmd /c ... > backend\server_<timestamp>.log 2>&1`; `Get-Content -Wait` in a second window | file grows on every request; shutdown ends with `Finished server process` |

Print this page. Do not rely on reading it from the laptop that is running the demo.
