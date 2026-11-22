# Discussion Notes — Room-Level Presence, Demo Network, and Classroom AP Setup

> **Date:** 2026-11-17 · **Participants:** team lead (A) with AI assistant · **Status:** internal working notes
> **Purpose:** record the design discussion on how the system proves classroom presence, what
> it cannot prove today, and which options could strengthen it later. These notes feed the
> December pilot plan, the M3 write-up, and the answers prepared for the supervisor.

---

## 1. Context

The end-of-November demo uses the three-condition rule: correct classroom network + valid
class time + two matching selfies. The Wi-Fi layer is the weakest link: it proves that the
**student's phone is visible on the same network segment as the server**, and — when
`ap_bssid` is pinned — that the **server** is associated with the scheduled AP. It does not
prove which AP the phone itself is associated with, and it does not measure distance.

Two supervisor answers frame the current position:

- A demo on a network the team controls (router or hotspot) is acceptable.
- "Check-in was made within the coverage area of the scheduled AP" is an acceptable claim
  when stated honestly; one AP practically covers one classroom, and even where coverage
  spills into adjacent rooms, AP capacity cannot serve all students across those rooms at
  the same time.

Supervisor follow-up (2026-11-16): use the existing NJUPT Wi-Fi, no separate AP needed.
Plan: re-test device visibility in the actual demo room before committing to that path.

---

## 2. What the system can and cannot distinguish today

| Student's real situation | Same-AP demo network | Campus network, bridged APs | Campus network with client isolation |
|---|---|---|---|
| In the scheduled classroom | accepted | accepted | **not visible → 403** |
| In the adjacent classroom, same AP coverage | **accepted** (cannot be distinguished) | **accepted** (cannot be distinguished) | not visible → 403 |
| In another building / dormitory | not visible → 403 | depends on L2 reachability | not visible → 403 |
| Wi-Fi off / mobile data only | not visible → 403 | not visible → 403 | not visible → 403 |

Key statement for the report:

> AP presence is a proxy for classroom presence, not proof of physical location inside the
> room. The current system verifies the network segment, not the individual device's AP
> association or signal distance.

---

## 3. Options to distinguish presence per classroom

### 3.1 BLE beacon per classroom (recommended for the December pilot)

A small Bluetooth Low Energy beacon is placed in each classroom. During check-in the phone
reads the beacon UUID/major/minor and sends it with the selfie; the server checks that the
beacon belongs to the scheduled room.

| Advantages | Costs / risks |
|---|---|
| Accurate per room; BLE does not pass through thick walls reliably | One beacon per classroom (hardware cost) |
| No campus IT access needed; we own and install the devices | Battery replacement every 6–12 months |
| Works offline; no cloud dependency | Phones must grant Bluetooth permission |

Indicative cost: ~IDR 75k per beacon. For 10 rooms ≈ IDR 750k one-time.

### 3.2 Rotating QR code per classroom (cheapest, software-only)

A screen/projector in each room shows a QR code that rotates every 30 seconds. The phone
scans it and sends the code with the check-in; the server validates code + timestamp.

| Advantages | Costs / risks |
|---|---|
| Zero hardware cost | Requires a screen/projector in every room |
| Rotating code resists photo forwarding | Students can still forward a screenshot within 30 s |
| Simple to implement | Rooms without a display cannot use it |

### 3.3 GPS geofencing (not recommended)

Indoor accuracy is ±10–30 m, which cannot separate room 301 from 302; GPS is trivially
spoofed and drains battery. Rejected.

### 3.4 AP management plane (ideal, blocked by access)

Reading the AP controller (SSH / SNMP / vendor API) would give client MAC ↔ associated AP ↔
RSSI ↔ association time. This is the only option that proves room-level presence for real
students on a shared campus SSID.

Verdict recorded in `docs/B/ap_management_plane.md`: **not viable for this project** — no
credentials, no authorisation, campus-owned infrastructure, vendor-dependent integration.

---

## 4. If AP admin access were available

Technically straightforward and the strongest option:

