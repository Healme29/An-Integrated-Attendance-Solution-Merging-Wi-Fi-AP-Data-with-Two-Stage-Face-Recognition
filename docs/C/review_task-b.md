# Review of Task B — Backend, Real Wi-Fi Validation & Deployment (branch `task-b`)

Reviewed on 2026-11-02. Scope: the four newest commits on `origin/task-b`
(`dad5475`, `792af1e`, `cf0e470`, `c3217a4`), evaluated against the mission in
`docs/B/TASK.md` ("prove the backend really works outside the dev machine").

Commits reviewed:

| Commit | Subject |
|---|---|
| `dad5475` | Harden seed_demo: 1-99 students, id reset, scoped cleanup of stale embeddings |
| `792af1e` | Fix Wi-Fi subnet detection (real netmask, bounded sweep) and unprivileged Linux fallback |
| `cf0e470` | Docs: G1 environment evidence, offline fallback, demo runbook, AP plane verdict, decisions D-002..D-008 |
| `c3217a4` | Docs: deployment guide followed from scratch - fix missing model dir, PowerShell examples, warm-up and firewall steps |

---

## Verdict

**Accepted — 8.5/10.**

B did what the mission asked: every claim in the new documents is backed by a
measurement (timestamps, raw command output, seconds), not a prediction. The
work closes the gap between "works on my laptop" and "proven outside the dev
machine" better than any other work package so far. Deductions are for work
that is still open (demo laptop, unmeasured fallback rung 1) and one real
platform risk that is not yet addressed (see Findings).

### Fit against the original mission

| Mission item (from `docs/B/TASK.md`) | Evidence delivered | Status |
|---|---|---|
| B1 — Wi-Fi validated on a real network | `network_validation.md`: measured on campus Wi-Fi, findings F1–F5 honestly recorded (incl. "only the gateway visible") | ✅ |
| Docker verified | `deployment_guide.md` §10: build ~4 min, image 3.4 GB, smoke 15/15, persistence across restart | ✅ |
| G1 — demo environment alive | `demo_environment.md`: cold start 5,926 ms, `TIMEZONE` proven applied (8 h gap UTC vs Asia/Shanghai), DB persists restart | ✅ on dev laptop; ⏸ physical demo laptop still open (§6) |
| G5 — offline fallback + AP plane verdict | `offline_fallback.md` (5-rung ladder), `ap_management_plane.md` verdict | ✅ (rung 1 hotspot unmeasured) |
| Deploy guide usable by a non-technical person | `guide_review.md`: followed from scratch in a clean clone, 6 real defects found and fixed in the guide | ⚸ partially — "followed by someone else unaided" is not yet earned (B says so explicitly) |
| Critical questions answered with evidence | `DECISIONS.md` D-002…D-008, all with ≥ 2 options + numbers | ✅ |

### Innovations worth noting

1. **Subnet detection fixed using the real netmask (D-004).** A bug B found
   through *validation* (interface is /17, code assumed /24), fixed with
   `ipaddress.IPv4Network`, a bounded sweep (`_MAX_SWEEP_HOSTS = 254`) so a scan
   can never take minutes, and — importantly — `/wifi/scan` now reports the
   range that was *actually* swept, not a wider one. 19 new unit tests
   (`test_wifi_subnet.py`) cover /24, /25, /17, bare-IP input, invalid config
   and the Windows `ipconfig` parser.
2. **Unprivileged Linux scan fallback (D-005).** scapy without `CAP_NET_RAW`
   raised `PermissionError` (also made 4 tests red on Linux while green on
   Windows — a cross-platform blind spot). Fixed with a fallback to ping sweep +
   `ip neigh` (+ `arp -a`), platform-correct ping flags, and a logged warning
   whenever the weaker path is used. Suite now **171 passed, 1 skipped** on
   Linux.
3. **Honest-behaviour decision instead of a cover-up (D-003).** On isolated
   campus SSIDs `face_only` is declared *understood behaviour*, not a system
   failure — but the team explicitly refuses to fake `wifi_verified = 1` during
   a demo. This protects the credibility of the three-condition claim the
   project is graded on.
4. **Guide-under-test methodology (`guide_review.md`).** Following your own
   deployment guide in a clean clone, recording every failing/ambiguous step
   (missing `backend/data/models/` after clone, PowerShell `curl` alias
   pitfalls, missing warm-up command), then fixing the guide — the same
   measure→decide loop the decision log demands.
5. **Measured demo-day recovery (D-006).** DB corruption → restore → healthy
   is timed at **6.2 s** (not guessed), with a documented detection path
   (`sqlite3.DatabaseError` in the server log) and `seed_demo.py --reset` as
   the last-resort rung.

---

## Does developing on Linux change anything?

Yes — mostly for the better, with two follow-ups:

**Improved:**
- Cross-platform bugs that were invisible on Windows became visible and got
  fixed (scapy `CAP_NET_RAW`, ping flags, `ip neigh` parsing). The test suite is
  now genuinely portable (171 passed on Linux).
