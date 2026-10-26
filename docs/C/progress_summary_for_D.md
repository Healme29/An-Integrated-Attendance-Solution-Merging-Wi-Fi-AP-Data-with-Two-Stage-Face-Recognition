# Progress Summary for D — C (Flutter / Real Devices) — FINAL, 2026-10-26

> Status: **C1 (uji HP asli) LOLOS untuk alur inti + kasus tepi kunci.**
> Sumber: `docs/C/device_test_log.md` (detail), `docs/C/review_7803d27.md` (review).

## 1. Ringkasan status

- Handover draft auto check-in prompt dari anggota A (commit `7803d27`)
  **di-review dan diterima** — sesuai `docs/A/auto_prompt_spec.md`.
- Branch kerja: `task-c` — 6 commit hari ini (fix bug kamera, review notes,
  empty states, versi+ikon, draft C2, log uji).

## 2. Uji di HP asli (C1) — HASIL

| Item | Nilai |
|---|---|
| Perangkat | Samsung Galaxy S24 (SM-S921B), Android 16 (API 36) |
| Build | `app-debug.apk` (177 MB, branch `task-c`) |
| Backend | laptop, TIMEZONE `Asia/Shanghai`, `/health` ok |
| Konektivitas | LAN kampus diblokir (firewall/AP isolation) → jalur USB `adb reverse` + URL `http://127.0.0.1:8000` — valid because MAC detection is server-side (ping sweep + ARP) |

**PASS (user-confirmed):** install, login (NIM), Settings + Test Connection,
kamera + selfie, START → `partial`, END → sukses, History.
**PASS (server-side evidence):** willian tanpa MAC → `device_not_seen_on_network`;
dobel check-in → 409 manusiawi; anti-replay → 409; luar-jadwal → 403 (diamati sendiri).
**Opsional tersisa:** banner otomatis live (butuh MAC terlihat), selfie gelap live,
MAC randomization live — logika server & app sudah terverifikasi unit/live lain.

## 3. Temuan & perbaikan bug (C3)

| # | Temuan | Solusi | Status |
|---|---|---|---|
| 1 | Kamera init gagal (izin ditolak dll.) → spinner abadi + crash laten di `dispose()` | Error state manusiawi + instruksi izin + **Retry** (mengikuti pola enroll) | ✅ commit `53ba44d` |
| 2 | Konektivitas: HP gagal menjangkau server via LAN kampus | `adb reverse` + URL `127.0.0.1:8000`; insiden `jam laptop salah 8 jam` juga ditemukan & disinkronkan | ✅ ditangani |

## 4. Polish UX (C4) & rilis (C5)

- Empty states: jadwal kosong (pesan + Refresh) & riwayat kosong (ikon + pesan)
  ✅ commit `de4a1bf`
- Rilis pra-v0.9: versi `0.9.0+1` + ikon app baru (person + check, 5 densitas)
  ✅ commit `c0ee76b` — **build `flutter build apk --release` dipicu terpisah;
  uji di HP KEDUA menunggu perangkat (Nov)**

## 5. Kebutuhan dari anggota lain

- **A/B:** tidak ada bug backend yang perlu di-fix — semua temuan hari ini
  sisi Flutter/lingkungan. API contract 100% sesuai spesifikasi.
- **Catatan isolasi kampus:** demo ke guru nanti (M2, ~18 Jan) — jika LAN kampus
  tetap terisolasi, jalankan server di hotspot laptop/HP atau pakai kabel USB;
  Wi-Fi verification tetap valid karena dihitung di sisi server.
