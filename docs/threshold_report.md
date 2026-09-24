# Face Similarity Threshold Report

Methodology and how to (re)generate the FAR/FRR evaluation for this deployment.
The report numbers below must be regenerated with **real enrollment data** on the
deployment machine before production tuning - do not rely on the placeholder.

## Why this matters

The attendance pipeline accepts a face when its ArcFace embedding has cosine
similarity >= `FACE_SIMILARITY_THRESHOLD` (env, default `0.5`) against a stored
sample. Setting the threshold too low admits impostors (False Accepts); too high
rejects legitimate students (False Rejects). The right value depends on the
camera, lighting, and population of the actual school.

## How to evaluate

1. Enroll students through the app - at least 2 students, ideally >= 3 selfies
   each, taken in real classroom lighting (front camera).
2. Run the evaluation script against the stored embeddings:

   ```bash
   python backend/scripts/evaluate_threshold.py --markdown --output docs/threshold_report.md
   ```

   The script only reads `backend/data/embeddings/student_*.pkl` - no ML models
   are loaded, so it is safe to run on any machine with a copy of that folder.
3. Review the FAR/FRR table, EER, and the suggested threshold.
4. Set `FACE_SIMILARITY_THRESHOLD` on the server and restart the backend.

## Interpretation guide

- **FAR** (False Accept Rate): fraction of impostor pairs scoring >= threshold.
- **FRR** (False Reject Rate): fraction of genuine pairs scoring < threshold.
- **EER**: operating point where FAR == FRR. For classroom attendance, bias
  slightly ABOVE the EER threshold - a rejected student can retry, but an
  accepted impostor marks attendance wrongly.
- Rule of thumb for ArcFace 512-D embeddings: genuine pairs usually score
  > 0.6, impostor pairs < 0.35. If the measured distributions overlap heavily,
  re-enroll with better lighting / more samples rather than moving the
  threshold.

## Current measurements

> Placeholder - regenerate with the command above after real enrollment.

| threshold | FAR | FRR |
|---|---|---|
| _pending real data_ | - | - |

- Suggested threshold: _pending_
- Approximate EER: _pending_
- Currently configured threshold: `0.5` (env `FACE_SIMILARITY_THRESHOLD`)
