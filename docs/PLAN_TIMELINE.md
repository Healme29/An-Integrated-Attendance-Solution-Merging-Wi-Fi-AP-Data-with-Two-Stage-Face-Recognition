# PROJECT PLAN & TIMELINE

> Living document. Everyone updates the **Progress Log** at the bottom when they finish
> a unit of work. Project-wide status lives here — nowhere else.
>
> Planning session: 2026-10-18. Minutes: `docs/meetings/2026-10-18_team_planning.md`.
> M2 replanning: 2026-11-01 — gates + four large work packages (see Phase 2 below).
> Full technical context: `docs/PROJECT_CONTEXT.md`.

---

## 1. Milestones

| Milestone | Deadline (approx.) | Success criteria |
|-----------|--------------------|-------------------|
| **M1 — Progress report** | **Nov 1, 2026** | Written progress report delivered, backed by: real-data threshold report (A), real-network Wi-Fi validation results (B), real-device test log (C), fixed dashboard test + evidence pack (D) |
| **M2 — Presentation & demo** | **Jan 18, 2027** | Live end-to-end demo on a real phone + real Wi-Fi; pilot classroom test completed (Dec 7–13, 2026); slides, demo script, and backup video ready; 2 dry runs done; demo scope locked Jan 8 |
| **M3 — Final submission** | **Mar 18, 2027** | Code freeze Mar 2; release build v1.0 (APK + backend deployed on school machine); final report assembled from all chapters; repository cleaned up |

## 2. Phase plan

### Phase 1 — M1: Real-data validation (Oct 19 → Nov 1, 2026)

| Week | A (lead, ML) | B (backend/Wi-Fi) | C (Flutter/devices) | D (docs/dashboard) |
|------|--------------|-------------------|---------------------|--------------------|
| Oct 19–25 | Enroll ≥3 people × ≥3 selfies, run `evaluate_threshold.py`, fill `docs/threshold_report.md` with real FAR/FRR/EER, pick threshold | Validate `/wifi/scan` + `/wifi/check/{mac}` on a real router; test subnet auto-detect, 60 s dedupe, BSSID pinning; document results | Full flow on a REAL Android phone: settings → login → enroll → start → end → history; log issues | Fix the failing dashboard test; review + commit the uncommitted dashboard redesign; run tests, save evidence + screenshots |
| Oct 26 – Nov 1 | Review members' results; integrate; verify 124/124 tests green | Consolidate network results into a summary doc for the report | Fix device-test bugs found; write device test summary | Collect each member's input **by Oct 29**; assemble and deliver progress report **Nov 1** |

### Phase 2 — M2: Pilot & demo (Nov 2, 2026 → Jan 18, 2027)

> This phase is **not** a task list. Each member receives **one large work package**
> (§2.2) with ordered stages, hard gates, a definition of done, and questions they must
> answer themselves. Members allocate their own time; only the gates are fixed.

#### 2.0 Language rule (binding for all members)

**OUTPUT AND INPUT IN ALL SYSTEMS OF THIS PROJECT MUST BE IN ENGLISH BECAUSE THIS ASSIGNMENT USES ENGLISH (THE RESULT).**

| Area | Language |
|------|----------|
| Work-package instructions for A, B, C (this section, `docs/A`, `docs/B`, `docs/C`) | Indonesian |
| Work-package instructions for D (`docs/D`) | English |
| App UI text, API responses and error `detail` strings, server logs, code comments, docstrings, commit messages | English |
| Deliverables in `docs/**`, CSV headers, dashboard text, slides, video, final report, README | English |
| Day-to-day group-chat conversation | free (Indonesian is fine) |

#### 2.1 Flow and gates — the required order

Each stage has a **gate**. A stage may not start before the previous gate is passed,
unless the gate owner records an exception in their `DECISIONS.md`.

| # | Gate | Date | Owner | Pass condition |
|---|------|------|-------|----------------|
| G1 | Demo environment alive on the real machine | Nov 8 | B | `/health` OK, data persists across restart, `TIMEZONE` and threshold env read correctly |
| G2 | Mobile release validated on a second phone | Nov 8 | C | Core flow (login → start → end → history) passes on the second device |
| G3 | ML configuration locked | Nov 15 | A | `docs/A/yolo_tuning.md` + final threshold written down, measured not assumed |
| G4 | Pilot date + student roster confirmed by the teacher | Nov 22 | D | Written in `docs/D/teacher_requirements.md` |
| G5 | Offline fallback proven | Nov 22 | B | Seed data + hotspot run with no internet |
| G6 | Auto check-in finished on a real device | Nov 22 | C | Banner → camera → start/end without manual intervention |
| G7 | Pilot students enrolled in the real classroom | Nov 29 | A | At least 5 students, embeddings captured in classroom lighting |
| G8 | Pilot rehearsal passed | Dec 6 | All | Server, phones and forms ready; one full simulation done |
| **G9** | **PILOT CLASSROOM TEST (Dec 7–13)** | **Dec 13** | A leads | 5–10 students, raw data stored |
| G10 | Pilot analysis + fix list | Dec 20 | A | Real numbers, every finding has an owner |
| G11 | All pilot fixes merged | Jan 3 | All | Tests green, G10 findings closed or dismissed with a written reason |
| G12 | **DEMO SCOPE LOCKED** | **Jan 8** | A | No new features after this date |
| G13 | Dry run #1 | Jan 9–10 | All | Full flow runs without help |
| G14 | Backup video + final slides | Jan 10 | D | A 30–60 s recording ready to play |
| G15 | Dry run #2 | Jan 14–15 | All | Timing and role split correct |
| **G16** | **M2 DEMO** | **Jan 18** | All | Live demo passes, or the fallback is used deliberately |

**Critical chain:** G4 → G7 → G9 → G10 → slides → G12 → G13 → G15 → G16. A one-week slip in
G4 (teacher availability) moves every later gate. **D owns G4, not A** — the pilot date is a
logistics problem, not an engineering one.

**Holiday rule:** Dec 21, 2026 – Jan 3, 2027 is the academic break. Writing-only work
(slides, docs, anti-spoofing write-up). No field tests, no mandatory meetings.

#### 2.2 Work packages

Each package is deliberately large: the owner decides how to slice it across the weeks, but
the **order of the stages and the gate dates are fixed**. If a gate cannot be passed on
time, the owner records why in `DECISIONS.md` and tells the group **before** the date.

##### Package A — "System accuracy calibration and evidence" (lead technical)

**Tujuan besar:** sistem punya angka akurasi yang bisa dipertanggungjawabkan di depan dosen,
dan demo memakai konfigurasi yang sudah diuji — bukan nilai default.

**Tahapan (urut, jangan diacak):**

1. **Tutup M1 dan jaga baseline** (Nov 2–8) — merge semua branch tertunda, `pytest` dan
   `smoke_test` hijau, tidak ada PR menggantung.
2. **Kalibrasi deteksi → G3** (Nov 2–15) — bandingkan `YOLO_CONF_THRESHOLD` 0.25 / 0.30 /
   0.35 dan `YOLO_IMG_SIZE` 640 vs 1280; tulis trade-off kecepatan vs recall di
   `docs/A/yolo_tuning.md`; kunci nilai final.
3. **Bukti ketahanan** (Nov 9–22) — minimal 5 orang, kondisi terang, redup, wajah miring,
   berkacamata, masker → `docs/A/robustness_test.md`.
4. **Siapkan pilot → G7** (Nov 16–29) — rencana pilot, metrik sukses, dan enroll 5–10 siswa
   di kelas asli → `docs/A/pilot_plan.md`.
