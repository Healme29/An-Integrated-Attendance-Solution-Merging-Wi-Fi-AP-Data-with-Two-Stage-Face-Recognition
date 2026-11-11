# Room-Level Presence — Timeboxed Spike (G5, stage 2)

> **Owner:** B · **Window:** 2026-11-09 → **2026-11-11 (closed early)** · **Gate:** G5
> **Verdict: room-exact presence is NOT deliverable on the campus network this month.
> It is exact on the demo network we control, which is the one the assessment uses.**
> **Stop rule:** the spike ends 2026-11-11 regardless of outcome. After that date it may
> only be reopened by a trigger in §7, never by a new idea. Time freed here goes to G1
> (demo machine) and G5 (hotspot rung), both due 2026-11-22.
>
> **Companion documents:** `threat_model.md` (what the three conditions prove, T1–T6),
> `ap_management_plane.md` (the access question in detail), `network_validation.md` §8
> (what `wifi_verified` means), `DECISIONS.md` D-011/D-013.

---

## 1. The question

> Can the system prove that a student's phone is **inside the scheduled classroom**, not
> merely somewhere on the same subnet?

The weakness that motivates the question: `check_mac_on_network()` only compares the
student's MAC against `scan_network_arp()` output (ARP scan, or ping + neighbour-table
fallback). If several classrooms share one broadcast domain, a phone in room 202 is visible
to a check-in for room 201, and no code on the server can tell them apart (recorded as T1 in
`threat_model.md`).

The spike had one job: decide whether a room-level signal is obtainable **with the access
we actually have**, or whether it must be declared future work. Both answers are acceptable;
an unverified claim is not.

## 2. Live evidence collected today (2026-11-11, passive only)

No management-plane probe was sent to campus equipment — no credentials, and probing
third-party infrastructure without authorisation is out of scope by policy
(`ap_management_plane.md` §3). Everything below comes from the machine's own association
and the beacons every Wi-Fi client already hears.

| # | Measurement | Command | Result |
|---|---|---|---|
| 1 | Subnet the host is on | `ip -4 -o addr show` | `wlo1 10.163.167.58/17` → sweep caps to `10.163.167.0/24` |
| 2 | Current AP (BSSID) | `wifi_scanner.get_current_bssid()` | `f4:74:88:70:c2:f1` (`NJUPT-CMCC`) |
| 3 | Same host, 2026-11-03 | `network_validation.md` §7.2 | `50:98:b8:c9:2b:e2` (`NJUPT-CMCC`) |
| 4 | Distinct BSSIDs of one SSID visible from one seat | `nmcli -t -f BSSID,SSID device wifi list` | **10** BSSIDs for `NJUPT-CMCC`, **10** for `eduroam`, **9** for `NJUPT`, **8** for `NJUPT-CHINANET` (39 beacon rows, 6 SSIDs) |
| 5 | Clients visible to the server | `wifi_scanner.scan_network_arp()` | **1** device — the gateway `70:c6:dd:09:b0:02` — in **6.15 s** |
| 6 | Privileged path | — | `scapy` ARP scan denied (`Operation not permitted`); unprivileged ping+neighbour fallback used |

Three facts follow directly from 3–5:

1. **The SSID carries no room information.** One SSID is broadcast by at least ten APs, so
   "on `NJUPT-CMCC`" narrows the location to a building-sized area, not a room.
2. **The host's AP changes between sessions at the same desk** (`50:98:…` → `f4:74:…` over
   eight days). A `schedules.ap_bssid` value copied from an earlier session is therefore
   stale, and no one on the team can say which AP serves which room without the campus
   map.
3. **The server cannot see other clients.** Only the gateway answers; client isolation /
   VLAN separation is still in force (unchanged from 2026-10-25). Even a perfect room map
   would not let the server observe a phone's AP.

Fact 2 is why live pinning (`DECISIONS.md` D-013) is mandatory at the demo: the BSSID must
be read on the demo network at setup time, never reused from a previous network.

## 3. Options, with the actual blocker

