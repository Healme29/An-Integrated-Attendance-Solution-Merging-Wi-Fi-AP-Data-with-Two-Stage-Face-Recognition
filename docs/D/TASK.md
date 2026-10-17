# TASK D — Teacher Dashboard (guided), Test Evidence, Reports, Presentation & Coordination

> **Read first:** `docs/PROJECT_CONTEXT.md` (project picture) and `docs/PLAN_TIMELINE.md`
> (deadlines). Your AI guide: `docs/D/PROMPT.md`.
> Estimated total workload: **20–24 hours** — balanced with B and C; A still carries the
> most complex share. You are NOT expected to write program code from scratch. Your one
> coding area is a single HTML file, and every step below tells you exactly what to do.

Your areas: (1) the **teacher dashboard** (one HTML file — perfect for guided editing),
(2) **test evidence** for every report, (3) **the progress report, final report, slides,
demo video**, and (4) **communication with the teacher/school**.

---

## PRIORITY 0 — must be done before the progress report (~Nov 1, 2026)

### D1. Commit the dashboard redesign that is sitting in the working tree
There is a big, finished-looking dashboard redesign that was never committed
(+1185 lines changed). Uncommitted work can be lost — commit it first.

1. See what changed: `git status` then `git diff --stat backend/static/dashboard.html`
2. Start the backend: `uvicorn backend.main:app --reload`
3. Open http://localhost:8000/dashboard and click through it. If it loads and shows
   attendance data correctly → it works.
4. If it works, commit it:
   ```bash
   git add backend/static/dashboard.html
   git commit -m "Redesign teacher dashboard"
   ```
5. If something is broken, write down exactly what you see and ask A or B for help
   before doing anything else.

### D2. Fix the ONE failing test (this is your one allowed Python edit)
The test suite has 124 tests; 123 pass. The failing one is
`backend/tests/test_routers.py :: TestRootEndpoint :: test_dashboard_served` (around
line 443). It checks that the served dashboard contains the text `"Teacher Dashboard"`,
but the redesigned dashboard's title is now
`"Face Attendance System - Presentation Dashboard"`.

Fix: open `backend/tests/test_routers.py`, find the line:

```python
assert "Teacher Dashboard" in response.text
```

change it to:

```python
assert "Face Attendance System - Presentation Dashboard" in response.text
```

Then verify: `python -m pytest backend/tests -q` → expect **124 passed**.
Commit: `git commit -am "Fix dashboard test to match new title"`.

### D3. Evidence pack (you will reuse this for every report)
Collect proof that the system works, saved into `docs/D/evidence/`:

1. Test output: `python -m pytest backend/tests -q` → copy the last lines into
   `docs/D/evidence/pytest_result.txt`
2. Smoke test (start the server first, second terminal):
   `python backend/scripts/smoke_test.py --base-url http://127.0.0.1:8000`
   → save output to `docs/D/evidence/smoke_test_result.txt`
3. Screenshots (browser): `/docs` (Swagger), `/dashboard` (teacher view),
   `/attendance/today` data. Save as `dashboard_overview.png`, etc.
4. When C finishes real-device testing: get 2–3 phone screenshots from C
   (login, selfie check-in, history) into the same folder.

### D4. Progress report (~Nov 1, 2026) — your main M1 deliverable
Collect one written input from each member by **Oct 29** (A: threshold numbers; B: Wi-Fi
validation results; C: device test summary; your own: D1–D3 evidence), then assemble a
short report with this skeleton (2–4 pages is enough):

1. **Goals** — the 3-condition attendance rule (copy from PROJECT_CONTEXT §1)
2. **What works now** — with your evidence pack (test counts, screenshots)
3. **First real-world results** — A/B/C inputs
4. **Plan ahead** — copy the milestone table from `docs/PLAN_TIMELINE.md`
5. **Risks** — copy the risk table from `docs/PLAN_TIMELINE.md`

---

## PRIORITY 1 — November–December 2026

### D5. Dashboard polish (one tiny change at a time — see your PROMPT.md)
Work from a prioritized wish list; each item = one small guided change = one commit:
- [ ] Status colors: `verified` green, `partial` yellow, `face_only` orange
- [ ] Filter by schedule (dropdown) and by date on the today view
- [ ] "Export CSV" button linking to `/attendance/export/csv`
- [ ] Print-friendly CSS (`@media print`) so teachers can print the list
- [ ] Works on a phone screen (responsive)

Rule: after every single change → save → refresh the browser → check → commit.
If anything breaks and you cannot fix it in 10 minutes → `git checkout -- <file>` is
NOT allowed to be scary; just ask A/B in the group chat.

### D6. Teacher communication
- Get the teacher's requirements for the final report (format, length, what the demo
  must show) and write them down in `docs/D/teacher_requirements.md`.
- Arrange the December pilot class test date with the teacher (A executes, you arrange
  and document; take photos/video, ~10 minutes of recording).

---

## PRIORITY 2 — January 2027 (presentation & demo)

### D7. Presentation materials
1. **Slides** (10–12 is enough): problem → 3-condition solution → architecture diagram
   (ask A/B for theirs) → live demo → real results (threshold table, pilot numbers,
   screenshots) → limitations (anti-spoofing) → future work.
2. **Demo script**: minute-by-minute who does what (A runs backend, C runs the phone,
   B on standby with seeded fallback data, you narrate and keep time).
3. **Backup video**: record the full flow once (30–60 s) in case Wi-Fi fails on stage.
4. Schedule **two dry runs** with the whole team before the date.

---

## PRIORITY 3 — February–March 2027 (final report)

### D8. Final report assembly
- Chapters arrive from members by **Mar 1**: A "Methods & Accuracy Evaluation",
  B "Backend Architecture & Attendance Flow", C "Mobile Application", plus YOUR
  "Testing & Conclusion" chapter (built from the evidence packs + pilot results).
- You compile everything into one consistent document (same tone, numbering, figures),
  A reviews the full draft by **Mar 8**.

---

## Your working rules

- Branch: `task-d`. Commit after every small verified change.
- You may edit: `backend/static/dashboard.html`, `docs/D/**`, and the ONE test line in
  D2. Anything else in Python/Dart → ask A or B first. Never use
  `git push --force`, `git reset --hard`, or delete files you didn't create.
- Stuck more than 30 minutes → ask in the group chat. That is normal and expected.

## Deliverables per milestone
| Milestone | What must exist from you |
|---|---|
| M1 (~Nov 1, 2026) | D1–D4 done: dashboard committed, 124/124 tests, evidence pack, progress report delivered |
| M2 (~Jan 18, 2027) | Slides + demo script + backup video + dashboard final polish; dry runs done |
| M3 (~Mar 18, 2027) | Final report assembled + your "Testing & Conclusion" chapter + teacher requirements documented |
