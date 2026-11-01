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

## Entri M2

### D-002 — Detection settings for the demo: keep conf 0.25, drop img size to 640
- **Date:** 2026-11-01 · **Stage:** M2 stage 2 / gate G3
- **Problem:** `YOLO_CONF_THRESHOLD=0.25` and `YOLO_IMG_SIZE=1280` were defaults nobody had
  measured; we needed a defensible setting for enrollment, check-in and the demo.
- **Options:** (1) keep 0.25/1280 — status quo, no measurement needed; (2) 0.25/640 — about
  4× faster, unknown recall cost on distance; (3) 0.30/640 — fewer false positives, risk of
  losing dim faces; (4) raise to 0.35/1280 — safest against false positives, slowest.
- **Evidence:** `docs/A/yolo_tuning.md` — 52 original photos × 6 combinations. Detection
  52/52 in every combination; conf 0.25/0.30/0.35 identical; 640 median 481 ms / p95
  618 ms vs 1280 median 1816 ms / p95 1985 ms (3.8×); detected face height 594 px vs
  582 px. On the 15 stored enrollment crops, 1280 produced nested duplicate boxes in 15/15
  images, 640 in 0/15.
- **Decision:** `YOLO_CONF_THRESHOLD=0.25` and `YOLO_IMG_SIZE=640`, applied as deployment
  environment values for the demo/pilot machine. The code default in `config.py` stays 1280
  until classroom-distance photos confirm 640 — changing a production default on 52
  close-up selfies would be over-fitting.
- **Consequences:** check-in spends ~1.3 s less in detection per photo; duplicate boxes
  stop inflating enrollment embeddings. Counter-risk: distant faces at the back of the room
  may be missed at 640 and were not measured here. A separate finding is now tracked: a
  photo with two people still enrolls both faces (not fixed by this decision).
- **Revisit by:** G7 (classroom enrollment photos) — decide whether enrollment needs a
  higher `imgsz` than check-in; re-check at G10 with pilot numbers.
