# Team Planning Session — Minutes

- **Date:** Sunday, October 18, 2026
- **Participants:** Team lead (A) and members B, C, D
- **Session type:** Task division + timeline planning + documentation restructure
- **Outcome documents:** `docs/PROJECT_CONTEXT.md`, `docs/PLAN_TIMELINE.md`,
  `docs/A/`, `docs/B/`, `docs/C/`, `docs/D/`

---

## 1. Situation on the table

The codebase has moved far ahead of the documentation. An audit performed during this
session (2026-10-18) verified:

- The four "Priority 1 blockers" described in the old task files are **already fixed
  and tested**: two-stage attendance pairing (start → partial → end → verified /
  face_only), schedule time enforcement with grace period, NIM login lookup, and the
  mobile/backend data contract.
- The test suite has **124 tests, 123 passing**. The single failure
  (`test_dashboard_served`) is caused by a stale test assertion, not a real bug: the
  test expects the text `"Teacher Dashboard"` but the dashboard was redesigned with the
  new title `"Face Attendance System - Presentation Dashboard"`.
- The dashboard redesign itself (~1185 lines changed) is sitting **uncommitted** in the
  working tree.
- `docs/threshold_report.md` is still a **placeholder** — the similarity threshold (0.5)
  has never been tuned with real face data.
- The system has never been tested on a real school Wi-Fi network, a real Android
  phone, or with real students.

Conclusion: the remaining work is **validation with real data + polish + reports +
presentation**, not new feature building.

## 2. Team composition and skills

| Member | Coding ability | Consequence for task division |
|--------|----------------|------------------------------|
| A | Strong (vibe-codes) | Gets the most complex share: ML accuracy validation, threshold tuning, integration, code review as lead |
| B | Strong (vibe-codes) | Backend validation on real networks, deployment, demo environment |
| C | Strong (vibe-codes) | Mobile app on real devices, release builds |
| D | Beginner (cannot code independently) | Non-code deliverables: reports, presentation, teacher communication — plus ONE carefully chosen, beginner-safe coding task (see below) |

## 3. Decisions

1. **Workload balance.** Every member gets roughly 20–30 hours of work across the 5
   months. A gets the hardest technical share; D's share is documentation-weighted but
   equally important for the grade.
2. **D still touches code — safely.** D polishes the teacher dashboard
   (`backend/static/dashboard.html`): a single HTML/CSS/JS file with no build step and
   instant browser feedback, ideal for guided "vibe coding". D's prompt file
   (`docs/D/PROMPT.md`) contains strict safety rails: one tiny change at a time, verify
   after each step, never touch Python backend files (the single allowed exception: the
   one-line test assertion fix).
3. **Per-member folders.** Each member gets `docs/<letter>/` containing:
   - `TASK.md` — their concrete task list with priorities, estimates, and milestone
     deliverables. Language: **Indonesian for A, B, C; English for D** (D's task file is
     step-by-step and doubles as a beginner guide).
   - `PROMPT.md` — a ready-to-paste prompt for their AI coding assistant
     (all in English for model accuracy). Each prompt is self-contained: mission,
     context summary, task details, file whitelist, verification commands, and
     report-back format.
4. **Single source of truth.** A new master file `docs/PROJECT_CONTEXT.md` gives any AI
   assistant (or a new contributor) the complete concrete picture: goals, rules,
   architecture, schema, endpoints, config, verified status, team, milestones, commands.
   `docs/PLAN_TIMELINE.md` holds the milestones and the living progress log.
5. **Out with the stale.** Old task files (`TASK_A_LEAD.md`, `TASK_B/C/D.md`,
   `PROMPT_AI_TEAM.md`) moved to `docs/archive/` — historical only. Stale root files
   `progress_report.txt` and `next_steps.txt` deleted (recoverable from git history).
   `PEMBAGIAN_TUGAS_2026-10.txt` archived because it was never committed (deleting it
   would lose it permanently). From now on, **all progress reporting lives in `docs/`**.
6. **All documentation in English** (reports, prompts, meeting minutes, context files)
   except member TASK files for A, B, C, which stay in Indonesian so nothing is
   ambiguous for the team.

## 4. Milestones agreed

| Milestone | Deadline | Note |
|-----------|----------|------|
| M1 — Progress report | **~Nov 1, 2026** (2 weeks from this session) | Backed by first real-data results from every member |
| M2 — Presentation & demo | **~Jan 18, 2027** (3 months) | Live demo on real phone + real Wi-Fi; pilot classroom test in December |
| M3 — Final submission | **~Mar 18, 2027** (5 months) | Code freeze Mar 2; report assembled from per-member chapters |

## 5. Immediate action items (owners)

| # | Action | Owner | Due |
|---|--------|-------|-----|
| 1 | Review + commit the uncommitted dashboard redesign; fix the `test_dashboard_served` assertion | D | Oct 25, 2026 |
| 2 | Enroll ≥3 people, run `evaluate_threshold.py`, fill `docs/threshold_report.md` with real FAR/FRR/EER | A | Oct 29, 2026 |
| 3 | Validate Wi-Fi scan + MAC check on a real router; document results | B | Oct 29, 2026 |
| 4 | Run the full app flow on a real Android phone; log all issues found | C | Oct 29, 2026 |
| 5 | Collect member inputs, assemble the M1 progress report | D | Nov 1, 2026 |
| 6 | Weekly 15-minute sync every Sunday; A checks the progress log | All | Recurring |

## 6. Working rules reaffirmed

- Branches: `task-a`, `task-b`, `task-c`, `task-d`; merges to `main` reviewed by A.
- `python -m pytest backend/tests -q` must pass before every commit (123/124 baseline
  until item 1 above is done).
- Never commit `attendance.db`, `*.pkl`, `yolov8m-face.pt`, face images, or log files.
- Stuck >30 minutes → ask the group; don't work in silence.
