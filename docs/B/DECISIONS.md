# DECISIONS — Member B (backend / deployment)

> Setiap keputusan teknis yang tidak sepele **wajib** ditulis di sini. File ini bagian
> dari penilaian M2: bukti bahwa kamu mengukur dulu, baru memutuskan.
>
> Aturan main:
> - Tulis entri **sebelum** pekerjaannya di-commit, perbarui setelah hasil pengukuran ada.
> - ISI ENTRI DALAM BAHASA INGGRIS (bagian dari dokumen proyek).
> - Minimal 2 opsi per keputusan, masing-masing dengan biaya dan risikonya.
> - Bukti = angka, log, hasil tes, atau artefak yang bisa dibuka orang lain. Belum diukur →
>   tulis `not measured yet`.

## Template entri (salin untuk setiap keputusan)

```markdown
### D-00X — <short title>
- **Date:** YYYY-MM-DD · **Stage:** <stage M2 / gate id>
- **Problem:** apa yang harus diputuskan, satu kalimat.
- **Options:** minimal 2, masing-masing dengan biaya dan risikonya.
- **Evidence:** angka / baris log / hasil tes / path artefak. Belum diukur → tulis apa adanya.
- **Decision:** pilihan + alasannya (satu paragraf, English).
- **Consequences:** apa yang jadi lebih sulit, apa yang gugur, apa yang harus ditinjau ulang.
- **Revisit by:** tanggal atau pemicu.
```

---

## Entri M1

### D-001 — Docker is not a substitute for native run on the Wi-Fi path
- **Date:** 2026-10-25 · **Stage:** M1 / B3
- **Problem:** Should the demo run the backend in Docker or natively on the machine?
- **Options:** (1) Docker everywhere — reproducible, but the container cannot see the
  host's Wi-Fi LAN; (2) native `uvicorn` everywhere — Wi-Fi scanning works, but setup
  depends on the machine; (3) Docker for the API demo and native for the Wi-Fi demo.
- **Evidence:** inside the container `/wifi/scan` returned `devices: []` with subnet
  defaulting to `192.168.1.0/24`; the same call natively detected the real subnet and the
  AP BSSID. Image is 3.4 GB on CPU wheels.
- **Decision:** Docker stays the documented deployment path for the API/dashboard, but any
  demo or pilot that must show Wi-Fi presence runs natively (or with host networking on
  Linux). This is stated explicitly in `docs/B/deployment_guide.md`.
- **Consequences:** the demo machine needs Python + `uvicorn` installed, not just Docker;
  the runbook must say which mode is active.
- **Revisit by:** demo preparation (G12/G13) — re-measure on the actual demo machine.

---

## Entri M2

### D-002 — Demo machine runs natively, not in Docker (G1)
- **Date:** 2026-11-02 · **Stage:** M2 stage 1 / G1
- **Problem:** Which run mode does the demo machine use, now that Wi-Fi presence is part of
  the demo?
- **Options:** (1) Native `uvicorn` only — Wi-Fi scan works, setup is a Python install;
  (2) Docker only — easy install, but no Wi-Fi visibility from inside the container;
  (3) both installed, Docker as a second option for dashboard-only rehearsals.
- **Evidence:** 2026-11-02 native run measured on a real network: `/wifi/scan` returned the
  gateway plus BSSID `50:98:b8:c9:2b:e2`, cold start to healthy **5.9 s**, smoke test 14/14
  (`docs/B/demo_environment.md` §2). 2026-10-25 in-container scan returned
  `devices: []` / BSSID `null` (`docs/B/deployment_guide.md` §10).
- **Decision:** The demo machine runs the backend **natively** with `uvicorn` on port 8000,
  using the locked env values in `demo_environment.md` §3. Docker stays documented for
  dashboard-only environments and for a Linux host with `network_mode: host`, but it is not
  on the demo critical path.
- **Consequences:** the demo laptop must have Python + `pip install -r backend/requirements.txt`
  done the day before, with the models already warmed. Docker images no longer need to be
  rebuilt for the demo, which removes the registry-mirror failure risk on demo day. The runbook
  must state the mode explicitly (it does, §2).
