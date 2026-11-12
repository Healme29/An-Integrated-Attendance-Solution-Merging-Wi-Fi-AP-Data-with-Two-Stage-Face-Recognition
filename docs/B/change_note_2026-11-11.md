# Change Note for the Team Lead — 2026-11-11 (`task-b`)

> **From:** B · **To:** A (team lead / reviewer) · **Commits:** `c5f30eb`, `c45d637`,
> plus the 2026-11-12 follow-up in §7 · **Branch:** `task-b`
> **Scope:** documentation only — zero code changes, zero behaviour changes.
> **What this note is for:** so the lead can review and merge without reading 600 added
> lines first, and so nobody re-opens the room-presence question during the demo weeks.

---

## 1. Why this commit exists

The 2026-11-09 replan (`PLAN_TIMELINE.md` §5, commit `fa93864`) gave B one new deliverable —
a timeboxed AP management-plane spike for room-level presence, "must not block the demo" —
and moved every date to a presentation around **2026-11-23**. This commit closes that
deliverable and the three items that follow from it, inside the window.

## 2. What changed, file by file

| File | Change | Why the lead should care |
|---|---|---|
| `docs/B/room_presence_spike.md` | **new** — options A–G, live measurements, verdict, stop rule, timebox accounting | This is the spike deliverable. Verdict: not viable on campus this month; exact on a network we control. Stop rule prevents it drifting into demo time |
| `docs/B/threat_model.md` | **new** — assets, trust boundaries, per-condition proof table, threats T1–T6, residual risk, fix order | Answers "can the Wi-Fi condition be gamed?" in writing, with the code line that defines it |
| `docs/B/DECISIONS.md` | **+3 entries**: D-011, D-012, D-013 | The spike verdict + stop rule; the log-capture method; the controlled-network decision with the lecturer's reply |
| `docs/B/ap_management_plane.md` | closed 2026-11-11; evidence replaced with today's numbers; no calendar revisit | Prevents someone re-opening an access question that cannot be solved without campus IT |
| `docs/B/network_validation.md` | **new §8** — what `wifi_verified` proves and what it does not; 2026-11-11 re-run table | This is the definition other documents will quote in the report |
| `docs/B/offline_fallback.md` | lecturer approval (§2), live-pinning note, **§4c** approved success wording, checklist row 10 | The sentence to say when the Wi-Fi check *passes* — the half that was missing |
| `docs/B/demo_runbook.md` | startup now logs to `backend/server_<timestamp>.log` (**§2b**), archive step, dry-run row | The "CCTV" record the demo needed; no code change |
| `docs/B/review_response.md` | finding 2 marked closed via PR #14 (`0541294`); **§10** status against the replan | Review status is now 4 of 7 closed, 3 open on hardware/people |
| `docs/PLAN_TIMELINE.md` | **new 2026-11-11 progress entry** at the top of §5 | Follows the existing convention (B entries of 2026-11-02 and 2026-11-03 are there). Move it if you want that file lead-only |
| `docs/B/change_note_2026-11-11.md` | **new** — this note | — |

Nothing outside `docs/B/*` and the one progress entry was touched. `backend/**`,
`mobile/**`, `backend/static/dashboard.html` are untouched.

## 3. The evidence in one table (all measured 2026-11-11, passive only)

| Measurement | Result | Where |
|---|---|---|
| BSSIDs of one SSID visible from one seat | 10 (`NJUPT-CMCC`), 10 (`eduroam`), 9 (`NJUPT`), 8 (`NJUPT-CHINANET`); 39 beacon rows, 6 SSIDs | spike §2 |
| Host's own AP, 3 Nov vs 11 Nov | `50:98:b8:c9:2b:e2` → `f4:74:88:70:c2:f1`, same desk | spike §2, network_validation §8.3 |
| Devices visible to the server | 1 (gateway), **6.15 s**, scapy denied → unprivileged fallback | spike §2 |
| Cold start → `/health` 200 | **9.1 s** today (cold page cache) vs 5.9 s on 2026-11-02 | runbook §2 |
| Log file capture | startup banner + access lines + scanner warnings + `Finished server process` | D-012, runbook §2b |
| Test suite | **187 passed** | — |

No probe was sent to campus equipment. The spike's negative result is the deliverable, not a
failure.

## 4. What the lead has to do

1. **Push** — B has no credentials on the working machine:
   ```bash
   git push origin task-b
   ```
2. **Open the PR** `task-b` → `main`. `task-b` is `main` + one docs commit, so the diff is
   exactly the nine files above (verified: `git diff --stat origin/main..HEAD`).
3. **Review in five minutes** if short on time: read spike §4 (verdict), D-011 (stop rule),
   threat_model §3.2 (the sentence we are allowed to say), runbook §2b (log command).
4. **Decide one thing:** whether the `PLAN_TIMELINE.md` progress entry stays (convention) or
   moves into `docs/B/`. Nothing else needs a decision.

Rollback is trivial: docs only, `git revert c5f30eb` restores the previous state with no code
impact.

## 5. What is **not** done — do not read this commit as closing them

| Open item | Blocked by | Owner | Due |
|---|---|---|---|
| G1 on the demo laptop (timed `pip install`, model warm-up, smoke) | the physical laptop | B | 2026-11-22 |
| G5 hotspot rung measured (2 phones, scan seconds, MAC stability) | a second phone | B | 2026-11-22 |
| Deployment guide followed unaided by an outsider | another person | D runs, B observes | before the December pilot |

All three still say **not measured yet** wherever they appear. Nothing in this commit claims
otherwise.

## 6. Honest wording for the report and the demo

Use the sentence in `threat_model.md` §3.2. Do not say "the system proves the student was in
the room" and do not say "the system cannot be gamed". On the assessment network (one AP, one
room) the claim is strong; on the campus network it is AP-coverage level, and that limitation
is documented rather than hidden.

---

## 7. Follow-up, 2026-11-12 (second commit on `task-b`)

| File | Change | Status |
|---|---|---|
| `docs/B/dry_run_2026-11-12.md` | **new** — seeded demo path executed end-to-end and measured: cold start 8.2 s, smoke 14/14, `/attendance/today` 5 rows, CSV correct, dashboard correct, log capture verified, restore 6.2 s + 6.1 s (re-confirms the figure in `deployment_guide.md` §8) | evidence, not a plan |
| `docs/B/mac_inventory.md` | **new** — phone-MAC collection procedure, private-MAC disable steps per platform, fill-in template, privacy/retention rules | procedure ready; table intentionally empty (needs the real phones) |
| `threat_model.md`, `network_validation.md`, `demo_environment.md`, `demo_runbook.md`, `review_response.md`, `PLAN_TIMELINE.md` | cross-links fixed, dry-run #0 recorded, disk figure updated (1.1 GB free), restore timing re-confirmed | ✅ |

Two things the follow-up changed in the operational picture:

1. **The host's subnet drifts between sessions** (`10.163.167.0/24` → `10.163.208.0/24` in
   two days). Set `WI_FI_SUBNET` explicitly on the demo network and keep the BSSID live-pinned
   (D-013).
2. **G1 cannot be measured on the B machine at all now** — 1.1 GB free, down from 6.2 GB. It
   must happen on the demo laptop.

Still open, unchanged: G1 (demo laptop), G5 hotspot with two phones, outsider guide run.

