# Review Response — Task B (`task-b`), review of 2026-11-02

> **Review under response:** "Review of Task B — Backend, Real Wi-Fi Validation &
> Deployment", 8.5/10, accepted to merge after findings 1 and 2.
> **Response date:** 2026-11-03 · **Last updated:** 2026-11-13 (Windows G1 + hardening
> measurements) · **Branch:** `task-b` · **Owner:** B
>
> Rule used here: a finding is only marked **closed** if there is a measurement or a test
> that anyone can re-run. Anything that needs hardware or another person stays **open** and
> says who has to do it.

---

## 1. Status of every finding

| # | Finding | Status | Where the proof is |
|---|---|---|---|
| 1 | BSSID read depends on deprecated `iwconfig` (High) | ✅ **closed** | `network_validation.md` §7, D-009, `test_wifi_subnet.py` |
| 2 | Fixes live only on `task-b`, `main` still broken (High) | ⏳ **ready, owner A** | §3 below: fast-forward, zero conflicts |
| 3 | G1 + `pip install` not run on the demo laptop (Medium) | ✅ **closed 2026-11-13** on the Windows 11 laptop (`guide_review.md` §5) | `demo_environment.md` §7, `guide_review.md` §5, evidence folder |
| 4 | Hotspot rung 1 unmeasured (Medium) | ⏸ **open** — needs a second phone | `offline_fallback.md` §2 |
| 5 | "Guide followed by another person unaided" (Medium) | ⏸ **open** — needs D or an outsider | §6 below: observer checklist |
| 6 | macOS `ping -W` is not a BSD flag (Low) | ✅ **closed** | D-010, `TestPingCommand` |
| 7 | Mixed commit contents, decisions without file links (Low) | ✅ **closed** (forward-looking part) | every new decision entry ends with **Evidence files:** |

Closed with evidence: **4 of 7** (findings 1, 3, 6, 7). Finding 2 is ready and only waits on
A's merge. Open: 4 and 5 — both physical, not code.

---

## 2. Finding 1 (High) — BSSID probe chain, closed with evidence

### The bug was reproducible on the machine that produced the original evidence

```
$ command -v iw; command -v nmcli; command -v iwconfig
(nothing)      ← iw is NOT installed here
/usr/bin/nmcli
/usr/sbin/iwconfig
```

So the old code worked **by luck**: it leaned on the one tool that is being removed.

### What changed

`backend/services/wifi_scanner.py` — `get_current_bssid()` now runs an ordered probe chain:

| Order | Probe | Notes |
|---|---|---|
| 1 | `iw dev <iface> link` | modern default; interface list from `iw dev` |
| 2 | `nmcli -t -f ACTIVE,BSSID device wifi` | NetworkManager hosts |
| 3 | `iwconfig` | legacy, kept last |

Outcomes are now distinguishable, which is the actual defect the review described:

| Situation | Before | After |
|---|---|---|
| BSSID readable | value | value (logged at DEBUG with the probe name) |
| Not associated / no Wi-Fi | `None`, silent | `None`, **no** warning (normal) |
| No probe can run | `None`, silent → all check-ins silently `face_only` | `None` + **one** `WARNING` per process, naming the consequence and the fix |

Measured on this laptop (AP `50:98:b8:c9:2b:e2`, same link as the October session):

```
>>> wifi_scanner._resolve_linux_bssid()
('50:98:b8:c9:2b:e2', 'nmcli', True)      # same BSSID the old iwconfig path returned

$ PATH=/nonexistent python -c "..."        # simulate "no tool at all"
WARNING services.wifi_scanner: Cannot read the current BSSID: none of 'iw', 'nmcli' or
'iwconfig' is available on this Linux host. AP pinning (schedules.ap_bssid) can never
verify, so check-ins will be recorded as face_only. Install 'iw' (package: iw) or set the
schedule ap_bssid to NULL.
```

### A bug the fix had to survive first

The first version of the `nmcli` parser was **also** wrong, and only the live run showed it:
terse mode escapes colons inside values.

```
$ nmcli -t -f ACTIVE,BSSID device wifi | grep '^yes'
yes:50\:98\:B8\:C9\:2B\:E2
```

A plain `AA:BB:..:FF` regex does not match that, so the fallback silently returned `None`
and `iwconfig` masked the defect. Fixed by unescaping `\:` before matching, and
`test_nmcli_real_terse_output_escapes_colons` pins the captured output verbatim. This is
worth stating plainly: an untested fallback is not a fallback — the review was right to ask
for it.

### Tests

