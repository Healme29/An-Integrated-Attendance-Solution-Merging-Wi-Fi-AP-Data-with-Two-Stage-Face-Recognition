# TUGAS B — Attendance Orchestrator + Schedule Logic

## Ringkasan
Kamu bertanggung jawab atas **logika bisnis inti sistem**: menghubungkan face recognition, Wi-Fi check, dan validasi jadwal menjadi satu alur attendance yang benar. Kamu juga mengelola endpoint attendance dan schedule CRUD.

---

## FILE YANG HARUS DIKERJAKAN

### 1. `backend/services/attendance.py` ⭐ PALING PENTING
**Apa yang sudah ada:** `get_schedules_for_now()`, `recognize_face()`, `mark_attendance()`. Alur dasarnya: detect → recognize → cek Wi-Fi → insert record.

**Yang harus kamu lakukan & perbaiki:**

#### ⚠️ CRITICAL — Two-Stage Attendance Logic (Priority 1, Blocker #2) [EST: 5 jam]
Ini adalah **fitur inti proyek**: attendance hanya valid jika ada "start" DAN "end" check-in untuk student + schedule yang sama.

- [ ] **Buat fungsi `get_existing_check(student_id, schedule_id, check_type)`:**
  ```python
  async def get_existing_check(student_id: int, schedule_id: int, check_type: str) -> dict | None:
      """Cari record attendance yang sudah ada untuk student+schedule+check_type tertentu."""
  ```
- [ ] **Buat fungsi `is_start_end_paired(student_id, schedule_id) -> bool`:**
  ```python
  async def is_start_end_paired(student_id: int, schedule_id: int) -> bool:
      """Cek apakah student sudah punya 'start' AND 'end' untuk schedule ini. Return True jika keduanya ada."""
  ```
- [ ] **Update `mark_attendance()`** — setelah insert check-in baru, cek apakah pasangan start/end sudah lengkap:
  - Jika check_type = "start" → status = "partial" (menunggu end)
  - Jika check_type = "end" → cari "start" yang sesuai. Jika ada → update BOTH records menjadi status = "verified"
  - Jika check_type = "end" tapi tidak ada "start" → tolak dengan error "Must check in at start of class first"
- [ ] **Add new status values di DB check constraint:** `CHECK(check_type IN ('start', 'end'))` sudah ada. Untuk status, kamu perlu nilai baru: `partial`, `verified`. Tapi `status` tidak punya CHECK constraint, jadi kamu bisa langsung pakai nilai baru tanpa migrasi.
- [ ] **Prevent duplicate check-in:** Jika student sudah check-in "start" untuk schedule yang sama hari ini, tolak "start" keduanya. Begitu juga untuk "end". Fungsi `get_existing_check()` di atas akan membantu ini.

#### ⚠️ HIGH — Schedule Time Enforcement (Priority 1, Blocker #3) [EST: 2 jam]
- [ ] **Di `routers/attendance.py` endpoint `check_attendance()`:** Sebelum memproses foto, panggil `get_schedules_for_now()`.
- [ ] **Validasi:** Jika `schedule_id` yang dikirim tidak ada di `get_schedules_for_now()` → tolak 400 "Attendance outside class hours".
  ```python
  schedules = await get_schedules_for_now()
  if not any(s["id"] == schedule_id for s in schedules):
      raise HTTPException(status_code=400, detail="Attendance outside class hours. Current time does not match any active schedule.")
  ```
- [ ] **Grace period:** Di `config.py` ada `ATTENDANCE_CHECK_WINDOW_MINUTES = 15`. Modifikasi `get_schedules_for_now()` untuk menambahkan window: start_time dikurangi 15 menit, end_time ditambah 15 menit.
- [ ] **Timezone handling:** Tambahkan konfigurasi timezone di `config.py` (default `Asia/Jakarta`). Gunakan `pytz` atau `zoneinfo` untuk konsistensi.

#### HIGH — Perbaikan `recognize_face()` [EST: 1 jam]
- [ ] **Koordinasi dengan A:** Setelah A fix signature `get_embedding()`, update pemanggilan di sini. Kode ini perlu diganti dari:
  ```python
  embedding = get_embedding(best_face["crop"])  # OLD
  ```
  menjadi:
  ```python
  embedding = get_embedding(full_image, best_face["bbox"])  # NEW
  ```
  Jadi kamu perlu meneruskan `full_image` (bukan `image_bytes`) ke `recognize_face()`.
