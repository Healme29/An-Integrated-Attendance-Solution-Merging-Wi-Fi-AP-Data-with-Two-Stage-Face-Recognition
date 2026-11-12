# Wi-Fi Network Validation — Real Network Results (Task B1)

> **Date of tests:** 2026-10-25 (campus network, Windows) · **re-run:** 2026-11-02 (Linux, scanner fix)
> **Tested by:** member A (on behalf of B) + member B's manual checks
> **Server:** `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000`,
> `TIMEZONE=Asia/Shanghai`
> **Scanner implementation:** ping sweep + `arp -a` parsing (Windows) / scapy ARP with a
> ping + `ip neigh` fallback (Linux) — **no Npcap required** on either platform

---

## 1. Environment

| Item | Value |
|---|---|
| OS | Windows 10.0.26200 |
| Laptop Wi-Fi IP | `10.163.235.210` **prefix /17** (netmask `255.255.128.0`) |
| Default gateway | `10.163.255.254` (MAC `70:c6:dd:09:b0:02`) |
| Current BSSID (laptop's AP) | `54:2b:de:fd:90:21` |
| Network type | Campus Wi-Fi (multiple classrooms, DHCP, one shared SSID) |
| Scanner | `scan_network_arp()` — ping sweep of the /24 + `arp -a` parse, 10 s result cache, 60 s `ap_logs` dedupe |

---

## 2. Test matrix (actual results, not predictions)

| # | Scenario | Command | Expected | Actual | Verdict |
|---|---|---|---|---|---|
| 1 | Subnet auto-detect (`WI_FI_SUBNET` unset) | `GET /wifi/scan` | subnet matches the interface | returned `10.163.235.0/24` while the interface is `10.163.235.210/17` | ⚠️ **too narrow** (see F1) |
| 2 | Device discovery (phone on the same Wi-Fi) | `GET /wifi/scan` | phone MAC appears | `count=1`, only the gateway `10.163.255.254` was found | ⚠️ **campus segmentation** (see F2) |
| 3 | Check a known MAC | `GET /wifi/check/70:c6:dd:09:b0:02` | `on_network: true` | `{"on_network": true, "bssid": "54:2b:de:fd:90:21"}` | ✅ |
| 4 | Check an unknown MAC | `GET /wifi/check/aa:bb:cc:dd:ee:99` | `on_network: false` | `{"on_network": false}` | ✅ |
| 5 | 60 s dedupe in `ap_logs` | two scans back-to-back | ≤ 1 new row per MAC per 60 s | `ap_logs` 9 → 10 rows (only **one** new row across two scans) | ✅ |
| 6 | Scan duration (fresh) | timed request | a few seconds | **2.4 s** | ✅ |
| 7 | Scan duration (cached) | immediate second request | ≈ 0 s | **0.0 s** (10 s cache) | ✅ |
| 8 | BSSID read | `GET /wifi/scan` | real AP BSSID | `54:2b:de:fd:90:21` (stable across runs) | ✅ |
| 9 | BSSID pinning (mismatch) | schedule with `ap_bssid` ≠ current AP | `wifi_verified=0` → status `face_only` | covered by automated test `test_two_stage_check_in_no_wifi_face_only`; live run needs an active window + real capture | ⚠️ **automated coverage only** |

### Real check-in evidence (same network, same session)

Two real two-stage check-ins were completed through the Flutter app on this network
(schedule `Demo Interactive`, room `Ruang Demo 105`):

| Attendance id | Check | Confidence | Wi-Fi verified | Status |
|---|---|---|---|---|
| 11 | start | 0.7075 | yes | verified |
| 12 | end | 0.7212 | yes | verified |

> ⚠️ **Demo artifact, read carefully:** student "Buchari" (id 8) is registered with
> MAC `70:c6:dd:09:b0:02`, which is the **campus gateway's own MAC**. The Wi-Fi check
> therefore always succeeds for this demo student. For the real pilot every student must
> be registered with **their own phone's Wi-Fi MAC**, otherwise the AP check proves nothing.

---

## 3. Findings (why results are what they are)

### F1. Subnet auto-detection assumes /24 — interfaces can be wider (real bug class) — **FIXED 2026-11-02**

`detect_local_subnet()` now derives the actual netmask from the interface (`ip -4 addr`
on Linux, `ipconfig` on Windows). If the network is wider than /24 the code logs a
warning and reports/sweeps **only the /24 containing this machine** (capped at 254
hosts). An explicit `WI_FI_SUBNET` wider than /24 is reduced the same way. The `/wifi/scan`
`subnet` field is now exactly the range that was pinged, so an operator can tell at a glance
what was searched.

On the 2026-10-25 campus network the interface was `/17` (`10.163.235.210/17`); the
scanner now returns and sweeps `10.163.235.0/24` (or the /24 of the host IP). Devices in
other /24s inside the /17 would still be missed unless `WI_FI_SUBNET` is set to their /24
or the sweep is expanded — but a full /17 sweep (32k hosts) takes minutes and is not
practical from a laptop, so the explicit-subnet + "scan the room's /24" guidance remains.
Tests: `backend/tests/test_wifi_subnet.py` (19 tests).

### F2. Only the gateway was visible — campus segmentation / client isolation
Inside `10.163.235.0/24` only the gateway answered. Two possible causes, both common on
campus networks:

1. **Client isolation (AP isolation)** on the SSID — clients cannot see each other, so
   ARP/ping never succeeds between two phones/laptops;
2. **VLAN/segment splitting** — the phone received an IP in a different /24 than the
   scanner's sweep range.

Consequence: ARP scanning from the server laptop is only reliable on a **flat, small
network where clients can see each other** (home router, a dedicated classroom AP with
isolation disabled, or a hotspot used for the demo).

### F3. Dedupe works as designed
`log_seen_devices()` skips rows for the same MAC within 60 s; the second scan produced no
new rows. This keeps `ap_logs` clean during rapid polling (relevant for the planned 5-minute
presence tracker in M2).

### F4. Scan speed is acceptable for check-in, too slow for continuous tracking
2.4 s per fresh scan (ping sweep of 254 hosts + ARP parse) and ~0 s within the 10 s cache.
A 5-minute presence tracker is therefore feasible time-wise (one fresh scan per tick), but
see F2 — on an isolated campus SSID it would mostly record "away" for everyone.

### F5. BSSID is readable and stable, but pinning alone cannot prove "inside the room"
`get_current_bssid()` returned `54:2b:de:fd:90:21` consistently. BSSID pinning correctly
rejects check-ins when the server is attached to a different AP. However, the server reads
**its own** BSSID, not the student's — the student's association is not observable from
ARP alone. Room-level presence needs the AP management plane (see Recommendations).

---

## 4. Recommendations

| Priority | Action | Why |
|---|---|---|
| **Pilot (M1)** | Set `WI_FI_SUBNET` explicitly to the classroom's /24 and register each student's **real phone MAC** (disable "private/random MAC" for the school SSID during enrollment; collection procedure and template in `mac_inventory.md`) | makes the AP check meaningful and predictable |
| **Pilot (M1)** | Run the demo/pilot on one access point where client isolation is **off** (or a dedicated router/hotspot) | ARP scanning then sees the phones |
| **M2** | Read client↔AP association + RSSI from the AP management plane (SSH/SNMP/controller API); pin the room via `schedules.ap_bssid` | real room-level presence; enables the RSSI threshold idea (~ -72 dBm ≈ outside the room) |
| **M2** | ✅ **DONE 2026-11-02:** derive the true netmask in `detect_local_subnet()`, cap the sweep, and report exactly what was swept | F1 is fixed; `/wifi/scan` no longer claims a range it did not search |
| **M2** | 5-minute presence tracker using dedupe + cached scans; away episodes visible on the teacher dashboard | the "student left mid-lesson" feature requested by the school |

---

## 5. Summary for the progress report (to member D, deadline 2026-10-29)

**Paragraph:** The Wi-Fi presence check was validated on a real campus network
(`10.163.235.210/17`, AP BSSID `54:2b:de:fd:90:21`). A fresh scan takes **2.4 s**
(0 s within the 10 s cache), the MAC lookup endpoint answers correctly for known and
unknown devices, and the 60 s dedupe keeps `ap_logs` at exactly one row per device per
minute. Two real two-stage check-ins through the mobile app completed successfully on this
network (confidence 0.71/0.72, status `verified`). The validation also exposed the main
limitation to report honestly: ARP scanning from the server laptop only sees devices in the
same flat /24 — the campus network is a /17 with (at least) client isolation or VLAN
splitting, so only the gateway was visible. Room-level presence therefore requires reading
client↔AP associations from the AP management plane (M2), which is also the prerequisite
for the RSSI-based "outside the room" threshold.

**Table (short version):**

| Check | Result |
|---|---|
| Scan duration (fresh / cached) | 2.4 s / 0.0 s |
| Subnet auto-detect | ⚠️ returns /24 although the interface is /17 |
| Devices visible on campus SSID | only the gateway (client isolation or VLAN split) |
| Known MAC check | ✅ `on_network: true` |
| Unknown MAC check | ✅ `on_network: false` |
| 60 s dedupe | ✅ one `ap_logs` row per MAC per minute |
| BSSID read | ✅ `54:2b:de:fd:90:21` (stable) |
| BSSID pinning mismatch | ✅ covered by automated tests (`face_only`) |
| Real two-stage check-in on this network | ✅ ids 11 & 12, `verified`, 0.71/0.72 |

---

## 6. Re-run on 2026-11-02 — scanner fixes measured on a real /17 interface

Second measurement session, on a Linux laptop on the same campus SSID
(`NJUPT-CMCC`, interface `wlo1` **10.163.216.151/17**, AP `50:98:b8:c9:2b:e2`), to verify the
F1 fix and to find out what the scanner does where raw sockets are not available.

### 6.1 Subnet detection before/after

| | Old code | New code |
|---|---|---|
| Detected network | `10.163.235.0/24` (hard-coded /24, real netmask ignored) | `10.163.128.0/17` (from `ip -4 addr`) |
| Range reported by `/wifi/scan` | `10.163.235.0/24` — **not** what was reachable | `10.163.216.0/24` — the /24 of this host, i.e. exactly what is swept |
| Hosts pinged | `.1`–`.254` of the last octet | 254 hosts of the reported /24 (a /25 would ping 126) |
| Operator feedback | silent | log line: `Interface network 10.163.128.0/17 is wider than /24; sweeping only 10.163.216.0/24` |

The reported subnet now matches the sweep, which removes the "it says /24 but the network is
/17" ambiguity from the earlier report. Devices in other /24s of the /17 are still missed by
design (a /17 sweep is not feasible); `WI_FI_SUBNET` must name the classroom /24.

### 6.2 Linux without root: raw sockets fail, fallback works

First attempt on Linux returned nothing because scapy needs `CAP_NET_RAW`:

```
PermissionError: [Errno 1] Operation not permitted   (socket(AF_PACKET, SOCK_RAW))
```

The same error made 4 pytest tests fail on Linux (3 prompt tests + the Wi-Fi cache test)
while they passed on Windows — a portability bug nobody had noticed. The scanner now:

1. tries scapy ARP as before;
2. on `ImportError`, `PermissionError` or any scan error, logs
   `scapy ARP scan failed (...); using ping + neighbour fallback` and
3. runs a **ping sweep + `ip neigh show`** (falling back to `arp -a`), which needs no
   privileges.

Platform ping flags were also wrong for Linux/macOS (the sweep always used the Windows
`-n 1 -w 200ms` form, so on Linux every ping failed silently). Fixed:
`-n 1 -w <ms>` on Windows, `-c 1 -W <s>` on Linux, and plain `-c 1` on macOS — BSD `ping`
has no per-packet millisecond flag that is portable across macOS releases, and the sweep
already bounds each call with a subprocess timeout (§7.3).

### 6.3 Results on the real network with the fix

| # | Scenario | Result | Verdict |
|---|---|---|---|
| 1 | `GET /wifi/scan`, no privileges, no `WI_FI_SUBNET` | `{"devices":[{"ip":"10.163.255.254","mac":"70:c6:dd:09:b0:02"}],"subnet":"10.163.216.0/24","count":1,"bssid":"50:98:b8:c9:2b:e2"}` | ✅ endpoint answers, subnet honest |
| 2 | Subnet auto-detect on /17 | interface `10.163.128.0/17` → sweeps `10.163.216.0/24` | ✅ F1 fixed |
| 3 | BSSID read on Linux | `50:98:b8:c9:2b:e2` via `iwconfig`, stable across calls | ✅ (single-tool version; hardened in §7) |
| 4 | Devices visible | only the gateway — same client-isolation/VLAN behaviour as 2026-10-25 | ⚠️ expected, F2 unchanged |
| 5 | Smoke test (includes real `/wifi/scan`) | 14/14 checks passed | ✅ |
| 6 | Unprivileged fallback path | used automatically, warning logged | ✅ |
| 7 | Automated tests | 171 passed, 1 skipped (23.8 s) | ✅ |

### 6.4 What this does **not** prove

- It is still **not measured** whether the scan sees a real phone on a **flat** network
  (home router / hotspot). That is the configuration the demo will use, so it is the next
  measurement (G5): join two phones to a hotspot with isolation off and record
  `devices`, `count`, seconds per scan. Expected: phones appear; not yet observed.
- No measurement on the demo laptop (Windows) with the new code yet — only the Linux host.

---

## 7. Re-run on 2026-11-03 — BSSID probe chain (review finding 1)

Triggered by the review of `task-b`: `get_current_bssid()` read the BSSID with **only**
`iwconfig`, a tool that current distros and minimal/server images no longer ship. If it is
missing, the function returned `None` with no log line, so `schedules.ap_bssid` could never
match and every check-in silently degraded to `face_only`.

### 7.1 What the machine actually has

```
$ command -v iw; command -v nmcli; command -v iwconfig
(nothing)                    # iw is NOT installed on this laptop
/usr/bin/nmcli               # NetworkManager 1.46
/usr/sbin/iwconfig           # legacy wireless-tools
```

So the pre-fix code worked **by luck**: it depended on the one tool that is on its way out.
This is exactly the failure mode the review predicted, and it was reproducible on the very
machine that produced the original evidence.

### 7.2 Before / after on the same link (AP `50:98:b8:c9:2b:e2`)

| | Before (`iwconfig` only) | After (probe chain) |
|---|---|---|
| Probe order | `iwconfig` | `iw dev <iface> link` → `nmcli -t -f ACTIVE,BSSID device wifi` → `iwconfig` |
| Result on this laptop | `50:98:b8:c9:2b:e2` (via `iwconfig`) | `50:98:b8:c9:2b:e2` (via **`nmcli`**, `iw` absent) |
| Tool missing | silent `None` → every check-in becomes `face_only` | one `WARNING` naming all three probes and the fix (`install iw`, or set `ap_bssid` to NULL) |
| Not associated with any AP | silent `None` | `None`, **no** warning (normal state, not a fault) |

Measured:

```
$ python -c "from services import wifi_scanner as w; print(w._resolve_linux_bssid())"
('50:98:b8:c9:2b:e2', 'nmcli', True)

$ PATH=/nonexistent python -c "..."          # simulate "no tool at all"
WARNING services.wifi_scanner: Cannot read the current BSSID: none of 'iw', 'nmcli' or
'iwconfig' is available on this Linux host. AP pinning (schedules.ap_bssid) can never
verify, so check-ins will be recorded as face_only. Install 'iw' (package: iw) or set the
schedule ap_bssid to NULL.
BSSID : None          # second call: no duplicate warning (once per process)
```

### 7.3 A bug the live run caught in the new code

The first version of the `nmcli` parser matched a plain `AA:BB:..:FF`. Real terse output
**backslash-escapes every colon inside a value**:

```
$ nmcli -t -f ACTIVE,BSSID device wifi | grep '^yes'
yes:50\:98\:B8\:C9\:2B\:E2
```

With the naive regex the fallback silently returned `None` and only `iwconfig` saved the
run — i.e. the new code was as fragile as the old one until it was executed against a real
NetworkManager. The parser now unescapes `\:` first, and
`test_nmcli_real_terse_output_escapes_colons` pins the verbatim captured output.

### 7.4 F6 — tool dependency is now a documented failure mode

| Scenario | Behaviour after the fix |
|---|---|
| `iw` present (current default on many distros) | BSSID read from `iw dev <iface> link` |
| `iw` absent, NetworkManager present | BSSID read from `nmcli` |
| Only legacy `iwconfig` | BSSID read from `iwconfig`, as before |
| None of the three | `None` + **one** `WARNING` per process, naming the consequence and the fix |
| Wireless interface down / not associated | `None`, no warning |

Tests added in `backend/tests/test_wifi_subnet.py` (`TestBssidParsers`,
`TestLinuxBssidProbes`, `TestPingCommand`): parser cases for `iw`/`nmcli` including the
escaped real output, probe order (iw wins over iwconfig), each fallback step, the
"not associated → no warning" case, the "no tool → warning exactly once" case, and the
three platform ping command shapes. Suite: `187 passed` (34 of them in the scanner file).

### 7.5 Still not proven

- The chain has **not** been exercised on Windows: `netsh` remains the only Windows probe.
  Nothing about that path changed, but the demo laptop run (§6 of
  `demo_environment.md`) is still the place to confirm it.
- macOS still has no BSSID probe (no macOS host in the project). `get_current_bssid()`
  returns `None` there and the same warning is *not* emitted, because the warning is
  Linux-specific; anyone running macOS must set `ap_bssid` to NULL. Recorded in D-010.

---

## 8. What `wifi_verified` actually means (2026-11-11)

Reviewers and the lecturer both asked the same question in different words: what does the
Wi-Fi condition *prove*? This section is the single place where that is defined, because
three other documents quote it.

### 8.1 The code path

`backend/services/attendance.py` lines 186–198 (owner: A — quoted, not modified by B):

```python
wifi_verified = False
if student and student["mac_address"]:
    wifi_verified = check_mac_on_network(student["mac_address"])
    if wifi_verified and schedule_row and schedule_row["ap_bssid"]:
        wifi_verified = is_same_bssid(get_current_bssid(), schedule_row["ap_bssid"])
```

So `wifi_verified = true` means **both** of these hold:

1. the student's `mac_address` is reachable on the server's L2 segment
   (`check_mac_on_network()` → `scan_network_arp()`, which does an ARP scan or a
   ping + neighbour-table fallback and matches the MAC), **and**
2. the **server** is associated with the AP pinned in `schedules.ap_bssid`
   (`get_current_bssid()` reads the server's own association).

### 8.2 The precise claim, and the three things it does not say

| Claim | Supported? |
|---|---|
| The student's device was on the classroom network at check-in time | ✅ yes |
| The check-in machine was associated with the scheduled AP | ✅ yes |
| The phone is inside room 201 | ❌ no |
| The server knows which AP the phone is attached to | ❌ no — it cannot; ARP has no AP dimension |
| The MAC belongs to that physical handset | ❌ no — MACs are spoofable and randomised |

The accepted wording is "the check-in was made **within the coverage area of the scheduled
AP**" (lecturer reply 2026-11-11, D-013). The failure modes are threats T1–T6 in
`threat_model.md`; the answer to "can this be gamed?" is "not fully, and here is exactly
where it can".

### 8.3 Measured re-run, 2026-11-11 (same laptop, campus network)

| # | Call | Result |
|---|---|---|
| 1 | `resolve_subnet()` | `10.163.167.0/24` (host is `10.163.167.58/17`; sweep capped to /24 and says so) |
| 2 | `get_current_bssid()` | `f4:74:88:70:c2:f1` — **different from the 2026-11-03 value** `50:98:b8:c9:2b:e2` at the same desk |
| 3 | `scan_network_arp()` | 1 device (gateway `70:c6:dd:09:b0:02`) in **6.15 s**; scapy denied (`Operation not permitted`), unprivileged fallback used |
| 4 | Passive beacon scan | 10 distinct BSSIDs of `NJUPT-CMCC` from one seat (39 beacon rows, 6 SSIDs) |

Two conclusions that belong in the report, not only in the log:

- **A pinned BSSID must be captured live at the venue.** Fact 2 above shows the host's AP
  changes between sessions without moving desks; a value copied from an earlier run would
  make every check-in `face_only`.
- **"On the campus SSID" is much weaker than "in the room"** because one SSID is served by
  at least ten APs (fact 4). This is the measured basis for the limitation in
  `room_presence_spike.md` §2 and `threat_model.md` §3.1.

### 8.4 What the `start` / `end` pair adds

`start` is written as `partial`, and `end` becomes `verified` only if **both** rows had
`wifi_verified = true` (`attendance.py` 194–205). That proves the device was on the
classroom network at **two separate moments**, not that it stayed. It is the strongest
statement the current design supports without a liveness check or a rotating token.
