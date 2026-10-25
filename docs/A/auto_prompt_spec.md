# SPEC — Auto Check-in Prompt (Tingkat 1: Polling)

> Untuk dikerjakan/ direview **C (Flutter)**. Endpoint backend sudah JADI dan
> teruji hidup (lihat Progress Log 2026-10-24). Perubahan backend: TIDAK ADA
> aturan presensi yang berubah — ini rekomendasi UI murni di atas sistem lama.

## Status
- ✅ **Backend selesai**: `GET /me/prompt?student_id=N` (backend/routers/prompt.py,
  terdaftar di main.py) + 7 test (backend/tests/test_prompt.py) — suite 131/131 hijau.
- ⬜ **Flutter**: heartbeat + navigasi otomatis (spec di bawah).

## Kontrak endpoint

```
GET /me/prompt?student_id=<id>          # app polls every 15–30 s while open
200 → {
  "student_id": 8,
  "prompt": true,            # TRUE = app boleh menampilkan banner auto check-in
  "check_available": true,   # ada stage yang bisa diisi (start/end)
  "wifi_seen": true,         # MAC device siswa terdeteksi di jaringan kelas
  "reason": null,            # alasan jika prompt=false
  "schedule_id": 9,
  "class_name": "Uji Auto Prompt",
  "room": "Ruang Seminar",
  "check_type": "start",     # stage yang harus diisi ("start" lalu "end")
  "bssid": "54:2b:de:fd:90:21"
}
```

Nilai `reason` yang mungkin saat `prompt=false`:
- `no_active_schedule` — tak ada kelas aktif sekarang (bisa idle, berhenti polling/informasi)
- `device_not_seen_on_network` — kelas aktif tapi MAC HP tidak ditemukan (banner TIDAK boleh muncul otomatis)
- `check_in_complete` — start+end sudah lengkap (berhenti prompt)
- `device: null mac` — siswa belum punya MAC di server (pulangkan ke Settings/daftar MAC)

404 → `student_not_found` (session invalid; arahkan ke login).

## Rencana integrasi Flutter (siapa mengerjakan: C)

1. **Service baru** `lib/services/prompt_service.dart`:
   - poll `GET /me/prompt?student_id=<id>` tiap 15–30 s ketika app di foreground
     (Timer.periodic; `%` pertimbangkan stop dgn WidgetsBindingObserver saat
     background untuk hemat baterai).
   - state minimal: last prompt json + dedupe (jangan tampilkan banner dua kali
     untuk check_type yg sama → simpan `schedule_id+check_type` yang sudah
     ditawarkan di memori).
2. **UI banner** di HomeScreen saat `prompt==true`:
   "Kelas {class_name} ({room}) terdeteksi — {check_type} check-in sekarang?"
   + countdown ikut jendela kelas (opsional) + tombol [Ya] → navigasi kamera
   dengan parameter `student`, `schedule_id`, `check_type` (parameter yang sama
   seperti tombol manual yang sudah ada — reuse flow camera & service).
3. **Navigasi otomatis**: setelah tombol Ya, lanjutkan alur kamera lama
   (`camera screen` → POST `/attendance/check`) — endpoint & validasi TIDAK
   berubah. Jangan pernah bypass kamera manual (kunci UX jujur).
4. **Settings**: tambah field "Auto check-in (on/off)" default ON — kuesioner
   etika: kamera tidak boleh membuka semuanya tanpa satu konfirmasi tap siswa.
5. **Error handling**: server down / timeout → sembunyikan banner; coba lagi
   di poll berikutnya. Jangan crash app atau blok alur manual yang sudah ada.

## Keputusan desain (harus dipegang)
- `prompt` hanya true bila MAC terlihat → premis "HP siswa dinyatakan di
  kelas server". Tanpa Wi-Fi: banner TIDAK muncul otomatis (siswa masih bisa
  check-in manual → status akhir jadi `face_only`, aturan lama).
- Semua logic jendela waktu/duplikasi/missing start tetap di backend —
  app tidak menghitung apa pun sendiri.

## Masa depan (Tingkat 2/3 — TIDAK untuk pilot pertama)
- WebSocket push realtime (ganti polling), atau FCM jika server sekolah
  punya akses internet. Dokumen ini akibat menandatangani perubahan validasi.
- Android WorkManager + connectivity_plus untuk membangunkan polling saat
  app background.