- [ ] **Atau restructure:** Ubah `recognize_face()` terima `np.ndarray` (image array) + `bytes` (raw) untuk fleksibilitas.

### 2. `backend/routers/attendance.py`
**Apa yang sudah ada:** `POST /attendance/check`, `GET /attendance/today`, `GET /attendance/student/{id}`.

**Yang harus diperbaiki:**
- [ ] **Schedule time validation** — integrasikan seperti dijelaskan di atas.
- [ ] **Response model:** Saat ini `AttendanceResponse` tidak cocok dengan response real dari `mark_attendance()`. Cek apakah semua field match. Contoh: `AttendanceResponse` punya field `wifi_verified: bool`, tapi di DB tersimpan sebagai integer (0/1). Ini perlu di-cast.
- [ ] **Student attendance history:** Tambahkan field `class_name`, `room`, `status` yang sudah di-join dengan schedules di query.
- [ ] **Pagination:** Tambahkan parameter `limit` (default 50) dan `offset` untuk endpoint attendance history.
- [ ] **Date filter:** Tambahkan parameter `start_date` dan `end_date` untuk `GET /attendance/today` agar lebih fleksibel (ganti nama jadi `GET /attendance/date-range` atau tambahkan query params).

### 3. `backend/routers/schedules.py`
**Yang sudah ada:** Hampir selesai. CRUD lengkap.

**Yang perlu:**
- [ ] **Update schedule:** Tambahkan `PUT /schedules/{id}` untuk mengupdate jadwal.
- [ ] **Get schedule by ID:** Tambahkan `GET /schedules/{id}`.
- [ ] **Validasi input:** Cek bahwa `start_time < end_time`. Cek `day_of_week` antara 0-6.
- [ ] **Overlap detection:** Cek apakah schedule baru overlap dengan schedule yang sudah ada di room yang sama pada hari yang sama.
  ```sql
  SELECT * FROM schedules WHERE day_of_week = ? AND room = ? AND start_time < ? AND end_time > ?
  ```
  Jika overlap → tolak dengan error.

### 4. `backend/models/schemas.py`
**Yang perlu:**
- [ ] **Update `AttendanceResponse`:** Pastikan field eksak sama dengan response `mark_attendance()`. Tambahkan field `student_name`, `class_name`, `room` untuk history.
- [ ] **Tambahkan `AttendanceHistoryResponse`:** Model khusus untuk endpoint history (join dengan schedule).
- [ ] **Tambahkan `ScheduleUpdate`:** Pydantic model untuk update schedule.

### 5. `backend/config.py`
**Yang perlu:**
- [ ] Tambahkan `TIMEZONE = "Asia/Jakarta"`
- [ ] Review `ATTENDANCE_CHECK_WINDOW_MINUTES = 15` — apakah perlu lebih panjang (30 menit)?

---

## DEPENDENCIES
- Modul A: Fungsi `detect_faces_from_bytes()`, `get_embedding()`, `compare_faces()`, `is_match()`
- Modul D: Fungsi `check_mac_on_network()`
- Database: tabel `students`, `schedules`, `attendance`
- Tidak ada dependency eksternal baru (semua via modul lain)

---

## INTEGRASI TIM
| Modul | Dependensi ke | Yang perlu dikoordinasikan |
|-------|---------------|---------------------------|
| attendance.py | A (face_recognition) | Signature `get_embedding()` — tanya A apakah sudah fix |
| attendance.py | D (wifi_scanner) | Fungsi `check_mac_on_network()` — seharusnya sudah stabil |
| routers/attendance.py | services/attendance.py | Dirimu sendiri — pastikan fungsi async dipanggil dengan `await` |
| routers/schedules.py | database.py | Tidak ada perubahan, sudah stabil |

---

## ESTIMASI WAKTU
| Sub-task | Estimasi |
|----------|----------|
| Two-stage logic (start + end pairing) | 5-6 jam |
| Schedule time enforcement + grace period | 2-3 jam |
| Perbaikan recognize_face (koordinasi A) | 1-2 jam |
| Fix response models & schemas | 1-2 jam |
| Tambahan fitur schedule CRUD | 2-3 jam |
| **Total** | **11-16 jam** |

---

## PRIORITAS
1. ⚠️ **CRITICAL** — Two-stage attendance logic (start → partial → end → verified)
2. ⚠️ **HIGH** — Schedule time enforcement
3. **HIGH** — Koordinasi dengan A untuk perbaikan recognize_face()
4. **MEDIUM** — Fix Pydantic response models
5. **LOW** — Pagination, date filter, overlap detection