`backend/tests/test_wifi_subnet.py` additions:

- `TestBssidParsers` — `iw link` connected / not connected / neighbouring-AP noise,
  `nmcli` active row, no active row, empty BSSID field, **real escaped terse output**.
- `TestLinuxBssidProbes` — `iw` wins over `iwconfig`; `iw` missing → `nmcli`; both missing →
  `iwconfig`; not associated → `None` with no warning; no tool → warning fired **exactly
  once** across two calls.
- `TestPingCommand` — the three platform shapes (see finding 6).

Full suite: **187 passed** (34 in the scanner file) at that time; the suite is **209 passed**
on 2026-11-13 after the Windows locale fix (§2.1 of `network_validation.md` §8.2).

### Operator-facing consequence

`offline_fallback.md` gained §4b: a pre-demo check for `"bssid": null`, the one-line fix
(set `ap_bssid` to NULL rather than hand-typing a MAC), and the sentence to say out loud.
A Wi-Fi feature that switches itself off is now either visible in the log or in the
checklist — never silent.

---

## 3. Finding 2 (High) — merge is safe, but it needs A, not B

Verified on 2026-11-03 against the real base:

```
origin/main = f4065e9   (task-b's base)
task-b      = HEAD
git merge-base --is-ancestor origin/main task-b   → YES
git merge-tree --write-tree origin/main task-b    → clean tree, no conflicts
```

So `task-b` merges into `main` as a **fast-forward**: no merge commit, no conflict
resolution, nothing to review twice. No file on `main` was touched by anyone since the base,
so the diff is exactly the four commits from the review.

Commands for **A** (B must not merge its own work):

```bash
git fetch origin
git checkout main
git merge --ff-only origin/task-b
git push origin main
```

If `--ff-only` refuses, someone moved `main`: run `git log --oneline origin/main ^task-b`
first and re-review the overlap instead of forcing anything.

I am not doing this myself: the review says "A as reviewer, per project convention", and B
merging B's own branch would defeat that.

---

## 4. Finding 3 (Medium) — G1 on the demo laptop: closed 2026-11-13

The review was right that this could not be closed from the old Linux machine. It is now
measured on the **Windows 11 laptop** that will run the demo (`10.0.22621`, AMD64, Python
3.12.10), native `uvicorn`, no Docker. Raw output and the re-runnable scripts live in
`docs/B/evidence/2026-11-13-windows/`; the reader-facing tables are
`demo_environment.md` §7 and `guide_review.md` §5.

**4.1 The timed install is done.** Fresh venv, `pip install -r backend/requirements.txt`:
**577 s** (12:09:36 → 12:19:13, exit 0), log kept at `.venv/pip_install.log`. It then needed
one extra command, `pip install dill==0.3.8`, because loading `yolov8m-face.pt` otherwise
raises `ModuleNotFoundError: No module named 'dill'`. That is a packaging defect in an
**A-owned** file, so B documented it rather than editing it: hardening item 7, D-012.

**4.2 The gate table, measured:**

| Measurement | Measured value |
|---|---|
| full install (fresh venv) | **577 s** |
| cold start → health | **17.3 s** (restart 25.3 s) |
| model warm-up: cold `/faces/recognize` | **13.4 s**, then **1.5–1.6 s** warm |
| server's own warm-up call | **8.3 s** |
| first check-in after warm-up | 1.4 s round trip on a no-face request (accepted path not measurable without a real face, see §4.3) |
| `/wifi/scan` on the live network | **4,281 ms** fresh / **29 ms** cached, 1 device, `bssid` present |
| `/health`, `/`, `/dashboard` | 5.4 / 1.7 / 6.2 ms |
| seed demo data | 0.7 s |
| backup / restore | 1.2 ms / **13.9 s** |

**4.3 What remains inside finding 3, honestly:** the real-face *accepted* check-in (enroll →
recognize → live `verified` row) is still **not measured** — there is no usable face photo on
this machine (the public datasets were unreachable). The latency of the code path around it
is measured; the matching outcome is covered by mocked tests only. It is marked
**not measured yet** everywhere it appears, not estimated.

If the team ends up demoing on a **different** physical laptop, these timings do not transfer:
repeat §5 of `guide_review.md` there (≈15 minutes) and replace this table. The procedure is
the deliverable; the numbers belong to the machine.

---

## 5. Finding 4 (Medium) — hotspot rung 1: still open, needs a second phone

