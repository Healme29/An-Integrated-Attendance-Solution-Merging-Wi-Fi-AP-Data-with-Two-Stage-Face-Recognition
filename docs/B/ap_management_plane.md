# AP Management Plane — Feasibility Verdict (G5 spike, timeboxed)

> **Timebox:** 2 hours of B's time, stage 2 (2026-11-09 → 2026-11-22).
> **Verdict: NOT VIABLE for this project.** The demo must not depend on it.
> **Why this document exists:** a negative finding is a result. It must be written down so
> nobody re-opens the idea during the demo weeks.

---

## 1. What we wanted

`/wifi/scan` can only prove "this MAC is somewhere on the same L2 segment". The stronger
claim a teacher actually wants is "this student is **inside this room**", ideally with a
signal-strength cut-off (the ~ −72 dBm idea from `docs/network_validation.md`). Reading the
AP's own client table would give: client MAC ↔ associated AP (BSSID) ↔ RSSI ↔ association
time. That is the management plane.

## 2. Options considered

| # | Option | Cost | Risk / blocker |
|---|---|---|---|
| 1 | SSH into the classroom AP and parse its client table | low code (paramiko), 1 day | needs admin credentials we do not have; AP firmware varies; campus IT owns the device |
| 2 | SNMP poll (`dot11StationTable`, `dot11AssocStationTable`) | low code (pysnmp), half a day | SNMP is usually disabled or restricted to the management VLAN; community string unknown; no authorisation to poll campus infrastructure |
| 3 | Vendor controller API (UniFi / Ruijie / H3C) | medium code, 1–3 days | requires a controller account and API access; the campus controller is not ours |
| 4 | Buy/host our own AP for the demo (router we control) | ~1 day setup, hardware cost | not a management-plane integration, but it gives us the **same observable evidence** (our own client table) and Wi-Fi we can configure |

## 3. Evidence collected (what was actually possible without admin rights)

- The campus SSID is shared across many classrooms (`NJUPT-CMCC`, BSSID
  `50:98:b8:c9:2b:e2` at the test location); there is no per-room SSID.
- Our own machine can read **its own** association only (`iwconfig` / `netsh wlan show
  interfaces`), never another client's.
- No credentials, controller URL or SNMP community string were provided by the school, and
  the team has no authorisation to poll campus network gear. Probing was therefore **not
  attempted** — that is a policy decision, not a technical failure.
- The scan already shows the campus network isolates clients / splits VLANs (F2), so even
  a perfect ARP table would not see the phones.

Not measured: SSH reachability, SNMP response, controller API availability. Without
authorisation these would be unauthorised probes of third-party infrastructure.

## 4. Verdict and what we do instead

**Not viable in the project timeframe (M2).** The blocker is access, not code: no
credentials, no authorisation, and no hardware we can reconfigure. Building an integration
we cannot test would be a claim without evidence.

Instead:

1. Run the demo/pilot on a **network we control**: a dedicated classroom router or a
   hotspot with client isolation off. There the ARP/ping scan works (it was measured to
   find devices on a flat network in `network_validation.md` §3).
2. Keep `schedules.ap_bssid` pinning: it proves the **server** is on the scheduled AP, which
   is a weaker but honest claim ("the check-in was made in the right room's coverage area").
3. State the limitation explicitly in the report: room-level presence per student is future
   work (RSSI + AP client table), blocked by management-plane access.

## 5. What would change the verdict

| Trigger | Then |
|---|---|
| The school gives AP admin credentials, an SNMP community, or controller API access | re-open option 1/2/3, timebox again, prototype against the real device |
| The school buys the classroom AP we specify (e.g. a UniFi AP with a local controller) | implement option 3/4, test RSSI cut-off with real phones |
| A pilot shows `face_only` on > 50 % of check-ins because of isolation | escalate: room-level presence moves from "future work" to a demo blocker |

**Revisit by:** 2027-03-01 (M3 hardening), or immediately if any trigger above fires.
