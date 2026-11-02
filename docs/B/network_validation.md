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
| **Pilot (M1)** | Set `WI_FI_SUBNET` explicitly to the classroom's /24 and register each student's **real phone MAC** (disable "private/random MAC" for the school SSID during enrollment) | makes the AP check meaningful and predictable |
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
`-n 1 -w <ms>` on Windows, `-c 1 -W <ms>` on macOS, `-c 1 -W <s>` on Linux.

### 6.3 Results on the real network with the fix

| # | Scenario | Result | Verdict |
|---|---|---|---|
| 1 | `GET /wifi/scan`, no privileges, no `WI_FI_SUBNET` | `{"devices":[{"ip":"10.163.255.254","mac":"70:c6:dd:09:b0:02"}],"subnet":"10.163.216.0/24","count":1,"bssid":"50:98:b8:c9:2b:e2"}` | ✅ endpoint answers, subnet honest |
| 2 | Subnet auto-detect on /17 | interface `10.163.128.0/17` → sweeps `10.163.216.0/24` | ✅ F1 fixed |
| 3 | BSSID read on Linux | `50:98:b8:c9:2b:e2` via `iwconfig`, stable across calls | ✅ |
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