Nothing in software blocks this; the blocker is physical. What the 2026-11-13 Windows run
*did* establish is the half that did not need a second phone: on the campus LAN the scanner
works on Windows (no Npcap, `ping` + `arp -a` sweep, BSSID via `netsh`), 4.3 s per fresh
254-host sweep, and again only the gateway was visible — campus client isolation, exactly as
on Linux (`network_validation.md` §8, F2). So the remaining question is specifically the
**flat hotspot**, not "does the scanner work on Windows".

The measurement plan is written in `offline_fallback.md` §2 and the slot to record it is in
`network_validation.md` §6.4/§8.4. What must be recorded, because "it works" is not evidence:

1. `count` and the MACs `/wifi/scan` returns with two phones joined;
2. seconds per scan (3 runs);
3. whether the phone MAC is **stable across a rejoin** (random/private MAC must be off);
4. whether the hotspot isolates clients (if it does, rung 2 is the fallback, not rung 1).

Owner: B + one phone-owning teammate. Before the first dry run.

---

## 6. Finding 5 (Medium) — "followed by another person unaided": open, needs D

This is the one finding that cannot be closed by the author by definition. The observer
protocol, so the run produces a usable record instead of "it went fine":

- **Who:** D (or any outsider who has not read the guide), 45–60 minutes, demo laptop.
- **Rule:** B does not speak, does not point, does not touch the keyboard. Only written
  answers if the observer is truly stuck ("the guide is wrong here — write it down first").
- **Record per step:** step number → worked / ambiguous / failed → the exact text they were
  looking for → how long it took.
- **Artifacts to check afterwards:** `backend\data\models\yolov8m-face.pt` exists,
  `/health` returns ok, one check-in succeeded, one CSV downloaded.
- **Output:** append a "§6 Second-person run" table to `guide_review.md` (it currently ends
  at §5, the self-run), then fix the guide and re-run the failed steps once.

Owner: D executes, B observes and fixes the guide. Target: before the second dry run.

---

## 7. Finding 6 (Low) — macOS ping flags, closed

`_ping_command()` on Darwin now returns `ping -c 1 <ip>`: BSD `ping` has no per-packet
millisecond flag that is stable across macOS releases, and it does not need one — each call
is bounded by `subprocess.run(timeout=timeout_ms/1000 + 1)` in `_ping_sweep`, and a single
packet is all the ARP cache needs. Pinned by
`TestPingCommand::test_darwin_uses_bsd_compatible_flags`, and the wrong sentence in
`network_validation.md` §6.2 (`-c 1 -W <ms>` on macOS) is corrected.

macOS still has **no BSSID probe**. That gap is now stated (D-010, `network_validation.md`
§7.5) instead of implied to work: on a macOS host `ap_bssid` must be NULL.

---

## 8. Finding 7 (Low) — navigability and commit hygiene

- **Commit hygiene:** this round is one commit for the code fix + one for the response docs,
  so a code change can be reviewed without reading prose. (The review is right that mixing
  them, as in the previous push, costs the reviewer time.)
- **Cross-links:** D-009 and D-010 end with an **Evidence files:** line naming the exact
  file, symbol and test that back the claim. Older entries were left as they are — rewriting
  history-referenced decisions to look tidier would be cosmetic, and the review marked this
  optional.

---

## 9. What is still open, and who unblocks it

| # | Open item | Blocked by | Owner | Target |
|---|---|---|---|---|
| 1 | Merge `task-b` → `main` | reviewer availability | **A** | before the next dry run |
| 2 | `dill==0.3.8` missing from `backend/requirements.txt` (fresh install ends in `500`) | A owns the file | **A** | before dry run #1 |
| 3 | Real-face accepted check-in latency (enroll → recognize → `verified` row) | no usable face photo on this machine | B | before dry run #1 |
| 4 | Hotspot rung 1 with two phones | a second phone | B | before dry run #1 |
| 5 | Guide followed unaided by an outsider | another person | D (B observes) | before dry run #2 |
| 6 | Docker build/run on the demo laptop (optional, D-002) | Docker daemon | B | only if Docker is kept |

Item 2 is new since 2026-11-13: a **fresh** install that follows `requirements.txt` exactly
produces a working server that fails on the first face call. That is worse than a missing
feature because the smoke test catches it late. Items 3–6 were already open and are
unchanged. Nothing on this list is claimed as done anywhere in the docs; wherever it is
referenced it carries the words **not measured yet** and the reason.

The hardening findings that came out of the same run but are **not** review findings —
upload-size gap on `/faces/recognize`, a `500` instead of a clean `503` for a missing model,
and the corrupt-DB hang — are tracked with owners in `hardening_checklist.md` §2.1 and §11.
