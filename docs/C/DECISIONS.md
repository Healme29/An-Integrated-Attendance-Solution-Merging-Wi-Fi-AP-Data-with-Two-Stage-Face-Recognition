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

### C-001 — Ownership transfer: dashboard + presentation artefacts from D to C
- **Date:** 2026-11-09 · **Stage:** M2 restructuring (team reassignment)
- **Problem:** Member D cannot commit (no git access) and the remaining D tasks sit on the
  demo's critical path, so the dashboard polish and the presentation materials have no one
  to execute them.
- **Options:** (1) keep the files with D and have A commit D's materials — every remote
  change waits for A; (2) transfer ownership explicitly to C and record it; (3) leave the
  tasks unassigned — blocks G14-class deliverables and the demo.
- **Evidence:** `docs/D/TASK.md` stage-1 polish items (status colors, schedule/date filter,
  CSV button, print CSS, responsive) are still open; the C dev-environment report
  (OS-based, no Flutter tooling) was recorded in the group chat on 2026-11-09.
- **Decision:** Ownership of `backend/static/dashboard.html` and of the slides / backup-video
  artefacts moves from D to C, effective 2026-11-09. D keeps written/evidence tasks, with A
  committing on D's behalf for anything that must land in `docs/**`. The "one small change =
  one commit = one browser check" rule still applies to every dashboard edit.
- **Consequences:** `docs/C/TASK.md`, `docs/D/TASK.md` and `PROJECT_CONTEXT.md §9` role
  boundaries are outdated until the M3 cleanup; every C dashboard commit must keep `pytest`
  green (the dashboard-title assertion is the guard).
- **Revisit by:** after the end-of-November presentation — confirm the transfer still fits
  the actual workload, or partially hand the dashboard back.

### C-002 — G6 exception: auto check-in paused until after the end-of-Nov presentation
- **Date:** 2026-11-09 · **Stage:** M2 / gate G6 (exception recorded per `PLAN_TIMELINE §2.1`)
- **Problem:** G6 (auto check-in finished on a real device, due Nov 22) is C's gate, but C
  has no Flutter dev environment this month, and the demo was moved up to end-of-November.
- **Options:** (1) keep G6 as a hard Nov 22 gate — not executable without Flutter tooling;
  (2) A finishes the auto-prompt work — violates the standing rule that A only reviews and
  decides (`PLAN_TIMELINE §2.3 #4`); (3) record an exception: defer G6, demo with the
  device-tested APK v0.9.0 using manual start/end check-in.
- **Evidence:** `docs/C/review_7803d27.md` (A's auto-prompt draft reviewed and accepted by
  C); progress log 2026-10-26 (real-device full flow passed on the Galaxy S24; APK v0.9.0
  built and install-verified). Flutter tooling unavailable on C's machine — recorded in
  chat, 2026-11-09.
- **Decision:** Option 3. G6 is deferred until after the end-of-November presentation; the
  demo flow uses APK v0.9.0 with manual check-in (already device-tested). The original G6
  pass criteria (banner → camera → start/end without manual intervention) stay unchanged
  and remain an open, graded item — not dismissed.
- **Consequences:** C's M2 package order changes (G6 falls behind the presentation); the
  auto check-in feature must not be promised in the demo narrative.
- **Revisit by:** first week of December 2026.

### C-003 — G4 (teacher confirmation) reassigned from D to C
- **Date:** 2026-11-09 · **Stage:** M2 / gate G4 (critical chain)
- **Problem:** G4 (pilot date + student roster confirmed by the teacher, due Nov 22) was
  D-owned; with the package redistribution it lost its owner while the whole gate chain
  (G4 → G7 → G9 → G10) depends on it.
- **Options:** (1) reassign to A — A already carries the largest package and leading a
  member's task violates §2.3 #4; (2) assign to C alongside the dashboard — it is a
  communication task, no code involved; (3) leave it unassigned until after presentation
  — pushes G7 and everything downstream.
- **Evidence:** `docs/PLAN_TIMELINE.md §2.1` critical chain; `docs/D/TASK.md` escalation
  note ("escalate to A the same day if the teacher has not answered by Nov 20").
- **Decision:** C owns G4: sends the teacher-confirmation message (approved draft), records
  the confirmed date / class / room / roster into `docs/D/teacher_requirements.md` (handed
  to the group chat; A commits the file if C cannot), and escalates to A in-chat by
  **Nov 20** if the teacher has not replied. The gate date (Nov 22) is unchanged.
- **Consequences:** C gains one non-code logistics task; the demo narrative must carry the
  honest status of the pilot date.
- **Revisit by:** Nov 22, or the day the teacher replies.
