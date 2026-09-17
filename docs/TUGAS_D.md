# TUGAS D — Wi-Fi Scanner + CRUD + Database + Testing

## Ringkasan
Kamu bertanggung jawab atas tiga area: (1) Wi-Fi network scanner, (2) database management & CRUD endpoints untuk student, (3) seluruh testing infrastructure. Tugas ini mencakup networking dan kualitas kode.

---

## FILE YANG HARUS DIKERJAKAN

### 1. `backend/services/wifi_scanner.py`
**Apa yang sudah ada:** `scan_network_arp()` (Windows via `arp -a`, Linux via Scapy), `check_mac_on_network()`, `log_ap_access()`.

**Yang harus diperbaiki & ditambahkan:**

#### ⚠️ HIGH — Perbaikan Wi-Fi Scanner [EST: 4-5 jam]
- [ ] **Windows ARP scan lebih akurat:** Saat ini hanya parse output `arp -a`. ARP cache mungkin tidak up-to-date.
  - **Solusi:** Sebelum jalankan `arp -a`, lakukan ping broadcast dulu untuk memancing ARP:
    ```python
    import subprocess, platform
    def ping_sweep(subnet):
        """Ping broadcast untuk populate ARP cache."""
        base = ".".join(subnet.split(".")[:3])
        for i in range(1, 255):
            ip = f"{base}.{i}"
            subprocess.run(["ping", "-n", "1", "-w", "100", ip],
                          capture_output=True, timeout=1)
    ```
  - Jalankan ping sweep di background thread sebelum scan utama.

- [ ] **Npcap requirement:** Di Windows, Scapy butuh Npcap. Jika Scapy tidak bisa import, fallback ke `arp -a`. Jika `arp -a` juga gagal, return error message.
- [ ] **MAC address normalization:** Buat fungsi `normalize_mac(mac: str) -> str` yang menghapus spasi, lowercasing, dan mengganti `-` dengan `:`. Gunakan di semua fungsi.
- [ ] **Scan throttling:** Scan dengan Scapy bisa membuat network admin curiga. Untuk Linux, kurangi rate ARP request (parameter `inter` dan `retry` di Scapy).
- [ ] **Network interface detection:** Otomatis deteksi network interface aktif (bukan hardcoded `192.168.1.0/24`). Gunakan `netifaces` atau `psutil` untuk list interfaces.
- [ ] **Improve `check_mac_on_network()`:** Tambahkan caching dengan TTL 30 detik. Jika scan dilakukan <30 detik yang lalu, gunakan hasil cache.
  ```python
  _scan_cache = {"devices": None, "timestamp": None}
  CACHE_TTL = 30  # detik

  def check_mac_on_network(mac_address: str, force_scan: bool = False) -> bool:
      now = time.time()
      if not force_scan and _scan_cache["devices"] and now - _scan_cache["timestamp"] < CACHE_TTL:
          devices = _scan_cache["devices"]
      else:
          devices = scan_network_arp()
          _scan_cache = {"devices": devices, "timestamp": now}
      ...
  ```
- [ ] **AP BSSID verification:** Tambahkan fungsi `check_bssid_on_network(target_bssid: str) -> bool` untuk verifikasi SSID/BSSID kelas (gunakan `netsh wlan show networks` di Windows atau `iwlist scan` di Linux).

#### MEDIUM — Extended Wi-Fi Features [EST: 2-3 jam]
- [ ] **Signal strength:** Jika memungkinkan, tambahkan informasi RSSI (signal strength) untuk setiap device yang terdeteksi.
- [ ] **Logging yang lebih baik:** Di `log_ap_access()`, tambahkan info apakah device baru (belum pernah terlihat) atau sudah ada di log sebelumnya.
- [ ] **SSID filtering:** Opsional filter perangkat berdasarkan SSID tertentu (misal hanya tampilkan device yang terhubung ke SSID "Sekolah-WiFi").

### 2. `backend/routers/wifi.py`
**Apa yang sudah ada:** `GET /wifi/scan`, `GET /wifi/check/{mac}`.

