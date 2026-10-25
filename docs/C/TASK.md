# TUGAS C — Aplikasi Flutter, Pengujian Device Nyata & Rilis

> **SERAH-TERIMA (24 Okt 2026):** integrasi auto check-in prompt sudah
> **diprototipekan oleh A** atas permintaan team lead — kode draft ada di branch
> `a`, commit `7803d27` (`mobile/lib/services/prompt_service.dart` + banner di
> `home_screen.dart` + toggle di `settings_screen.dart`; spec:
> `docs/A/auto_prompt_spec.md`, live test: `docs/A/demo/`). **C dimohon
> review** sebelum melanjutkan — bukan mulai dari nol. Sisa tugas C di bawah
> (uji HP asli dsb.) tetap seperti aslinya.

> **Baca dulu:** `docs/PROJECT_CONTEXT.md` dan `docs/PLAN_TIMELINE.md`.
> Estimasi total beban kerja: **18–22 jam** (seimbang dengan B dan D; A tetap terberat).

Fokus kamu: aplikasi mobile harus **benar-benar berjalan mulus di HP asli** — saat ini
baru pernah dites di emulator/mocked. Semua screen sudah ada (login, home, camera,
enroll, history, settings, attendance) di `mobile/lib/screens/`. Tugas kamu menguji,
memperhalus, dan membuat build rilis — bukan membangun dari nol.

---

## PRIORITAS 0 — wajib sebelum laporan kemajuan (~1 Nov 2026)

### C1. Uji alur penuh di HP Android ASLI
Siapkan: 1 HP Android asli (aktifkan USB debugging), backend jalan di PC
(`uvicorn backend.main:app --reload`), HP dan PC di Wi-Fi yang sama.

1. `cd mobile` → `flutter pub get` → `flutter run` (pilih HP fisik, bukan emulator).
2. Di app: **Settings** → isi Server URL dengan `http://<IP-lokal-PC>:8000`
   (bukan `10.0.2.2` — itu hanya untuk emulator). Tes koneksi.
3. Jalankan alur lengkap dan catat hasil tiap langkah di `docs/C/device_test_log.md`:
   - Login dengan NIM yang terdaftar (`GET /students/?nim=`)
   - **Enroll Face**: ambil ≥3 selfie → muncul pesan sukses + jumlah embedding
   - Pilih jadwal yang aktif → **check-in START** → status `partial` muncul benar
   - **check-in END** → status `verified` (atau `face_only` jika Wi-Fi gagal)
   - **History**: riwayat muncul, warna status benar
4. Uji kasus tepi (edge cases) dan catat: izin kamera ditolak lalu diberikan; server
   mati saat app terbuka; jadwal kosong; selfie gelap/tutup mata; check-in dobel
   (harus muncul error 409 yang manusiawi, bukan crash).
5. Catat juga: merek/versi HP, versi Android, perilaku kamera (lambat? fokus?).

**Selesai jika:** setiap langkah alur ada baris hasil di `device_test_log.md`, semua
bug yang ditemukan ada nomor issue + screenshot (simpan di `docs/C/screenshots/`),
dan bug ringan langsung kamu perbaiki.

### C2. Bahan laporan kemajuan
Ringkas hasil C1 (alur mana yang lolos, bug apa yang ketemu) untuk D paling lambat
**29 Okt 2026**.

---

## PRIORITAS 1 — November 2026

### C3. Perbaiki bug hasil pengujian device
Bekerja dari `device_test_log.md`: satu issue = satu commit kecil. Kalau penyebabnya di
backend (misal response berubah), koordinasi dengan B — jangan ubah backend sendiri.

### C4. Polish UX
- **Loading state** di setiap screen yang manggil API (indicator/skeleton).
- **Empty state**: tidak ada jadwal / tidak ada history → tampil pesan + ilustrasi
  sederhana, bukan layar kosong.
- **Error state**: pesan error dari backend (`detail`) ditampilkan manusiawi +
  tombol "Coba lagi". App TIDAK BOLEH crash karena jaringan.
- Dark mode (opsional kalau waktu cukup).

### C5. Build rilis v0.9 (untuk demo)
1. Ganti nama tampilan app & ikon (`flutter_launcher_icons` atau manual di
   `android/app/src/main/res`), set `version:` di `pubspec.yaml` (mis. `0.9.0+1`).
2. `flutter build apk --release` → APK ada di `build/app/outputs/flutter-apk/`.
3. Install APK di HP KEDUA (bukan HP dev) → ulangi alur inti. Ini meniru kondisi guru/siswa.
4. Simpan APK dengan nama versi jelas; jangan commit APK ke repo (besar) — simpan di
   Drive/share tim.

---

## PRIORITAS 2 — Desember 2026 – Maret 2027

### C6. Dukungan pilot kelas nyata (Desember)
Siapkan HP demo untuk siswa: app ter-install, server URL tersetel, kamera cepat.
Bantu siswa selama pilot, catat masalah UX yang mereka alami.

### C7. Persiapan demo presentasi (Januari 2027)
- HP demo siap: baterai penuh, APK final, brightness pas, mode terbang MATI.
- Punya rencana cadangan: rekaman video alur (30–60 detik) kalau demo live gagal
  (koordinasi dengan D yang merekam).

### C8. Release final v1.0 + bab laporan (Februari–Maret 2027)
- Perbaiki semua temuan pilot; `flutter analyze` bersih; build v1.0.
- Update `mobile/README.md` (masih boilerplate Flutter!) → isi: fitur app, screen
  list, cara build, cara set server URL, troubleshooting kamera.
- Bab laporan akhir — "Aplikasi Mobile": serahkan ke D paling lambat **1 Mar 2027**
  (arsitektur app, alur UI, hasil uji device, kendala nyata di lapangan).

---

## Batasan kerja (wajib)
- Branch: `task-c`. Sebelum commit: `flutter analyze` bersih dan backend tetap hijau.
- File yang boleh kamu ubah: semua di `mobile/**` (kecuali `mobile/README.md` boleh,
  itu tugasmu), `docs/C/*`. Backend → koordinasi dengan B/A; dashboard → milik D.
- Jangan commit: file build (`build/`, `.dart_tool`), APK, database, foto wajah.
- Macet >30 menit → tanya di grup.

## Deliverable per milestone
| Milestone | Yang harus ada dari kamu |
|---|---|
| M1 (~1 Nov 2026) | `device_test_log.md` lengkap + bug ringan diperbaiki + ringkasan untuk D |
| M2 (~18 Jan 2027) | APK v0.9 teruji di 2 HP + HP demo siap + bug demo diperbaiki |
| M3 (~18 Mar 2027) | APK v1.0 final + `mobile/README.md` baru + bab laporan mobile |
