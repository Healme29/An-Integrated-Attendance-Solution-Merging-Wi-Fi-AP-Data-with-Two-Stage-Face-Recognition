# Deployment Guide — Followed From Scratch (M2 stage 3)

> **Why:** the guide must work for someone who has never deployed anything. I followed it
> myself, in a clean copy of the repository, and wrote down every step that failed or was
> ambiguous. Gate: none (feeds G12–G16).
> **Date:** 2026-11-02 · **Executed by:** B · **Environment:** Linux laptop + a clean
> `git clone` into `/tmp`, native run path (§5b).

---

## 1. What was executed
| Guide step | Executed? | Result |
|---|---|---|
| §5b step 0 — create venv | ✅ `python3 -m venv .venv` | worked |
| §5b step 0 — `pip install -r backend/requirements.txt` | ⏸ **not executed** | multi-GB torch/ultralytics download; the existing repo `venv` already has the exact pinned versions, so the commands themselves are unchanged. **Still unproven from scratch — must be timed once on the demo laptop** |
| §5b step 1 — download YOLO weights into `backend/data/models/` | ❌ **failed as written** | `backend/data/models/` does not exist in a fresh clone → download cannot create the folder. Fixed in the guide with `New-Item -ItemType Directory -Force` |
| §5b step 2 — set env values | ✅ | values accepted; verified via the timezone behaviour |
| §5b step 3 — start `python -m uvicorn backend.main:app` | ✅ | healthy in ~6 s, DB created automatically |
| §5b step 4 — health / `/wifi/scan` / smoke test | ✅ | `{"status":"ok"...}`, scan found the gateway + BSSID, smoke **14/14** |
| §11 — `seed_demo.py --reset --students 5` | ✅ | 5 students, 1 open class, 5 attendance rows; dashboard served them |
| §3, §10 — Docker build/run | ⏸ not executed here | no Docker daemon on this machine; last real run was 2026-10-25 (guide §10) |
| §8 — backup/restore (native) | ✅ replace + restart | healthy in **6.2 s** (guide §8) |

## 2. Steps that were wrong or confusing (all fixed in the guide)
| # | Step | Problem | Fix |
|---|---|---|---|
| 1 | §5b step 1 | `curl.exe -o backend\data\models\...` fails: the folder does not exist after clone | create the folder first; sanity-check the file size |
| 2 | §5–§8 shell examples | mixed cmd/PowerShell syntax: `curl` is an alias for `Invoke-WebRequest` in PowerShell, and `-d "{...}"` quoting breaks | all examples now PowerShell-safe (`curl.exe`, `Invoke-RestMethod`, single-quoted bodies) |
| 3 | §7 model warm-up | "upload any photo" with no command | exact `curl.exe -F` call plus what the answer looks like |
| 4 | §5 | after changing `.env`, nothing said how to stop/start or that `restart` does not reload env | added `docker compose stop/up -d` and the note |
| 5 | (missing) | no way to open the firewall port or find the machine IP for the phone | added the `New-NetFirewallRule` and `Get-NetIPAddress` commands |
| 6 | (missing) | readers may think the missing `attendance.db` is an error | explicit note: first start creates it |

## 3. What a non-technical reader still needs told (content, not commands)
- The **run mode matters**: native for a Wi-Fi demo, Docker only for dashboard-only
  (decision D-002). The guide now says this at the top (§0) and in §5b.
- The **timezone** is a demo-critical setting, not a nicety — a wrong value produced real
  403s during C's device testing.
- Keep a **backup copy** of `attendance.db` on a USB stick; restoring is measured at ~6 s.

## 4. Remaining gaps before this gate can be called passed
1. Time the real `pip install -r backend/requirements.txt` on the demo laptop (the one step
   never executed end to end here).
2. Run §3/§10 (Docker) once more on the demo laptop if Docker is kept installed.
3. Have **someone else** (D, or a person outside the team) follow the guide while B only
   watches; record their stumbles in this file. Until that happens the claim "followed by
   another person without help" is **not earned** — the DoD for this stage requires it.
