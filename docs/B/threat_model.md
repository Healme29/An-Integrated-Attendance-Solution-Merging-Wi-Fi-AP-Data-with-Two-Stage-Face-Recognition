# Threat Model — What the Three Conditions Prove (and What They Do Not)

> **Owner:** B · **Created:** 2026-11-11 · **Status:** living document, reviewed whenever a
> condition changes · **Related:** `room_presence_spike.md` (why room-exact proof is out of
> scope this month), `network_validation.md` §7–§8, `DECISIONS.md` D-011/D-013.
>
> **Why this file exists:** the honest question "can a student game the Wi-Fi condition?"
> cannot be answered "no". This document states precisely what each condition establishes,
> which attacks it stops, which it does not, and what we say about it in the report and
> during the demo. Every claim below is tied to code that exists, not to intent.

---

## 1. Assets

| Asset | Where | Why it matters |
|---|---|---|
| An attendance row with `status = 'verified'` | `attendance` table | This is the only artefact that says "present, on time, in the right room" |
| A student's identity binding | `students` + `faces` tables | Decides *who* the attendance row belongs to |
| The AP↔room mapping | `schedules.ap_bssid` | Decides *where* the check-in is allowed to happen |

The system's whole value is the integrity of the first row. Everything else supports it.

## 2. Trust boundaries

```
[phone app]  --HTTP, no auth-->  [backend]  --raw ARP / neighbour table-->  [L2 network]
   untrusted                     trusted            unauthenticated observation
                                                          |
                                                   [AP / router]
                                       controlled at the demo, campus-managed otherwise
```

Two boundaries are weak by construction and are documented instead of hidden:

1. **The app→backend boundary has no authentication.** There is no session token, no API
   key, no per-device credential: `POST /attendance/check?student_id=…` accepts a
   `student_id` from anyone who can reach port 8000 (verified: no auth dependency in
   `backend/routers/*.py`). The face match is the only gate on identity.
2. **The L2 boundary only observes.** `check_mac_on_network()` compares the student's MAC
   against `scan_network_arp()` (ARP scan, or ping + neighbour-table fallback,
   `backend/services/wifi_scanner.py`); it sees *that* a MAC is reachable on the subnet, never
   *which AP* that MAC is associated with.

## 3. What each condition actually proves

Implementation reference: `backend/services/attendance.py` lines 186–198.

| Condition | Mechanism | Proves | Does **not** prove |
|---|---|---|---|
| **Face** | YOLOv8-face detection → ArcFace embedding → cosine ≥ `FACE_SIMILARITY_THRESHOLD` (0.5), must match the logged-in `student_id` | The face in the frame resembles that student's enrolled faces | That a live person is present (no liveness/anti-spoofing) |
| **Time** | Schedule day + `start_time`–`end_time` ± `ATTENDANCE_CHECK_WINDOW_MINUTES` (15) | The request was made during the class window | That the student stayed for the class |
| **Wi-Fi** | `check_mac_on_network(student.mac_address)` **and**, when `schedules.ap_bssid` is set, `is_same_bssid(get_current_bssid(), ap_bssid)` | The student's device is reachable on the same L2 as the check-in machine, **and** the check-in machine is associated with the scheduled AP | Which AP the student's phone is on; that the phone is inside the room; that the MAC belongs to that physical phone |
| **Two-stage** | `start` stored as `partial`; `end` becomes `verified` only if both rows had `wifi_verified = true` | Presence at two separate moments | That the student was present in between |

### 3.1 The wording we are allowed to use

The lecturer (Zhe Zhang, reply received 2026-11-11) accepted the claim **"the check-in was
made within the coverage area of the scheduled AP"**, provided the limitation is stated
honestly, and added the practical argument:

> "In practice, an AP only covers one classroom. Even an AP can cover multiple classrooms,
> the capacity is not enough to hold all students."

