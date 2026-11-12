# Review Response — Task B (`task-b`), review of 2026-11-02

> **Review under response:** "Review of Task B — Backend, Real Wi-Fi Validation &
> Deployment", 8.5/10, accepted to merge after findings 1 and 2.
> **Response date:** 2026-11-03 · **Branch:** `task-b` · **Owner:** B
>
> Rule used here: a finding is only marked **closed** if there is a measurement or a test
> that anyone can re-run. Anything that needs hardware or another person stays **open** and
> says who has to do it.

---

## 1. Status of every finding

| # | Finding | Status | Where the proof is |
|---|---|---|---|
| 1 | BSSID read depends on deprecated `iwconfig` (High) | ✅ **closed** | `network_validation.md` §7, D-009, `test_wifi_subnet.py` |
| 2 | Fixes live only on `task-b`, `main` still broken (High) | ✅ **closed** — PR #14 merged into `main` as `0541294` on 2026-11-03 (merge by `hocsilens`, zero file changes vs `task-b`) | §3 below, kept as the record of how it was verified |
| 3 | G1 + `pip install` not run on the demo laptop (Medium) | ⏸ **open** — blocked by hardware and by disk on this machine | `demo_environment.md` §6 item 5, §6.1 |
| 4 | Hotspot rung 1 unmeasured (Medium) | ⏸ **open** — needs a second phone | `offline_fallback.md` §2 |
| 5 | "Guide followed by another person unaided" (Medium) | ⏸ **open** — needs D or an outsider | §6 below: observer checklist |
| 6 | macOS `ping -W` is not a BSD flag (Low) | ✅ **closed** | D-010, `TestPingCommand` |
| 7 | Mixed commit contents, decisions without file links (Low) | ✅ **closed** (forward-looking part) | every new decision entry ends with **Evidence files:** |

Closed: 4 of 7 (both High ones that were code, the merge, plus the Low flag bug).
Open: 3 (all three need a physical demo laptop, a second phone, or another person — no amount
of code on this machine can close them).

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

Full suite: **187 passed** (34 in the scanner file).

### Operator-facing consequence

`offline_fallback.md` gained §4b: a pre-demo check for `"bssid": null`, the one-line fix
(set `ap_bssid` to NULL rather than hand-typing a MAC), and the sentence to say out loud.
A Wi-Fi feature that switches itself off is now either visible in the log or in the
checklist — never silent.

---

## 3. Finding 2 (High) — merge is safe, but it needs A, not B — **closed by PR #14**

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

## 4. Finding 3 (Medium) — G1 on the demo laptop: still open, and honestly so

Two halves, and they are not the same risk.

**4.1 The timed `pip install` was not run here, on purpose.** This machine's root filesystem
has **6.2 GB free** (90 % used). `ultralytics` pulls `torch` plus the `nvidia-*` CUDA wheels —
2–3 GB of downloads and more unpacked. Running the measurement here would fill the disk and
destroy the working environment, so the number would cost more than it is worth. It is
recorded as **not measured yet** rather than estimated (`demo_environment.md` §6.1).

**4.2 G1 on the physical laptop is the measurement that matters**, and it needs the laptop.
The table to fill in is already written; the steps are §5b and §12 of
`deployment_guide.md`. What to paste into `demo_environment.md` §6:

| Measurement | Command | Unit |
|---|---|---|
| full install | `time pip install -r backend/requirements.txt` (fresh venv) | minutes |
| cold start → health | start server, poll `/health` until ok | seconds |
| model warm-up | first `/faces/recognize` (downloads `buffalo_l`) | minutes + MB |
| first check-in after warm-up | `/attendance/check` | seconds |
| `/wifi/scan` on the demo network | includes `bssid` and `subnet` | seconds, device count |

Owner: B, on the demo laptop, before dry run #1. Cannot be done from this machine.

---

## 5. Finding 4 (Medium) — hotspot rung 1: still open, needs a second phone

Nothing in software blocks this; the blocker is physical. The measurement plan is already
written in `offline_fallback.md` §2 and the slot to record it is in
`network_validation.md` §6.4. What must be recorded, because "it works" is not evidence:

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
- **Output:** append a "§7 Second-person run" table to `guide_review.md`, then fix the guide
  and re-run the failed steps once.

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
| 1 | ~~Merge `task-b` → `main`~~ | — | ~~A~~ | **closed 2026-11-03, PR #14 → `0541294`** |
| 2 | G1 table + timed `pip install` on the demo laptop | the laptop | B | before dry run #1 (now before 2026-11-23) |
| 3 | Hotspot rung 1 with two phones | a second phone | B | before dry run #1 (G5, 2026-11-22) |
| 4 | Guide followed unaided by an outsider | another person | D (B observes) | before the December pilot |

Nothing on this list is claimed as done anywhere in the docs. Wherever it is referenced, it
carries the words **not measured yet** and the reason.

---

## 10. Update 2026-11-11 — the replan added work, and it is done

A's accelerated-timeline commit `fa93864` (2026-11-09) gave B one new deliverable and moved
every date forward. Status against it:

| New item from `PLAN_TIMELINE.md` §5 | Status | Evidence |
|---|---|---|
| Timeboxed AP management-plane spike for room-level presence, 9–22 Nov, must not block the demo | ✅ **closed 2026-11-11** | `room_presence_spike.md` (options A–G, measurements, verdict, stop rule), D-011 |
| The subnet-collision weakness must be documented, not hidden | ✅ **written** | `threat_model.md` (assets, trust boundaries, T1–T6, residual risk, fix order), `network_validation.md` §8 |
| Lecturer's written answers must be reflected in the claims | ✅ **done** | D-013, `threat_model.md` §3.1–3.2, `offline_fallback.md` §4c |
| Log written to a file on demo day ("CCTV") | ✅ **procedure + measured output** | D-012, `demo_runbook.md` §2b |
| Seeded demo path executed end-to-end (fallback rung 3 + rung 4) | ✅ **dry run #0, 2026-11-12** | `dry_run_2026-11-12.md` (cold start 8.2 s, smoke 14/14, CSV/dashboard correct, restore 6.2/6.1 s) |
| Phone MAC inventory procedure + template (original duty 4, never written) | ✅ **procedure ready; table deliberately empty** | `mac_inventory.md` |

Still open from §9: G1 (demo laptop), hotspot with two phones, outsider guide run. All three
need hardware or another person, and all three are still recorded as **not measured yet**.

The finding 2 process note is kept above unchanged: the review's rule was that B must not
merge its own branch, and B did not — A merged it after the two High findings were answered.

