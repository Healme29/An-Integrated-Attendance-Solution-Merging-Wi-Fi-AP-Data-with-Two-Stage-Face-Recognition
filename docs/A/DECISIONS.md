# DECISIONS — Member A (lead / ML)

> Setiap keputusan yang tidak sepele **wajib** ditulis di sini. File ini bagian dari
> penilaian M2: bukti bahwa kamu berpikir dulu sebelum mengerjakan, bukan menunggu
> arahan lead (kamu sendiri lead-nya).
>
> Aturan main:
> - Tulis entri **sebelum** pekerjaannya di-commit, perbarui setelah hasil pengukuran ada.
> - ISI ENTRI DALAM BAHASA INGGRIS (bagian dari dokumen proyek).
> - Minimal 2 opsi per keputusan. Tanpa opsi = bukan keputusan, itu asumsi.
> - Bukti harus berupa angka, log, atau artefak yang bisa dibuka orang lain. Kalau belum
>   diukur, tulis `not measured yet` — jangan menebak.

## Template entri (salin untuk setiap keputusan)

```markdown
### D-00X — <short title>
- **Date:** YYYY-MM-DD · **Stage:** <stage M2 / gate id>
- **Problem:** apa yang harus diputuskan, satu kalimat.
- **Options:** minimal 2, masing-masing dengan biaya dan risikonya.
- **Evidence:** angka / baris log / hasil tes / path artefak. Belum diukur → tulis apa adanya.
- **Decision:** pilihan + alasannya (satu paragraf, English).
- **Consequences:** apa yang jadi lebih sulit, apa yang gugur, apa yang harus ditinjau ulang.
- **Revisit by:** tanggal atau pemicu (mis. "after pilot", "if FAR > 0.02").
```

---

## Contoh yang sudah terpakai (jangan diulang, tapi silakan ditantang dengan data baru)

### D-001 — Keep FACE_SIMILARITY_THRESHOLD at 0.5
- **Date:** 2026-10-26 · **Stage:** M1 / A1
- **Problem:** Default threshold 0.5 had never been tested against real face data.
- **Options:** (1) lower to 0.40 — more genuine matches accepted, higher risk of false
  attendance; (2) raise to 0.60 — safer against impostors, higher risk of rejecting valid
  students; (3) keep 0.5.
- **Evidence:** `docs/threshold_report.md` — 15 samples, 30 genuine pairs, 75 impostor
  pairs, FAR = FRR = 0.00 across the 0.25–0.65 band.
- **Decision:** Keep 0.5. The distributions are fully separated, so the exact midpoint of
  the safe gap is the least risky choice; moving it would be tuning without evidence.
- **Consequences:** The sample is small (3 people) and was not captured in classroom
  lighting, so the decision is provisional.
- **Revisit by:** after the pilot (G10) — re-run `evaluate_threshold.py` on pilot
  enrollment photos; change only if FAR > 0 or a valid student is rejected.

---

## Entri M2 (tambahkan di bawah ini)

<!-- Mulai dari sini. Entri pertama yang diharapkan: konfigurasi YOLO final (gate G3). -->
