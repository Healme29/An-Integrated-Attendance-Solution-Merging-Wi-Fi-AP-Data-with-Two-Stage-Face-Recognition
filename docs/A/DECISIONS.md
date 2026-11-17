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
- **Update (2026-11-01, same day):** the owner approved flipping the code default to
  `YOLO_IMG_SIZE=640` as well, so a machine where nobody sets env values still runs the
  measured setting. The env override stays for G7. This does not change the counter-risk
  above: G7 must still measure 640 vs 1280 on classroom-distance faces.
- **Revisit by:** G7 (classroom enrollment photos) — decide whether enrollment needs a
  higher `imgsz` than check-in; re-check at G10 with pilot numbers.

### D-003 — Bind check-in to the logged-in student; one photo, one face
- **Date:** 2026-11-01 · **Stage:** M2 stage 3 / pre-G7 security fix
- **Problem:** `POST /attendance/check` had no `student_id`, so the student was decided
  purely by the face in the photo (`max(faces, key=confidence)`). If student A's phone sent
  a photo containing A and friend B, the server could record B (and grant B attendance if
  B's device was on the classroom network), while A got nothing and no error. Separately,
  `POST /faces/enroll` stored one embedding per detected face, so a friend in the frame was
  enrolled into the owner's profile.
- **Options:** (1) status quo — zero work, hole stays and is trivially demonstrable;
  (2) bind the check to the signed-in `student_id` and reject a face that matches somebody
  else (403) — small change, closes impersonation, but a two-person photo still has to pick
  one face; (3) reject any photo with more than one detected box — one rule, but nested
  duplicate boxes would block legitimate selfies (15/15 cropped enrollment inputs);
  (4) enroll only the largest face and silently ignore the rest — stops profile
  contamination but hides the mistake from the student; (5) combine 2 + dedupe +
  significance filter + one-face enrollment + audit column.
- **Evidence:** Code path before the change: `backend/services/attendance.py:84` and
  `backend/routers/faces.py:80-91`. 7 of the 52 original photos really contain two people
  (`docs/A/yolo_tuning.md`). Measured on those photos at conf 0.25 / imgsz 640: second-face
  area relative to the largest = **0.147–0.243** for a real second person and
  **0.007–0.028** for background faces, so a 0.10 threshold separates them with margin.
  Nested duplicate boxes: **1 box in 1 of 52** original photos, but **15/15** cropped
  enrollment inputs — dedupe is required before "more than one face" can be trusted.
  After the change: 13 new tests (`backend/tests/test_identity_binding.py`), full suite
  **153 passed**.
- **Decision:** Implement option 5. `student_id` is a required query parameter; the
  recognized face must equal it (403 "Identity mismatch"), and an unknown student is 404.
  Detector boxes are deduplicated by containment (intersection / smaller area ≥ 0.6), and
  a second face with ≥ 10% of the largest face's area is rejected with 400 "Multiple faces
  detected" at both check-in and enrollment. Enrollment stores exactly one embedding (the
  largest face). `attendance.faces_detected` stores the raw box count for audit.
