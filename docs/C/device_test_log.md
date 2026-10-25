# Device Test Log — C1 (HP Android asli)

> Diisi saat langkah uji berjalan (tugas C1 di `docs/C/TASK.md`).
> Backend jalan di laptop: `$env:TIMEZONE='Asia/Shanghai'; python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`
> App di HP → Settings → Server URL = `http://<IP-laptop>:8000` → Test Connection.

## Perangkat uji
| Item | Nilai |
|---|---|
| HP | (merek + model) |
| Android versi | |
| Build | `app-debug.apk` (169.2 MB, 2026-10-25) |
| Server URL dipakai | |
| Kondisi jaringan | HP + laptop satu Wi-Fi? AP: `54:2b:de:fd:90:21` |

## Alur uji (centang saat lulus)
- [ ] **Install**: `adb install build\app\outputs\flutter-apk\app-debug.apk` — app terbuka tanpa crash
- [ ] **Login**: NIM `F25040126` (Buchari) → profil muncul
- [ ] **Settings**: server URL tersimpan + Test Connection hijau (izin "network" OK)
- [ ] **Create demo class** (simulator/sistem) → jadwal aktif +1..+10 menit CST
- [ ] **AUTO PROMPT**: banner "Class ... detected!" muncul otomatis di Home saat kelas aktif + MAC terlihat
- [ ] Tap **Check in now** → layar kamera terbuka → ambil selfie
- [ ] **START** check → hasil: confidence ≥ threshold, status `partial`
- [ ] Banner kedua (**END**) muncul sendiri beberapa saat kemudian → selfie lagi
- [ ] **END** check → status `verified` (Wi-Fi OK) / `face_only` (Tanpa Wi-Fi)
- [ ] Banner **berhenti** setelah lengkap (`check_in_complete`) — tidak muncul lagi
- [ ] **History**: riwayat hari ini tampil, warna status benar
- [ ] **Dashboard guru** (PC) baris presensi sesuai + jam CST tampil tepat

## Kasus tepi (catat hasil)
| Kasus | Hasil (kelakuan + screenshot #) |
|---|---|
| Izin kamera ditolak lalu diizinkan ulang | |
| Server mati saat app terbuka (banner harus senyap, app tidak crash) | |
| Tidak ada kelas aktif (idle, banner tidak muncul) | |
| Willian (`F25040128`, tanpa MAC): kelas aktif | banner TIDAK boleh muncul (`device_not_seen_on_network`) |
| DOBEL check-in stage sama (harus 409 manusiawi) | |
| Foto yang SAMA dipakai orang lain (anti-replay → 409) | |
| MAC jadwal duplikat via settings (server tolak — kalau UI-nya tersedia) | |
| Selfie gelap / tutup mata (face not recognized) | |
| MAC randomization HP ON (device tidak terlihat → banner tidak muncul) | |

## Catatan kinerja
- Waktu buka kamera: ___ s — lambat/fokus? ___
- Polling terasa? (app idle OK, tidak berat) ___
- Bug ditemukan → tandai issue #:

## Screenshot
Simpan di `docs/C/screenshots/`, nomor sesuai tabel di atas.
