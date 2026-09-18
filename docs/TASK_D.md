# TASK D — Wi-Fi Scanner + CRUD + Database + Testing

## Summary
You are responsible for three areas: (1) Wi-Fi network scanner, (2) database management & CRUD endpoints for students, (3) the entire testing infrastructure. This task covers networking and code quality.

---

## FILES TO WORK ON

### 1. `backend/services/wifi_scanner.py`
**What already exists:** `scan_network_arp()` (Windows via `arp -a`, Linux via Scapy), `check_mac_on_network()`, `log_ap_access()`.

**What must be fixed & added:**

#### ⚠️ HIGH — Wi-Fi Scanner Improvements [EST: 4-5 hours]
- [ ] **More accurate Windows ARP scan:** Currently only parses `arp -a` output. ARP cache may not be up-to-date.
  - **Solution:** Before running `arp -a`, do a broadcast ping first to populate ARP cache:
    ```python
    import subprocess, platform
    def ping_sweep(subnet):
        """Ping broadcast to populate ARP cache."""
        base = ".".join(subnet.split(".")[:3])
        for i in range(1, 255):
            ip = f"{base}.{i}"
            subprocess.run(["ping", "-n", "1", "-w", "100", ip],
                          capture_output=True, timeout=1)
    ```
  - Run ping sweep in a background thread before the main scan.

- [ ] **Npcap requirement:** On Windows, Scapy needs Npcap. If Scapy can't be imported, fallback to `arp -a`. If `arp -a` also fails, return an error message.
- [ ] **MAC address normalization:** Create function `normalize_mac(mac: str) -> str` that removes spaces, lowercases, and replaces `-` with `:`. Use in all functions.
- [ ] **Scan throttling:** Scanning with Scapy can make network admins suspicious. For Linux, reduce ARP request rate (use `inter` and `retry` parameters in Scapy).
- [ ] **Network interface detection:** Auto-detect active network interface (not hardcoded `192.168.1.0/24`). Use `netifaces` or `psutil` to list interfaces.
- [ ] **Improve `check_mac_on_network()`:** Add caching with 30-second TTL. If a scan was done <30 seconds ago, use cached results.
  ```python
  _scan_cache = {"devices": None, "timestamp": None}
  CACHE_TTL = 30  # seconds

  def check_mac_on_network(mac_address: str, force_scan: bool = False) -> bool:
      now = time.time()
      if not force_scan and _scan_cache["devices"] and now - _scan_cache["timestamp"] < CACHE_TTL:
          devices = _scan_cache["devices"]
      else:
          devices = scan_network_arp()
          _scan_cache = {"devices": devices, "timestamp": now}
      ...
  ```
- [ ] **AP BSSID verification:** Add function `check_bssid_on_network(target_bssid: str) -> bool` to verify class SSID/BSSID (use `netsh wlan show networks` on Windows or `iwlist scan` on Linux).

#### MEDIUM — Extended Wi-Fi Features [EST: 2-3 hours]
- [ ] **Signal strength:** If possible, add RSSI (signal strength) info for each detected device.
- [ ] **Better logging:** In `log_ap_access()`, add info on whether the device is new (never seen before) or already in previous logs.
- [ ] **SSID filtering:** Optionally filter devices by specific SSID (e.g., only show devices connected to SSID "School-WiFi").

### 2. `backend/routers/wifi.py`
**What already exists:** `GET /wifi/scan`, `GET /wifi/check/{mac}`.

**What's needed:**
- [ ] **Scan parameter:** Add optional `subnet` parameter with default from config.
- [ ] **Response detail:** In `/wifi/scan`, add the interface used, scan time, device count.
- [ ] **Logging:** Every time a scan is performed, log to the `ap_logs` table.

### 3. `backend/routers/students.py`
**What already exists:** Full CRUD for students.

**What must be added:**
- [ ] **Search by NIM:** Add `nim` query param in `GET /students/`:
  ```python
  @router.get("/", response_model=list[StudentResponse])
  async def list_students(nim: Optional[str] = None):
      db = await get_db()
      if nim:
          cursor = await db.execute("SELECT * FROM students WHERE nim = ?", (nim,))
      else:
          cursor = await db.execute("SELECT * FROM students ORDER BY name")
      ...
  ```
  This is important for the login screen in Flutter (Task C).
- [ ] **Bulk create:** Add endpoint `POST /students/bulk` that accepts a list of students in one request.
- [ ] **Import CSV:** Add endpoint `POST /students/import` that accepts a CSV file with columns `name,nim,mac_address`.
- [ ] **Export CSV:** Add `GET /students/export` that returns CSV.

### 4. `backend/models/database.py`
**What already exists:** `get_db()` and `init_db()` with 5 tables.

**What's needed:**
- [ ] **Connection pooling:** Currently every `get_db()` opens a new connection. Add simple connection pool or reuse connection.
- [ ] **Migration system:** Create a simple migration system. Add a `schema_version` table for tracking schema versions:
  ```sql
  CREATE TABLE IF NOT EXISTS schema_version (
      version INTEGER PRIMARY KEY,
      applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  ```
- [ ] **Indexes:** Add indexes for frequently used queries:
  ```sql
  CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(student_id);
  CREATE INDEX IF NOT EXISTS idx_attendance_schedule ON attendance(schedule_id);
  CREATE INDEX IF NOT EXISTS idx_attendance_timestamp ON attendance(timestamp);
  CREATE INDEX IF NOT EXISTS idx_students_nim ON students(nim);
  CREATE INDEX IF NOT EXISTS idx_schedules_day_time ON schedules(day_of_week, start_time);
  ```