- **Consequences:** every client must send `student_id` (Flutter app, demo simulator, smoke
  test, phone simulator updated). A student photographed with a friend now gets a clear
  rejection and must retake the selfie alone; a distant bystander does not block a normal
  selfie. Existing enrolled profiles may still contain a friend's embeddings from before
  this fix (7/52 source photos had two people), so re-enrollment is required before the
  pilot. The 0.10 threshold is measured on 3 people only. **Honest limitation:** the
  endpoint has no session token, so `student_id` is claimed, not proven; a determined pair
  could still do a "buddy check-in" by sending the friend's id together with a fresh photo
  of that friend (Wi-Fi then requires the friend's device on the classroom network). This
  fix closes accidental and obvious impersonation, not a colluding pair; real prevention
  needs an authenticated session, which is out of scope for M2 and recorded for M3.
- **Update (2026-11-01, same day):** the contaminated demo profiles were rebuilt with
  `backend/scripts/reenroll_clean.py`, which classifies every source photo with the same
  detect → dedupe → tiny-filter → distinct-people path as the API, deletes the old
  rows/pickle/crops, and enrolls through `POST /faces/enroll`. Result: students 8, 9 and 11
  each ended with exactly 5 embeddings, and all 15 came from single-person photos
  (`orang_1` 17/17 usable, `orang_2` 17/21 usable — the 4 rejected photos had a second face
  at ratio 0.147–0.243, `orang_3` 14/14 usable). `docs/threshold_report.md` shows the
  impostor tail moving down after the rebuild (FAR 0.1733 → 0.0400 at threshold 0.15,
  0.0400 → 0.0000 at 0.20), which is direct evidence that the old profiles were
  contaminated. Deployment on real students is still G7.
- **Revisit by:** G7 (classroom photos, more faces at distance) and G10 (pilot logs: count
  of 400 "multiple faces" and 403 "identity mismatch"; raise/lower the 0.10 ratio if either
  is too frequent).

### D-004 — Rebuild demo profiles from scratch instead of topping them up
- **Date:** 2026-11-01 · **Stage:** M2 stage 3 / cleanup after D-003
- **Problem:** students 8, 9 and 11 were enrolled before D-003, so their 5 stored embeddings
  may include a friend's face. How do we make the demo profiles trustworthy without losing
  the students, their attendance history or the dashboard rows?
- **Options:** (1) top up to 5 with clean photos — impossible under the cap without deleting
  something, and there is no way to tell which stored embedding belongs to the friend;
  (2) delete all faces rows, pickle and crops, then re-enroll only single-person photos —
  provable result, but it destroys the old embeddings; (3) create new student records —
  clean profiles, but attendance history, dashboard names and NIMs split in two;
  (4) leave the profiles until G7 — zero work, but the demo and any threshold re-measurement
  would keep using possibly contaminated data.
- **Evidence:** `backend/scripts/reenroll_clean.py` classifies every source photo with the
  same path as the API and found `orang_2` **17/21 usable**, with 4 photos rejected for a
  second face at ratio **0.147–0.243** (the same range as D-003). A real top-up is therefore
  not possible without deleting rows, which confirms option 1 is not safe. After the rebuild:
  students 8/9/11 each have exactly **5 rows = 5 pickle entries = 5 crops**, all from
  single-person photos. `docs/threshold_report.md` re-measurement: FAR at 0.15 dropped
  **0.1733 → 0.0400** and at 0.20 **0.0400 → 0.0000** with the same 15 samples, i.e. the old
  profiles really were contaminated. Attendance history is unaffected because rows reference
  `student_id`, not `faces.id`.
- **Decision:** option 2. Back up `attendance.db`, `backend/data/embeddings/` and
  `backend/data/faces/` first, reset the three profiles, re-enroll 5 accepted photos each
  through the real `POST /faces/enroll` endpoint, and verify count equality. The script stays
  in the repo for the G7 classroom enrollment and for any future suspected contamination.
- **Consequences:** the old embeddings are gone from the live profile (kept in the local
  backup only), so earlier per-photo scores cannot be recomputed without restoring that
  backup. The demo now uses profiles that provably contain one face per photo. This does not
  fix contamination for real students; G7 still re-enrolls the pilot group from scratch.
- **Revisit by:** G7 — repeat the same script for the pilot roster, and re-run it if a profile
  ever produces a suspicious false accept.

---

## Entri M2 — perencanaan demo (Nov 2026)

### D-005 — Accelerated demo: presentation ~Nov 23, submission & demonstration end of November
- **Date:** 2026-11-09 · **Stage:** M2 / affects G7–G16 ordering and the demo scope (former G12)
- **Problem:** The team will be assessed at a collection and demonstration at the end of
  November (~2 weeks after this decision), roughly two months earlier than the planned
  G16 demo on Jan 18. The gate schedule must be re-cut without weakening the claims.
- **Options:** (1) keep the Jan 18 plan and demo an untested subset live — risk of
  overclaiming and a failed live demo; (2) compress: lock the feature-complete core for
  the end-of-Nov demo, shift the classroom-pilot chain to December, cut the robustness
  study to a mini version for presentation evidence, and write the scope honestly;
  (3) request that the assessment move to January — not in the team's control.
- **Evidence:** Already measured and available for the slides today: `docs/threshold_report.md`
  (15 samples / 30 genuine / 75 impostor pairs, FAR = FRR = 0.00 in the 0.25–0.65 band,
  threshold 0.5 per D-001), `docs/A/yolo_tuning.md` (52/52 detection in all six combinations;
  640 median 481 ms vs 1280 median 1816 ms; D-002), robustness sanity run (46/46 usable
  accepted, 0 false accepts, p50 1069 ms, `docs/A/robustness_test.md`), 153/153 tests.
  **Not measured yet:** full 5×5 robustness (P4/P5 missing), classroom enrollment
  (blocked on the former D-owned G4), and the real-classroom pilot.
- **Decision:** Option 2. The end-of-November demo set is: NIM login → face enrollment
  (including the two-person rejection) → two-stage check-in (start/partial → end/verified)
  → teacher dashboard with live rows → CSV export → protection demos (400 "multiple faces",
  403 "identity mismatch", 409 duplicate). Evidence slides use only the measured numbers
  above plus a mini robustness study (3 people × 3 conditions: bright, dim, angled) that
  must be labelled "measured on N samples". The full 5×5 robustness study and the classroom
  pilot (G7 → G9 → G10) move to December after the presentation; config stays as locked in
  D-002 (`conf 0.25`, `imgsz 640`, threshold 0.5) — **no tuning before the demo without a new
  decision entry**. G4 (teacher confirmation) is reassigned per C-003 and keeps its Nov 22 date.
- **Consequences:** gates G7–G16 are re-sequenced around the presentation and recorded in
  `docs/PLAN_TIMELINE.md`; the December plans (pilot runbook, G7 checklist in
  `docs/A/pilot_plan.md`) remain the target after the demo, so no pilot-preparation work
  done so far is wasted; the honest-limitations slide must list what was NOT measured.
- **Revisit by:** after the presentation — restore the original M2 order for the December
  pilot; re-verify at the January submission that the scope text still matches reality.

---

### D-006 — Strict classroom mode: refuse check-in when the phone is not on the classroom network
- **Date:** 2026-11-10 · **Stage:** M2 stage 3 (robustness) / affects G7 pilot and the demo
- **Problem:** A student could record attendance from anywhere: the Wi-Fi result only
  downgraded the row to `face_only`, and the app opened the camera outside the class window.
  The intended rule is "photo only when the time is right AND the student is in the room".
  Observed case: a 23:25–23:27 class accepted `start` at 23:29 and `end` at 23:30 because
  the ±15 min grace applies to both stages (rows 18–19 in the demo DB).
- **Options:** (1) keep the current soft rule — any face match records attendance, Wi-Fi is
  advisory (`face_only`); (2) strict mode behind `REQUIRE_CLASSROOM_WIFI=true` — no device
  visible on the classroom network means HTTP 403 and no row, keeping the soft rule as the
  default for environments without a classroom network; (3) always strict — simplest, but
  breaks every setup whose server is not on the classroom subnet, including all current
  tests.
- **Evidence:** `backend/tests/test_classroom_wifi_strict.py` (11 tests: preflight reasons,
  403 without network, 200 with network, `/schedules/active` filtering) and the full suite
  at **198 passed**. Location verification is two-layer by design: the student MAC must be
  visible in the server's ARP table, and when `schedules.ap_bssid` is set the server itself
  must be associated with that BSSID (`docs/B/network_validation.md` F6 covers the case
  where the BSSID cannot be read). A campus-wide SSID still means the BSSID pin proves the
  *server's* AP, not each phone's AP — the honest limit of a laptop-side scan.
- **Decision:** Option 2. Edge cases are rejected **before** the camera opens through
  `GET /attendance/preflight` (time window, wrong day, classroom network, duplicate stage,
  end-without-start) and enforced again server-side in `POST /attendance/check`, so a
  modified client cannot bypass it. The mobile app now lists only `/schedules/active`, which
  removes the "pick an old schedule and take a photo" dead end.
- **Consequences:** the demo machine must be the classroom network host (laptop hotspot
  `Attendance-Demo` or a laptop inside the classroom LAN); enrolment MAC addresses must be
  real, because a placeholder MAC can never verify. `face_only` rows remain possible only
  when the flag is off.
- **Revisit by:** before the G7 classroom enrolment — confirm the flag and the hotspot
  address are part of the runbook; revisit the BSSID layer if the campus AP controller ever
  exposes per-client AP information.

---