5. **Pimpin pilot dan analisis → G9, G10** (Dec 7–20) — eksekusi lapangan, lalu
   `docs/A/pilot_report.md`: persen start→end tersambung, persen `verified` vs `face_only`,
   detik per check-in, daftar kegagalan.
6. **Kunci scope dan jaga integrasi → G12–G16** (Dec 21–Jan 18) — satu halaman "apa yang
   didemokan / apa yang tidak"; draft `docs/A/anti_spoofing.md` (kerja tulis, aman di minggu
   libur); verifikasi konfigurasi akhir di mesin demo.

**Selesai jika (DoD):** dokumen di atas berisi angka nyata; konfigurasi final tertulis
sebagai env yang benar-benar dipakai di mesin demo; scope demo muat satu halaman; baseline
tes hijau sepanjang periode.

**Pertanyaan kritis wajib kamu jawab sendiri** (`docs/A/DECISIONS.md`):

- Apakah threshold 0.5 masih benar untuk pencahayaan kelas asli, atau harus berbeda per
  kamera/HP?
- Berapa biaya (detik per check-in dan false reject) menaikkan `YOLO_IMG_SIZE` ke 1280 saat
  demo?
- Kalau akurasi jatuh saat pilot, apakah penyebabnya model, kualitas enrollment, atau
  kamera HP? Buktikan dengan data, bukan dugaan.
- Apa yang **tidak** akan kita klaim di laporan karena belum pernah diukur?

**Peran kepemimpinan (berubah):** kamu **reviewer**, bukan tukang solusi. Anggota wajib
datang dengan usulan + bukti; kamu memutuskan. Kalau ditanya "harus bagaimana", balas
dengan pertanyaan yang memaksa mereka mengukur dulu.

##### Package B — "System ready for the classroom and the demo" (backend / deployment)

**Tujuan besar:** backend terbukti jalan di luar laptop pengembang — di mesin demo, di
jaringan kelas, tanpa internet, dan bisa dipulihkan kalau rusak di hari demo.

**Tahapan (urut):**

1. **Lingkungan demo nyata → G1** (Nov 2–8) — deploy di mesin yang akan dipakai, verifikasi
   persistensi, env, dan smoke test.
2. **Peta batas jaringan dan fallback offline → G5** (Nov 9–22) — timebox investigasi AP
   management plane (SSH/SNMP/controller) untuk presence per ruangan; tulis "layak / tidak
   layak" beserta alasannya. **Tidak boleh menahan demo.** Sebelumnya siapkan
   `seed_demo.py` + hotspot + prosedur "internet mati" satu halaman.
3. **Uji panduan dari nol** (Nov 23–29) — ikuti `docs/B/deployment_guide.md` persis seperti
   orang non-teknis; perbaiki setiap langkah yang membingungkan.
4. **Operasi server pilot → G8, G9** (Dec 6–13) — DB bersih, `TIMEZONE`, `CORS`, threshold
   dari A, backup sebelum dan sesudah; catat semua gangguan jaringan.
5. **Analisis jaringan dan mulai hardening → G11** (Dec 14–Jan 3) — masukkan temuan pilot ke
   `docs/B/network_validation.md`; mulai checklist produksi (CORS spesifik, backup rutin,
   batas upload).
6. **Latihan ketahanan dan runbook → G12–G16** (Jan 4–18) — uji restore backup, uji fallback
   end-to-end, cetak runbook demo (port, `adb reverse`, urutan menyalakan, siapa menghubungi
   siapa).

**Selesai jika (DoD):** backend jalan di mesin demo; `deployment_guide.md` berhasil diikuti
orang lain tanpa bantuan; fallback offline terbukti; runbook demo tercetak dan diuji di
dry run #1.

**Pertanyaan kritis wajib kamu jawab sendiri** (`docs/B/DECISIONS.md`):

- Kalau `/wifi/scan` hanya melihat gateway (sudah terukur di kampus), apakah `face_only`
  kita sebut kegagalan sistem atau perilaku yang dimengerti? Siapa yang memutuskan dan di
  dokumen mana?
- Masih tepatkah Docker untuk mesin demo, mengingat container tidak bisa melihat Wi-Fi LAN
  host? Bandingkan dengan jalan native + bukti pengukuran.
- Berapa lama waktu pemulihan kalau DB rusak di hari demo? Ukur, jangan tebak.
- Fitur apa yang harus **dimatikan** saat demo supaya risiko turun?

##### Package C — "The app in students' hands" (Flutter)

**Tujuan besar:** aplikasi yang dipakai siswa asli di kelas asli tidak crash, tidak
membingungkan, dan bisa dipasang ulang kapan saja oleh siapa pun di tim.

**Tahapan (urut):**

1. **Rilis teruji dua HP → G2** (Nov 2–8) — APK v0.9 di HP kedua, alur inti lulus, catat
   perbedaan perilaku antar perangkat.
2. **Ambil alih auto check-in → G6** (Nov 9–22) — review kode A (`7803d27`), jadikan
   milikmu, selesaikan banner → kamera → start/end, uji di HP asli.
3. **Polish UX** (Nov 9–22) — loading, empty, dan error state di semua layar, tombol retry,
   tidak pernah crash karena jaringan. Dark mode hanya kalau masih ada waktu.
4. **Siapkan pengalaman siswa** (Nov 23–Dec 6) — alur enroll yang jelas (3–5 selfie +
   panduan wajah), instruksi satu halaman untuk siswa pilot, HP pilot ter-install dan URL
   server tersetel.
5. **Dukung pilot → G9** (Dec 7–13) — dampingi siswa, catat kebingungan UX secara real-time.
6. **Perbaiki temuan dan bangun RC → G11** (Dec 14–Jan 3) — satu temuan satu commit kecil,
   `flutter analyze` bersih, build release candidate.
7. **Siapkan demo → G13–G16** (Jan 4–18) — APK final, HP demo (baterai, brightness, mode
   pesawat mati, kamera diuji), rekam layar untuk video cadangan bersama D.

**Selesai jika (DoD):** APK terpasang dan lulus di dua HP; auto check-in jalan tanpa
intervensi; instruksi siswa ada; HP demo punya checklist yang bisa dijalankan orang lain
dalam dua menit.

**Pertanyaan kritis wajib kamu jawab sendiri** (`docs/C/DECISIONS.md`):

- Kalau koneksi HP→PC diblokir Wi-Fi kampus (sudah terbukti), jalur mana yang kita bakukan
  untuk demo: `adb reverse`, hotspot, atau server publik? Bandingkan risiko tiap opsi.
- Berapa lama siswa butuh dari membuka app sampai check-in selesai? Ukur pada 3 orang.
- Pada kondisi apa app sebaiknya **menolak** check-in daripada mencoba terus (misal kamera
  gelap)? Siapa yang dirugikan oleh tiap pilihan?
- Apa yang terjadi kalau siswa menutup app di antara dua tahap? Sudahkah diuji?

##### Package D — "Evidence, communication and presentation" (dashboard, reports, demo)

**Big goal:** the project must be defensible in front of a teacher or panel using real
evidence, and the demo must run on a script that cannot fail silently.

**Stages (in order):**

1. **Finish the dashboard and refresh evidence** (Nov 2–15) — close the remaining polish
   items (status colors, schedule/date filter, CSV button, print CSS, responsive); one small
   change, one commit, one browser check. Refresh `docs/D/evidence/`.
