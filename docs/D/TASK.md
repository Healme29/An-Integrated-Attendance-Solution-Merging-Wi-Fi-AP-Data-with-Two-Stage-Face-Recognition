# TASK D — Teacher Dashboard (guided), Test Evidence, Reports, Presentation & Coordination

> **ROLE CHANGE (Nov 9, 2026 — see `docs/D/DECISIONS.md` D-002):** ownership of
> `backend/static/dashboard.html`, the slides and the backup video moves to C (C-001) on
> 2026-11-09, and G4 (teacher confirmation) execution moves to C (C-003). D keeps written
> and evidence work: drafting teacher messages and forms, observation sheets, evidence
> transcriptions. Anything D produces is delivered in the group chat; A commits it into
> `docs/**` on D's behalf (D has no git access). Do not edit `backend/static/dashboard.html`
> yourself from now on. Timeline: presentation ~Nov 23, submission & demo end of November —
> see `docs/A/DECISIONS.md` D-005 and the 2026-11-09 progress-log entry.

> **Read first:** `docs/PROJECT_CONTEXT.md` (project picture) and `docs/PLAN_TIMELINE.md`
> (deadlines). Your AI guide: `docs/D/PROMPT.md`.
> Estimated total workload: **20–24 hours** — balanced with B and C; A still carries the
> most complex share. You are NOT expected to write program code from scratch. Your one
> coding area is a single HTML file, and every step below tells you exactly what to do.

Your areas: (1) the **teacher dashboard** (one HTML file — perfect for guided editing),
(2) **test evidence** for every report, (3) **the progress report, final report, slides,
demo video**, and (4) **communication with the teacher/school**.

> **LANGUAGE RULE:** OUTPUT AND INPUT IN ALL SYSTEMS OF THIS PROJECT MUST BE IN ENGLISH
> BECAUSE THIS ASSIGNMENT USES ENGLISH (THE RESULT). This means: app UI, API responses and
> errors, logs, code comments, commit messages, every file in `docs/**`, CSV headers,
> dashboard text, slides, video, and the final report are all in English. Only the group
> chat may be Indonesian.

> **M2:** your work is one large package in "M2 WORK PACKAGE D" below. You split your own
> weeks; only the order of the stages and the gate dates are fixed
> (`docs/PLAN_TIMELINE.md` §2.1). Every non-trivial decision goes into
> `docs/D/DECISIONS.md` — that file is graded.

---

## PRIORITY 0 — M1 (DONE, Nov 1, 2026)

> ✅ Dashboard redesign committed, the failing test fixed, evidence pack collected, progress
> report delivered. The section below is kept as a record; do not redo it.

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

## M2 WORK PACKAGE D — "Evidence, communication and presentation" (Nov 2, 2026 → Jan 18, 2027)

> One large package. You decide how to split the weeks; the **stage order** and the **gate
> dates** are fixed (`docs/PLAN_TIMELINE.md` §2.1). Every non-trivial decision goes into
> `docs/D/DECISIONS.md` — graded.

**Big goal:** the project must be defensible in front of a teacher or panel using real
evidence, and the demo must run on a script that cannot fail silently.

| # | Stage | Window | Gate | What you produce |
|---|-------|--------|------|------------------|
| 1 | Finish the dashboard + refresh evidence | Nov 2–15 | — | Remaining polish items (status colors, schedule/date filter, CSV button, print CSS, responsive). One small change → one commit → one browser check. Refresh `docs/D/evidence/` |
| 2 | Teacher requirements + pilot logistics | Nov 16–29 | **G4** | `docs/D/teacher_requirements.md` written, and the **pilot date + student roster locked**. This is the project's critical path — treat it as your most important deadline |
| 3 | Pilot pack + slide skeleton | Nov 30–Dec 6 | — | Observation sheet, metrics form, recording plan, who stands where, slide outline |
| 4 | Document the pilot | Dec 7–13 | **G9** | Photos, video, notes, timings into `docs/D/pilot_evidence/` |
| 5 | Slides v1 + pilot results | Dec 14–27 | — | 10–12 slides: problem → three-condition rule → architecture → live demo → real numbers → limitations → future work |
| 6 | Demo script + backup video | Dec 28–Jan 10 | **G14** | Minute-by-minute roles (A backend, C phone, B fallback standby, D narrates + keeps time) + a 30–60 s recording of the full flow |
| 7 | Dry runs + final materials | Jan 11–18 | **G13, G15, G16** | Run both dry runs, fix what breaks, final slides, printed handout, timekeeper on the day |

**Done when:** dashboard final; `teacher_requirements.md` and the pilot date locked early;
the pilot documented with photos, video and numbers; slides + script + backup video
finished; two dry-run reports written; you can run the demo from paper without improvising.

**Critical-thinking questions you must answer yourself** (`docs/D/DECISIONS.md`):

- What exactly must the panel see in the first 60 seconds, and what can be cut without
  weakening the claim?
- Which evidence is a real measurement and which is only a screenshot? Label them
  differently in the slides.
- If the live demo fails on stage, what is the exact sentence you say and what do you show
  next?
- What would a skeptical examiner attack first (anti-spoofing, Wi-Fi reliability, small
  sample size), and where in the slides is the honest answer?

**Escalation:** stage 2 is the only stage in the whole plan that can stop everyone else.
If the teacher has not answered by **Nov 20**, tell A the same day — do not wait.

Old task IDs still apply: D5 = stage 1, D6 = stage 2, D7 = stages 3–7.

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
- Stuck more than 30 minutes → ask in the group chat **with a proposal**, never with a raw
  problem. "I tried A and B, results here, I pick B because this" is the expected shape.
- Every non-trivial decision goes into `docs/D/DECISIONS.md` (problem → at least 2 options
  → evidence → decision → consequences → revisit trigger).

## Deliverables per milestone
| Milestone | What must exist from you |
|---|---|
| M1 (~Nov 1, 2026) | ✅ D1–D4 done: dashboard committed, tests green, evidence pack, progress report delivered |
| M2 (~Jan 18, 2027) | G4 teacher date + roster · G14 slides + script + backup video · dashboard final · dry-run reports |
| M3 (~Mar 18, 2027) | Final report assembled + your "Testing & Conclusion" chapter + teacher requirements documented |
