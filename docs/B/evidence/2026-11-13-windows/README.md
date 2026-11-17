# Measured evidence — Windows 11 laptop, 2026-11-13

Raw console output from the runs referenced by `docs/B/demo_environment.md` §7,
`docs/B/network_validation.md` §8, `docs/B/hardening_checklist.md`,
`docs/B/guide_review.md` §5, `docs/B/review_response.md` §4 and the pre-flight in
`docs/B/offline_fallback.md` §5. Nothing here is a prediction; each number was printed by
the scripts in `scripts/`.

## Machine and environment

| Item | Value |
|---|---|
| OS | Windows 11 `10.0.22621` (AMD64, Intel64 Family 6 Model 140) |
| Python | 3.12.10 in a project-local `.venv` (system Python 3.13.5 is unusable, see D-012) |
| Time zone | China Standard Time (`Asia/Shanghai`, UTC+8) |
| Network | campus Wi-Fi, interface `10.163.158.239/17`, gateway `10.163.255.254`, AP BSSID `78:2c:29:09:e2:f2` |
| Server | native `uvicorn backend.main:app`, isolated `DATABASE_PATH`/`DATA_DIR` under `%TEMP%` |
| Test suite | `209 passed` in 38.71 s |
| Install | `pip install -r backend/requirements.txt` = **577 s** (12:09:36 → 12:19:13), Tsinghua mirror |

## Files

| File | Produced by | Contents |
|---|---|---|
| `measurements-g1.txt` | `scripts/measure.py` | cold start, health/dashboard latency, TIMEZONE, `/wifi/scan`, restart persistence, smoke (before the `dill` fix), seed, backup |
| `measurements-hardening.txt` | `scripts/measure2.py` | recognition error paths before the fix, upload-cap behaviour, 24-way parallel writes/reads, clean shutdown, backup/restore, corrupt-DB startup |
| `measurements-facepath.txt` | `scripts/measure3.py` | YOLO cold load and warm latency, enroll/check-in without a face, 11 MB uploads, shutdown, log scan |
| `measurements-smoke.txt` | `scripts/smoke_check.py` | full smoke test after the `dill` fix: **15/15** |
| `measurements-models.txt` | `scripts/measure_arcface.py` + inline run | ArcFace/YOLO load time, RSS, model download sizes and hash |
| `measurements-corrupt-db.txt` | `scripts/probe_corrupt.py` | what happens to the process when `attendance.db` is not a SQLite file |

## How to re-run

The scripts hard-code two absolute paths (`ROOT` = this repository, `TMP` = a scratch
folder) because they must run **outside** the repository so the real `backend/attendance.db`
is never touched. Edit those two constants, then:

```powershell
.venv\Scripts\python.exe docs\B\evidence\2026-11-13-windows\scripts\measure.py
```

Each run creates its own scratch database; delete `%TEMP%\opencode\g1win` before a fresh
run. The corrupt-DB probe intentionally leaves a hanging process: kill it with
`Stop-Process -Name python` if the script is interrupted.

## What these numbers do **not** prove

- No real face photo was available on this machine (no face image was reachable from this
  network, and the repository must not contain face photos). The pipeline was exercised up
  to detection and to the "no face" exit path. ArcFace **matching** latency on a real face
  is therefore **not measured yet** (owner: A/B with a consented photo).
- No second phone was available, so the hotspot rung of the Wi-Fi check is **not measured
  yet** (`docs/B/offline_fallback.md` §2).
- Whether this laptop is the *final* demo laptop is a team decision; the numbers describe
  one physical Windows 11 laptop and must be repeated if the demo machine changes.
