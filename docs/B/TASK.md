# TUGAS B — Backend, Validasi Wi-Fi Nyata & Deployment

> **Baca dulu:** `docs/PROJECT_CONTEXT.md` dan `docs/PLAN_TIMELINE.md`.
> Estimasi total beban kerja: **18–22 jam** (seimbang dengan C dan D; A tetap terberat).

Fokus kamu: membuktikan bahwa backend **benar-benar bekerja di luar mesin pengembang** —
di jaringan Wi-Fi nyata, di Docker, di mesin demo — dan menyiapkan lingkungan demo
untuk presentasi. Logika two-stage & schedule enforcement SUDAH selesai dan lolos tes;
jangan diubah.

---

## PRIORITAS 0 — wajib sebelum laporan kemajuan (~1 Nov 2026)

### B1. Validasi Wi-Fi di jaringan NYATA
Wi-Fi scanner belum pernah diuji di router sungguhan. Uji dan catat hasilnya:

1. Nyalakan server (`uvicorn backend.main:app --reload`), pastikan laptop/PC terhubung
   Wi-Fi (Windows: butuh **Npcap** terpasang untuk Scapy).
2. Hubungkan 1–2 HP ke Wi-Fi yang sama, lalu:
   - `GET /wifi/scan` → apakah MAC HP muncul di daftar device?
   - `GET /wifi/check/{mac_hp}` → `on_network: true`?
3. Uji perilaku spesifik dan catat hasilnya:
   - **Subnet auto-detect** (`WI_FI_SUBNET` tidak diset) → apakah subnet terdeteksi benar?
   - **Dedupe 60 detik**: scan dua kali berturut-turut → tabel `ap_logs` tidak dobel.
   - **BSSID pinning**: buat jadwal dengan `ap_bssid` diisi → check-in harus jadi
     `face_only` kalau server tidak terhubung ke AP itu (`is_same_bssid(get_current_bssid(), ap_bssid)`).
   - **Kecepatan**: berapa detik satu scan penuh?
4. Catat SEMUA hasil di file baru `docs/B/network_validation.md`:
   tabel pengujian (skenario, hasil, catatan), model router/OS, kegagalan yang ditemui.

**Selesai jika:** `docs/B/network_validation.md` berisi hasil nyata (bukan prediksi)
untuk semua skenario di atas, dan kamu tahu persis kenapa `face_only` terjadi kalau MAC
tidak terdeteksi.

### B2. Bahan laporan kemajuan
Ringkas hasil B1 jadi 1 paragraf + tabel untuk D paling lambat **29 Okt 2026**.

---

## PRIORITAS 1 — November 2026

### B3. Deployment di mesin demo
1. `docker compose up -d --build` dari root → cek `docker compose logs -f backend`.
2. Verifikasi: `GET /health` ok, database persist setelah container di-restart
   (volume `backend-data`), env variables terbaca (`TIMEZONE=Asia/Jakarta`,
   `CORS_ORIGINS` spesifik, `FACE_SIMILARITY_THRESHOLD` dari A).
3. Jalankan smoke test ke server Docker:
   `python backend/scripts/smoke_test.py --base-url http://127.0.0.1:8000`
4. Tulis `docs/B/deployment_guide.md`: langkah dari nol (install Docker → build →
   set env → verifikasi), ditulis untuk orang non-teknis sekalipun (bakal dipakai D & guru).

### B4. Data demo untuk presentasi
Buat script `backend/scripts/seed_demo.py` (koordinasi dulu dengan A sebelum menambah
script): bikin siswa contoh + jadwal yang aktif pas jam presentasi + data presensi
contoh, plus opsi `--reset` untuk membersihkan. Ini cadangan kalau demo live gagal.

### B5. Verifikasi fitur data teacher
- `GET /attendance/export/csv?date=&schedule_id=` → buka CSV-nya, cek kolom & format tanggal.
- `GET /attendance/student/{id}` → cek pagination (`limit`, `offset`) dan header
  `X-Total-Count` benar.
- Dashboard guru membaca data yang sama (jangan ubah `dashboard.html` — itu milik D).

---

## PRIORITAS 2 — Desember 2026 – Februari 2027

### B6. Dukungan pilot kelas nyata
Bersama A: siapkan server di ruang kelas (kunci: Wi-Fi AP kelas, `TIMEZONE`, threshold
final), pantau selama pilot, catat masalah jaringan yang muncul.

### B7. Hardening produksi (checklist, kerjakan setelah pilot)
- `CORS_ORIGINS`: ganti `*` dengan origin dashboard/HP yang dipakai sekolah.
- Backup `attendance.db` (langkah manual singkat, masukkan ke deployment guide).
- Pastikan `MAX_UPLOAD_BYTES`, `MAX_EMBEDDINGS_PER_STUDENT`, `MIN_FACE_BBOX_PX`
  sesuai kebutuhan sekolah.
- Rencana fallback demo offline (bahan M2): server lokal + hotspot + data seed.

### B8. Bab laporan akhir — "Arsitektur Backend & Alur Presensi"
Serahkan ke D paling lambat **1 Mar 2027**: diagram alur check-in (request → validasi
waktu → deteksi → recognition → Wi-Fi → two-stage pairing → status), penjelasan
arsitektur service, hasil validasi jaringan, deployment.

---

## Batasan kerja (wajib)
- Branch: `task-b`. Tes hijau sebelum commit (`python -m pytest backend/tests -q`).
- File yang boleh kamu ubah: `backend/services/wifi_scanner.py` (jika ada bug hasil
  validasi), `backend/Dockerfile`, `docker-compose.yml`, `backend/scripts/seed_demo.py`
  (baru), `docs/B/*`. Router/service lain → koordinasi dengan pemilik.
- JANGAN ubah: `backend/static/dashboard.html` (milik D), `mobile/**` (milik C),
  `backend/services/attendance.py` & `face_recognition.py` (milik A) tanpa izin.
- Jangan commit: `attendance.db`, `*.pkl`, model `.pt`, foto wajah, log.
- Macet >30 menit → tanya di grup.

## Deliverable per milestone
| Milestone | Yang harus ada dari kamu |
|---|---|
| M1 (~1 Nov 2026) | `docs/B/network_validation.md` berisi hasil nyata + ringkasan untuk laporan |
| M2 (~18 Jan 2027) | Backend ter-deploy di mesin demo + `seed_demo.py` + deployment guide awal |
| M3 (~18 Mar 2027) | Hardening selesai + deployment guide final + bab backend laporan |
