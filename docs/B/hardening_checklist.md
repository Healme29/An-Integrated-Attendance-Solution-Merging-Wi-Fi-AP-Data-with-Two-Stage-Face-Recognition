# Production Hardening Checklist — backend (Task B7, started M2 stage 5)

> **Owner:** B · **Status:** first pass, 2026-11-13 · **Scope:** the FastAPI backend,
> SQLite, the Wi-Fi scanner and the deployment files.
>
> Rule for this page: **only mark ✅ when there is a test, a config line or a measured
> number that anyone can re-run.** A control that is missing is listed as ❌ with the
> concrete risk and the smallest honest mitigation. "Not needed for the pilot" is an
> acceptable decision *if it is written down*; silence is not.
>
> This is the M3 hardening backlog (due with the final report). It does not block the
> November demo: the demo runs on a network the team controls and is not exposed to the
> internet.

---

## 1. Summary

| Area | Status | Demo blocker? | Evidence / action |
|---|---|---|---|
| Upload size and file type | ✅ enforced | no | `MAX_UPLOAD_BYTES` (413), JPEG/PNG magic bytes, tests in `test_hardening.py` |
| SQL injection | ✅ parameterized | no | every value goes through `?`; one `COUNT(*)` f-string uses a static fragment only |
| Face count / identity binding | ✅ enforced | no | A's identity-binding work; tests in `test_identity_binding.py` |
| CORS | ⚠️ config, default `*` | no | demo sets one origin; a wildcard is still the default |
| Authentication / authorization | ❌ none | **no, if kept on a controlled LAN** | see §3 — bind to hotspot/LAN, firewall, never expose to the internet |
| Transport encryption (TLS) | ❌ none | no | HTTP on a private hotspot; see §4 |
| SQLite concurrency | ✅ measured, see §5 | no | 24/24 parallel writes and 24/24 reads succeeded, 0 `database is locked` |
| Backup / restore | ✅ measured | no | `deployment_guide.md` §8, `demo_environment.md` §2.7 and §7.2 |
| Dependency pinning | ⚠️ partial | no | all direct deps pinned except `insightface>=2.0`; no hashes; **`dill` missing entirely** (§9, D-012) |
| Model availability at runtime | ⚠️ fails loudly, late | **yes, if the demo laptop is not prepared** | missing `.pt` / missing `dill` → 500 on every recognition; no startup check (§7a) |
| Corrupt DB at startup | ⚠️ clear error, process lingers | no | startup aborts with `sqlite3.DatabaseError`, but the OS process stays alive (§5.1) |
| Error message leakage | ⚠️ low | no | `/health` returns the exception text on DB failure (503) |
| Rate limiting / abuse | ❌ none | no | recognition is CPU-expensive; see §6 |
| Data at rest (faces, embeddings) | ❌ unencrypted | no | pilot data only; see §7 |
| Logs and personal data | ⚠️ low | no | no image bytes logged; MAC/IP addresses are logged in `ap_logs` |
| Docker runs as root | ⚠️ not fixed | no | Docker is not on the demo critical path (D-002) |

Legend: ✅ done and tested · ⚠️ partly done / needs a decision · ❌ absent, documented

---

## 2. What is already enforced (do not regress)

Measured / re-runnable:

1. **Upload cap** — `routers/faces.py` reads at most `MAX_UPLOAD_BYTES` (default 10 MB) and
   returns **413**; test `TestEnrollHardening::test_oversized_upload_rejected`.
2. **File type** — only JPEG/PNG magic bytes; other types get **400 Unsupported image
   format**; `test_unsupported_format_rejected`. The extension is not trusted.
3. **Small-face filter** — faces smaller than `MIN_FACE_BBOX_PX` (40 px) are rejected at
   enrollment; `test_tiny_face_rejected`.
4. **Embedding cap** — at most `MAX_EMBEDDINGS_PER_STUDENT` (5) samples per student;
   `test_max_embeddings_limit`.
