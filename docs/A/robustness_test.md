# Robustness test — recognition under classroom-realistic conditions

> Deliverable for M2 stage 3 ("Bukti ketahanan"), owner A. Target window: **9–22 Nov 2026**,
> before classroom enrollment (**G7**, 29 Nov) and the pilot (**G9**, 7–13 Dec).
>
> **Status: protocol ready, measurement NOT done yet.** The results tables below say
> `not measured yet` on purpose. Do not fill a cell from memory; fill it from a run of
> `backend/scripts/robustness_eval.py` and keep the raw output.

## Question

Threshold 0.5 was chosen on close-up, well-lit selfies (D-001, `docs/threshold_report.md`).
Real check-ins happen in a classroom: dim light at the back, faces turned toward a
projector, glasses, and — despite the rule — sometimes a mask. The question is not "does
the model work", it is:

1. Which of the five conditions (bright, dim, angled, glasses, mask) causes the most
   false rejects at the deployed threshold?
2. Does any condition cause a **false accept** (a probe accepted as the wrong person)?
3. Is a failure caused by the detector (no face / two faces), by ArcFace (low score), or by
   the enrollment profile (one person's genuine scores are low in every condition)?

Answers go into `docs/A/pilot_report.md` (analysis) and the final report chapter.

## Non-negotiable rules

- **Photos never enter git.** `.gitignore` excludes `robustness_captures/`, but check
  `git status` before every commit anyway. The report contains anonymised labels only.
- **Production data is not touched.** Run the whole test against a separate
  `DATABASE_PATH` and `DATA_DIR` (see *Isolation* below), so the demo profiles stay clean.
- **Consent first.** No photo without the participant's explicit consent (see below).
- **Pre-registered thresholds.** The acceptance numbers below are fixed before measuring.
  Moving them afterwards turns a test into a story.

## Participants and consent

- Minimum **5 people**. The three demo students (Buchari, Willian, Latul) can be P1–P3;
  P4 and P5 must be two additional volunteers (this is the current blocker).
- Each participant is told, in person and in the group chat: what is captured, why, where
  it is stored, who sees it, and when it is deleted. They may stop at any time and ask for
  deletion; a refusal has no consequence for the project.
- Store photos only on the machine that runs the test, under `robustness_captures/`.
  Do not upload them to the group chat, the report, slides, or the demo video.
- Map `P1..P5` to student ids in a local note, not in a committed file. The mapping itself is
  not sensitive, but names next to face photos are.
- **Delete the raw photos by 1 Dec 2026** or when the pilot report is written, whichever is
  later. Keep the anonymised score tables in `docs/A/robustness_raw.md`.
- Glasses/mask are the participant's own; nobody is asked to buy or remove anything.

## Conditions and capture rules

Camera: the demo phone (Samsung Galaxy S24, front camera), **no flash, no beauty mode, HDR
off**, 4:3 JPEG. Distance **50 cm** from the face, phone held at eye level by the
participant or a helper. Do not zoom. Three frames per condition, taken a few seconds
apart; all three are probes (they measure retry behaviour, not just the best shot).

| Condition | How to capture | Light target (lux at face) | Why it is in the test |
|---|---|---|---|
| `bright` | Classroom lights on, face toward the light, no window behind | 300–600 | Baseline; should match the M1 selfies |
| `dim` | Classroom lights off, only window / projector / screen light, still recognisable by eye | 20–80 | Back rows and evening classes |
| `angled` | Head turned **30–45°** yaw, plus one frame at ~15° pitch (looking down at the phone) | same as `bright` | Students look at the screen, not the lens |
| `glasses` | Participant's own prescription glasses, no tint/mirror, normal room light | same as `bright` | Common; tests reflection and frame occlusion |
| `mask` | Surgical or cloth mask covering nose and mouth, normal room light | same as `bright` | Rule says no mask; measure what actually happens if someone tries |

Record in the local manifest: `person, condition, frame, lux, phone, timestamp, notes`. The
lux value can come from a phone light-meter app; ±20% is enough, the point is to separate
"bright" from "dim", not to calibrate a sensor.

## Isolation (do not pollute the demo database)

Run a second backend instance with its own data directory. PowerShell example:

```powershell
$env:DATABASE_PATH   = "C:\attendance_robustness\robustness.db"
$env:DATA_DIR        = "C:\attendance_robustness\data"
$env:YOLO_IMG_SIZE   = "640"
python -m uvicorn backend.main:app --port 8011
```

Enroll each participant **in the `bright` condition only** (5 frames, one face per frame,
the normal enrollment rule). Those profiles are the reference; the other four conditions
are probes. Keeping the reference "normal" is deliberate: a profile built from dim photos
would hide the very failure the pilot will see.

Name probes as:

```
robustness_captures/P1/bright/bright_01.jpg
robustness_captures/P1/dim/dim_01.jpg
robustness_captures/P1/angled/angled_01.jpg
robustness_captures/P1/glasses/glasses_01.jpg
robustness_captures/P1/mask/mask_01.jpg
...
```

## Procedure (about 20 minutes per person)

1. Consent, assign the next free `P` label, note the profile student id.
2. Enroll 5 `bright` frames through the app or `POST /faces/enroll?student_id=`.
   Confirm `total_embeddings=5`; a rejection means retake that frame alone.
3. Capture the five conditions (3 frames each) and move the files into the folder layout.
4. After all participants: run the evaluation (below) on the isolated embeddings directory.
5. Write the numbers into the tables, delete the raw photos, keep the anonymised output.

## Metrics

Evaluated at the deployed `FACE_SIMILARITY_THRESHOLD=0.5`
(`backend/scripts/robustness_eval.py` uses the same code path as `/attendance/check`:
detect → merge duplicate boxes → tiny-face filter → multi-face rejection → ArcFace →
max similarity over the person's stored embeddings).

| Metric | Definition | Denominator |
|---|---|---|
| `detection` | a usable single face was found | all probes |
| `accept` | correct person's top-1 score ≥ 0.5 | usable probes |
| `false accept` | a different enrolled person scores ≥ 0.5 as top-1 | usable probes |
| `rejected` | face found, correct score < 0.5 (false reject) | usable probes |
| `no_face` / `multi_face` / `no_embedding` | policy/model outcome, student must retry | all probes |
| `retry_rate` | `1 − accept` over all probes | all probes |
| latency | seconds from upload to decision (detector + ArcFace) | all probes |

Report `genuine_min` and `genuine_mean` per person as well: one person with a low minimum in
**every** condition points at their enrollment, not at the condition.

## Pre-registered acceptance thresholds

With 5 people × 3 frames = **15 probes per condition**, one probe is 6.7%, so the pass rule
is stated in counts as well.

| Condition | Detection | Accept (at 0.5) | False accepts | Pass rule |
|---|---|---|---|---|
| `bright` | ≥ 95% | ≥ 95% | 0 | 15/15 detected, ≥ 15/15 accepted |
| `angled` | ≥ 90% | ≥ 87% | 0 | ≥ 14/15 detected, ≥ 13/15 accepted |
| `glasses` | ≥ 93% | ≥ 93% | 0 | ≥ 14/15 detected and accepted |
| `dim` | ≥ 87% | ≥ 80% | ≤ 1 | ≥ 13/15 detected, ≥ 12/15 accepted, 0–1 false accept |
| `mask` | reported, no target | reported, no target | **any false accept fails the test** | documented as a limitation |

A false accept in any condition fails the test regardless of the accept rate: granting
attendance to the wrong person is the one error the system exists to prevent.

## Results

`not measured yet` — every cell. The table is filled only from the script output below.

| Condition | probes | detected | accepted | rejected | false accepts | no face | multi face | no embedding | retry rate |
|---|---|---|---|---|---|---|---|---|---|
| `bright` | not measured yet | | | | | | | | |
| `dim` | not measured yet | | | | | | | | |
| `angled` | not measured yet | | | | | | | | |
| `glasses` | not measured yet | | | | | | | | |
| `mask` | not measured yet | | | | | | | | |

Per person (useful to separate condition effects from enrollment quality):

| Person | bright accept | dim accept | angled accept | glasses accept | mask accept | lowest genuine score |
|---|---|---|---|---|---|---|
| P1 | not measured yet | | | | | |
| P2 | not measured yet | | | | | |
| P3 | not measured yet | | | | | |
| P4 | not measured yet | | | | | |
| P5 | not measured yet | | | | | |

### Sanity check of the evaluation script (not a robustness result)

The script was smoke-tested on the **52 existing selfies** (`gambar_percobaan/orang_1..3`,
all `bright`-ish, the same photos used for enrollment) against the re-enrolled profiles.
This proves the script runs and counts correctly; it is **not** evidence about dim light,
angles, glasses or masks, and it must not be quoted as such.

| Person | probes | usable | accepted | false accepts | multi face | no embedding | p50 ms |
|---|---|---|---|---|---|---|---|
| `orang_1` | 17 | 17 | 17 | 0 | 0 | 0 | 1083 |
| `orang_2` | 21 | 17 | 17 | 0 | 4 | 0 | 1023 |
| `orang_3` | 14 | 12 | 12 | 0 | 0 | 2 | 1086 |
| **all** | 52 | 46 | 46 | 0 | 4 | 2 | 1069 |

The 4 `multi face` rows are the known two-person photos from D-003 (correctly rejected),
and the 2 `no embedding` rows are frames where ArcFace found no face inside a valid YOLO
box. Lowest genuine score was 0.546 (orang_1) — above 0.5, but close enough that a worse
frame could fall below it; that is exactly what the `dim`/`angled` conditions must measure.

## Analysis commands

```bash
# main table, one row per person/condition plus an aggregate
python backend/scripts/robustness_eval.py \
    --images-dir robustness_captures \
    --embeddings-dir C:/attendance_robustness/data/embeddings \
    --person P1=<id> --person P2=<id> --person P3=<id> --person P4=<id> --person P5=<id> \
    --markdown --output docs/A/robustness_raw.md

# within-condition separability: only if each condition was enrolled as its own profile set
python backend/scripts/evaluate_threshold.py \
    --embeddings-dir C:/attendance_robustness/condition_profiles/<condition>/embeddings --markdown
```

`robustness_eval.py` answers "will this student be accepted in this condition?"
`evaluate_threshold.py` answers "do genuine and impostor scores still separate inside this
condition?" The first is the product question; the second is only a diagnostic.

## Decision rules (write the outcome in `docs/A/DECISIONS.md`)

1. **Pass** → record the numbers, note the weakest condition in the pilot plan, no config
   change.
2. **False accept** → stop and investigate before the pilot: inspect the pair, check whether
   profiles are contaminated, and only then consider a threshold change with new FAR/FRR
   evidence. Do not silently raise the threshold.
3. **Low accept in one condition** → in order: better capture guidance/retry copy (C's
   screen), then one condition sample added to enrollment (still ≤ 5 embeddings), then
   document the limitation. A global threshold drop is the last option and needs a D-entry.
4. **Mask accepted** → treat as a spoofing finding, not a success. It means occlusion is not
   protecting the system; record it for `docs/A/anti_spoofing.md` and the report's
   limitations.

## Known limits of this test

- 5 people is a small sample; it finds big effects, not small ones.
- One phone model and one room. A different front camera changes absolute scores.
- The mask condition has no acceptance target; the result is descriptive.
- The reference profile is `bright` only. That matches the pilot's enrollment plan, but it
  means "dim enrollment" is not tested here (it is a possible G7 follow-up).
- This is a **cooperative** test: participants want to be recognised. It does not measure
  spoofing (photo on a screen, video replay); that is out of scope for M2 and drafted in
  `docs/A/anti_spoofing.md`.
