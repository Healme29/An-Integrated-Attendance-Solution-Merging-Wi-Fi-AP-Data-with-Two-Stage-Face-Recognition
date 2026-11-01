# DECISIONS — Member B (backend / deployment)

> Setiap keputusan teknis yang tidak sepele **wajib** ditulis di sini. File ini bagian
> dari penilaian M2: bukti bahwa kamu mengukur dulu, baru memutuskan.
>
> Aturan main:
> - Tulis entri **sebelum** pekerjaannya di-commit, perbarui setelah hasil pengukuran ada.
> - ISI ENTRI DALAM BAHASA INGGRIS (bagian dari dokumen proyek).
> - Minimal 2 opsi per keputusan, masing-masing dengan biaya dan risikonya.
> - Bukti = angka, log, hasil tes, atau artefak yang bisa dibuka orang lain. Belum diukur →
>   tulis `not measured yet`.

## Template entri (salin untuk setiap keputusan)

```markdown
### D-00X — <short title>
- **Date:** YYYY-MM-DD · **Stage:** <stage M2 / gate id>
- **Problem:** apa yang harus diputuskan, satu kalimat.
- **Options:** minimal 2, masing-masing dengan biaya dan risikonya.
- **Evidence:** angka / baris log / hasil tes / path artefak. Belum diukur → tulis apa adanya.
- **Decision:** pilihan + alasannya (satu paragraf, English).
- **Consequences:** apa yang jadi lebih sulit, apa yang gugur, apa yang harus ditinjau ulang.
- **Revisit by:** tanggal atau pemicu.
```

---

## Contoh yang sudah terpakai (jangan diulang, tapi silakan ditantang dengan data baru)

### D-001 — Docker is not a substitute for native run on the Wi-Fi path
- **Date:** 2026-10-25 · **Stage:** M1 / B3
- **Problem:** Should the demo run the backend in Docker or natively on the machine?
- **Options:** (1) Docker everywhere — reproducible, but the container cannot see the
  host's Wi-Fi LAN; (2) native `uvicorn` everywhere — Wi-Fi scanning works, but setup
  depends on the machine; (3) Docker for the API demo and native for the Wi-Fi demo.
- **Evidence:** inside the container `/wifi/scan` returned `devices: []` with subnet
  defaulting to `192.168.1.0/24`; the same call natively detected the real subnet and the
  AP BSSID. Image is 3.4 GB on CPU wheels.
- **Decision:** Docker stays the documented deployment path for the API/dashboard, but any
  demo or pilot that must show Wi-Fi presence runs natively (or with host networking on
  Linux). This is stated explicitly in `docs/B/deployment_guide.md`.
- **Consequences:** the demo machine needs Python + `uvicorn` installed, not just Docker;
  the runbook must say which mode is active.
- **Revisit by:** demo preparation (G12/G13) — re-measure on the actual demo machine.

---

## Entri M2 (tambahkan di bawah ini)

<!-- Entri pertama yang diharapkan: mode jalan untuk mesin demo (gate G1). -->