2. **Teacher requirements and pilot logistics → G4** (Nov 16–29) — write the teacher's
   requirements into `docs/D/teacher_requirements.md` and **lock the pilot date and student
   roster**. This is the project's critical path: treat it as your most important deadline.
3. **Pilot pack and slide skeleton** (Nov 30–Dec 6) — observation sheet, metrics form,
   recording plan, who stands where, slide outline.
4. **Document the pilot → G9** (Dec 7–13) — photos, video, notes, timings into
   `docs/D/pilot_evidence/`.
5. **Slides v1 and pilot results** (Dec 14–27) — 10–12 slides: problem → three-condition
   rule → architecture → live demo → real numbers → limitations → future work.
6. **Demo script and backup video → G14** (Dec 28–Jan 10) — minute-by-minute roles (A runs
   the backend, C runs the phone, B stands by with the fallback, D narrates and keeps time),
   plus a 30–60 s recording of the full flow.
7. **Dry runs and final materials → G13, G15, G16** (Jan 11–18) — run both dry runs, fix
   what breaks, final slides, printed handout, timekeeper on the day.

**Done when:** dashboard final; `teacher_requirements.md` and the pilot date locked early;
pilot documented with photos, video and numbers; slides + script + backup video finished;
two dry-run reports written; you can run the demo from paper without improvising.

**Critical-thinking questions you must answer yourself** (`docs/D/DECISIONS.md`):

- What exactly must the panel see in the first 60 seconds, and what can be cut without
  weakening the claim?
- Which evidence is a real measurement and which is only a screenshot? Label them
  differently.
- If the live demo fails on stage, what is the exact sentence you say and what do you show
  next?
- What would a skeptical examiner attack first (anti-spoofing, Wi-Fi reliability, small
  sample size), and where in the slides is the honest answer?

**Dependency note:** D's stage 2 is the only stage in the whole plan that can stop everyone
else. Escalate to A the same day if the teacher has not answered by **Nov 20**.

#### 2.3 Critical-thinking rules (all members — part of the grading)

1. **`docs/<X>/DECISIONS.md` is mandatory.** Each entry: problem → at least 2 options →
   evidence/measurement → decision → consequences → revisit trigger.
2. **Never hand over a problem without a proposal.** A question in the group chat must look
   like: "I tried A and B, here are the results, I pick B because this, do you agree?" —
   never "this error, what do I do?".
3. **Numbers before opinions.** Every performance claim (accuracy, speed, stability) must
   come with how it was measured. If it was not measured, write "not measured yet".
4. **A only reviews and decides.** If A ends up doing another member's work, the package
   failed — record that in the progress log.
5. **Retire old assumptions with evidence.** Example already found: "Npcap is required on
   Windows" is wrong for the ping + ARP path. Every document you touch gets re-verified
   against the actual code or behaviour.
6. **Write down what failed.** A negative finding (e.g. the AP management plane is not
   viable) is a result, not a failure, and it belongs in the report.

#### 2.4 Weekly ritual

Sunday review + one progress-log entry per member (in English) answering three things:
what was measured, what was decided, what is blocked. Entries go at the top of §5.

### Phase 3 — M3: Polish & submission (Jan 19 → Mar 18, 2027)

| Period | Work |
|--------|------|
| Jan 19 – Feb 15 | Fix all pilot/demo findings. B: production hardening checklist (CORS origins, `TIMEZONE=Asia/Jakarta`, upload caps, DB backup). C: final app polish, app icon/splash/name, versioning. A: re-verify accuracy numbers on final hardware, anti-spoofing limitation write-up. D: start assembling the final report. |
| Feb 16 – Mar 1 | Each member writes their final-report chapter (see TASK.md files) and hands it to D **by Mar 1**. D compiles, A reviews the whole report. |
| Mar 2–15 | **Code freeze Mar 2.** Regression: full test suite green, smoke test, one more end-to-end pass on real device. Release build v1.0. Final repo cleanup (no stray logs/DBs). |
| Mar 16–18 | Buffer. Final submission. |

## 3. Deliverables per member per milestone

| Member | M1 (Nov 1, 2026) | M2 (Jan 18, 2027) | M3 (Mar 18, 2027) |
|--------|------------------|-------------------|-------------------|
| A | `docs/threshold_report.md` filled with real numbers + chosen threshold | G3 ML config locked; G7 enrollment; G9 pilot led; G10 `pilot_report.md`; G12 scope locked | Final accuracy chapter; frozen ML config; AGENTS.md current |
| B | Real-network Wi-Fi validation results | G1 demo machine; G5 offline fallback; guide validated from scratch; runbook printed | Deployment guide; hardening done; backend chapter |
| C | Real-device test log + quick fixes | G2 second phone; G6 auto check-in owned; pilot support; demo phones + final APK | Release APK v1.0; mobile app chapter |
| D | Failing test fixed; dashboard redesign committed; evidence pack; progress report | G4 teacher date + roster; G14 slides + script + backup video; dry-run reports | Final report assembled; testing & conclusion chapter |

M2 is executed as four **work packages** with fixed gates (§2.2). Each member plans their
own weeks; nobody waits for A to hand out steps. Every member maintains
`docs/<X>/DECISIONS.md` — that file is graded.

## 4. Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| Wi-Fi scan doesn't see student devices on school router | `face_only` status already covers it; document as known behavior; demo on a network we control |
| Camera/ML accuracy poor in classroom lighting | Enroll in the actual classroom; tune threshold on the deployment camera (A) |
| Demo-day network failure | B prepares an offline fallback: pre-seeded demo data + phone hotspot |
| D blocked on dashboard code | One tiny change at a time, with AI guidance (see `docs/D/PROMPT.md`); escalate to A/B if stuck >30 min |
| Deadline drift | Progress Log review every Sunday; A pings members who go quiet |
| Teacher unavailable in Dec / exam season delays G4 | Lock the date by **Nov 22**; keep Dec 14–20 as a pilot backup window; slides (W8–W9) do not depend on pilot data so they can proceed in parallel |
| Campus client isolation keeps `/wifi/scan` to the gateway | Demo on a network we control; `face_only` documented as expected behaviour; the AP-management-plane spike is timeboxed and can be declared "not viable" without blocking the demo |
| Academic break (Dec 21 – Jan 3) kills momentum | Writing-only work scheduled there (slides, docs, anti-spoofing); no field tests, no mandatory meetings |
| January scope creep ("one more feature") | Hard scope lock **Jan 8** (G12); Jan 16–17 is polish-only buffer |
| Live demo fails on stage | B's seeded offline fallback + D's 30–60 s backup video, both verified in dry run #1 (G13), not on the day |

## 5. Progress Log (append newest entry at the top)

### 2026-11-13 — B: G1 measured on the Windows demo laptop; Windows locale bug fixed; hardening gaps quantified

- **The demo machine changed, so G1 was re-measured instead of inherited.** Windows 11
  `10.0.22621` AMD64, Python **3.12.10** in a fresh `.venv` (3.13 cannot install the pinned
  wheels), native `uvicorn`, no Docker. Fresh `pip install -r backend/requirements.txt`
  **577 s**, exit 0. Cold start → `/health` **17.3 s** (restart 25.3 s, dominated by the
  `torch` import), `/health` / `/` / `/dashboard` **5.4 / 1.7 / 6.2 ms**, `TIMEZONE` delta
  **8.0 h**, data persisted across restart, seed **0.7 s** (5 students, 5 rows, CSV 6 lines),
  backup **1.2 ms** / restore **13.9 s**, fresh-DB start **14.7 s**. G1's pass condition is
  met on the machine that will run the demo; a different laptop needs a re-run (procedure:
  `guide_review.md` §5).