| Capability | What it gives | Effect on attendance |
|---|---|---|
| Client association table | Which AP each client MAC is attached to | Exact room check: the student's AP must equal the scheduled AP |
| Per-client RSSI | Signal strength of that client at that AP | Reject clients below a distance threshold (e.g. −72 dBm ≈ outside the room) |
| Per-AP VLAN separation | Each room's AP in its own VLAN | Isolation per room; the server only sees devices in its own room |

Implementation sketch: server polls the controller API (or SNMP `dot11StationTable`) on
check-in, resolves the student's MAC to an AP + RSSI, and compares with `schedules.ap_bssid`
plus an RSSI cut-off. This turns the current two-layer check (MAC visible + server BSSID)
into a three-layer check (MAC visible + server BSSID + **student associated to that AP with
acceptable RSSI**).

Blocked today by policy, not by code. Revisit if the school provides credentials, an SNMP
community, or a controller API account.

---

## 5. Usability: teachers should not handle BSSID values

Requiring a teacher to type a BSSID is unrealistic. Proposed UI simplification:

1. Teacher opens the dashboard **while physically in the classroom**, on the demo/server
   laptop connected to the classroom Wi-Fi.
2. Clicks **"Detect Classroom AP"**.
3. The backend reads the current AP (BSSID + SSID + subnet) — the probe chain already
   exists and is tested (`docs/B/DECISIONS.md` D-009).
4. The form shows friendly text ("Connected to AP on NJUPT-CMCC, subnet 10.163.x.0/24")
   and stores the BSSID in a hidden field.
5. "Save" completes the schedule; the teacher never sees a raw MAC address.
6. Optional warning in the dashboard when the server's current BSSID no longer matches a
   schedule's pinned AP.

Effort: small — one read-only endpoint (`GET /wifi/current-ap`) plus dashboard wiring.
Not required for the end-of-November demo; candidate for the pilot tooling.

---

## 6. Decisions / recommendations

1. Keep the current Wi-Fi claim ("coverage area of the scheduled AP") for the
   end-of-November demo. Do not add features during the scope freeze (D-005).
2. Do not demo strict mode on the campus SSID until device visibility is measured in the
   actual room. If invisible, run with `REQUIRE_CLASSROOM_WIFI=false` and state the
   `face_only` outcome openly.
3. For the December pilot, evaluate the BLE beacon as the per-room differentiator; QR code
   is the fallback where no beacon budget/approval exists.
4. Record the AP-management-plane option as future work in the final report; it is the only
   exact solution for a shared campus SSID.
5. Add the "Detect Classroom AP" dashboard helper after the presentation, not before.

---

## 7. Supervised Q&A wording (prepared for the meeting)

| Question | Prepared answer |
|---|---|
| How do you know the student is in the room? | We verify the phone is on the scheduled AP's network. One AP ≈ one classroom, which is why we describe it as the AP coverage area, not as proof of a seat in the room. |
| Could a student check in from the next classroom? | Only if the network lets the server see that phone (same AP coverage or a bridged flat network). On an isolated network they are invisible and rejected. We state this limit openly. |
| Could you make it per room? | Yes — three options: BLE beacon per room, rotating QR code per room, or reading the AP controller. The first two need no campus IT access; the controller route needs credentials we do not have. |
| What about photo spoofing? | No liveness detection; mitigations are two check-ins at different times plus network presence. Listed as a limitation. |

---

## 8. Open items

| # | Item | Owner | When |
|---|---|---|---|
| 1 | Re-test `/wifi/scan` on NJUPT in the actual demo room with 1–2 phones | lead / B | before the Monday meeting / demo rehearsal |
| 2 | Decide demo network path from that measurement | lead | before the demo rehearsal |
| 3 | BLE beacon feasibility + cost note for the December pilot | lead | after the presentation |
| 4 | "Detect Classroom AP" dashboard helper | lead (server/app ownership) | after the presentation |
| 5 | Add room-level presence paragraph to the limitations slide | C (slides) | before dry run #1 |
