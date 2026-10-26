# Progress Summary for D — C (Flutter / Real Devices) — draft 1, 2026-10-26

> Status pre-progress: C1 masih berjalan (menggunakan jalur USB `adb reverse`
> karena jalur LAN Wi-Fi kampus kemungkinan diblokir firewall/AP isolation —
> lihat bagian "Belum terselesaikan"). Dokumen ini akan difinalkan sebelum
> **29 Okt 2026**.

## 1. Ringkasan status

- Handover draft auto check-in prompt dari anggota A (commit `7803d27`) sudah
  **di-review dan diterima** — implementasi sesuai `docs/A/auto_prompt_spec.md`
  (polling `GET /me/prompt`, banner per stage unik, error silent). Catatan
  lengkap: `docs/C/review_7803d27.md`.
- Branch kerja: `task-c`.

## 2. Uji di HP asli (C1) — setup selesai, alur inti pengujian berjalan

| Item | Nilai |
|---|---|
| Perangkat | Samsung Galaxy S24 (SM-S921B), Android 16 (API 36) |
| Build | `app-debug.apk` (177 MB), branch `task-c` @ fix kamera `53ba44d` |
| Backend | di laptop, TIMEZONE `Asia/Shanghai`, `/health` ok |
| Konektivitas | Jalur LAN `10.163.169.214:8000` GAGAL dari HP; fallback `adb reverse tcp:8000 tcp:8000` (akses USB) dengan URL `http://127.0.0.1:8000` |
| Akun uji | Buchari `F25040126` (MAC terdaftar), Willian `F25040128` (tanpa MAC) |

## 3. Temuan perbaikan bug (C3) — temporarily 1

| # | Temuan | Solusi | Status |
|---|---|---|---|
| 1 | Kamera init gagal (mis. izin ditolak) → layar spinner abadi + potensi crash `LateInitializationError` saat dispose | Layar error manusawi + petunjuk mengizinkan kamera + tombol "Retry" (mengikuti pola enroll) | ✅ commit `53ba44d` |

## 4. Belum terselesaikan (akan update sebelum 29 Okt)

- Halaman "Test Connection" server via LAN Wi-Fi kampus → **dugaan Windows
  Firewall inbound TCP 8000 / AP isolation** — sedang dibypass dengan jalur USB;
  cek keaslian Wi-Fi tidak terpengaruh karena MAC verification dilakukan di
  sisi server melalui scan ARP laptop.
- Alur inti: login → enroll → START → END → history — sedang dijalankan, hasil
  per langkah masuk `docs/C/device_test_log.md` (PASS/FAIL + screenshot).
- 9 kasus tepi (izin kamera, server mati, dobel check-in 409, anti-replay,
  MAC randomization, dll.) — belum semua dijalankan.

## 5. Kebutuhan dari anggota lain

- **A/B:** tidak ada perubahan backend yang dimintakan C saat ini (semua bug
  yang ditemukan di sisi Flutter).
- **B/A:** bila LAN demo nanti tetap terisolasi, pertimbangkan hotspot
  laptop sebagai AP uji agar `wifi_seen` dapat diverifikasi end-to-end.