- On a Linux *host*, Docker with `network_mode: host` becomes a real option
  for Wi-Fi demos (impossible on Docker Desktop/Windows).

**Not yet handled (see Findings 1 & 2):**
- `get_current_bssid()` still shells out to `iwconfig`, which modern distros
  (and minimal/server images) often do not ship. On such a machine the BSSID
  is silently `None` → **BSSID pinning fails for every check-in** → statuses
  quietly degrade to `face_only` even when the Wi-Fi check should pass. This
  worked on B's laptop only because `iwconfig` happens to be installed.
- macOS ping flags: `_ping_command` uses `-W` for Darwin, which BSD `ping`
  does not support (it is the Linux flag). Cosmetic today (no macOS host in
  the project) but worth one small fix.

---

## Findings (ordered by priority — fix these first)

| # | Finding | Severity | Why it matters | Suggested fix |
|---|---|---|---|---|
| 1 | **BSSID read on Linux depends on `iwconfig`**, a deprecated tool absent from many current distros. No fallback, no test for the "tool missing" case. | **High** | On the demo laptop this silently disables room pinning and downgrades every check-in to `face_only` — the failure is invisible in logs unless someone looks. | Add `iw dev <iface> link` (and/or `nmcli -f BSSID dev wifi`) as fallback before `iwconfig`; log a warning when no tool is found; add a unit test for the missing-tool path. |
| 2 | **The subnet fix + 19 new tests live only on `origin/task-b`**; `main` still carries the /24 assumption and the privilege-crashing scapy path. | **High** | If the demo (or anyone else) runs from `main`, none of B's fixes are present. | Merge `task-b` into `main` after review (A as reviewer, per project convention). |
| 3 | **G1 verified on the dev laptop, not the physical demo machine** (`demo_environment.md` §6 open); `pip install -r backend/requirements.txt` was never executed end-to-end (multi-GB torch download skipped, `guide_review.md` §4). | Medium | The one untested step is exactly the one a fresh demo laptop needs. | Re-run G1 on the demo laptop: time the full `pip install`, warm the models, repeat the smoke test; record numbers in `demo_environment.md`. |
| 4 | **Fallback rung 1 (hotspot) is unmeasured** — `offline_fallback.md` marks it `not measured yet`; no second phone + hotspot session has been run. | Medium | Rung 1 is the *primary* demo path; its numbers (devices found, seconds per scan, MAC stability across rejoins, private-MAC handling) are quoted nowhere yet. | Schedule one hotspot session with a second phone before the dry run; record results in `network_validation.md`. |
| 5 | **"Guide followed by another person unaided" is not yet earned** — B states this explicitly in `guide_review.md` §4. | Medium | It is part of the stage's own definition of done. | Have D (or someone outside the team) follow `deployment_guide.md` on the demo laptop while B only observes; record their stumbles. |
| 6 | macOS ping flag `-W` is not a BSD `ping` option. | Low | No macOS host today; correctness issue if anyone ever runs the scanner there. | Use `-c 1` (drop `-W`) for Darwin, or branch on the flag set. |
| 7 | Docs-only commits mix with a code fix in the same push (`792af1e` + three docs commits pushed together); `DECISIONS.md` entries reference evidence across files without links. | Low | Minor navigability/tracing cost for the report (M3) later. | Optional: add file-path cross-links in future decision entries. |

---

## Scorecard

| Dimension | Score | Note |
|---|---|---|
| Mission fit (real-network proof, deployment, demo readiness) | 9/10 | Every gate targeted has measured evidence; demo-machine repeat still open |
| Engineering quality (fix + tests) | 9/10 | Root-caused fix, bounded sweep, 19 targeted tests, suite green cross-platform |
| Documentation & decision discipline | 9/10 | D-002…D-008 with options + numbers; honest `not measured yet` markers |
| Platform robustness (Linux consequences) | 6.5/10 | Good catch on scapy/ping; `iwconfig` dependency left exposed |
| Test completeness vs claims | 8/10 | Smoke 14/14, pytest 171 passed; hotspot rung and other-person guide run untested |
| **Overall** | **8.5/10** | Accept to merge (after Finding 1/2 are addressed) |

---

## Recommended next actions, in order

1. Fix Finding 1 (BSSID fallback on Linux) + a small test, on `task-b`.
2. Merge `task-b` → `main` (Finding 2) so the fixes are on the demo path.
3. Re-run G1 on the physical demo laptop, including a timed full
   `pip install -r backend/requirements.txt` (Finding 3).
4. One hotspot session with a second phone; fill in the `not measured yet`
   slot in `offline_fallback.md` / `network_validation.md` (Finding 4).
5. D follows `deployment_guide.md` unaided on the demo laptop (Finding 5).
6. Optional in the same pass: macOS ping flag (Finding 6).