5. **Roster import cap** — CSV import is limited to 2 MB and must be UTF-8
   (`routers/students.py`), so a giant file cannot exhaust memory.
6. **Parameterized SQL** — every user value is bound with `?`. The only f-string is
   `f"SELECT COUNT(*) {base}"` in `routers/attendance.py`, where `base` is built from
   constant fragments and the values are still bound.
7. **Duplicate/replay protection** — one `start` and one `end` per student+schedule (409),
   plus the photo fingerprint guard (`services/photo_guard.py`).

### 2.1 Gaps found while writing this checklist (not yet fixed)

| # | Gap | Risk | Owner / file |
|---|---|---|---|
| 1 | `/faces/recognize` and `/attendance/check` call `await file.read()` **without** the `MAX_UPLOAD_BYTES` check that `/faces/enroll` has | a hostile client on the LAN can force an arbitrarily large read into RAM. **Measured 2026-11-13:** enroll rejects 11 MB with **413** in 88 ms, `recognize` accepts the same 11 MB body (**200**, 145 ms) and `check` accepts it too (**400** after decoding, 155 ms) — the cap is simply not applied | A (`routers/faces.py`, `routers/attendance.py`) |
| 2 | `/faces/enroll` writes the crop to `DATA_DIR/faces` **before** the max-embedding check | a rejected 6th enrollment leaves an orphan JPEG (no matching embedding, harmless but untidy) | A (`routers/faces.py`) |
| 3 | `save_embeddings` writes the pickle, then the DB insert runs; a crash in between leaves the two stores out of sync | the recognition path reads the pickle, so the face is usable while `faces` has one row fewer — low impact | A (`services/face_recognition.py`) |
| 4 | The YOLO checkpoint is dill-pickled but `dill` is not in `backend/requirements.txt` | a machine that installs only the requirements returns **500** on every recognition (measured on a clean Windows venv, D-012). **Fix:** add `dill==0.3.8` | A (`requirements.txt`), documented by B in guide §5b/§7 |
| 5 | Missing model file is only discovered on the first recognition | `FileNotFoundError: YOLOv8-face model not found …` becomes a **500 Internal Server Error**; an operator reads "the AI is broken" instead of "download the model" | A (`routers`/`services`) — M3: fail fast at startup or map to 503 with an actionable detail |
| 6 | On a corrupt DB, startup aborts but the **process does not exit** (still alive after 87 s; only killed manually) | an operator who restarts keeps stacking processes; the port is never bound, so it looks like "nothing is happening" | A (`models/database.py` — `aiosqlite` connection not closed on failure) |

## 3. Authentication and authorization — ❌ absent

**Risk:** anyone who can reach port 8000 can list students, read attendance, delete
students, or enroll a face. On a campus SSID that is every student on the VLAN.

**Why it is not fixed now:** the team has no token/SSO requirement in the assignment and
the demo runs on a hotspot the presenter controls. Adding auth would touch A-owned routers
and break C's already-tested APK flow two weeks before the presentation.

**Mitigation for the pilot (mandatory on the day):**

- run the hotspot with a password that is **not** printed on the public slide;
- keep the backend on the hotspot only; do not join the laptop to the campus SSID while the
  server is listening;
- if the laptop must be on campus Wi-Fi, add an inbound firewall rule limited to the
  hotspot subnet, not "any";
- after the demo, stop the server (it is not a service).

**M3 options:** (1) a single `X-API-Key` header on mutating routes (small, but the Flutter
app needs one more setting); (2) teacher login + signed session cookie for the dashboard
and API; (3) full OIDC/SSO — rejected as disproportionate for one classroom.

## 4. Transport — ❌ HTTP only

All traffic, including face images, is plain HTTP. On a WPA2 hotspot the link layer is
encrypted, but there is no server authentication.

**Mitigation for the pilot:** private hotspot, no internet exposure, no captive portal.

**M3 options:** run `uvicorn --ssl-keyfile/--ssl-certfile` with a self-signed certificate
(the app must trust it), or put the backend behind a TLS reverse proxy (Caddy/nginx). The
APK would need to trust the certificate — coordinate with C before choosing.

