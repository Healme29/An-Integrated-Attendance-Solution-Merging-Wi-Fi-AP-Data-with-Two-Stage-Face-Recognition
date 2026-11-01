# DECISIONS — Member C (Flutter / real devices)

> Setiap keputusan UX atau teknis yang tidak sepele **wajib** ditulis di sini. File ini
> bagian dari penilaian M2: bukti bahwa kamu menguji di perangkat nyata lalu memutuskan,
> bukan menunggu arahan.
>
> Aturan main:
> - Tulis entri **sebelum** pekerjaannya di-commit, perbarui setelah hasil pengukuran ada.
> - ISI ENTRI DALAM BAHASA INGGRIS (bagian dari dokumen proyek).
> - Minimal 2 opsi per keputusan, masing-masing dengan biaya dan risikonya.
> - Bukti = angka, screenshot, log, atau hasil uji perangkat. Belum diukur → tulis
>   `not measured yet`.

## Template entri (salin untuk setiap keputusan)

```markdown
### D-00X — <short title>
- **Date:** YYYY-MM-DD · **Stage:** <stage M2 / gate id>
- **Problem:** apa yang harus diputuskan, satu kalimat.
- **Options:** minimal 2, masing-masing dengan biaya dan risikonya.
- **Evidence:** angka / screenshot / log / path artefak. Belum diukur → tulis apa adanya.
- **Decision:** pilihan + alasannya (satu paragraf, English).
- **Consequences:** apa yang jadi lebih sulit, apa yang gugur, apa yang harus ditinjau ulang.
- **Revisit by:** tanggal atau pemicu.
```

---

## Contoh yang sudah terpakai (jangan diulang, tapi silakan ditantang dengan data baru)

### D-001 — Fixed connectivity path: `adb reverse` + `127.0.0.1`, LAN IP as override
- **Date:** 2026-10-26 · **Stage:** M1 / C1
- **Problem:** The app must reach the backend from a real phone, but the campus WLAN
  blocks phone → PC HTTP traffic.
- **Options:** (1) `http://<PC-LAN-IP>:8000` — natural, but blocked by firewall/AP
  isolation on campus; (2) `adb reverse tcp:8000 tcp:8000` + `http://127.0.0.1:8000` —
  works over USB, requires a cable and one command; (3) public tunnel — adds a dependency
  on internet and a third party.
- **Evidence:** with the LAN IP, uvicorn access logs showed no incoming request at all;
  with `adb reverse`, `GET /health` returned 200 from the phone browser and the full flow
  passed on a Galaxy S24.
- **Decision:** Default the app to `http://127.0.0.1:8000` (works with `adb reverse`),
  keep the server-URL field in Settings for LAN use, and document the adb command.
- **Consequences:** the demo needs a USB cable or a working same-network path; Wi-Fi
  verification stays server-side and is unaffected.
- **Revisit by:** demo preparation (G13) — if the demo network allows phone → PC
  traffic, LAN IP becomes the primary path.

---

## Entri M2 (tambahkan di bawah ini)

<!-- Entri pertama yang diharapkan: pilihan jalur koneksi untuk hari demo (gate G2). -->