- **Scanner works on Windows without Npcap**, BSSID via `netsh`: live `/wifi/scan`
  **4,281 ms** fresh / **29 ms** cached, subnet `10.163.158.0/24` inside the real `/17`,
  `ap_logs` 0 → 1 → 1 (dedupe). Only the gateway was visible — campus client isolation (F2),
  same as Linux; the hotspot rung is still **not measured yet** (needs a second phone).
- **Real bug caught by the new platform:** the Windows subnet parser matched the English
  label `Subnet Mask`, which a localized `ipconfig` translates, silently degrading to a /24
  guess. Fixed in `backend/services/wifi_scanner.py` (`parse_ipconfig_prefix`,
  `_prefix_from_netmask`, non-contiguous masks rejected) with **4 new tests** (Chinese,
  French, `(Preferred)`, invalid mask). Suite: **209 passed** (38.7 s). Decision D-011.
- **Model path measured end to end:** `yolov8m-face.pt` 52,028,566 bytes (sha256
  `219f490a…`), `buffalo_l` 341,268,726 bytes unpacked in 5 `.onnx` files under
  `%USERPROFILE%\.insightface` — **not** `DATA_DIR`, because `insightface 2.1` hard-codes
  `~/.insightface`. Cold `/faces/recognize` **13.4 s**, warm **1.5–1.6 s**, server warm-up
  **8.3 s**, both models resident ≈ **1.0 GB RSS**. Loading the `.pt` needs `dill==0.3.8`,
  which is **missing from the A-owned `requirements.txt`** → a fresh install returns `500` on
  the first face call until A adds it (D-012, hardening item 7). Smoke test 12/15 → **15/15**
  after the manual install.
- **Hardening gaps are now numbers, not opinions** (`hardening_checklist.md` §2.1/§5/§7a):
  24 parallel writes all 200 (wall 823 ms), 24 parallel reads all 200 (68 ms), zero
  `database is locked`; upload cap is enforced on enroll (**413**) but **not** on
  `/faces/recognize` (**200** with an 11 MB file); a missing model returns `500` instead of a
  clean `503`; a corrupt DB logs `DatabaseError` and **keeps the process alive without
  binding the port**, so the runbook now says kill it before restoring. Items 7–10 are A's,
  listed with owners.
- **Decisions:** D-011 (locale-independent netmask), D-012 (Python 3.12 + missing `dill` +
  model location), D-013 (open API/no TLS only on a controlled hotspot — demo posture),
  D-014 (lazy model load plus a deliberate warm-up call, not eager startup). Every entry has
  an **Evidence files:** line.
- **Docs:** `demo_environment.md` §7, `network_validation.md` §8 (+ cross-platform table),
  `offline_fallback.md` §0/§5 (model paths and an offline pre-flight), `demo_runbook.md`
  §2 (step 0 `dill`, measured start/warm-up/restore), `deployment_guide.md` §7/§9/§13,
  `guide_review.md` §1/§2/§5, `review_response.md` findings 3/4 and §9. Raw output and
  re-runnable scripts: `docs/B/evidence/2026-11-13-windows/`.
- **Still honestly open:** hotspot rung with 1–2 phones, the outsider guide run, real-face
  accepted check-in latency (no usable photo), Docker on the demo laptop (optional, D-002).

### 2026-11-09 — Team: timeline accelerated (presentation ~Nov 23, submission & demo end of November) + package redistribution recorded
- **Replanning (drives this entry):** the team will be assessed at a presentation in about
  two weeks (≈ **Nov 23**) and a collection/demonstration at the end of November. The
  accelerated scope is recorded by A in `docs/A/DECISIONS.md` (D-005): the demo set is the
  feature-complete core (NIM login, enrollment, two-stage check-in, dashboard, CSV export,
  400/403/409 protection demos); the classroom pilot chain (**G7 → G9 → G10**) is re-planned
  for **December after the presentation**; the robustness study is cut to a mini version
  (3 people × bright/dim/angled) for presentation evidence, full 5×5 study resumes later.
  Config stays frozen at D-002 values (`conf 0.25`, `imgsz 640`, threshold 0.5).
- **Ownership transfer D → C (recorded as C-001 / D-002):** `backend/static/dashboard.html`
  and the slides / backup-video artefacts are now owned by **C**; only C edits the dashboard.
  D keeps written/evidence tasks; **A commits on D's behalf** when needed (D has no git
  access). Every dashboard commit must keep `pytest` green (title assertion).
- **G6 exception (C-002):** C has no Flutter dev environment this month, so auto check-in
  work is paused until after the presentation; the demo uses the device-tested APK v0.9.0
  with manual start/end check-in. Original G6 criteria remain open, not dismissed.
- **G4 reassigned (C-003):** teacher confirmation of pilot date/roster (due **Nov 22**,
  unchanged) is now owned by **C**, with escalation to A by **Nov 20** if the teacher has
  not replied. This is the critical chain — no silent slip.
- **Roles otherwise unchanged**, per the original work packages: A = accuracy/evidence
  (robustness, re-measurement, DECISIONS, review) and lead; **B = server/network** (demo
  machine G1, hotspot/offline fallback **G5 due Nov 22**, deployment guide, and the
  timeboxed AP management-plane spike for room-level presence in stage 2 Nov 9–22 — the
  spike must not block the demo); C = dashboard + presentation artefacts + G4.
- **Weekly ritual unchanged:** Sunday review entries in this log; `DECISIONS.md` entries
  before the work is committed.

### 2026-11-03 — B: review findings 1/6 fixed (BSSID probe chain, macOS ping), 2/3/4/5 scoped
- **Review of `task-b` (8.5/10, 2026-11-02) answered finding by finding in
  `docs/B/review_response.md`:** 3 closed with re-runnable evidence, 4 left open with the
  exact person who unblocks them. Nothing is claimed done without a test or a measurement.
- **Finding 1 (High) closed — `iwconfig` was the only BSSID probe.** Reproduced the risk on
  this laptop: `iw` is **not installed**, `nmcli`/`iwconfig` are. `get_current_bssid()` now
  runs `iw dev <iface> link` → `nmcli -t -f ACTIVE,BSSID device wifi` → `iwconfig`, returns
  the same BSSID (`50:98:b8:c9:2b:e2`, now via `nmcli`), stays silent when merely not
  associated, and logs **one** actionable `WARNING` per process when no probe exists
  (`PATH=/nonexistent` reproduced). The live run also exposed that `nmcli -t` escapes colons
  (`yes:50\:98\:B8\:...`), so the first fallback parser silently failed — unescape + pinned
  test. 15 new tests; suite **187 passed**.
- **Finding 6 (Low) closed:** Darwin gets `ping -c 1` (no `-W`); each call is already bounded
  by the subprocess timeout. macOS has no BSSID probe and now says so (D-010).
- **Finding 2 (High) prepared, not executed:** verified `origin/main` is an ancestor of
  `task-b` and `git merge-tree` is clean → ff-merge, no conflicts; merge command handed to
  **A** per the review's reviewer rule.
- **Findings 3/4/5 kept open on purpose:** the timed `pip install` was **not** run here — the
  root filesystem has 6.2 GB free and torch + CUDA wheels would fill it (`demo_environment.md`
  §6.1); the demo laptop run, the two-phone hotspot session and the outsider guide run need
  hardware and people, so they are scheduled with owners, not faked.