## 5. SQLite concurrency — ⚠️ measured, no failures observed

`models/database.py` opens a new connection per request and does not enable WAL or a busy
timeout. Concurrent writes can therefore return `database is locked`.

**Measurement (2026-11-13, Windows 11 laptop, native server, 24 parallel clients):**

| Pattern | Requests | Wall | Latency p50 / max | Status codes | `database is locked` in log |
|---|---|---|---|---|---|
| Parallel `POST /students/` (write) | 24 | **823 ms** | **337 ms** / 769 ms | **24 × 200** | **0** |
| Parallel `GET /students/` (read) | 24 | **68 ms** | **41 ms** / 50 ms | **24 × 200** | **0** |

Interpretation, honestly bounded: 24 simultaneous writers did **not** reproduce a lock at
this scale, because each request's write is short (one INSERT + commit). A classroom demo is
1–3 phones, so this is comfortably inside the measured envelope. It does **not** prove the
absence of `database is locked` under longer write transactions (bulk import, a slow disk);
no WAL and no busy timeout still means the *failure mode exists*, it just was not triggered.
Evidence: `docs/B/evidence/2026-11-13-windows/measurements-hardening.txt` §5.

**M3 options:** (1) `PRAGMA journal_mode=WAL` + `PRAGMA busy_timeout=5000` once per
connection (needs A's approval, `models/database.py` is A-owned); (2) one background writer
queue; (3) move to PostgreSQL — rejected for the pilot scale.

### 5.1 Corrupt database: loud error, but the process lingers (new, 2026-11-13)

`init_db()` raises `sqlite3.DatabaseError: file is not a database` and `uvicorn` logs
`Application startup failed. Exiting.` — correct and easy to diagnose. However the OS process
was **still alive after 87 s** and never bound the port; it had to be killed
(`measurements-corrupt-db.txt`). An operator who "just restarts" accumulates processes.

Likely cause: the `aiosqlite` connection opened in `init_db()` is not closed when the first
statement raises. `models/database.py` is A-owned, so this is recorded, not patched.
Mitigation on demo day is already in the runbook: restore the backup instead of retrying
(D-006), and the measured restore is **13.9 s** on this laptop.

## 6. Rate limiting — ❌ absent

`/faces/recognize` and `/attendance/check` run YOLO + ArcFace. A loop of requests can pin
the CPU and make the live demo fail.

**Mitigation for the pilot:** only the presenter's phone and the teacher browser are on the
hotspot; no other clients. If a demo phone misbehaves, stop it.

**M3 options:** per-IP token bucket middleware (e.g. 5 check-ins/min/student), or a global
semaphore around the face pipeline. Measure the effect on latency before enabling.

## 7. Face data at rest — ❌ unencrypted

Enrollment crops (`DATA_DIR/faces/*.jpg`), embeddings (`*.pkl` and the `faces.embedding`
BLOB) and the SQLite file are stored in clear text. That is acceptable for the pilot only
because the data belongs to consenting team members and is deleted after the demo.

**Rules that must stay true:**

- `attendance.db`, `*.pkl`, `*.pt` and face photos are git-ignored (checked in `.gitignore`);
- demo data is deleted after the presentation (`seed_demo.py --reset` removes the demo
  students and their artefacts);
- real student photos are never committed to the repo or uploaded to slides.

**M3:** OS-level disk encryption (BitLocker) on the demo laptop, plus a documented deletion
procedure. Application-level encryption of embeddings is optional and probably overkill.

## 7a. Model availability at runtime — ⚠️ fails loudly, but late

The model files are the difference between "the system works" and "every check-in is a 500",
and the failure is only discovered on the first recognition:

| Situation | Observed behaviour (2026-11-13) |
|---|---|
| `yolov8m-face.pt` missing | `500 Internal Server Error`; log: `FileNotFoundError: YOLOv8-face model not found at …` |
| checkpoint present but `dill` not installed | `500`; log: `ModuleNotFoundError: No module named 'dill'` |
| both present, first call | **13,435 ms** (cold load), then **1.5–1.6 s** |
| ArcFace `buffalo_l` missing | would download on first *detected* face — untested here (no face image), ~289 MB + 341 MB unpacked |
| memory with both models resident | **1,001 MB RSS** for the backend process |

**Mitigation now (demo day):** the runbook pre-flight checks the `.pt` size and does one
throwaway recognition. **M3:** a startup check that loads/validates the models (or a
`/health?deep=true`) so a mis-provisioned machine fails in seconds, not on stage.

---

## 8. Error messages, logs and `/docs`

- `/health` returns `{"status":"error","database":"<ExceptionType>: <message>"}` on a DB
  failure. That is useful for the operator and not sensitive on a private LAN; in a public
  deployment it should be a generic message with the detail only in the server log.
- FastAPI's `/docs` and `/redoc` are enabled. The runbook uses `/docs` only when asked.
  Disable them for a public deployment (`FastAPI(docs_url=None)`).
- Access logs include client IPs; `ap_logs` stores MAC/IP/BSSID. No image bytes are logged.

## 9. Dependencies and build

- Direct dependencies are pinned except `insightface>=2.0` (unpinned). `pip install` does
  not use a hash-verified lock file, so a compromised index could substitute a package.
- **A pinned-but-missing dependency is worse than an unpinned one:** `dill` is required to
  unpickle `yolov8m-face.pt` and is not listed at all, so a clean install returns 500 on
  every recognition (measured, D-012). Add `dill==0.3.8` to `requirements.txt`.
- Python 3.11/3.12 work; **3.13 does not** because of the pinned wheels (measured
  2026-11-13). The Dockerfile uses `python:3.11-slim`, consistent with that.
- Measured clean install: **577 s** (9 min 37 s) for the full pinned set on a Windows venv
  with a fast mirror (`docs/B/evidence/2026-11-13-windows/README.md`). The Windows resolver
  picked the **CPU** `torch` wheel (126.7 MB), not the CUDA bundle.
- The Docker image runs as root and has no `HEALTHCHECK`. Docker is not on the demo path
  (D-002), so this is an M3 item: add a non-root user and a healthcheck, then re-run the
  2026-10-25 deployment verification because the image will have changed.

## 10. Operations checklist for the pilot day (copy into the runbook)

1. `REQUIRE_CLASSROOM_WIFI` and `CORS_ORIGINS` set explicitly (no wildcard).
2. Server bound to the hotspot interface; firewall rule limited to the hotspot subnet.
3. Backup taken after the last enrollment and before the first check-in.
4. Server stopped after the demo; hotspot turned off.
5. Face crops of non-consenting people deleted; demo rows exported for the report first.

---

## 11. Open items and owners

| # | Item | Owner | When |
|---|---|---|---|
| 1 | WAL + busy timeout decision (A-owned file) | A + B | M3, before the final pilot |
| 2 | Rate limit or face-pipeline semaphore | B | M3 |
| 3 | Auth decision (API key vs teacher login) | A + B | M3 |
| 4 | TLS for the pilot (or written "private hotspot only") | B + C | M3 |
| 5 | Docker non-root + healthcheck, then re-verify | B | M3 |
| 6 | Delete pilot face data procedure | B | before submission |
| 7 | Add `dill==0.3.8` to `backend/requirements.txt` (one line, closes the 500) | **A** | immediately |
| 8 | Apply `MAX_UPLOAD_BYTES` to `/faces/recognize` and `/attendance/check` (§2.1 gap 1) | **A** | M3 (measured, not fixed) |
| 9 | Fail fast when models are missing; return 503 with an actionable detail instead of 500 | A + B | M3 |
| 10 | Close the `aiosqlite` connection when `init_db()` raises so the process exits (§5.1) | **A** | M3 |

Legend: items 7–10 are outside B's allowed files; B measured them and wrote the evidence
into `docs/B/evidence/2026-11-13-windows/` instead of patching A's code.
