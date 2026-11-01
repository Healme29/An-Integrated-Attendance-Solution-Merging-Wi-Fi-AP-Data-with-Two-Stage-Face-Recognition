# TUGAS B — Backend, Validasi Wi-Fi Nyata & Deployment

> **Baca dulu:** `docs/PROJECT_CONTEXT.md` dan `docs/PLAN_TIMELINE.md`.
> Estimasi total beban kerja: **18–22 jam** (seimbang dengan C dan D; A tetap terberat).

Fokus kamu: membuktikan bahwa backend **benar-benar bekerja di luar mesin pengembang** —
di jaringan Wi-Fi nyata, di Docker, di mesin demo — dan menyiapkan lingkungan demo
untuk presentasi. Logika two-stage & schedule enforcement SUDAH selesai dan lolos tes;
jangan diubah.

> **ATURAN BAHASA:** OUTPUT DAN INPUT DI SEMUA SISTEM PROYEK INI HARUS DALAM BAHASA
> INGGRIS, karena tugas besar ini berbahasa Inggris dan hasilnya juga dinilai dalam bahasa
> Inggris. Artinya: UI, response/error API, log server, komentar kode, commit message,
> seluruh `docs/**` (termasuk laporanmu), header CSV, teks dashboard, slides, dan video —
> semuanya Inggris. Yang boleh tetap Indonesia: arahan tugas ini dan obrolan di grup.

> **M2:** paket kerjamu ada di bagian "PAKET KERJA M2" di bawah. Kamu yang membagi waktu
> per minggu; yang tetap hanya urutan tahap + tanggal gate (`docs/PLAN_TIMELINE.md` §2.1).

---

## PRIORITAS 0 — M1 (SELESAI 1 Nov 2026)

> ✅ `docs/B/network_validation.md` berisi hasil nyata, Docker terverifikasi,
> `seed_demo.py` ada, fitur data (CSV + pagination) sudah dicek. Jangan dikerjakan ulang.

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

## PAKET KERJA M2 — "Sistem siap kelas & siap demo" (2 Nov 2026 → 18 Jan 2027)

> Satu paket besar. Kamu yang membagi waktu per minggu; yang tetap adalah **urutan tahap**
> dan **tanggal gate** (`docs/PLAN_TIMELINE.md` §2.1). Setiap keputusan tidak sepele wajib
> ditulis di `docs/B/DECISIONS.md` — itu bagian dari penilaian M2.

**Tujuan besar:** backend terbukti jalan di luar laptop pengembang — di mesin demo, di
jaringan kelas, tanpa internet, dan bisa dipulihkan kalau rusak di hari demo.

| # | Tahap | Periode | Gate | Yang dikerjakan + bukti |
|---|-------|---------|------|--------------------------|
| 1 | Lingkungan demo nyata | 2–8 Nov | **G1** | Deploy di mesin yang benar-benar akan dipakai; `/health` ok, data persist setelah restart, `TIMEZONE` + threshold dari A terbaca, smoke test lulus |
| 2 | Peta batas jaringan + fallback offline | 9–22 Nov | **G5** | Timebox investigasi AP management plane (SSH/SNMP/controller) → tulis "layak / tidak layak" + alasan. Wajib juga: `seed_demo.py` + hotspot + prosedur "internet mati" satu halaman. **Spike ini tidak boleh menahan demo** |
| 3 | Uji panduan deploy dari nol | 23–29 Nov | — | Ikuti `docs/B/deployment_guide.md` persis seperti orang non-teknis; perbaiki setiap langkah yang membingungkan (catat: langkah mana yang gagal) |
| 4 | Operasi server pilot | 6–13 Des | **G8, G9** | DB bersih, `TIMEZONE`, `CORS`, threshold dari A, backup sebelum & sesudah, catat semua gangguan jaringan saat pilot |
| 5 | Analisis jaringan + mulai hardening | 14 Des–3 Jan | **G11** | Temuan pilot masuk `docs/B/network_validation.md`; perbaiki bug scanner yang ketemu; mulai checklist produksi (CORS spesifik, backup rutin, batas upload) |
| 6 | Latihan ketahanan + runbook demo | 4–18 Jan | **G12–G16** | Uji restore backup, uji fallback end-to-end, cetak runbook demo (port, `adb reverse`, urutan menyalakan, siapa menghubungi siapa) |

**Selesai jika (DoD):** backend jalan di mesin demo; `deployment_guide.md` berhasil diikuti
orang lain tanpa bantuanmu; fallback offline terbukti; runbook demo tercetak dan diuji di
dry run #1.

**Pertanyaan kritis wajib kamu jawab sendiri** (di `docs/B/DECISIONS.md`):

- Kalau `/wifi/scan` hanya melihat gateway (sudah terukur di kampus), apakah `face_only`
  kita sebut kegagalan sistem atau perilaku yang dimengerti? Siapa yang memutuskan, dan di
  dokumen mana keputusan itu hidup?
- Masih tepatkah Docker untuk mesin demo, mengingat container tidak bisa melihat Wi-Fi LAN
  host? Bandingkan dengan jalan native + bukti pengukuran.
- Berapa lama waktu pemulihan kalau DB rusak di hari demo? Ukur, jangan tebak.
- Fitur apa yang harus **dimatikan** saat demo supaya risiko turun?

ID lama (B3–B7) tetap berlaku dan menempel pada tahap di atas: B3 = tahap 1+3, B4 = tahap 2,
B5 = bagian dari tahap 4, B6 = tahap 4, B7 = tahap 5+6.

---

## M3 (19 Jan – 18 Mar 2027) — belum dimulai

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
- Macet >30 menit → tanya di grup **dengan usulan**, bukan dengan masalah mentah.
- Setiap keputusan tidak sepele wajib masuk `docs/B/DECISIONS.md` (problem → minimal 2 opsi
  → bukti → keputusan → konsekuensi → kapan ditinjau ulang).

## Deliverable per milestone
| Milestone | Yang harus ada dari kamu |
|---|---|
| M1 (~1 Nov 2026) | ✅ `docs/B/network_validation.md` berisi hasil nyata + ringkasan untuk laporan |
| M2 (~18 Jan 2027) | G1 mesin demo · G5 fallback offline · panduan deploy tervalidasi dari nol · runbook demo tercetak |
| M3 (~18 Mar 2027) | Hardening selesai + deployment guide final + bab backend laporan |