- **Docs:** `network_validation.md` §7 (before/after, the escaped-`nmcli` bug, F6),
  `DECISIONS.md` D-009/D-010 with **Evidence files:** cross-links, `offline_fallback.md` §4b
  (what to do when `bssid` is null) and checklist row 7, `demo_environment.md` §6/§6.1/§6.2.

### 2026-11-02 — B: G1 environment verified, scanner bugs fixed (measured), offline fallback + runbook drafted
- **G1 verification (native mode, isolated DB, `TIMEZONE=Asia/Shanghai`,
  `FACE_SIMILARITY_THRESHOLD=0.5`, `YOLO_IMG_SIZE=640`, `CORS_ORIGINS` scoped):** cold start →
  `/health` ok in **5.9 s**; `TIMEZONE` proven by an 8 h gap between schedule
  `created_at` `17:46:30` (CST) and the SQLite UTC student timestamp; data persisted across
  a full stop/start; smoke test **14/14** (15th check is Windows-only); seeded demo data
  served by `/attendance/today` + CSV. Evidence: `docs/B/demo_environment.md`.
- **Two scanner bugs found and fixed (`backend/services/wifi_scanner.py`, allowed file):**
  (1) subnet detection ignored the real netmask — on the campus `/17` it reported
  `10.163.235.0/24` while the host is `10.163.216.151/17`; it now reads the true netmask,
  reports/sweeps **exactly the /24 that is pinged** (`10.163.216.0/24`) and logs a warning;
  (2) Linux without `CAP_NET_RAW` raised `PermissionError`, and the ping sweep used Windows
  flags on Linux (silent no-op) — now platform-correct ping + `ip neigh` fallback with a
  warning. 19 new tests (`test_wifi_subnet.py`); suite **171 passed, 1 skipped** (two
  previously Windows-only tests are now portable).
- **Recovery measured, not guessed:** corrupted DB → startup fails with
  `sqlite3.DatabaseError`; restore backup + start → healthy in **6.2 s** (D-006).
- **Deliverables:** `demo_environment.md` (G1 table + open items), `offline_fallback.md`
  (one-page fallback ladder + hotspot/`adb reverse` order + the honest sentence for
  `face_only`), `demo_runbook.md` (draft, printed copy, dry-run log table),
  `ap_management_plane.md` (**verdict: not viable** — no AP access/authorisation; demo on a
  network we control), `seed_demo.py` hardened (1–99 students, id reset, scoped cleanup of
  stale embeddings, honest MAC note), `deployment_guide.md` (§5b native run, §8 measured
  restore, §11 seed data, §12 2026-11-02 verification), `network_validation.md` §6 (F1
  fixed, Linux findings), decisions D-002…D-008.
- **Deployment guide followed from scratch in a clean clone (`guide_review.md`):** one real
  defect found — `backend/data/models/` does not exist after `git clone`, so the documented
  weights download fails as written; also fixed PowerShell-incompatible `curl`/`-d` examples,
  the vague model warm-up step, missing firewall/IP commands, and the missing stop/start
  instructions. `pip install` (multi-GB) and Docker were **not** re-executed here and are
  still open; "followed by another person without help" is not earned yet.
- **Still open for G1:** repeat the table on the physical Windows demo laptop, measure a scan
  with 1–2 real phones on a flat hotspot (not measured yet), warm up `buffalo_l` there.

