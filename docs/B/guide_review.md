# Deployment Guide — Followed From Scratch (M2 stage 3)

> **Why:** the guide must work for someone who has never deployed anything. I followed it
> myself, in a clean copy of the repository, and wrote down every step that failed or was
> ambiguous. Gate: none (feeds G12–G16).
> **Date:** 2026-11-02 (Linux laptop, clean `git clone` into `/tmp`, native path §5b) and
> **2026-11-13** (Windows 11 demo laptop, fresh `.venv`, same §5b path — see §5).
> **Executed by:** B · **Not yet executed by:** anyone else (§4 item 3).

---

## 1. What was executed
| Guide step | Executed? | Result |
|---|---|---|
| §5b step 0 — create venv | ✅ `python3 -m venv .venv` / `python -m venv .venv` | worked on both machines |
| §5b step 0 — `pip install -r backend/requirements.txt` | ✅ **run 2026-11-13 on the Windows laptop, timed** | **577 s** (12:09:36 → 12:19:13, exit 0) from a fresh Python 3.12.10 venv; log `.venv/pip_install.log`. Then a **second** command is needed: `pip install dill==0.3.8` (hardening item 7) |
| §5b step 1 — download YOLO weights into `backend/data/models/` | ❌ **failed as written** | `backend/data/models/` does not exist in a fresh clone → download cannot create the folder. Fixed in the guide with `New-Item -ItemType Directory -Force` |
| §5b step 2 — set env values | ✅ | values accepted; verified via the timezone behaviour |
| §5b step 3 — start `python -m uvicorn backend.main:app` | ✅ | Linux ~6 s, **Windows 17.3 s** (restart 25.3 s); DB created automatically |
| §5b step 4 — health / `/wifi/scan` / smoke test | ✅ | `{"status":"ok"...}`, scan found the gateway + BSSID, smoke **15/15** on Windows (12/15 before `dill`) |
| §11 — `seed_demo.py --reset --students 5` | ✅ | 5 students, 1 open class, 5 attendance rows; dashboard served them; **0.7 s** on Windows |
| §3, §10 — Docker build/run | ⏸ not executed here | no Docker daemon on either machine; last real run was 2026-10-25 (guide §10). Optional per D-002 |
| §8 — backup/restore (native) | ✅ replace + restart | Linux **6.2 s**, Windows **13.9 s** to healthy (guide §8) |

## 2. Steps that were wrong or confusing (all fixed in the guide)
| # | Step | Problem | Fix |
|---|---|---|---|
| 1 | §5b step 1 | `curl.exe -o backend\data\models\...` fails: the folder does not exist after clone | create the folder first; sanity-check the file size |
| 2 | §5–§8 shell examples | mixed cmd/PowerShell syntax: `curl` is an alias for `Invoke-WebRequest` in PowerShell, and `-d "{...}"` quoting breaks | all examples now PowerShell-safe (`curl.exe`, `Invoke-RestMethod`, single-quoted bodies) |
| 3 | §7 model warm-up | "upload any photo" with no command | exact `curl.exe -F` call plus what the answer looks like |
| 4 | §5 | after changing `.env`, nothing said how to stop/start or that `restart` does not reload env | added `docker compose stop/up -d` and the note |
| 5 | (missing) | no way to open the firewall port or find the machine IP for the phone | added the `New-NetFirewallRule` and `Get-NetIPAddress` commands |
| 6 | (missing) | readers may think the missing `attendance.db` is an error | explicit note: first start creates it |
| 7 | §5b step 0 | **2026-11-13:** a fresh install from `requirements.txt` was not enough — the first `/faces/recognize` returned `500 ModuleNotFoundError: No module named 'dill'` | added `pip install dill==0.3.8` to step 0, with the exact error text in §9 troubleshooting. Still A's call to add it to `requirements.txt` |
| 8 | §7 model paths | the guide implied `buffalo_l` lands in `DATA_DIR`; `insightface 2.1` hard-codes `~/.insightface`, so on Windows it is `%USERPROFILE%\.insightface` | corrected; the backup instruction now names that folder explicitly (D-012) |
| 9 | §8 restore | nothing said what a corrupt DB looks like when it fails | added: startup logs `sqlite3.DatabaseError: file is not a database`, the **process stays alive and never binds the port**, so it must be killed before restoring |

## 3. What a non-technical reader still needs told (content, not commands)
- The **run mode matters**: native for a Wi-Fi demo, Docker only for dashboard-only
  (decision D-002). The guide now says this at the top (§0) and in §5b.
- The **timezone** is a demo-critical setting, not a nicety — a wrong value produced real
  403s during C's device testing.
- Keep a **backup copy** of `attendance.db` on a USB stick; restoring is measured at ~6 s.

## 4. Remaining gaps before this gate can be called passed
1. ~~Time the real `pip install -r backend/requirements.txt` on the demo laptop.~~ ✅ Done
   2026-11-13: **577 s**, fresh Python 3.12 venv, exit 0. The remaining half is not a timing
   but an ownership issue: `dill==0.3.8` still has to be added to `backend/requirements.txt`
   by A, or every fresh install ends in a `500` on the first face call.
2. Run §3/§10 (Docker) once on the demo laptop **if** Docker is kept installed. It is
   optional (D-002) and still not executed; `not measured yet`.
3. Have **someone else** (D, or a person outside the team) follow the guide while B only
   watches; record their stumbles in §6. Until that happens the claim "followed by
   another person without help" is **not earned** — the DoD for this stage requires it.

---

## 5. Windows 11 run — 2026-11-13 (fresh venv, native path)

Same clean-copy procedure, different machine: Windows 11 `10.0.22621`, Python 3.12.10,
native `uvicorn`, no Docker. Raw output: `docs/B/evidence/2026-11-13-windows/`.

| Step | Result | Difference from Linux |
|---|---|---|
| Python version | 3.12.10 required | **3.13 cannot build the pinned wheels** — corrected in guide §5b |
| `pip install -r ...` | **577 s**, exit 0 | first real end-to-end timing; Linux never completed it |
| extra install | `dill==0.3.8` | **not in requirements** → first face call `500` (guide §9) |
| cold start → healthy | **17.3 s**; restart **25.3 s** | ~3× Linux (5.9 s); dominated by `torch` import, still inside T−30 |
| `/health`, `/`, `/dashboard` | 5.4 / 1.7 / 6.2 ms | same order of magnitude |
| `/wifi/scan` | **4,281 ms** fresh, **29 ms** cached | no Npcap needed; `netsh` gives the BSSID |
| `seed_demo.py --reset --students 5` | **0.7 s**, 5 students, 5 rows, CSV 6 lines | identical |
| backup / restore | **1.2 ms** / **13.9 s** | restore is ~2× Linux; still under the 1-minute rung |
| smoke test | **15/15**, 10.4 s | was 12/15 until `dill` was installed |
| corrupt DB | process stays alive, never binds :8000 | same failure, now documented in guide §8 |

The install, start and scan numbers above are the same figures that appear in
`demo_environment.md` §7 and `network_validation.md` §8 — one run, one set of numbers, no
second source of truth.
