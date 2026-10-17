# TUGAS A — LEAD: Validasi ML, Threshold Tuning & Integrasi

> **Baca dulu:** `docs/PROJECT_CONTEXT.md` (konteks lengkap proyek) dan
> `docs/PLAN_TIMELINE.md` (tenggat ganti). File ini adalah daftar tugasmu.
> Estimasi total beban kerja: **25–30 jam** (bagian paling rumit di tim, sesuai kesepakatan).

Peran kamu ada dua: (1) **validasi akurasi sistem dengan data nyata** — bagian teknis
paling kritis proyek, dan (2) **lead**: review PR anggota lain, jaga tes tetap hijau,
pimpin integrasi dan uji coba kelas nyata.

Yang sudah TIDAK perlu kamu kerjakan (sudah selesai & lolos tes): two-stage logic,
schedule enforcement, hardening enrollment, NIM lookup, CSV export. Jangan dibangun ulang.

---

## PRIORITAS 0 — wajib sebelum laporan kemajuan (~1 Nov 2026)

### A1. Evaluasi threshold dengan data wajah NYATA (paling penting)
Sistem masih memakai nilai default `FACE_SIMILARITY_THRESHOLD = 0.5` yang belum pernah
diuji. Kamu harus mengganti placeholder di `docs/threshold_report.md` dengan angka nyata.

Langkah konkret:
1. Enroll minimal **3 orang, masing-masing ≥3 selfie** dengan kondisi kelas asli
   (kamera depan HP, lewat app atau Swagger `POST /faces/enroll?student_id=`).
2. Jalankan:
   ```bash
   python backend/scripts/evaluate_threshold.py --markdown --output docs/threshold_report.md
   ```
   Script ini hanya membaca `backend/data/embeddings/student_*.pkl` — tidak memuat model
   ML, aman dijalankan di mesin mana pun.
3. Baca tabel FAR/FRR dan EER. Patokan ArcFace: pasangan orang yang sama biasanya
   skor >0.6, orang berbeda <0.35. Untuk presensi kelas, pilih threshold sedikit DI ATAS
   EER (ditolak bisa retry; diterima palsu = presensi salah).
4. Kalau distribusi genuine/impostor tumpang tindih → perbaiki kualitas enroll
   (pencahayaan, jumlah sampel), JANGAN asal geser threshold.
5. Tulis threshold terpilih ke konfigurasi deployment (env `FACE_SIMILARITY_THRESHOLD`)
   dan catat di `docs/threshold_report.md`.

**Selesai jika:** `docs/threshold_report.md` berisi tabel FAR/FRR nyata, nilai EER,
threshold terpilih + alasannya (bukan placeholder).

### A2. Review & merge pekerjaan anggota
- Semua PR dari `task-b`, `task-c`, `task-d` kamu review sebelum merge.
- Jaga baseline tes: `python -m pytest backend/tests -q` → 124 lulus setelah D
  memperbaiki tes dashboard.
- PR kamu sendiri: minta B jadi pemeriksa kedua (cross-check).

---

## PRIORITAS 1 — November–Desember 2026

### A3. Eksperimen YOLO (dokumentasikan trade-off, jangan asal ubah)
- `YOLO_CONF_THRESHOLD`: bandingkan 0.25 vs 0.30 vs 0.35 → catat recall wajah vs false positive.
- `YOLO_IMG_SIZE`: bandingkan 640 vs 1280 → catat kecepatan vs akurasi deteksi.
- Tulis rekomendasi singkat (satu tabel cukup) di bagian baru `docs/threshold_report.md`
  atau file `docs/A/yolo_tuning.md`.

### A4. Uji ketahanan wajah nyata (robustness)
Minimal 5 orang, kondisi berbeda: terang, redup, wajah miring, berkacamata, pakai masker
(setengah wajah). Catat: berhasil deteksi? embedding keluar? skor similarity berapa?
Tulis hasilnya di `docs/A/robustness_test.md`.

### A5. Integrasi end-to-end rutin
Setiap kali ada merge: `pytest` + `python backend/scripts/smoke_test.py --base-url http://127.0.0.1:8000`
(server harus jalan duluan). Catat hasil di progress log `docs/PLAN_TIMELINE.md`.

---

## PRIORITAS 2 — Januari–Maret 2027

### A6. Dokumentasi anti-spoofing (kejujuran teknis untuk laporan)
InsightFace `buffalo_l` TIDAK punya deteksi liveness. Tulis di file
`docs/A/anti_spoofing.md`: keterbatasan ini + mitigasi yang sudah ada (two-stage selfie
pada dua waktu berbeda, Wi-Fi AP check, suasana kelas terawasi). Ini jadi bahan bab
"limitations" di laporan akhir.

### A7. Pimpin uji coba kelas nyata (pilot, Desember 2026)
- Rencanakan bersama B (server) dan D (dokumentasi + izin guru): 5–10 siswa, satu jadwal nyata.
- Tentukan metrik sukses: berapa % check-in start→end tersambung, berapa % verified
  vs face_only, berapa detik per check-in.
- Setelah pilot: triage temuan, bagikan perbaikan ke pemilik modul.

### A8. Bab laporan akhir — "Metode & Evaluasi Akurasi"
Serahkan ke D paling lambat **1 Mar 2027**. Isi: metodologi evaluasi, tabel FAR/FRR/EER,
threshold terpilih, hasil robustness, hasil pilot, keterbatasan.

---

## Batasan kerja (wajib)
- Branch: `task-a`. Commit kecil-kecil, pesan jelas. Tes harus hijau sebelum commit.
- File yang boleh kamu ubah: `backend/services/face_detection.py`,
  `backend/services/face_recognition.py`, `backend/scripts/evaluate_threshold.py`,
  `docs/threshold_report.md`, `docs/A/*`, `AGENTS.md` (jika arsitektur berubah).
  File anggota lain → koordinasi dulu.
- Ubah konfigurasi lewat **env variable** saat running/deployment, bukan hardcode.
- Jangan commit: `attendance.db`, `*.pkl`, `yolov8m-face.pt`, foto wajah, log.
- Macet >30 menit → tanya di grup.

## Deliverable per milestone
| Milestone | Yang harus ada dari kamu |
|---|---|
| M1 (~1 Nov 2026) | `threshold_report.md` terisi nyata + threshold terpilih + review PR anggota |
| M2 (~18 Jan 2027) | Pipeline stabil untuk demo + pilot selesai & dianalisis + config final |
| M3 (~18 Mar 2027) | Bab akurasi laporan + config ML terkunci + `AGENTS.md` mutakhir |