**Yang perlu:**
- [ ] **Scan parameter:** Tambahkan parameter `subnet` (opsional) dengan default dari config.
- [ ] **Response detail:** Di `/wifi/scan`, tambahkan interface yang digunakan, scan time, jumlah device.
- [ ] **Logging:** Setiap kali scan dilakukan, log ke tabel `ap_logs`.

### 3. `backend/routers/students.py`
**Apa yang sudah ada:** CRUD lengkap untuk student.

**Yang perlu ditambahkan:**
- [ ] **Search by NIM:** Tambahkan query param `nim` di `GET /students/`:
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
  Ini penting untuk login screen di Flutter (tugas C).
- [ ] **Bulk create:** Tambahkan endpoint `POST /students/bulk` yang menerima list student dalam satu request.
- [ ] **Import CSV:** Tambahkan endpoint `POST /students/import` yang menerima file CSV dengan kolom `name,nim,mac_address`.
- [ ] **Export CSV:** Tambahkan `GET /students/export` yang mengembalikan CSV.

### 4. `backend/models/database.py`
**Apa yang sudah ada:** `get_db()` dan `init_db()` dengan 5 tabel.

**Yang perlu:**
- [ ] **Connection pooling:** Saat ini setiap `get_db()` buka koneksi baru. Tambahkan simple connection pool atau reuse connection.
- [ ] **Migration system:** Buat sistem migrasi sederhana. Tambahkan tabel `schema_version` untuk tracking versi skema:
  ```sql
  CREATE TABLE IF NOT EXISTS schema_version (
      version INTEGER PRIMARY KEY,
      applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  ```
- [ ] **Indexes:** Tambahkan index untuk query yang sering dipakai:
  ```sql
  CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(student_id);
  CREATE INDEX IF NOT EXISTS idx_attendance_schedule ON attendance(schedule_id);
  CREATE INDEX IF NOT EXISTS idx_attendance_timestamp ON attendance(timestamp);
  CREATE INDEX IF NOT EXISTS idx_students_nim ON students(nim);
  CREATE INDEX IF NOT EXISTS idx_schedules_day_time ON schedules(day_of_week, start_time);
  ```
- [ ] **Cascade delete:** Pastikan tabel `faces` sudah ON DELETE CASCADE (di `init_db()`) sehingga saat student dihapus, face records juga ikut terhapus.

### 5. `backend/utils/helpers.py`
**Apa yang sudah ada:** `ensure_dir()`, `image_bytes_to_array()`.

**Yang perlu:**
- [ ] **Tambah `normalize_mac(mac: str) -> str`:** Fungsi utility untuk normalisasi MAC address, dipakai oleh wifi_scanner.
- [ ] **Tambah `validate_image_bytes(bytes: bytes) -> bool`:** Validasi magic bytes untuk cek apakah file adalah gambar.
- [ ] **Tambah `get_timestamp() -> str`:** Helper untuk format timestamp konsisten.

### 6. ⭐ TESTING — SEMUA FILE TEST [EST: 8-10 jam]

#### `backend/tests/conftest.py`
**Yang sudah ada:** Setup test DB, mock untuk face detection, face recognition, Wi-Fi scanner, is_match.

**Yang perlu diperbaiki:**
- [ ] **Update mocks** jika ada perubahan signature fungsi di `face_detection.py` dan `face_recognition.py` (koordinasi dengan A).
- [ ] **Tambahkan fixtures untuk sample data:**
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
**Yang perlu ditambahkan:**
- [ ] **Test untuk `wifi_scanner.normalize_mac()`** (buat dulu fungsinya).
- [ ] **Test untuk `ap_logs`** — test insert dan select dari tabel ap_logs.
- [ ] **Test untuk `attendance.get_schedules_for_now()`** — validasi filter berdasarkan hari dan jam. Mock `datetime.now()` untuk test berbagai skenario waktu.
- [ ] **Test untuk `attendance.mark_attendance()`** dengan berbagai status (partial, verified, present, face_only).
- [ ] **Test untuk caching** di `check_mac_on_network()`.

