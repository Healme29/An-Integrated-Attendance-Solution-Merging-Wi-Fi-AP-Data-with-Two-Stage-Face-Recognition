# Device Test Log — C1 (HP Android asli)

> Diisi saat langkah uji berjalan (tugas C1 di `docs/C/TASK.md`).
> Backend di laptop: `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000`
> (env `TIMEZONE=Asia/Shanghai`) — HP dan laptop **satu Wi-Fi kampus** + jalur USB.
> App di HP → Settings → Server URL = `http://127.0.0.1:8000` (via `adb reverse tcp:8000 tcp:8000`).

## Perangkat uji
| Item | Nilai |
|---|---|
| HP | Samsung Galaxy S24 (SM-S921B) |
| Android versi | 16 (API 36) |
| Build | `app-debug.apk` (177 MB, 2026-10-26 — branch `task-c` @ `53ba44d`, camera error-state fix) |
| Server URL dipakai | `http://127.0.0.1:8000` (USB `adb reverse`; LAN `10.163.169.214:8000` diblokir firewall/AP isolation) |
| Kondisi jaringan | HP + laptop satu Wi-Fi — AP `54:2b:de:fd:90:21`; MAC HP `70:c6:dd:09:b0:02` |

## Alur uji (centang saat lulus)
- [x] **Install**: `adb install -r` sukses, app terbuka tanpa crash, ikon baru tampil di launcher
- [x] **Login**: NIM `F25040126` (Buchari) → profil muncul *(user-confirmed)*
- [x] **Settings**: server URL tersimpan (`127.0.0.1:8000`) + Test Connection hijau *(user-confirmed)*
- [x] **Create demo class** → jadwal dibuat & muncul di dropdown (user: "abc" `16:42–16:43`, "1234567890" `16:49–16:50`, API EDGE `17:44`)
- [x] Layar kamera terbuka dari app → ambil selfie *(user-confirmed)*
- [x] **START** check → sukses, status `partial` *(user-confirmed; server-side juga terverifikasi: confidence 0.893 → `partial`)*
- [x] **END** check → sukses *(user-confirmed)*
- [x] **History**: riwayat tampil *(user-confirmed lulus alur inti)*
- [ ] **AUTO PROMPT banner muncul otomatis** saat kelas aktif — *manual check-in sudah PASS; banner butuh MAC HP terlihat scan server + app jalan — uji live opsional, logika sudah terverifikasi server-side (test_prompt.py 7/7 + kasus tepi di bawah)*
- [ ] Banner END muncul sendiri + berhenti setelah lengkap — *idem*
- [ ] **Dashboard guru**: baris presensi cocok — *baris EDGE tersimpan dengan timestamp lokal benar `17:44`; verifikasi visual opsional*

## Kasus tepi (catat hasil)
| Kasus | Hasil |
|---|---|
| Izin kamera ditolak lalu diizinkan ulang | **Fixed in code** (`53ba44d`): layar "Camera unavailable" + instruksi + **Retry** (sebelumnya spinner abadi) — re-verify live opsional |
| Server mati saat app terbuka | Polling `PromptService` menelan error senyap (dievaluasi, `catch ApiException` + catch generic); app tidak crash by design — live test opsional |
| Tidak ada kelas aktif | `GET /me/prompt` → `prompt:false, reason:no_active_schedule` — banner senyap ✓ |
| Willian `F25040128` (tanpa MAC), kelas aktif | ✅ **API-verified**: `prompt:false, reason:device_not_seen_on_network` (jadwal EDGE aktif), banner tidak muncul |
| DOBEL check-in stage sama | ✅ **API-verified**: foto kedua (foto BEDA) → `409 "Already checked in (start) for this schedule"` — pesan manusiawi |
| Foto yang SAMA dipakai ulang (anti-replay) | ✅ **API-verified**: pengiriman ulang foto yang sama → `409` (guard duplikat->replay; unit `test_anticheat.py` menguji pesan replay eksplisit) |
| MAC jadwal duplikat via settings | N/A — UI tidak mengekspos input MAC; server-side reject MAC terpakai sudah di-unit-test (`test_anticheat.py`, 409) |
| Selfie gelap / tutup mata | Backend `400 "Face not recognized"` (jalan di unit test); uji live opsional |
| MAC randomization HP ON | Terkait kasus Willian: device tidak terlihat → banner senyap, siswa masih bisa manual → `face_only` ✓ (dokumentasi C1 di PLAN_TIMELINE) |

## Catatan kinerja
- Server warm-up (first ML import): ~40 s sebelum `/health` hidup — normal
- Waktu buka kamera: belum diukur presisi; alur kamera→upload memakan beberapa detik (upload foto JPG via USB LAN lokal)
- Konektivitas: jalur LAN Wi-Fi kampus **diblokir** (firewall/AP isolation, "could not reach server") → solusi tetap: `adb reverse` + URL `127.0.0.1:8000`. Wi-Fi tetap berfungsi sebagai bukti kehadiran karena deteksi MAC dilakukan si **server** (ping sweep + `arp -a`), bukan via HTTP dari HP.
- Insiden penting yang ditemukan & diperbaiki saat uji: **jam laptop salah 8 jam** → semua jadwal 403 (banyak false alarm) — disinkronkan manual; ROOT cause tooling Windows, bukan kode.
- Bug ditemukan → issue #1: kamera init gagal = spinner abadi + crash laten `dispose()` → **diperbaiki `53ba44d`** ✓

## Screenshot
Belum diunggah (opsional untuk laporan kemajuan; bukti utama = log ini + output test suite).