### 2026-11-01 — A: Package A evidence base — 640 default, clean profiles, robustness protocol, pilot plan
- **Config default:** `YOLO_IMG_SIZE` in `backend/config.py` is now **640** (the owner approved
  the flip after G3, D-002 update note). Env override stays for the G7 classroom
  re-measurement. `docs/PROJECT_CONTEXT.md`, `docs/A/yolo_tuning.md` (recommendation +
  follow-up #3) and `docs/A/DECISIONS.md` follow.
- **Clean re-enrollment (D-004):** new `backend/scripts/reenroll_clean.py` — scan with the
  same detect → dedupe → tiny-filter → distinct-people path as the API, reset rows/pickle/
  crops, enroll through the real `POST /faces/enroll`, then verify. Backed up the DB,
  embeddings and crops first. Rebuilt students 8/9/11: **5 embeddings each, every one from a
  single-person photo**. `orang_1` 17/17 usable, `orang_3` 14/14, `orang_2` 17/21 — the 4
  rejected photos had a second face at ratio **0.147–0.243** (same range as D-003).
- **Contamination confirmed:** after the rebuild `evaluate_threshold.py` still reports 15
  samples / 30 genuine / 75 impostor pairs, but FAR at threshold 0.15 dropped
  **0.1733 → 0.0400** and at 0.20 **0.0400 → 0.0000**. The old profiles really contained
  impostor-side data. Threshold decision unchanged at **0.5**.
- **Robustness:** protocol `docs/A/robustness_test.md` — 5 conditions (bright, dim, angled,
  glasses, mask) × 5 people × 3 frames, consent, isolated `DATABASE_PATH`/`DATA_DIR`,
  pre-registered acceptance thresholds, metrics and decision rules. New
  `backend/scripts/robustness_eval.py` mirrors the check-in path (multi-face rejection
  included). Sanity run on the 52 existing selfies: 46 usable, 46 accepted, **0 false
  accepts**, 4 multi-face (the known two-person photos), 2 no-embedding, p50 1069 ms. The
  result tables stay `not measured yet` — P4/P5 and the five conditions are the blocker.
- **Pilot:** `docs/A/pilot_plan.md` draft — dates/gates G4→G10, G7/G8 checklists, T−90..T+90
  runbook, success metrics (linkage ≥ 90%, verified ≥ 80%, retry ≤ 15%, p50 ≤ 5 s), data
  collection, failure matrix, roles, ethics. Roster/room/AP BSSID are placeholders until D
  confirms G4 (Nov 22); enrollment in the real room is G7 (Nov 29).
- **Repo hygiene:** `.gitignore` now excludes `robustness_captures/` and `docs/A/pilot/`
  (face photos and signed forms stay out of git).
- **Verification:** `python -m pytest backend/tests -q` → **153 passed**;
  `smoke_test.py` against the live server → **15/15**; no production behaviour changed
  besides the 640 detection default.

### 2026-11-01 — A: multi-face identity hole closed (D-003)
- **Hole:** `/attendance/check` had no `student_id`, so the recorded student was whoever
  the detector saw. A photo of A+B could record B (and grant B attendance) while A got
  nothing and no error. Enrollment stored every face in frame, so a friend could be
  enrolled into someone else's profile.
- **Check-in fix:** `student_id` is now a required query parameter; the matched face must
  equal it, otherwise **403 "Identity mismatch"** and no row. Unknown student → 404.
- **Multi-face fix:** detector boxes are deduplicated first (containment ≥ 0.6; 15/15
  cropped inputs produced nested duplicates, 1/52 originals). A second face with ≥ 10% of
  the largest face's area → **400 "Multiple faces detected"**. Measured separation: real
  second person 0.147–0.243, background faces 0.007–0.028.
- **Enrollment fix:** stores exactly one embedding (the largest distinct face) and rejects
  photos with two people.
- **Audit:** new column `attendance.faces_detected` (raw box count) + migration, returned
  by the API and included in the CSV export.
- **Clients updated:** `mobile/lib/services/api_service.dart`, `camera_screen.dart`,
  `home_screen.dart`; `backend/scripts/smoke_test.py`, `simulate_phone.py`;
  `docs/A/demo/auto_prompt_simulator.html`.
- **Tests:** new `backend/tests/test_identity_binding.py` (13 tests) → full suite
  **153 passed**.
- **Follow-ups:** re-enroll all demo students at G7 (pre-fix profiles may contain a
  friend's embeddings); re-check the 0.10 ratio with classroom photos; count 400/403 in
  pilot logs at G10. **Known limit:** no session token yet, so `student_id` is claimed, not
  proven — a colluding pair could still swap identities (M3: authenticated session).

### 2026-11-01 — A: G3 closed — YOLOv8-face measured; conf 0.25 + img size 640 chosen
- New script `backend/scripts/yolo_tuning.py` calls the YOLO model directly with explicit
  `conf`/`imgsz` (production code and its config import untouched). Grid: conf
  0.25/0.30/0.35 × imgsz 640/1280 over the **52 original photos**
  (`gambar_percobaan/orang_1..3`).
- **Detection: 52/52 in all six combinations.** The confidence threshold changes nothing in
  the 0.25–0.35 band on close-up well-lit selfies (mean confidence 0.893).
- **`imgsz=1280` costs 3.8× for zero recall gain:** median 1816 ms vs 481 ms, p95
  1985 ms vs 618 ms; detected face height 582 px vs 594 px (−2%).
- **Side finding (duplicates):** on the 15 stored enrollment crops, 1280 produced nested
  duplicate boxes in **15/15** images, 640 in **0/15**. `POST /faces/enroll` stores one
  embedding per detected box, so one photo could burn 2–3 of the 5 embedding slots.
- **Second finding (identity contamination):** 7 of the 52 photos genuinely contain two
  people, and enrollment accepts every face in the frame — a friend in the photo gets
  enrolled into that student's profile. Tracked as follow-up #2 in `docs/A/yolo_tuning.md`,
  not fixed in this change.
- **Decision D-002 recorded** (`docs/A/DECISIONS.md`): keep `YOLO_CONF_THRESHOLD=0.25`, set
  `YOLO_IMG_SIZE=640` as a deployment env value. The code default in `config.py` stays 1280
  until classroom-distance photos at G7 confirm 640.
- Deliverables: `docs/A/yolo_tuning.md`, `backend/scripts/yolo_tuning.py`, D-002.
- **Handover:** B sets `YOLO_IMG_SIZE=640` on the demo/pilot machine and records it in the
  runbook (G1/G8).

### 2026-11-01 — A: M2 stage 1 closed — baseline green, no dangling branches
- `python -m pytest backend/tests -q` → **140 passed** in 19.1 s (warnings only:
  pytest-asyncio loop-scope notice, pydantic v1-style config).
- Branch sweep: no unmerged branches on origin or locally; `origin/a` and `origin/task-c`
  fully merged (`git log main..origin/a` empty). Legacy `tugas-a..d` (2026-09-17) untouched
  — delete at M3 cleanup.
- Working tree clean, `main` == `origin/main`.
- Stage-2 environment verified: numpy 1.26.4, ultralytics 8.2.100, onnxruntime 1.18.1,
  torch 2.14.0+cpu, cv2 4.12.0.
- Stage-2 inputs ready: 52 photos (`gambar_percobaan/orang_1..3` = 17/21/14), 3 students
  with stored embeddings (8, 9, 11), `yolov8m-face.pt` present.
- Next: `backend/scripts/yolo_tuning.py` → conf 0.25/0.30/0.35 × img 640/1280 →
  `docs/A/yolo_tuning.md` + D-002, closing **G3**.

### 2026-11-01 — M2 plan published: 16 gates + four large work packages + critical-thinking rules
- **M1 closed out.** Progress report delivered today; baseline suite green (140/140 after
  the anti-cheat tests), threshold decision recorded at 0.5, Docker deployment verified,
  real-device flow passed, release APK v0.9.0 built and install-verified.
- **M2 replanned from "monthly themes" to a gate-based flow** (§2): Nov 2, 2026 →
  Jan 18, 2027. Pilot locked for **Dec 7–13, 2026** with **Dec 14–20** as the backup
  window; demo scope locked **Jan 8**; dry runs **Jan 9–10** and **Jan 14–15**.
- **Four large work packages** replace the old micro-task list (§2.2). Owners allocate
  their own time; only the gates are fixed. Critical chain: teacher date (G4) → classroom
  enrollment (G7) → pilot (G9) → analysis (G10) → slides → scope lock (G12) → dry runs.
- **Critical thinking is now graded.** Every member keeps `docs/<X>/DECISIONS.md`
  (created today, each with a worked example from M1). A's role is explicitly reviewer,
  not solver — "asked how" must be answered with "measure first".
- **Language rule made explicit** (§2.0 and `AGENTS.md`): work-package instructions for
  A/B/C are Indonesian, for D English; **all system output and input — UI, API, logs,
  comments, docs, CSV, slides, report — is English.**
- Next: each member reads their own package in `docs/<X>/TASK.md` and reports their
  own week split in the group chat by **Nov 3**; G1/G2 are due **Nov 8**.

### 2026-10-26 — C: REAL-DEVICE TEST PASSED (C1 core) + edge-case evidence + v0.9 prep; A: 3-student threshold re-run
- **C1 PASSED on the real phone** (Samsung Galaxy S24, Android 16): install,
  login (NIM), Settings + Test Connection, camera + selfie, **START →
  `partial`**, END check, History — user-confirmed; details + environment
  notes in `docs/C/device_test_log.md`.
  - Connectivity path documented: campus WLAN blocks phone→PC HTTP
    (firewall/AP isolation) → **`adb reverse tcp:8000 tcp:8000` + URL
    `http://127.0.0.1:8000`**; Wi-Fi verification stays server-side (ping
    sweep + ARP) and is unaffected. A laptop-clock drift of 8 h was also
    found and fixed during testing (cause of all schedule 403s).
- **Edge-case evidence (server-side, schedule id 18 `EDGE demo`):** fresh
  held-out photo → 200 `partial` (0.893); duplicate same-stage second photo →
  **409** ("Already checked in (start)"); same-photo replay → **409**;
  Willian (no valid MAC) → `prompt:false,
  reason:device_not_seen_on_network`. All logged in C's device log.
- **C3 fix:** camera init failure previously showed an infinite spinner (+
  latent `LateInitializationError` crash on dispose) — now error state with
  instructions + **Retry** (`53ba44d`).
- **C4/C5 prep:** friendly empty states for schedules & history (`de4a1bf`);
  release prep v0.9.0+1 + new launcher icon in 5 densities (`c0ee76b`).
  Release-side C5 next: `flutter build apk --release`, install on a SECOND
  phone (Nov item).
- **Handover review recorded:** `docs/C/review_7803d27.md` — prompt draft
  accepted (spec-compliant). C2 summary finalized:
  `docs/C/progress_summary_for_D.md` (the D-input that was due Oct 29 — done
  early).
- **A's M1 blocker cleared:** student #3 enrolled (5 embeddings from
  `gambar_percobaan/orang_3`) → `evaluate_threshold.py` re-run with **3
  students / 13 samples / 23 genuine + 55 impostor pairs**: FAR = FRR = 0.00
  in the 0.25–0.65 band → **threshold kept 0.5** (decision note in
  `docs/threshold_report.md`). Later same day: student #3 renamed
  **Latul (`F25040131`)** and Willian topped up to the full **5/5
  embeddings** → re-run now **15 samples / 30 genuine / 75 impostor
  pairs**, FAR = FRR = 0.00 at 0.25–0.65 — decision unchanged (0.5).
- **D3 evidence pack collected** (`docs/D/evidence/`): pytest 139 passed
  +1 skipped, smoke test **15/15**, `flutter analyze` clean, `flutter test`
  pass, **release APK v0.9.0 (`app-release.apk`, 51.7 MB) built and
  install-verified on the S24**; APK also pushed to
  `Download/StudentAttendance-v0.9.0.apk` on the user's phone for sharing
  with teammate Willian (no APK in git).

### 2026-10-25 — A (covering B): Docker deployment verified + seed script + compose fixes
- **B3 done:** image builds and runs; `GET /health` OK; `TIMEZONE=Asia/Shanghai` applied;
  smoke test **15/15** against the container (and 15/15 against the native server).
- **Compose/Dockerfile fixes (real bugs found during deployment):**
  - the volume `backend-data:/app/data` used to **shadow the baked-in YOLO weights**;
    state now lives in `/app/data/dbdata` (verified: `yolov8m-face.pt` visible at runtime);
  - `TIMEZONE` and `CORS_ORIGINS` were not passed into the container at all;
  - host port is now overridable via `BACKEND_PORT`;
  - torch/torchvision installed from the **CPU wheel index** — the default CUDA wheels
    added ~3 GB for nothing (image now 3.4 GB total).
- **China deployment note documented:** Docker Hub is unreachable from this network;
  `docs/B/deployment_guide.md` explains registry mirrors (`docker.m.daocloud.io`,
  `dockerproxy.com`) + `docker desktop restart`.
- **Confirmed limitation (measured):** `/wifi/scan` inside the container returns
  `devices: []` (subnet defaults to `192.168.1.0/24`, BSSID null) — containers cannot see
  the host Wi-Fi LAN. Wi-Fi presence requires native run or Linux host networking; the
  guide now states this explicitly.
- **B4 (new):** `backend/scripts/seed_demo.py` — demo students, a schedule active now and
  sample attendance rows; flags `--reset`, `--students N`, `--db PATH`; tested against a
  temporary database (START before END, correct server timezone).
- **Smoke test bug fixed:** `GET /dashboard` check looked for "Teacher Dashboard" (a string
  that never existed); now checks the real page markers.

### 2026-10-25 — A (covering B): real-network Wi-Fi validation documented + data features verified
- **B1 deliverable created:** `docs/B/network_validation.md` with measured results on the
  real campus network — fresh scan **2.4 s**, cached **0 s**, 60 s dedupe confirmed
  (`ap_logs` +1 row across two back-to-back scans), known/unknown MAC checks correct,
  BSSID `54:2b:de:fd:90:21` stable, two real two-stage check-ins (`verified`, 0.71/0.72).
- **Real finding (bug class):** `detect_local_subnet()` hard-codes `/24` while the laptop
  interface is **/17** (`10.163.235.210/17`), and `_ping_sweep()` is capped at `.1–.254`.
  On the campus SSID only the gateway was visible → **client isolation or VLAN splitting**;
  ARP scanning works only on flat, small networks. Room-level presence therefore needs the
  AP management plane (M2) — also the prerequisite for the RSSI "outside the room" idea.
- **Demo-artifact warning recorded:** student Buchari (id 8) is registered with the
  campus **gateway's** MAC, so his Wi-Fi check always passes. Real pilot students must be
  enrolled with their own phone MAC.
- **B5 verified:** `docs/B/data_features_check.md` — history pagination (`X-Total-Count: 12`,
  `limit/offset` pages correct, newest first) and CSV export (`text/csv`, correct header,
  local timestamps, `yes/no` Wi-Fi column).
- **B2 summary ready:** paragraph + table for member D inside `network_validation.md §5`.

### 2026-10-25 — A: app renamed "Student Attendance", default backend URL fixed, phone login path cleared
- **Rename (English UI)**: Android launcher label, login title, home AppBar, MaterialApp
  title, dashboard sidebar + page title → **"Student Attendance"** ("Student Attendance
  System" for the teacher dashboard). API title stays "Face Attendance API" (internal,
  technical). `pubspec.yaml` package name `face_attendance` and import paths unchanged
  (internal technical identifier; renaming would churn every import for zero user value).
- **Login timeout root cause (real phone)**: `ApiService._defaultBaseUrl` was
  `http://10.0.2.2:8000` — an emulator-only alias. On the Galaxy S24 that host does not
  exist, so requests hung for 15 s and failed with "Server took too long to respond."
  Diagnosis evidence: the uvicorn access log had **no** `GET /students/?nim=...` entry,
  i.e. the request never left the phone; phone-browser `http://127.0.0.1:8000/health`
  returned OK (adb reverse path works).
  Fix: default is now `http://127.0.0.1:8000` (works for real device + emulator with
  `adb reverse tcp:8000 tcp:8000`; LAN users override in Settings), and the timeout
  message now tells the user exactly what to check.
- Analyzer clean, Flutter widget test + backend dashboard test green. Rebuilt
  `app-debug.apk`, reinstalled on the S24, app data cleared so the new default applies.
- Design discussion recorded for M2/M3 (see conversation): away-episode tracking via
  periodic ARP scans, RSSI threshold (~ -72 dBm ≈ "outside the room") read from the AP
  management plane (SSH/SNMP/controller API), teacher status overrides (izin/sakit),
  BSSID pinning using the existing `schedules.ap_bssid` column.

### 2026-10-25 — A: anti-cheat pass 1 + teacher-dashboard time bug FIXED + APK build started
- Cheat-hole review done (see conversation notes): biggest gaps = (1) borrowed/
  shared MAC for wifi_verified, (2) photo-file identity swap / replay, plus
  longer-term items (no server auth — device binding in M2; liveness
  detection; MAC randomization on phones documented for C1).
  First-line fixes implemented:
  - **One MAC = one student**: `POST /students/` and `PUT /students/{id}/mac`
    reject a MAC already registered to another student (409, normalized
    comparison — dashes/uppercase caught). 404 added for missing student on
    mac update. Live-verified.
  - **Photo replay guard**: `backend/services/photo_guard.py` + hook in
    `/attendance/check` — the same photo file may be accepted at most once
    per day per student (blocks shared-file identity swap); cross-day reuse
    still allowed; state is process-local (resets on restart, documented).
- Teacher-dashboard "wrong time" bug root cause: `schedules.created_at` was
  neither in the DB schema (older DBs) nor in `ScheduleResponse` (pydantic
  stripped it before the dashboard could read it). Fixed everywhere:
  column added to `models/database.py` + safe `ALTER TABLE` migration in
  `init_db`, INSERT now writes an explicit **CST** timestamp (consistent
  with attendance rows), and `ScheduleResponse.created_at` added.
  Live-verified: `"created_at":"2026-10-25T08:42:51"` (CST, correct).
- Demo-class creation in the browser simulator now matches the requested
  behaviour: press at 10:00 → class **10:01–10:10** (opens +1 min, closes
  +10 min, computed in server CST from the browser); log shows when the
  banner will appear. Headless sim produces the same window.
- Tests: 9 new anti-cheat tests in `backend/tests/test_anticheat.py`
  (+ conftest: schedules schema match, per-test photo-guard reset) —
  suite now **140/140**.
- Task-C handover note updated in `docs/C/TASK.md` (already reviewed);
  real-device route started: `flutter build apk --debug` for the user's
  Android phone (HP asli = C1) since Windows-desktop run stays blocked by
  the Developer-Mode symlink requirement.

### 2026-10-25 — A: simulator upgraded to REAL WEBCAM (camera screen opens from the banner)
- `docs/A/demo/auto_prompt_simulator.html` now mirrors the real app flow:
  **Enable camera (live webcam)** button (getUserMedia, permission once per
  browser), banner tap → phone display switches to a **camera screen**
  (mirrored preview + big white capture button, "Back" = cancel), optional
  **auto-capture 3 s** countdown, frame captured to canvas → JPEG →
  `POST /attendance/check`. File-upload flow kept as fallback (photo picker)
  when camera is denied/unavailable. All texts already English; headless
  sim terminal output translated to English too.
- Rationale answered for the team: a web page cannot silently open a webcam
  (needs one user permission + requirement), so the old upload picker was a
  stand-in; the FLUTTER app itself does open the camera screen directly.
- C-task handover note added to `docs/C/TASK.md` (A prototyped the Flutter
  prompt integration; C reviews commit `7803d27` on branch `a` before
  continuing with real-device testing C1).
- GitHub push configured: `git config --global http.proxy
  socks5://127.0.0.1:10808`; branch `a` pushed & tracking origin.

### 2026-10-24 — A: Flutter auto-prompt integration drafted + TWO local simulators running
- Flutter side implemented (draft for **C** to review/own — user requested A
  to prototype it now): `mobile/lib/services/prompt_service.dart` (polling
  service, 20 s heartbeat, dedupe per stage `scheduleId:checkType`), API
  method `getCheckInPrompt`, banner card + "Check in now / Later" in
  `home_screen.dart` (lifecycle-aware: pauses when app backgrounded),
  `auto_check_in_on` toggle in `session_service.dart` + Settings switch.
  `flutter analyze`: **No issues found**. NOT committed to mobile branch —
  sits on task-a for C's review.
- Headless e2e test PASSED (`backend/scripts/simulate_phone.py`): creates a
  fresh demo schedule (unique room, midnight-safe window), then
  banner→tap→START (79.9%, partial) → banner flips END →tap (85.4%,
  verified) → `check_in_complete` banner stops. Full loop 90 s.
- Visual phone simulator: `docs/A/demo/auto_prompt_simulator.html`
  (browser window mimicking the app: banner, Log, photo upload stand-in for
  the camera, auto-tap option, demo-class creator with Shanghai-time
  windows). Served at http://127.0.0.1:8765/auto_prompt_simulator.html
  (`python -m http.server 8765` in `docs/A/demo`).
- Blocked for REAL desktop app run: Windows build needs Developer Mode
  (symlink) — admin denied in this shell. Everything else works on
  emulator/real phone; `10.0.2.2:8000` already the app default.

### 2026-10-24 — A: auto check-in prompt feature BUILT & VERIFIED live (tier 1)
- New endpoint `GET /me/prompt?student_id=N` (`backend/routers/prompt.py`,
  registered in `main.py`): polls-friendly contract for the mobile app —
  returns `prompt` (strict: schedule active + stage open + device MAC seen on
  the classroom network), `check_available`, `check_type` (auto start→end),
  `wifi_seen`, `bssid`, `reason`. READS existing services only; no attendance
  rule changed — check-ins still go through the fully-enforced
  `POST /attendance/check`.
- 7 new tests (`backend/tests/test_prompt.py`): whole suite now **131/131**
  (includes 124 baseline).
- Live verification (schedule "Uji Auto Prompt" id 9, Buchari MAC = gateway):
  prompt start ✅ → start check (confidence 0.972) → prompt flips to `end`
  ✅ → end check (0.955) → `reason: check_in_complete`, banner stops ✅.
  Willian (no valid MAC): `check_available=true` but `prompt=false`,
  `device_not_seen_on_network` ✅. Room-overlap guard also observed working.
- Spec for C (Flutter heartbeat + banner + auto-navigate):
  `docs/A/auto_prompt_spec.md`. Mobile files untouched (C's area).
- (Earlier same day: threshold evaluation with 2 students → report + live
  Wi-Fi/two-stage verification; see previous entries.)

### 2026-10-24 — A: end-to-end Wi-Fi + two-stage check-in VERIFIED live
- Server run with `TIMEZONE=Asia/Shanghai` (CST); Wi-Fi scan auto-detected
  subnet 10.163.207.0/24 and BSSID 54:2b:de:fd:90:21 correctly in local time.
- **Discovery: `/wifi/scan` on Windows does NOT need Npcap** — it uses ping
  sweep + `arp -a` (see `wifi_scanner.py::_scan_windows`). The "Npcap required
  on Windows" note in AGENTS.md/PROJECT_CONTEXT is outdated for this path;
  Npcap only matters for raw Scapy (Linux path) capture. Candidate doc fix.
- Set Buchari MAC (simulated as gateway device) via `PUT /students/8/mac`.
- `POST /attendance/check?schedule_id=8&check_type=start` with a HELD-OUT
  photo (never enrolled) → matched, confidence **0.943**, `wifi_verified=true`,
  status `partial` ✅ (recognition works on unseen photos, not just enrolled ones)
- `end` check with another held-out photo → confidence **0.688**,
  `wifi_verified=true`, **status `verified`** — both rows finalized ✅
- Full two-stage flow + Wi-Fi check automation confirmed working live.
- Observed issue for review: `students/faces.created_at` + `ap_logs.scan_time`
  use SQLite `CURRENT_TIMESTAMP` (UTC) while `attendance.timestamp` is local —
  inconsistent; fix candidate in `models/database.py`.

### 2026-10-24 — A: first enrollment + threshold evaluation done (2 students)
- Fixed environment: `onnxruntime` failed to import because NumPy 2.2.6 was
  installed; restored the pinned `numpy==1.26.4` from `backend/requirements.txt`.
- Created students: Buchari `F25040126` (id 8) and Willian `F25040128` (id 9).
- Enrolled faces: Buchari 5 selfies (varied location/lighting/expression),
  Willian 3 selfies. Stored under `gambar_percobaan/orang_1|orang_2/` (gitignored).
- Ran `evaluate_threshold.py` → wrote real FAR/FRR/EER to `docs/threshold_report.md`:
  genuine min **0.708** vs impostor max **0.224** → distributions fully separated.
  **Threshold kept at 0.5** (midpoint of safe gap [0.224, 0.708]).
- ⚠️ Pending: still 2/3 students — recruit `orang_3` and re-run the evaluation
  before the M1 progress report (~Nov 1). See caveats in `docs/threshold_report.md`.

### 2026-10-18 — Planning session + repository audit + docs restructure (all)
- Audited the repository against reality: 124 tests, **123 passing**, 1 failing
  (`test_dashboard_served` — stale `"Teacher Dashboard"` assertion vs. redesigned
  dashboard titled "Face Attendance System - Presentation Dashboard"). Assigned to D.
- Found ~1185 lines of **uncommitted** dashboard redesign work
  (`backend/static/dashboard.html`). Assigned to D (review → commit).
- Confirmed `docs/threshold_report.md` is still a placeholder → A's top priority.
- Restructured `docs/`: created `PROJECT_CONTEXT.md` (master AI reference),
  `PLAN_TIMELINE.md` (this file), `meetings/`, per-member folders `A/ B/ C/ D/`
  with `TASK.md` + `PROMPT.md`.
- Archived outdated docs to `docs/archive/` (old `TASK_*.md`, `PROMPT_AI_TEAM.md`,
  `PEMBAGIAN_TUGAS_2026-10.txt`). Deleted stale root files `progress_report.txt` and
  `next_steps.txt` (recoverable from git history). All progress tracking now lives in
  `docs/`.
- Next: Phase 1 starts Oct 19 — each member follows their `docs/<X>/TASK.md` P0 items.