#### `backend/tests/test_routers.py`
**Yang perlu ditambahkan:**
- [ ] **Test untuk search student by NIM:** `GET /students/?nim=12345`.
- [ ] **Test untuk bulk create student.**
- [ ] **Test untuk pagination attendance history.**
- [ ] **Test untuk schedule time validation** — pastikan request attendance di luar jam kelas ditolak 400.
- [ ] **Test untuk duplicate check-in** — start → start lagi → tolak.
- [ ] **Test untuk two-stage sequence** — start → end → cek status "verified".

#### `backend/tests/test_attendance_scenarios.py`
**Yang perlu ditambahkan:**
- [ ] **Test: End without start** — coba check_type=end tanpa start → harus tolak.
- [ ] **Test: Start → end → duplicate end** — tolak end kedua.
- [ ] **Test: Wrong schedule time** — mock datetime.now() ke waktu di luar jadwal → tolak.
- [ ] **Test: Grace period** — mock datetime.now() ke 10 menit sebelum start → masih diterima.
- [ ] **Test: No WiFi (face only)** — mock wifi_scanner return False → status "face_only".
- [ ] **Test: Student doesn't have MAC** — student tanpa mac_address → wifi_verified = False.
- [ ] **Test: Multi-student recognition** — 2 student terdaftar, photo student A → recognize student A.

### 7. `main.py` & `config.py` (Minor)
- [ ] **Tambahkan logging** di `main.py` — gunakan `logging` module, log setiap request masuk.
- [ ] **Health check endpoint:** Tambahkan `GET /health` yang return status database (cek koneksi SQLite).
- [ ] **CORS hardening:** Di `main.py`, ganti `allow_origins=["*"]` dengan list origin spesifik untuk production.

---

## DEPENDENCIES

| Package | Versi | Fungsi |
|---------|-------|--------|
| `scapy` | 2.5.0 | ARP scan (Linux) |
| `aiosqlite` | 0.20.0 | Database async |
| `pytest` | 8.3.3 | Testing framework |
| `pytest-asyncio` | 0.24.0 | Async test support |
| `httpx` | 0.27.2 | HTTP test client |
| `numpy` | 1.26.4 | Test data generation |
| **Opsional:** `netifaces`, `psutil`, `pytz` | - | Network interface detection |

---

## INTEGRASI TIM
| Modul | Dependensi ke | Yang perlu dikoordinasikan |
|-------|---------------|---------------------------|
| wifi_scanner.py | Tidak ada | Berdiri sendiri |
| students.py | database.py | Berdiri sendiri (sudah stabil) |
| conftest.py | A (face_detection, face_recognition) | Update mocks jika A ubah signature |
| Semua test | A + B + C | Pastikan test passing setelah semua perubahan |

---

## ESTIMASI WAKTU
| Sub-task | Estimasi |
|----------|----------|
| Perbaikan Wi-Fi scanner (ping sweep, caching, normalisasi) | 4-5 jam |
| Extended Wi-Fi (BSSID check, RSSI) | 2-3 jam |
| CRUD improvement (search NIM, bulk, import/export) | 2-3 jam |
| Database improvements (index, migration, pooling) | 2-3 jam |
| Update conftest.py + fixtures | 2-3 jam |
| Update test_services.py | 2-3 jam |
| Update test_routers.py | 2-3 jam |
| Update test_attendance_scenarios.py | 3-4 jam |
| **Total** | **19-27 jam** |

---

## PRIORITAS
1. ⚠️ **HIGH** — Perbaikan Wi-Fi scanner (ping sweep + caching)
2. ⚠️ **HIGH** — Update test infrastructure (conftest.py, update mocks)
3. **HIGH** — Search student by NIM (untuk login Flutter)
4. **HIGH** — Test scenarios (two-stage, schedule validation, dll)
5. **MEDIUM** — Database indexes + migration system
6. **MEDIUM** — Bulk import/export student
7. **LOW** — CORS hardening, health check, logging