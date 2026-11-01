# DECISIONS — Member D (dashboard, evidence, reports, presentation)

> Every non-trivial decision must be written here. This file is part of the M2 grading:
> it shows that you thought before you acted instead of waiting for the lead.
>
> Rules:
> - Write the entry **before** the work is committed; update it once the measurement is in.
> - Write entries in English.
> - At least 2 options per decision. One option is not a decision, it is an assumption.
> - Evidence = a number, a screenshot, a file path, or a test result. If nothing has been
>   measured yet, write `not measured yet`. Never guess.

## Entry template (copy for each decision)

```markdown
### D-00X — <short title>
- **Date:** YYYY-MM-DD · **Stage:** <M2 stage / gate id>
- **Problem:** what must be decided, in one sentence.
- **Options:** at least 2, each with its cost and its risk.
- **Evidence:** measurement, log line, screenshot path, test result. Nothing measured yet
  → say so.
- **Decision:** what was chosen and why (one paragraph).
- **Consequences:** what becomes harder, what is now off the table, what must be revisited.
- **Revisit by:** date or trigger.
```

---

## Worked examples already used (do not redo them; do challenge them with evidence)

### D-001 — Fix the stale test, not the product name
- **Date:** 2026-10-21 · **Stage:** M1 / D2
- **Problem:** One test failed because it expected the text `"Teacher Dashboard"`, but the
  redesigned dashboard is titled `"Face Attendance System - Presentation Dashboard"`.
- **Options:** (1) rename the dashboard so the stale test passes — product changes to
  satisfy a test; (2) update the assertion to the real title — the test follows the
  intended product; (3) delete the test.
- **Evidence:** `git diff` of `backend/static/dashboard.html` plus loading
  `http://localhost:8000/dashboard` in the browser showed the new title renders correctly
  and the page works.
- **Decision:** Update the assertion (option 2). The dashboard redesign was the intended
  product change; the test was the outdated artifact. Deleting the test would remove the
  only guard that `/dashboard` is actually served.
- **Consequences:** the dashboard title is now asserted, so any future rename must update
  the test in the same commit.
- **Revisit by:** M3 code freeze — confirm the assertion still matches the shipped title.

---

## M2 entries (add below this line)

<!-- First expected entry: which dashboard polish items survive the demo scope cut (G12). -->