- [ ] **Cascade delete:** Ensure the `faces` table has ON DELETE CASCADE (in `init_db()`) so when a student is deleted, face records are also deleted.

### 5. `backend/utils/helpers.py`
**What already exists:** `ensure_dir()`, `image_bytes_to_array()`.

**What's needed:**
- [ ] **Add `normalize_mac(mac: str) -> str`:** Utility function for MAC address normalization, used by wifi_scanner.
- [ ] **Add `validate_image_bytes(bytes: bytes) -> bool`:** Validate magic bytes to check if the file is an image.
- [ ] **Add `get_timestamp() -> str`:** Helper for consistent timestamp formatting.

### 6. ⭐ TESTING — ALL TEST FILES [EST: 8-10 hours]

#### `backend/tests/conftest.py`
**What already exists:** Test DB setup, mocks for face detection, face recognition, Wi-Fi scanner, is_match.

**What must be fixed:**
- [ ] **Update mocks** if function signatures change in `face_detection.py` and `face_recognition.py` (coordinate with A).
- [ ] **Add fixtures for sample data:**
  ```python
  @pytest_asyncio.fixture
  async def seed_sample_data(test_db):
      """Seed database with sample student + schedule."""
      db = await test_db()
      await db.execute("INSERT INTO students (id, name, nim, mac_address) VALUES (1, 'Alice', '12345', 'aa:bb:cc:dd:ee:ff')")
      await db.execute("INSERT INTO schedules (id, class_name, day_of_week, start_time, end_time) VALUES (1, 'Math 101', 0, '08:00', '09:30')")
      await db.commit()
      await db.close()
  ```

#### `backend/tests/test_services.py`
**What must be added:**
- [ ] **Test for `wifi_scanner.normalize_mac()`** (create the function first).
- [ ] **Test for `ap_logs`** — test insert and select from ap_logs table.
- [ ] **Test for `attendance.get_schedules_for_now()`** — validate filtering by day and time. Mock `datetime.now()` to test various time scenarios.
- [ ] **Test for `attendance.mark_attendance()`** with various statuses (partial, verified, present, face_only).
- [ ] **Test for caching** in `check_mac_on_network()`.

#### `backend/tests/test_routers.py`
**What must be added:**
- [ ] **Test for search student by NIM:** `GET /students/?nim=12345`.
- [ ] **Test for bulk create student.**
- [ ] **Test for pagination attendance history.**
- [ ] **Test for schedule time validation** — ensure attendance request outside class hours is rejected (400).
- [ ] **Test for duplicate check-in** — start → start again → reject.
- [ ] **Test for two-stage sequence** — start → end → check status "verified".

#### `backend/tests/test_attendance_scenarios.py`
**What must be added:**
- [ ] **Test: End without start** — try check_type=end without start → should reject.
- [ ] **Test: Start → end → duplicate end** — reject second end.
- [ ] **Test: Wrong schedule time** — mock datetime.now() to a time outside schedule → reject.
- [ ] **Test: Grace period** — mock datetime.now() to 10 minutes before start → still accepted.
- [ ] **Test: No WiFi (face only)** — mock wifi_scanner to return False → status "face_only".
- [ ] **Test: Student doesn't have MAC** — student without mac_address → wifi_verified = False.
- [ ] **Test: Multi-student recognition** — 2 students enrolled, student A photo → recognize student A.

### 7. `main.py` & `config.py` (Minor)
- [ ] **Add logging** in `main.py` — use `logging` module, log every incoming request.
- [ ] **Health check endpoint:** Add `GET /health` that returns database status (check SQLite connection).
- [ ] **CORS hardening:** In `main.py`, replace `allow_origins=["*"]` with a specific origin list for production.

---

## DEPENDENCIES

| Package | Version | Function |
|---------|---------|----------|
| `scapy` | 2.5.0 | ARP scan (Linux) |
| `aiosqlite` | 0.20.0 | Async database |
| `pytest` | 8.3.3 | Testing framework |
| `pytest-asyncio` | 0.24.0 | Async test support |
| `httpx` | 0.27.2 | HTTP test client |
| `numpy` | 1.26.4 | Test data generation |
| **Optional:** `netifaces`, `psutil`, `pytz` | - | Network interface detection |

---

## TEAM INTEGRATION
| Module | Depends on | What to coordinate |
|--------|------------|-------------------|
| wifi_scanner.py | None | Standalone |
| students.py | database.py | Standalone (already stable) |
| conftest.py | A (face_detection, face_recognition) | Update mocks if A changes signatures |
| All tests | A + B + C | Ensure tests pass after all changes |

---

## TIME ESTIMATES
| Sub-task | Estimate |
|----------|----------|
| Wi-Fi scanner fixes (ping sweep, caching, normalization) | 4-5 hours |
| Extended Wi-Fi (BSSID check, RSSI) | 2-3 hours |
| CRUD improvement (search NIM, bulk, import/export) | 2-3 hours |
| Database improvements (index, migration, pooling) | 2-3 hours |
| Update conftest.py + fixtures | 2-3 hours |
| Update test_services.py | 2-3 hours |
| Update test_routers.py | 2-3 hours |
| Update test_attendance_scenarios.py | 3-4 hours |
| **Total** | **19-27 hours** |

---

## PRIORITIES
1. ⚠️ **HIGH** — Wi-Fi scanner fixes (ping sweep + caching)
2. ⚠️ **HIGH** — Update test infrastructure (conftest.py, update mocks)
3. **HIGH** — Search student by NIM (for Flutter login)
4. **HIGH** — Test scenarios (two-stage, schedule validation, etc.)
5. **MEDIUM** — Database indexes + migration system
6. **MEDIUM** — Bulk import/export student
7. **LOW** — CORS hardening, health check, logging