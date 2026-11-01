# TUGAS A — LEAD: Validasi ML, Threshold Tuning & Integrasi

> **Baca dulu:** `docs/PROJECT_CONTEXT.md` (konteks lengkap proyek) dan
> `docs/PLAN_TIMELINE.md` (tenggat ganti). File ini adalah daftar tugasmu.
> Estimasi total beban kerja: **25–30 jam** (bagian paling rumit di tim, sesuai kesepakatan).

Peran kamu ada dua: (1) **validasi akurasi sistem dengan data nyata** — bagian teknis
paling kritis proyek, dan (2) **lead**: review PR anggota lain, jaga tes tetap hijau,
pimpin integrasi dan uji coba kelas nyata.

Yang sudah TIDAK perlu kamu kerjakan (sudah selesai & lolos tes): two-stage logic,
schedule enforcement, hardening enrollment, NIM lookup, CSV export. Jangan dibangun ulang.

> **ATURAN BAHASA:** OUTPUT DAN INPUT DI SEMUA SISTEM PROYEK INI HARUS DALAM BAHASA
> INGGRIS, karena tugas besar ini berbahasa Inggris dan hasilnya juga dinilai dalam bahasa
> Inggris. Artinya: UI aplikasi, response/error API, log server, komentar kode, commit
> message, seluruh isi `docs/**`, header CSV, teks dashboard, slides, video, dan laporan —
> semuanya Inggris. Yang boleh tetap Indonesia: arahan tugas ini dan obrolan di grup.

> **M2:** paket kerjamu ada di bagian "PAKET KERJA M2" di bawah. Kamu yang membagi waktu
> per minggu; yang tetap hanya urutan tahap + tanggal gate (`docs/PLAN_TIMELINE.md` §2.1).

---

## PRIORITAS 0 — M1 (SELESAI 1 Nov 2026)

> ✅ Threshold report terisi angka nyata, threshold 0.5 diputuskan dengan bukti, PR anggota
> sudah direview, tes hijau. Bagian ini disimpan sebagai catatan; jangan dikerjakan ulang.


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

## PAKET KERJA M2 — "Kalibrasi akurasi & bukti" (2 Nov 2026 → 18 Jan 2027)

> Satu paket besar. Kamu yang membagi waktu per minggu; yang tetap adalah **urutan tahap**
> dan **tanggal gate** di `docs/PLAN_TIMELINE.md` §2.1. Setiap keputusan tidak sepele wajib
> ditulis di `docs/A/DECISIONS.md` — file itu bagian dari penilaian M2.

**Tujuan besar:** sistem punya angka akurasi yang bisa dipertanggungjawabkan di depan dosen,
dan demo memakai konfigurasi yang sudah diuji, bukan nilai default.

| # | Tahap | Periode | Gate | Yang dikerjakan + bukti |
|---|-------|---------|------|--------------------------|
| 1 | Tutup M1, jaga baseline | 2–8 Nov | — | Merge semua branch tertunda; `pytest` + `smoke_test` hijau; tidak ada PR menggantung |
| 2 | Kalibrasi deteksi | 2–15 Nov | **G3** | Bandingkan `YOLO_CONF_THRESHOLD` 0.25 / 0.30 / 0.35 dan `YOLO_IMG_SIZE` 640 vs 1280 → `docs/A/yolo_tuning.md` (tabel trade-off kecepatan vs recall) + nilai final dikunci |
| 3 | Bukti ketahanan | 9–22 Nov | — | Minimal 5 orang: terang, redup, wajah miring, berkacamata, masker → `docs/A/robustness_test.md` |
| 4 | Siapkan pilot | 16–29 Nov | **G7** | `docs/A/pilot_plan.md` (metrik sukses) + enroll 5–10 siswa di kelas asli |
| 5 | Pimpin pilot + analisis | 7–20 Des | **G9, G10** | Eksekusi lapangan + `docs/A/pilot_report.md`: % start→end tersambung, % `verified` vs `face_only`, detik per check-in, daftar kegagalan |
| 6 | Kunci scope + jaga integrasi | 21 Des–18 Jan | **G12–G16** | Satu halaman "apa yang didemokan / tidak"; draft `docs/A/anti_spoofing.md` (kerja tulis, aman di minggu libur); verifikasi config di mesin demo |

**Selesai jika (DoD):** keempat dokumen berisi angka nyata; konfigurasi final tertulis
sebagai env yang benar-benar dipakai di mesin demo; scope demo muat satu halaman; baseline
tes hijau sepanjang periode.

**Pertanyaan kritis wajib kamu jawab sendiri** (di `docs/A/DECISIONS.md`):

- Apakah threshold 0.5 masih benar untuk pencahayaan kelas asli, atau harus berbeda per
  kamera/HP?
- Berapa biaya (detik per check-in dan false reject) menaikkan `YOLO_IMG_SIZE` ke 1280 saat
  demo?
- Kalau akurasi jatuh saat pilot, penyebabnya model, kualitas enrollment, atau kamera HP?
  Buktikan dengan data.
- Apa yang **tidak** akan kita klaim di laporan karena belum pernah diukur?

**Peran kepemimpinan (berubah):** kamu **reviewer**, bukan tukang solusi. Anggota wajib
datang dengan usulan + bukti; kamu memutuskan. Kalau ditanya "harus bagaimana", balas
dengan pertanyaan yang memaksa mereka mengukur dulu. Kalau kamu sampai mengerjakan bagian
orang lain, catat itu di progress log — itu tanda paketnya gagal.

Rutin yang tetap berlaku: setiap merge → `pytest` + `smoke_test`, hasilnya masuk progress
log `docs/PLAN_TIMELINE.md`. Review tiap Minggu.

---

## M3 (19 Jan – 18 Mar 2027) — belum dimulai

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
- Macet >30 menit → tanya di grup **dengan usulan**, bukan dengan masalah mentah.
- Setiap keputusan tidak sepele wajib masuk `docs/A/DECISIONS.md` (isi entri: problem →
  minimal 2 opsi → bukti → keputusan → konsekuensi → kapan ditinjau ulang).

## Deliverable per milestone
| Milestone | Yang harus ada dari kamu |
|---|---|
| M1 (~1 Nov 2026) | ✅ `threshold_report.md` terisi nyata + threshold terpilih + review PR anggota |
| M2 (~18 Jan 2027) | G3 config ML terkunci · G7 enrollment kelas asli · G9 pilot dipimpin · G10 `pilot_report.md` · G12 scope demo terkunci |
| M3 (~18 Mar 2027) | Bab akurasi laporan + config ML terkunci + `AGENTS.md` mutakhir |
