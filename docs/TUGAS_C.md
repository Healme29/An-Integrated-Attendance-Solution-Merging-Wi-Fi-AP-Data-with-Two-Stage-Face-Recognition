# TUGAS C — Flutter Mobile App (Frontend)

## Ringkasan
Kamu bertanggung jawab atas **aplikasi mobile Flutter** yang digunakan siswa untuk check-in attendance. Aplikasi ini mengambil foto selfie, mengirim ke backend, dan menampilkan hasilnya.

---

## FILE YANG HARUS DIKERJAKAN

### 1. `mobile/lib/models/student.dart`
**Apa yang sudah ada:** `Student` model + `AttendanceResult` model.

**Yang harus diperbaiki:**

#### ⚠️ CRITICAL — Fix Data Contract Mismatch (Priority 1, Blocker #4) [EST: 1 jam]
Masalah: `AttendanceResult` Flutter mengharapkan response dari `POST /faces/recognize` (field: `recognized`, `student_id`, `student_name`, `confidence`), **TAPI** endpoint yang dipanggil oleh `camera_screen.dart` adalah `POST /attendance/check` yang mengembalikan response BERBEDA (field: `id`, `student_id`, `schedule_id`, `check_type`, `confidence`, `wifi_verified`, `status`, `timestamp`).

- [ ] **Buat model baru `AttendanceCheckResponse`:**
  ```dart
  class AttendanceCheckResponse {
    final int id;
    final int studentId;
    final int scheduleId;
    final String checkType;
    final double? confidence;
    final bool wifiVerified;
    final String status;
    final DateTime timestamp;
    final String? studentName;  // Ambil dari mana? koordinasi dengan B

    AttendanceCheckResponse({...});

    factory AttendanceCheckResponse.fromJson(Map<String, dynamic> json) {...}
  }
  ```
- [ ] **Update `camera_screen.dart`** untuk menampilkan `status` ("present", "face_only", "partial", "verified") di layar hasil.
- [ ] **Update `attendance_screen.dart`** untuk menerima `AttendanceCheckResponse` bukan `AttendanceResult`.
- [ ] **Simpan `AttendanceResult` lama** untuk endpoint `POST /faces/recognize` (mungkin dipakai nanti).

### 2. `mobile/lib/services/api_service.dart`
**Apa yang sudah ada:** HTTP client dengan method `getStudents()`, `createStudent()`, `checkAttendance()`, `scanWifi()`, `getSchedules()`.

**Yang harus diperbaiki & ditambahkan:**

#### ⚠️ HIGH — Network Error Handling [EST: 2 jam]
- [ ] **Wrapper semua panggilan API** dengan try-catch. Jangan sampai app crash karena network error.
- [ ] **Buat helper function:**
  ```dart
  static Future<T> _safeRequest<T>(Future<T> Function() request, T fallback) async {
    try {
      return await request();
    } on SocketException {
      throw Exception("No internet connection. Check your network.");
    } on HttpException {
      throw Exception("Server error. Please try again later.");
    } on FormatException {
      throw Exception("Invalid response from server.");
    }
  }
  ```
- [ ] **Timeout handling:** Tambahkan `http.Client` dengan timeout 30 detik.
- [ ] **Retry mechanism:** Tambahkan opsi retry otomatis (1x retry untuk timeout).

#### HIGH — Student Login Screen [EST: 3-4 jam]
- [ ] **Buat `lib/screens/login_screen.dart`:**
  - TextField untuk NIM (nomor induk mahasiswa)
  - Tombol "Login"
  - Panggil `GET /students/` → cari student dengan NIM yang cocok
  - Simpan `student_id` dan `student_name` di SharedPreferences
  - Jika tidak ditemukan, tampilkan error "Student not found. Please contact admin."
- [ ] **Update `api_service.dart`:** Tambahkan method `getStudentByNim(String nim)` → `GET /students/?nim={nim}` (koordinasi dengan D untuk endpoint ini).
- [ ] **Update `main.dart`:** Setelah login, navigasi ke `HomeScreen` dengan parameter `studentId`.

#### HIGH — Enroll Face Screen [EST: 4-5 jam]
- [ ] **Buat `lib/screens/enroll_screen.dart`:**
  - Dropdown untuk memilih student (dari `GET /students/`)
  - Kamera preview
  - Tombol "Take Photo"
  - Panggil `POST /faces/enroll?student_id=X` dengan multipart upload
  - Tampilkan hasil: "Face enrolled successfully" + jumlah embedding
  - Jika gagal: "No face detected" atau error message
- [ ] **Update `home_screen.dart`:** Tambahkan tombol "Enroll Face" di halaman utama.

#### MEDIUM — Configurable Server URL [EST: 1-2 jam]
- [ ] **Buat `lib/screens/settings_screen.dart`:**
  - TextField untuk backend URL (default: `http://10.0.2.2:8000`)
  - Tombol "Save"
  - Simpan URL di SharedPreferences
  - Panggil `ApiService.setBaseUrl(url)` setelah disimpan