He also confirmed that demonstrating on **a network we control** is acceptable ("Either
should be fine"). Both answers are recorded in `DECISIONS.md` D-013.

### 3.2 The sentence to say out loud (demo and report)

> "The Wi-Fi condition proves that the student's device was on the classroom network while
> the check-in machine was associated with the scheduled AP — that is, within that AP's
> coverage area. It does not prove the phone was inside room 201, and we never claim to know
> which AP a phone is attached to."

## 4. Threat table

Severity is judged for **the campus pilot** (shared L2, real students); the assessment demo
runs on a controlled network (D-013), which lowers T1, T5 and T6 to negligible.

| # | Attack | What the attacker needs | Detected today? | Severity | Mitigation now | Mitigation later |
|---|---|---|---|---|---|---|
| **T1** | Check in from another room on the same subnet | Phone on the same L2 as the server, outside the AP's coverage | No automatic detection. `ap_logs` stores MAC + timestamp + server BSSID, so an audit is *possible* after the fact | Medium on campus; negligible on the controlled demo network | Demo on a network we control; single AP per room by construction; AP-coverage wording (§3.1) | Phone-reported BSSID (app, D-011 option D) or per-room SSID (option E) |
| **T2** | Proxy attendance (phone handed to a friend) | The friend must present the *student's* face (a photo of it); a selfie of the friend is rejected by identity binding (403) | No automatic detection; timestamps of `start`/`end` and `faces_detected` are stored | High in general | Identity binding + two separate selfies raise the cost well above a naive proxy | Rotating classroom token on the dashboard (D-011 option F) |
| **T3** | MAC spoofing / randomised MAC | Set a device's MAC to the enrolled MAC (rooted Android, laptop), or fail to disable private MAC | No; a wrong MAC produces a false *negative* (`face_only`), a spoofed one a false *positive* | High when combined with T2/T4 | Controlled network; MAC list per demo phone (`offline_fallback.md` §4b) | Device key created at enrollment (public-key binding instead of MAC) |
| **T4** | Presentation attack (printed photo / screen instead of a face) | A photo of the student, good light, phone held still | No liveness check exists | Medium | Enrolment photos done beforehand; invigilation at the demo; stated as a limitation | Liveness detection — out of scope for this timeline |
| **T5** | Call the API directly, bypassing the app | Any device on the LAN: `POST /attendance/check?student_id=N&…` with a matching face image. **No authentication exists** | Not at the API layer; the face still has to match | High on an open LAN; low on the demo network | Demo network only; port 8000 not exposed beyond it; documented here | Session/token after NIM login, HTTPS (owner: A for backend, C for app) |
| **T6** | Replay a captured check-in request | Read the plaintext HTTP request on the LAN during the window | No anti-replay nonce | Low (narrow window) | Controlled network | Nonce + signed timestamp, HTTPS |

## 5. Residual risk we disclose in the report

1. **Location is AP-level, not room-level.** Accepted by the lecturer under the
   coverage-area wording; a multi-room AP or a multi-AP room weakens it, and both cases are
   named.
2. **Identity rests on the face only** — no liveness, no device credential; the API is
   unauthenticated. Anyone who obtains a good photo of a student and LAN access can attempt a
   check-in; whether they succeed depends on similarity thresholds, not on authentication.
3. **MAC addresses are identifiers, not credentials.** Spoofing is trivial and MAC
   randomisation creates false negatives; the system treats a MAC match as a hint, never as
   proof of a specific handset.

## 6. What we would fix first, in order, if the timeline allowed

| Priority | Fix | Closes | Effort (estimate, not measured) | Owner |
|---|---|---|---|---|
| 1 | Session token after NIM login + HTTPS | T5, T6 | medium | A (+ C for the app) |
| 2 | Rotating classroom token on the dashboard | T2 (remote proxy), raises T1's cost | small–medium | A (dashboard moved to C) |
| 3 | Phone reports its own BSSID; schedule may hold a BSSID list | T1 | medium; iOS entitlement risk | C |

Nothing on this list was started; the deadline (presentation ≈ 2026-11-23) makes adding an
untested mechanism to the demo the larger risk. This is the same conclusion recorded in
`room_presence_spike.md` §4.