| # | Mechanism | What it would prove | Cost | Blocker today |
|---|---|---|---|---|
| **A** | SSH into the classroom AP, read its client table | Phone MAC ↔ BSSID ↔ RSSI ↔ association time — true room-level | ~1 day (paramiko) | No admin credentials; campus IT owns the device |
| **B** | SNMP poll (`dot11StationTable`, `dot11AssocStationTable`) | Same as A | ~0.5 day (pysnmp) | SNMP disabled or restricted to the management VLAN; community string unknown; no authorisation |
| **C** | Vendor controller API (UniFi / Ruijie / H3C) | Same as A, aggregated | 1–3 days | No controller account; the controller is not ours |
| **D** | The app reports **its own** BSSID; schedule holds a BSSID list | The phone's AP, without touching campus gear | 4–8 h (C) | iOS needs the `NEHotspotNetwork` entitlement plus location permission; cannot be built or tested this month (C has no Flutter tooling — C-002) |
| **E** | Per-room SSID or VLAN | Room identity *is* the network identity | campus IT change | Not in the team's control; not a software task |
| **F** | Rotating classroom token on the dashboard (QR/number) | Physical presence at check-in time, independent of network | 4–6 h (A) + ~3 h (C) | Real fix for proxy attendance too, but it is A's + C's surface, and untested additions to the demo are the bigger risk this month (D-007) |
| **G** | Use a router **we control**, read its client table | Exact room-level: one AP, one room, clients we can list | ~1 day setup | None for the assessment — this is the demo configuration (D-013) |

## 4. Verdict

- **A, B, C — not viable.** The blocker is authorisation, not code. Writing an integration
  we cannot run would be a claim without evidence.
- **E — not ours to decide.** Infrastructure change owned by campus IT.
- **D — plausible, not testable this month.** It is the right next step and is recorded as
  such; it is not a demo dependency.
- **F — the strongest non-network mitigation**, but it belongs to A and C and does not fit
  the frozen demo scope (D-007). Recommended first post-demo fix alongside authentication
  (`threat_model.md` §6).
- **G — viable and adopted for the assessment.** On a router we control, room-level presence
  is effectively exact because there is exactly one AP and one room. This is also what the
  lecturer approved: demonstrating on a network we control is acceptable, and "in practice,
  an AP only covers one classroom" (D-013).

**Net result:** on the assessment network the claim is strong; on the campus network it
stays at AP-coverage level and is stated as a limitation. Nothing in the demo depends on a
mechanism that was not measured.

## 5. What we do instead (no new code)

1. **Demo on the router/hotspot we control** (D-013). Capture its BSSID at setup and pin it
   live; one AP, one room, so "the check-in happened here" is true at AP granularity.
2. **Keep `schedules.ap_bssid` pinning.** It proves the **server** is on the scheduled AP —
   a weaker but honest claim, and the one the lecturer accepted.
3. **State the limitation in the report and in the demo narration**, using the sentence in
   `threat_model.md` §3.2 — never "the system cannot be gamed".
4. **Keep the audit trail.** `ap_logs` stores MAC + timestamp + server BSSID, so a disputed
   check-in can be examined after the fact even though it cannot be auto-detected.
5. **Do not add D or F before the presentation.** Both are recorded as post-demo work.

## 6. Residual risk after this verdict

| Risk | Level on demo network | Level on campus pilot | Where it is stated |
|---|---|---|---|
| Phone in another room on the same L2 | negligible (single AP, one room) | medium | `threat_model.md` T1, §3.1 |
| Proxy attendance | unchanged (identity binding + two selfies) | high | `threat_model.md` T2 |
| MAC spoofing / randomised MAC | low (MAC list per demo phone, `offline_fallback.md` §4b) | high | `threat_model.md` T3 |
| Unauthenticated API | low (isolated demo network) | high | `threat_model.md` T5 |

## 7. Triggers that reopen the spike

| Trigger | Then |
|---|---|
| Campus IT provides AP credentials, an SNMP community, or controller API access | re-open A/B/C, timebox again, prototype against the real device |
| The school buys the AP we specify (local controller) | implement G on classroom hardware, test an RSSI cut-off |
| C regains Flutter tooling and a test device | prototype D (app-reported BSSID), starting with Android only |
| Pilot shows `face_only` on > 50 % of check-ins | escalate: room-level presence moves from "future work" to a demo blocker |

**Revisit by:** after the November assessment (M3), or immediately if a trigger fires.

## 8. Timebox accounting

| Date | Work | Output |
|---|---|---|
| 2026-11-11 — session 1 | Read the mandate (`PLAN_TIMELINE.md` §5), re-read `ap_management_plane.md`, list options A–G | option table |
| 2026-11-11 — session 2 | Passive measurement of the campus network (rows 1–6 above) | evidence table §2 |
| 2026-11-11 — session 3 | Verdict, stop rule, cross-links to `threat_model.md` and D-011/D-013 | this document |

Total: three short sessions on one day, inside the 2026-11-09 → 2026-11-22 window. No campus
probe, no new dependency, no demo dependency. The spike is **closed**, not suspended — the
remaining eleven days of the window go to G1 and G5.
