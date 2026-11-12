# Phone MAC Inventory — Procedure and Template

> **Owner:** B · **Applies to:** classroom pilot (December) and any live Wi-Fi demo
> **Status:** procedure ready; the table is **empty on purpose** — no MAC has been collected
> yet, because that needs the actual phones. Do not invent values.
> **Related:** `threat_model.md` T3 (MAC spoofing), `network_validation.md` §5 (pilot
> configuration), D-008 (demo seed uses fake `02:00:…` MACs), `offline_fallback.md` §2.

---

## 1. Why this exists

`attendance.py` uses `students.mac_address` as the Wi-Fi signal: `check_mac_on_network()`
returns true only if that MAC is reachable on the server's L2 segment. If the registered MAC
is wrong, the student is never marked `wifi_verified` — a **false negative** that looks like a
broken system on demo day.

Two facts make this fragile in practice:

1. **Modern phones randomise their MAC per network.** Unless "private/random MAC" is turned
   off for the classroom SSID, the phone presents a different MAC on every join and rejoin.
2. **The ARP scan shows MACs, not names.** To map a MAC to a student you need one moment where
   both are known: either the student reads it from the phone, or the app displays it.

Therefore the inventory is collected **before** the pilot, verified **on** the pilot network,
and treated as an identifier, not a credential (`threat_model.md` §5.3).

## 2. Collection procedure (10 minutes per student, one-time)

### 2.1 Per phone — turn off randomised MAC for the target SSID

| Platform | Path (names vary by version) |
|---|---|
| Android 10+ | Settings → Network & internet → Internet → ⚙ next to the SSID → **Privacy** → **Use device MAC** |
| iOS 14+ | Settings → Wi-Fi → ⓘ next to the SSID → **Private Wi-Fi Address** → **Off** |
| HarmonyOS / MIUI / ColorOS | same idea: Wi-Fi → network details → Privacy / "Random MAC" → off |

Do this **only for the classroom/demo SSID**, not globally — a phone-wide change is a privacy
regression the student did not ask for.

### 2.2 Read the MAC

Either is acceptable; record which one was used:

- **From the phone** (most reliable): Android → Settings → About phone → Status → Wi-Fi MAC
  address; iOS → Settings → General → About → Wi-Fi Address.
- **From the network** (must be joined to the target SSID at that moment):
  ```bash
  curl "http://127.0.0.1:8000/wifi/scan"
  # or, on the same L2, look at ap_logs after the student connects
  ```
  The scan output is a list of `{ip, mac}` pairs with no names — match by asking the student
  to disconnect and reconnect while you watch, or compare before/after a scan.

### 2.3 Verify it survived a rejoin

Ask the student to leave and rejoin the SSID, then scan again. If the MAC changed, private
MAC is still on — fix that before recording anything.

### 2.4 Register it

```bash
# create the student first if needed
curl -X POST "http://127.0.0.1:8000/students/" \
     -H "Content-Type: application/json" \
     -d '{"name":"<name>","nim":"<nim>","mac_address":"<aa:bb:cc:dd:ee:ff>"}'

# existing student: update only the MAC
curl -X PUT "http://127.0.0.1:8000/students/<id>/mac" \
     -H "Content-Type: application/json" \
     -d '{"mac_address":"<aa:bb:cc:dd:ee:ff>"}'
```

Then confirm the mapping with a real check-in on the pilot network: the row must have
`wifi_verified: true`. If it says `face_only` while the phone is on the same network, the MAC
in the database does not match what the phone presents — re-read §2.2.

## 3. Template (fill during collection; do not commit real MACs to a public branch)

| # | Student name | NIM | Phone model | MAC (lowercase) | Source (phone / scan) | Private MAC off | Stable after rejoin | Registered (`PUT`) | `wifi_verified` on pilot |
|---|---|---|---|---|---|---|---|---|---|
| 1 | | | | | | ☐ | ☐ | ☐ | ☐ |
| 2 | | | | | | ☐ | ☐ | ☐ | ☐ |
| 3 | | | | | | ☐ | ☐ | ☐ | ☐ |
| 4 | | | | | | ☐ | ☐ | ☐ | ☐ |
| 5 | | | | | | ☐ | ☐ | ☐ | ☐ |

Rules for this table:

- Normalise to lowercase `aa:bb:cc:dd:ee:ff`; `normalize_mac()` accepts `-` and `:` but a
  single format avoids duplicate-looking entries.
- One row per **phone**, not per student: a student with two phones needs two rows and only
  one is registered at a time.
- If a phone is replaced, update the row and `PUT` the new MAC; a stale MAC only ever causes a
  false negative, never a false positive.

## 4. Privacy and retention

- A MAC is a device identifier. Collect it with the student's knowledge, state that it is used
  only for attendance, and keep the filled table **out of the public repository**
  (`docs/A/pilot/` is already gitignored). Store it with the pilot data, delete it after the
  report is written.
- Do not put real MACs into `seed_demo.py` or screenshots: the seed uses `02:00:…` placeholders
  on purpose (D-008), and a random MAC in a screenshot invites the question "whose phone is
  that?".

## 5. What this inventory does not fix

Turning MAC randomisation off and recording the address makes the **Wi-Fi signal work**, not
**tamper-proof**. A rooted phone can still present someone else's MAC
(`threat_model.md` T3), and the system still cannot tell which AP the phone is attached to
(T1). Those are separate limitations, documented separately; this page only removes the
operational false negatives.
