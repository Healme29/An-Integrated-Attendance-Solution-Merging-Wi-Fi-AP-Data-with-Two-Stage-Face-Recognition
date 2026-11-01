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

> **ATURAN BAHASA:** OUTPUT DAN INPUT DI SEMUA SISTEM PROYEK INI HARUS DALAM BAHASA
> INGGRIS, karena tugas besar ini berbahasa Inggris dan hasilnya juga dinilai dalam bahasa
> Inggris. Artinya: teks UI aplikasi, pesan error, log, komentar kode, commit message,
> seluruh `docs/**`, README mobile, slides, dan video — semuanya Inggris. Yang boleh tetap
> Indonesia: arahan tugas ini dan obrolan di grup.

> **M2:** paket kerjamu ada di bagian "PAKET KERJA M2" di bawah. Kamu yang membagi waktu
> per minggu; yang tetap hanya urutan tahap + tanggal gate (`docs/PLAN_TIMELINE.md` §2.1).

---

## PRIORITAS 0 — M1 (SELESAI 1 Nov 2026)

> ✅ Alur penuh lulus di HP asli (Galaxy S24), kasus tepi terdokumentasi, APK v0.9.0
> terbangun dan terpasang. Catatan lama di bawah disimpan sebagai referensi.

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

## PAKET KERJA M2 — "Aplikasi di tangan siswa" (2 Nov 2026 → 18 Jan 2027)

> Satu paket besar. Kamu yang membagi waktu per minggu; yang tetap adalah **urutan tahap**
> dan **tanggal gate** (`docs/PLAN_TIMELINE.md` §2.1). Setiap keputusan tidak sepele wajib
> ditulis di `docs/C/DECISIONS.md` — itu bagian dari penilaian M2.

**Tujuan besar:** aplikasi yang dipakai siswa asli di kelas asli tidak crash, tidak
membingungkan, dan bisa dipasang ulang kapan saja oleh siapa pun di tim.

| # | Tahap | Periode | Gate | Yang dikerjakan + bukti |
|---|-------|---------|------|--------------------------|
| 1 | Rilis teruji dua HP | 2–8 Nov | **G2** | APK v0.9 di HP **kedua** (bukan HP dev), alur inti lulus, catat perbedaan perilaku antar perangkat di `device_test_log.md` |
| 2 | Ambil alih auto check-in + polish UX | 9–22 Nov | **G6** | Review `7803d27`, jadikan milikmu, selesaikan banner → kamera → start/end di HP asli; loading / empty / error state + retry di semua layar; app tidak boleh crash karena jaringan |
| 3 | Siapkan pengalaman siswa | 23 Nov–6 Des | — | Alur enroll jelas (3–5 selfie + panduan wajah), instruksi pilot satu halaman untuk siswa, HP pilot ter-install + URL server tersetel |
| 4 | Dukung pilot | 7–13 Des | **G9** | Dampingi siswa, catat kebingungan UX secara real-time (bukan dari ingatan setelahnya) |
| 5 | Perbaiki temuan + bangun RC | 14 Des–3 Jan | **G11** | Satu temuan satu commit kecil; `flutter analyze` bersih; build release candidate |
| 6 | Siapkan demo | 4–18 Jan | **G13–G16** | APK final; HP demo (baterai, brightness, mode pesawat mati, kamera diuji); rekam layar untuk video cadangan bersama D |

**Selesai jika (DoD):** APK terpasang dan lulus di dua HP; auto check-in jalan tanpa
intervensi manual; instruksi siswa ada; HP demo punya checklist yang bisa dijalankan orang
lain dalam dua menit.

**Pertanyaan kritis wajib kamu jawab sendiri** (di `docs/C/DECISIONS.md`):

- Kalau koneksi HP→PC diblokir Wi-Fi kampus (sudah terbukti), jalur mana yang kita bakukan
  untuk demo: `adb reverse`, hotspot, atau server publik? Bandingkan risiko tiap opsi.
- Berapa lama siswa butuh dari membuka app sampai check-in selesai? Ukur pada 3 orang.
- Pada kondisi apa app sebaiknya **menolak** check-in daripada mencoba terus (misal kamera
  gelap)? Siapa yang dirugikan oleh tiap pilihan?
- Apa yang terjadi kalau siswa menutup app di antara dua tahap? Sudahkah diuji?

ID lama tetap berlaku: C3 = tahap 2, C4 = tahap 2, C5 = tahap 1+5, C6 = tahap 3+4,
C7 = tahap 6.

---

## M3 (19 Jan – 18 Mar 2027) — belum dimulai

### C8. Release final v1.0 + bab laporan
- Perbaiki semua temuan pilot; `flutter analyze` bersih; build v1.0.
- Update `mobile/README.md` (masih boilerplate Flutter!) → isi: fitur app, daftar screen,
  cara build, cara set server URL, troubleshooting kamera.
- Bab laporan akhir — "Aplikasi Mobile": serahkan ke D paling lambat **1 Mar 2027**
  (arsitektur app, alur UI, hasil uji device, kendala nyata di lapangan).

---

## Batasan kerja (wajib)
- Branch: `task-c`. Sebelum commit: `flutter analyze` bersih dan backend tetap hijau.
- File yang boleh kamu ubah: semua di `mobile/**` (kecuali `mobile/README.md` boleh,
  itu tugasmu), `docs/C/*`. Backend → koordinasi dengan B/A; dashboard → milik D.
- Jangan commit: file build (`build/`, `.dart_tool`), APK, database, foto wajah.
- Macet >30 menit → tanya di grup **dengan usulan**, bukan dengan masalah mentah.
- Setiap keputusan tidak sepele wajib masuk `docs/C/DECISIONS.md` (problem → minimal 2 opsi
  → bukti → keputusan → konsekuensi → kapan ditinjau ulang).

## Deliverable per milestone
| Milestone | Yang harus ada dari kamu |
|---|---|
| M1 (~1 Nov 2026) | ✅ `device_test_log.md` lengkap + bug ringan diperbaiki + ringkasan untuk D |
| M2 (~18 Jan 2027) | G2 dua HP teruji · G6 auto check-in selesai · dukungan pilot · HP demo + APK final |
| M3 (~18 Mar 2027) | APK v1.0 final + `mobile/README.md` baru + bab laporan mobile |