- [ ] **Update `home_screen.dart**: Tambahkan icon gear di AppBar untuk navigasi ke settings.
- [ ] **Update `main.dart`:** Load URL dari SharedPreferences saat startup.

#### MEDIUM — Attendance History Screen [EST: 2-3 jam]
- [ ] **Buat `lib/screens/history_screen.dart`:**
  - ListView dengan semua attendance record student yang login
  - Panggil `GET /attendance/student/{student_id}`
  - Tampilkan: class_name, check_type, status, timestamp, confidence
  - Color coding: hijau untuk "verified"/"present", kuning untuk "partial"/"face_only", merah untuk error
- [ ] **Update `home_screen.dart`:** Tambahkan tombol "My History".

#### LOW — UI Polish [EST: 2-3 jam]
- [ ] **Loading states:** Tambahkan shimmer/skeleton loader saat data di-load.
- [ ] **Empty states:** Tampilkan ilustrasi + teks jika tidak ada data (misal no schedules, no history).
- [ ] **Responsive layout:** Pastikan UI terlihat baik di layar kecil (5") dan besar (7").
- [ ] **Dark mode:** Dukung tema gelap (via `ThemeData` dengan `brightness: Brightness.dark`).
- [ ] **Localization:** Minimal support Bahasa Indonesia (gunakan `intl` package).

### 3. `mobile/lib/screens/home_screen.dart`
**Yang sudah ada:** Dropdown schedule, segmented button (start/end), tombol camera, tombol scan WiFi.

**Yang harus ditambahkan:**
- [ ] Tampilkan nama student yang sedang login (dari SharedPreferences).
- [ ] Tombol "Enroll Face" → navigasi ke `EnrollScreen`.
- [ ] Tombol "My History" → navigasi ke `HistoryScreen`.
- [ ] Tombol settings (gear icon) → navigasi ke `SettingsScreen`.
- [ ] Auto-refresh schedules setiap kali screen muncul (panggil `_loadSchedules()` di `didChangeDependencies`).

### 4. `mobile/lib/screens/camera_screen.dart`
**Apa yang sudah ada:** Camera preview, capture, upload to API.

**Yang harus diperbaiki:**
- [ ] **Fix response handling:** Ganti `AttendanceResult.fromJson` → `AttendanceCheckResponse.fromJson`.
- [ ] **Better error messages:** Jika status code 400, tampilkan detail error dari backend: `json.decode(response.body)["detail"]`.
- [ ] **Camera permission handling:** Jika kamera tidak tersedia atau permission denied, tampilkan pesan jelas dan tombol "Go Back".
- [ ] **Flash toggle:** Tambahkan tombol flash on/off untuk pencahayaan kurang.
- [ ] **Face guide overlay:** Tambahkan frame oval di tengah layar sebagai panduan posisi wajah (mirip face ID).

### 5. `mobile/lib/screens/attendance_screen.dart`
**Apa yang sudah ada:** Icon check/cancel, teks "ATTENDANCE RECORDED"/"NOT RECOGNIZED".

**Yang harus diperbaiki:**
- [ ] **Update untuk menerima `AttendanceCheckResponse`** — tampilkan:
  - `status`: "present"/"face_only"/"partial"/"verified"
  - `wifi_verified`: icon WiFi check atau silang
  - `confidence`: progres bar visual
  - `check_type`: "START" atau "END"
  - `timestamp`: waktu check-in
- [ ] **Animasi:** Tambahkan animasi circular reveal atau checkmark animation untuk pengalaman lebih baik.
- [ ] **Vibration & sound:** Tambahkan haptic feedback (vibrate) untuk sukses/gagal.

### 6. `mobile/pubspec.yaml`
**Yang perlu ditambahkan:**
- `flutter_local_notifications` (opsional, untuk notifikasi)
- Pastikan `camera: ^0.11.0+2` kompatibel dengan target SDK.

---

## DEPENDENCIES

| Package | Versi | Fungsi |
|---------|-------|--------|
| `http` | ^1.2.2 | HTTP client |
| `camera` | ^0.11.0+2 | Kamera |
| `path_provider` | ^2.1.4 | Path temp file |
| `shared_preferences` | ^2.3.2 | Local storage |
| `intl` | ^0.19.0 | Format tanggal |
| `flutter` | >=3.0.0 | Framework |

---

## INTEGRASI TIM
| Modul | Dependensi ke | Yang perlu dikoordinasikan |
|-------|---------------|---------------------------|
| api_service.dart | B (attendance router) | Format response `POST /attendance/check` |
| enroll_screen.dart | A (faces router) | Format response `POST /faces/enroll` |
| login_screen.dart | D (students router) | Endpoint `GET /students?nim=...` |
| history_screen.dart | B (attendance router) | Format response `GET /attendance/student/{id}` |

---

## ESTIMASI WAKTU
| Sub-task | Estimasi |
|----------|----------|
| Fix data contract mismatch | 1-2 jam |
| Network error handling | 2-3 jam |
| Login screen | 3-4 jam |
| Enroll face screen | 4-5 jam |
| Configurable URL (settings) | 1-2 jam |
| Attendance history screen | 2-3 jam |
| UI Polish | 2-3 jam |
| **Total** | **15-22 jam** |

---

## PRIORITAS
1. ⚠️ **CRITICAL** — Fix data contract (AttendanceCheckResponse model + camera_screen.dart)
2. ⚠️ **HIGH** — Network error handling (app jangan crash)
3. **HIGH** — Login screen (biar student bisa login)
4. **HIGH** — Enroll face screen (biar bisa daftar wajah dari HP)
5. **MEDIUM** — Configurable URL + history screen
6. **LOW** — UI Polish, animasi, dark mode