- **Revisit by:** G13 (dry run #1) — if the demo laptop's native setup proves unstable,
  re-open option 3 with measured evidence.

### D-003 — `face_only` on isolated networks is expected behaviour, not a system failure
- **Date:** 2026-11-02 · **Stage:** M2 / G5 (answers critical question 1)
- **Problem:** On the campus network `/wifi/scan` sees only the gateway (measured). When a
  check-in then ends as `face_only`, do we call that a system failure or understood
  behaviour?
- **Options:** (1) Failure — block the demo until room-level presence works (needs AP
  management access we do not have: `ap_management_plane.md`); (2) understood behaviour —
  `face_only` correctly records "face matched, Wi-Fi not verified", demo on a network we
  control; (3) hide it — force `wifi_verified = 1` for the demo (dishonest: it would fake
  the very condition the project claims to check).
- **Evidence:** measured twice on campus Wi-Fi (2026-10-25 and 2026-11-02): only the gateway
  appears, phones are connected but invisible → client isolation / VLAN split
  (`network_validation.md` §2, §6). `face_only` is an existing, tested status that stores
  `wifi_verified = 0`; the two-stage logic is unchanged.
- **Decision:** It is **understood behaviour**. The decision lives here (owner: B) and is
  restated in `network_validation.md` (F2), `PROJECT_CONTEXT.md` (§14 known limitations) and
  the demo script (`docs/B/offline_fallback.md` §4 supplies the sentence to say on stage).
  A ratifies it as reviewer; D carries it into the report/slides. Demo runs on a network we
  control so the positive path (`verified`) is also shown.
- **Consequences:** we must never claim "room-level presence" — only "device seen on the
  classroom network". Room-level presence is future work, blocked by management-plane access.
  If a pilot produces `face_only` for most check-ins, the limitation moves from "documented"
  to "demo blocker" and is escalated to A.
- **Revisit by:** G10 (pilot analysis) — count `face_only` share; or immediately if the
  school provides AP access.

### D-004 — Fix subnet detection using the real netmask, capped at one /24 (G5)
- **Date:** 2026-11-02 · **Stage:** M2 / G5
- **Problem:** `detect_local_subnet()` hard-coded /24 and `_ping_sweep()` pinged `.1–.254`
  of the last octet, so on a /17 interface the reported subnet did not match reality and
  neighbouring /24s were silently unreachable.
- **Options:** (1) keep /24 and document it; (2) read the real netmask and sweep the whole
  network (a /17 = 32k hosts, minutes per scan, heavy ping load — unusable for check-in);
  (3) read the real netmask, report/sweep only the /24 that contains the host, log a
  warning, and let `WI_FI_SUBNET` name the classroom /24 when needed.
- **Evidence:** before/after table in `network_validation.md` §6.1: detected network
  `10.163.235.0/24` (wrong) → `10.163.128.0/17` (real), reported range `10.163.216.0/24`
  (exactly what was swept). 19 new unit tests in `backend/tests/test_wifi_subnet.py`
  cover /24, /25, /17, bare-IP input, invalid config and the Windows `ipconfig` parser.
- **Decision:** Option 3. `detect_local_network()` returns the true network,
  `detect_local_subnet()`/`resolve_subnet()` return the bounded sweep target, and
  `sweep_hosts()` honours the prefix while capping at 254 addresses. The value in the
  `/wifi/scan` response is always the range that was actually pinged.
- **Consequences:** `/wifi/scan` can no longer overstate what it searched. A demo on a
  network wider than /24 needs `WI_FI_SUBNET` pointing at the room's /24 — added to the
  deployment guide (§5b) and the troubleshooting table. No router change was needed, so the
  fix stayed inside B's allowed files.
- **Revisit by:** after the first pilot on the classroom network, or if a scan exceeds
  ~5 s (the cap would then need tuning).

### D-005 — Unprivileged Linux scan fallback and correct ping flags
- **Date:** 2026-11-02 · **Stage:** M2 / G5
- **Problem:** On Linux, scapy needs `CAP_NET_RAW`; without it the scan raised
  `PermissionError` and `/wifi/scan` failed (also made 4 tests red on Linux while green on
  Windows). In addition the ping sweep always used the Windows flags, so Linux pings failed
  silently.
- **Options:** (1) require root/CAP_NET_RAW on every Linux machine; (2) catch the error and
  return `[]` (hides the failure, the check-in then reports `face_only` with no clue why);
  (3) catch it, log a warning, and fall back to an unprivileged ping sweep + `ip neigh`
  (with `arp -a` as a second fallback).
- **Evidence:** `PermissionError: Operation not permitted` on `socket(AF_PACKET, SOCK_RAW)`
  before the change; after it, `/wifi/scan` returned the gateway and BSSID on the same
  unprivileged machine (`network_validation.md` §6.2, §6.3) and the full suite went
  **171 passed, 1 skipped**.
- **Decision:** Option 3. Platform-correct ping commands (`-n/-w` Windows, `-c/-W`
  macOS/Linux) plus the `ip neigh` fallback. A warning is always logged when the fallback is
  used, so the operator knows which path produced the result.
- **Consequences:** Linux laptops and Docker images without NET_RAW can still verify Wi-Fi
  presence (weaker than raw ARP: only hosts that answer ping and are in the neighbour table
  appear; a client that blocks ICMP may be missed — the same limitation the Windows path
  already had). Root remains optional, not required.
- **Revisit by:** pilot, if phones are missed on a flat network — then compare scapy-as-root
  vs fallback counts on the same network and record both.

### D-006 — Demo-day recovery: backup file + measured restore, seeded data as last resort
- **Date:** 2026-11-02 · **Stage:** M2 / G12–G16 (answers critical question 3)
- **Problem:** How long does recovery take if the database is damaged on demo day, and what
  is the recovery path?
- **Options:** (1) restore a copy of `attendance.db` made before the demo (needs a backup
  file, loses nothing after the backup); (2) re-run `seed_demo.py --reset` (fast, but wipes
  real rows and re-creates demo rows); (3) no plan — debug live.
- **Evidence:** measured on 2026-11-02 with a seeded DB: random bytes over the file →
  `sqlite3.DatabaseError: file is not a database`, server refuses to start; copy backup
  over it + start → `{"status":"ok","database":"ok"}` in **6,172 ms** (5.9 s interpreter +
  FastAPI startup, ~0.3 s copy). `seed_demo.py --reset --students 5` runs in ~1 s and the
  dashboard serves the rows immediately (`demo_environment.md` §2.6–2.7).
- **Decision:** Primary = option 1 (backup taken 30 min before the demo, copied to USB and
  phone). Secondary = option 2. The exact commands are in `deployment_guide.md` §8 and the
  runbook §4. The number quoted on stage/report is **"under 10 s plus the time to notice"**,
  not a guess.
- **Consequences:** the demo checklist now includes "take a backup" (runbook step 4); the
  detection story matters more than the restore story — a damaged DB shows up as
  connection-refused, so the runbook says to check the server log tail for
  `sqlite3.DatabaseError` first.
- **Revisit by:** dry run #1 — time the real procedure on the demo laptop, including the
  time to notice.

### D-007 — What is switched off or excluded during the live demo (answers critical question 4)
- **Date:** 2026-11-02 · **Stage:** M2 / G12 (scope lock input)
- **Problem:** Which features should be turned off or kept out of the live demo to reduce
  risk without weakening the claim?
- **Options:** (1) demo everything the system can do (max surface, max failure modes);
  (2) demo only the three-condition flow + dashboard/CSV, and disable the risky extras;
  (3) demo only pre-seeded data (no live check-in) — safest but proves nothing.
- **Evidence:** measured failure modes so far: BSSID pinning adds a check that legitimately
  fails when the server sits on a different AP (`network_validation.md` F5); Docker cannot
  see Wi-Fi (D-001/D-002); campus client isolation makes phones invisible (F2); a wrong
  timezone produced 403s in C's device tests; the AP management plane is unavailable
  (`ap_management_plane.md`).
- **Decision:** Option 2. Off/excluded for the live demo: **Docker** (native only),
  **`ap_bssid` pinning on the demo schedule** (leave it `NULL`; pinning is shown from the
  measured evidence instead), **automatic Wi-Fi presence tracking / 5-minute tracker** (not
  built), **enrollment in front of the audience** (done beforehand), **campus Wi-Fi**
  (hotspot or LAN instead), and **CORS wildcard** (set to the dashboard origin). Kept on:
  two-stage check-in, identity binding, time window, Wi-Fi presence on the controlled
  network, dashboard, CSV export.
- **Consequences:** the demo claims "a device is seen on the classroom network", not "we
  pin the exact AP"; slides must show the pinning code/evidence instead of performing it.
  Any "one more feature" request after **2027-01-08** is refused (G12).
- **Revisit by:** G12 (scope lock); nothing is added back after that date.

### D-008 — Seed data identities and the fake-MAC trade-off (G5)
- **Date:** 2026-11-02 · **Stage:** M2 / G5
- **Problem:** Should seeded demo students use fake MACs (safe, but Wi-Fi prompt always
  false) or a real phone MAC (live-looking prompt, but one MAC can only belong to one
  student and must be reset afterwards)?
- **Options:** (1) fake locally-administered MACs `02:00:00:00:00:NN` for all demo students;
  (2) overwrite one demo student's MAC with the presenter's real phone MAC; (3) create a
  separate "live" student for the real phone and keep seeded students untouched.
- **Evidence:** measured 2026-11-02: with fake MACs `/me/prompt?student_id=5` returns
  `check_available: true, reason: device_not_seen_on_network` while
  `/attendance/today` and the CSV show the seeded rows (`demo_environment.md` §2.6). Also a
  hard rule from the M1 work: one MAC = one student (409 on duplicates), and Buchari's row
  currently carries the gateway's MAC (a documented demo artifact).
- **Decision:** Option 1 for the dashboard/offline fallback, option 3 for a live Wi-Fi
  demo: seeded students keep fake MACs, and the presenter's phone is registered on a
  separate real student (or via `PUT /students/{id}/mac`) **before** the demo, never during
  it. `seed_demo.py --reset` also deletes the embedding pickles/crops of the students it
  deletes, so a reused id cannot match an old face.
- **Consequences:** the seeded fallback can never show a Wi-Fi `verified` row — that is
  correct and must be said out loud. The live student's MAC must be reset after the demo
  (documented in the runbook shutdown section as an optional cleanup).
- **Revisit by:** dry run #1 — if projector time is short, prefer the seeded dashboard and
  one live check-in with the real student.

### D-009 — How to read the AP BSSID without depending on a deprecated tool (review finding 1)
- **Date:** 2026-11-03 · **Stage:** M2 / post-review fix on `task-b`
- **Problem:** `get_current_bssid()` used `iwconfig` only. That tool is no longer installed by
  default on current distros, and this laptop is the proof: `iw` is absent, `iwconfig` is
  present (`evidence: §7.1 of network_validation.md`). On a machine where the opposite is
  true, the BSSID is `None`, `schedules.ap_bssid` can never match, and every check-in
  silently becomes `face_only` — a Wi-Fi feature switched off with no error anywhere.
- **Options:** (1) keep `iwconfig` and document it as a requirement; (2) probe a chain
  `iw` → `nmcli` → `iwconfig` and warn once when none of them work; (3) add a Python
  netlink/`libnm` binding and avoid shelling out entirely.
- **Evidence:** measured 2026-11-03 on `NJUPT-CMCC` (`network_validation.md` §7.2):
  `_resolve_linux_bssid()` → `('50:98:b8:c9:2b:e2', 'nmcli', True)` on a host without `iw`;
  `PATH=/nonexistent` → one `WARNING` + `None`; not-associated → `None` with no warning.
  The live run also exposed that `nmcli -t` escapes colons (`yes:50\:98\:B8\:...`), so a
  naive parser silently failed — fixed and pinned by
  `test_nmcli_real_terse_output_escapes_colons`.
- **Decision:** option 2. Order is newest-tool-first, degraded state is a **warning that
  names the consequence and the fix** (`install iw`, or set `ap_bssid` to NULL), and the
  warning fires once per process so it cannot flood `/wifi/scan` logs.
- **Consequences:** zero new dependencies (all three probes are optional; absence is handled);
  three subprocess calls per 10 s cache window worst case; operators get one actionable line
  instead of a silent downgrade. Shelling out remains (option 3 rejected: no `libnm` in
  `requirements.txt`, and the three CLI tools cover every distro the team can meet).
- **Revisit by:** demo laptop run (`demo_environment.md` §6) — confirm `netsh` still works
  there; if the team standardises on NetworkManager, `nmcli` can be promoted to first.
- **Evidence files:** `backend/services/wifi_scanner.py` (`_LINUX_BSSID_PROBES`),
  `backend/tests/test_wifi_subnet.py` (`TestLinuxBssidProbes`),
  `docs/B/network_validation.md` §7.

### D-010 — macOS support: fix the ping flags, do not pretend BSSID works (review finding 6)
- **Date:** 2026-11-03 · **Stage:** M2 / post-review fix on `task-b`
- **Problem:** `_ping_command()` passed `-W <ms>` on Darwin, and `get_current_bssid()` has no
  macOS probe at all. No macOS host exists in the project, so both issues are invisible.
- **Options:** (1) drop macOS from the supported set and say so; (2) fix what is provably
  wrong (ping flags) and document the BSSID gap; (3) implement airport/networksetup probes
  and test them — impossible to verify without hardware.
- **Evidence:** `ping(8)` on macOS exposes no per-packet millisecond flag that is stable
  across releases, while the sweep already bounds every call with
  `subprocess.run(timeout=timeout_ms/1000 + 1)`; a single packet is enough to populate the
  ARP cache. Measured shape now asserted by `TestPingCommand::test_darwin_uses_bsd_compatible_flags`
  (`network_validation.md` §6.2, §7.5).
- **Decision:** option 2. Darwin gets `ping -c 1 <ip>`; the BSSID gap is stated in
  `network_validation.md` §7.5 and in the deployment guide instead of being papered over.
- **Consequences:** no false confidence on an untested platform. If a macOS host ever joins
  the demo, `ap_bssid` must be NULL (no pinning) and the ping sweep still works.
- **Revisit by:** only if a macOS machine becomes a demo target; otherwise closed.
- **Evidence files:** `backend/services/wifi_scanner.py` (`_ping_command`),
  `backend/tests/test_wifi_subnet.py` (`TestPingCommand`).

### D-011 — Windows netmask parsing must not depend on the display language (G5)
- **Date:** 2026-11-13 · **Stage:** M2 / G5 (Windows demo-laptop run)
- **Problem:** the Windows branch of `detect_local_network()` found the netmask by searching
  for the English label `Subnet Mask`. A localized Windows (Chinese, French, …) prints a
  translated label, so the mask was not found and subnet detection degraded to a guessed /24
  — the scanner would then report and sweep a range that is not the machine's real network.
  The failure is silent, which is the worst property for a Wi-Fi gate.
- **Options:** (1) keep the English label and require an English Windows — free, but the
  demo laptop's language is not something the project controls; (2) keep the English fast
  path and add an order-based fallback: after the adapter's IPv4 address line, take the
  first netmask-shaped token and require it to be a contiguous mask; (3) shell out to
  PowerShell `Get-NetIPAddress -PrefixLength`; (4) use a library — `psutil` exposes addresses
  but not netmasks on Windows, so this is not available without a new dependency.
- **Evidence:** on this laptop `ipconfig` is English (`Subnet Mask . . . : 255.255.128.0`),
  and the server detected `10.163.128.0/17`, then logged
  `Interface network 10.163.128.0/17 is wider than /24; sweeping only 10.163.158.0/24`
  and returned exactly `10.163.158.0/24` as `subnet` (`measurements-g1.txt` §3). New unit
  tests feed captured Chinese (`子网掩码`) and French (`Masque de sous-réseau`) blocks,
  an `(Preferred)` suffix and a non-contiguous `255.0.255.0`, which must be rejected;
  suite goes from 205 to **209 passed**.
- **Decision:** option 2. A netmask that is not a run of ones followed by zeros cannot be a
  CIDR prefix, so it is rejected instead of silently converted. Option 3 was kept as a
  mental fallback but not implemented: it would add a subprocess whose output format also
  changes with PowerShell versions.
- **Consequences:** the fallback depends on `ipconfig` printing the mask near the address
  line; that order is pinned by a captured fixture, and `WI_FI_SUBNET` remains the explicit
  escape hatch (already in the troubleshooting table). A future Windows build that reorders
  the output would make detection fall back to "nothing found", which is loud (no wrong
  subnet is claimed).
- **Revisit by:** the first run on the actual demo laptop if its Windows language is not
  English; or if Windows changes `ipconfig` output.
- **Evidence files:** `backend/services/wifi_scanner.py` (`parse_ipconfig_prefix`,
  `_prefix_from_netmask`), `backend/tests/test_wifi_subnet.py` (locale cases).

### D-012 — Reference interpreter is Python 3.12, and the YOLO checkpoint needs `dill`
- **Date:** 2026-11-13 · **Stage:** M2 / G1 (clean install on the Windows laptop) + M3 hygiene
- **Problem:** which Python version and dependency set lets a **fresh** machine actually
  recognise a face? The pinned requirements were assumed to be sufficient; the clean-install
  run proved otherwise.
- **Options:** (1) move to Python 3.13 and unpin `numpy`/`onnxruntime`/`opencv-python` —
  A's threshold and G3 numbers were measured on the pinned versions, so this silently
  invalidates existing evidence; (2) pin Python 3.12 and add the one missing runtime
  dependency (`dill`) to the install steps; (3) produce a hash-pinned lock file — correct
  long-term, disproportionate two weeks before the presentation.
- **Evidence:** system Python **3.13.5** cannot install the pinned set (no cp313 wheels for
  `numpy==1.26.4`, `onnxruntime==1.18.1`, `opencv-python==4.10.0.84`; pip falls back to
  source builds and fails). Python **3.12.10** installs in **577 s**
  (`INSTALL_STARTED/FINISHED` in `.venv/pip_install.log`, Tsinghua mirror). With the model
  file present, `/faces/recognize` still returned **500**: `torch.load` of
  `yolov8m-face.pt` raises `ModuleNotFoundError: No module named 'dill'`
  (`measurements-g1.txt` §5, full traceback in `run2/s1.log`). After
  `pip install dill==0.3.8`: `/faces/recognize` → 200, cold 13.4 s, warm 1.5–1.6 s, smoke
  **15/15** (`measurements-smoke.txt`).
- **Decision:** option 2. Python 3.12 is the reference interpreter; the Dockerfile stays on
  `python:3.11-slim` (also supported). B adds `pip install dill==0.3.8` to
  `deployment_guide.md` §5b immediately and **asks A to add `dill==0.3.8` to
  `backend/requirements.txt`** (`requirements.txt` is A-owned, so B does not edit it).
- **Consequences:** until A makes that one-line change, a machine that follows only
  `requirements.txt` gets a 500 on the first recognition; the guide, the runbook pre-flight
  and the troubleshooting table now name the symptom and the fix. The Docker path has the
  same hole because the checkpoint is mounted, not installed.
- **Revisit by:** when `requirements.txt` is updated (then delete the extra command), or if
  the model file is replaced by a checkpoint that is not dill-pickled.
- **Evidence files:** `.venv/pip_install.log`, `docs/B/evidence/2026-11-13-windows/`,
  `docs/B/deployment_guide.md` §5b/§7/§9.

### D-013 — Demo security posture: open API + no TLS, constrained to a controlled hotspot
- **Date:** 2026-11-13 · **Stage:** M2 / G12 input, M3 backlog
- **Problem:** the backend has no authentication, no transport encryption and no rate
  limiting (`hardening_checklist.md` §3, §4, §6). Is that acceptable for the November demo,
  and what must be true on the day?
- **Options:** (1) add an API key or teacher login plus TLS before the demo — touches A's
  routers and C's device-tested APK two weeks before the presentation, with a real chance of
  breaking the demo; (2) keep the open API but shrink the blast radius: run only on a
  password-protected hotspot the team controls, scope the firewall rule to the hotspot
  subnet, one CORS origin, strict Wi-Fi mode on, stop the server after the demo; (3) demo
  only seeded dashboard data with the radio off — safest, but it cannot show the
  three-condition check-in that is the project's claim.
- **Evidence:** every endpoint answers without credentials, over plain HTTP (observed in all
  runs above; there is no auth dependency in any router). The demo network is a
  laptop/phone hotspot, not the campus SSID — on campus the scanner sees only the gateway
  anyway (F2), so the campus network is not a viable demo path. `REQUIRE_CLASSROOM_WIFI=true`
  turns the Wi-Fi condition into a visible 403 instead of a silent `face_only`.
- **Decision:** option 2 for the November demo. The controls are written into
  `demo_runbook.md` §2/§5 and stated as a limitation on the slides. Option 1 remains the M3
  plan (API key vs teacher login is still open, `hardening_checklist.md` §11).
- **Consequences:** the demo must never be reachable from the campus VLAN or the internet;
  the presenter's phone MAC is registered as a student, so one phone is both client and
  attendance device — acceptable for a pilot, to be said out loud in the report. Any public
  deployment in this state would be a serious fault, which is why the limitation is explicit.
- **Revisit by:** before any pilot where people outside the team can reach the server, or as
  soon as C's APK needs a token.

### D-014 — Warm the models with one deliberate call; do not load them at startup
- **Date:** 2026-11-13 · **Stage:** M2 / G12 (demo readiness)
- **Problem:** the first recognition after a cold start costs ~13 s (YOLO weights) and the
  first ArcFace use adds ~3 s and 341 MB of model files. Where should that cost be paid:
  at startup, in the background, or at the first real request?
- **Options:** (1) keep the lazy load and require one throwaway `/faces/recognize` before the
  audience arrives; (2) eager load in `lifespan` — startup grows by ~13 s and the server
  refuses to start on a machine with a missing model, a new hard dependency on demo day;
  (3) preload on a background thread — hides the cost but changes A's `main.py` and makes
  startup behaviour nondeterministic.
- **Evidence:** `/health` is ready in **17.3 s** without touching the models; the first
  `/faces/recognize` took **13,435 ms**, then **1,637 / 1,535 ms**; the smoke warm-up call
  after a fresh start took **8,282 ms** (page cache warm); ArcFace loads in **2.8–3.0 s** and
  the process holds **1,001 MB RSS** with both models resident; a missing `.pt` produces a
  500 `FileNotFoundError` on every recognition (`measurements-g1.txt` §5). With warm-up
  done, the full smoke test runs in **10.4 s**.
- **Decision:** option 1. `demo_runbook.md` §2 step 8 requires one throwaway recognition call
  after startup, and the pre-flight check verifies the `.pt` file is ~52 MB. `main.py` stays
  untouched (A-owned).
- **Consequences:** forgetting the warm-up costs ~13 s on the first live check-in (visible,
  not fatal); the demo laptop needs ~1 GB of free RAM for the backend process on top of the
  browser and OS. A machine without the model fails loudly with 500s, which the
  troubleshooting table now maps to "download the model / install dill".
- **Revisit by:** M3 — a deep health probe or an env-flag eager load, once A agrees to touch
  the startup path.
