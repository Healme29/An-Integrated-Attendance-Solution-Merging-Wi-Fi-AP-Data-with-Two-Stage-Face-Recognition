# YOLOv8-face tuning — confidence and input size

> Deliverable for M2 stage 2 (gate **G3**). Owner: A.
> Measured on the real photos stored in this repository, not estimated.
> Reproduce with the command at the bottom.

## Question

The service ran with `YOLO_CONF_THRESHOLD=0.25` and `YOLO_IMG_SIZE=1280` by default
(`backend/config.py`) when this measurement was taken. Nobody had measured what those two
numbers cost or buy. Two questions:

1. Does raising the confidence threshold lose faces?
2. What does `imgsz=1280` buy compared with `imgsz=640`, and what does it cost in latency?

## Method

- Script: `backend/scripts/yolo_tuning.py` (calls the YOLO model directly with explicit
  `conf`/`imgsz`, so production code and its config import are untouched).
- Dataset: **52 original photos** in `gambar_percobaan/orang_1` (17), `orang_2` (21),
  `orang_3` (14) — phone selfies of the three enrolled students, several of them taken
  with a second person in frame.
- Grid: `conf` in {0.25, 0.30, 0.35} × `imgsz` in {640, 1280} = 6 combinations.
- One warm-up inference per combination is discarded. Every image is decoded once per
  combination and the inference call is timed with `perf_counter`.
- "Faces found" = images where at least one face survived. This is a **recall proxy**, not
  true recall: the photos are not labelled and every photo is known to contain at least one
  face, so the only failure this can detect is "no face at all".
- "Duplicate boxes" = boxes removed because they overlap at least 60% of the smaller box
  (intersection-over-minimum-area). Plain IoU misses nested boxes; this rule catches them.

## Measured results (52 original photos)

| conf | imgsz | faces found | one distinct face | more than one | duplicate boxes | median ms | p95 ms | median face height px | mean confidence |
|------|-------|-------------|-------------------|---------------|-----------------|-----------|--------|------------------------|------------------|
| 0.25 | 640 | 100.0% (52/52) | 45/52 | 7 | 0 | 481 | 618 | 594 | 0.893 |
| 0.30 | 640 | 100.0% (52/52) | 45/52 | 7 | 0 | 492 | 599 | 594 | 0.893 |
| 0.35 | 640 | 100.0% (52/52) | 45/52 | 7 | 0 | 465 | 566 | 594 | 0.893 |
| 0.25 | 1280 | 100.0% (52/52) | 44/52 | 8 | 1 | 1816 | 1985 | 582 | 0.889 |
| 0.30 | 1280 | 100.0% (52/52) | 44/52 | 8 | 0 | 1857 | 2046 | 582 | 0.889 |
| 0.35 | 1280 | 100.0% (52/52) | 44/52 | 8 | 0 | 1789 | 1952 | 582 | 0.889 |

Environment: Windows 10, Intel64 Family 6 Model 140 (CPU only),
ultralytics 8.2.100, torch 2.14.0+cpu, numpy 1.26.4, opencv 4.12.0,
`yolov8m-face.pt` (49.6 MB), torch threads 7.

## Side measurement — the 15 stored enrolled crops

`backend/data/faces/` holds the crops saved during enrollment. Those are small images
(208–598 px wide). Running the detector on them gave the same detection rate, but the box
count behaved differently:

| imgsz | images with more than one box | explanation |
|-------|-------------------------------|-------------|
| 640 | 0/15 | one box per crop |
| 1280 | **15/15** | nested duplicate boxes on the same face (max IoU 0.5–0.70, containment ≈ 1.0) |

Upscaling a 208 px crop to 1280 px makes the model emit several nested boxes for the same
face. Plain NMS at IoU 0.7 does not merge them, so `detect_faces()` returns 2–3 boxes for
one person.

## Findings

1. **The confidence threshold changes nothing on this dataset.** 0.25, 0.30 and 0.35
   detect exactly the same faces. The faces here are close-up and well lit (mean confidence
   0.89), so the threshold is far from being the limiting factor. Lower confidence is still
   the safer direction for classroom photos, where faces are smaller and dimmer.
2. **`imgsz=1280` is 3.8× slower for no recall gain.** Median 1816 ms vs 481 ms, p95
   1985 ms vs 618 ms, identical 52/52 detection, and the detected face size is nearly the
   same (582 px vs 594 px, −2%). On this CPU a single check-in spends ~1.8 s in detection
   alone at 1280.
3. **`imgsz=1280` creates nested duplicate boxes on small images.** Measured on 15/15
   already-cropped enrollment inputs. On the 52 original photos this was rare: 1 duplicate
   box in 1 image, so the slot-burn risk was mostly limited to cropped inputs, not to normal
   selfies. It still mattered because `POST /faces/enroll` used to loop over **every**
   detected face and store one embedding per box (`backend/routers/faces.py`), so any
   duplicate could consume several of the 5 allowed embedding slots with the same face.
   **Status: fixed on 2026-11-01** — detector output is deduplicated and enrollment stores
   exactly one face.
4. **7 of the 52 photos genuinely contain two people** (6 in `orang_2`, 1 in `orang_3`).
   This is not a detector error — but it exposed a separate risk: enrollment accepted every
   face in the image, so a student who enrolled with a friend in frame stored the friend's
   face in their own profile. **Status: fixed on 2026-11-01** — enrollment now rejects a
   second significant face; see D-003.
5. The one extra "distinct face" at 1280 (8 vs 7) is a face found at higher resolution
   only. At this dataset size it cannot be classified as a true distant face or as a false
   positive without labels.

## Recommendation (to be locked as `G3`)

| Setting | Value | Reason |
|---------|-------|--------|
| `YOLO_CONF_THRESHOLD` | **0.25** | No recall difference in the 0.25–0.35 band; keep the value that maximises recall for distant or dim classroom faces |
| `YOLO_IMG_SIZE` | **640** for check-in and enrollment | Identical detection on all 52 photos, 3.8× lower latency, and no duplicate boxes on small inputs |

Set it as the `config.py` default (`YOLO_IMG_SIZE=640`) and keep the env override for the
pilot machine. The default was 1280 when this was measured; the owner approved the flip on
2026-11-01 after reviewing the table above. Gate G7 still re-measures 640 vs 1280 on
classroom-distance photos before the pilot — a 640 default is not a claim that 640 is right
for faces 30–80 px tall, only that 1280 is not paying for itself on selfies.

## Known limits of this measurement

- 52 photos, 3 people, all close-up selfies from one phone class of device.
- No labelled ground truth, so "recall" is only "at least one face found".
- CPU-only machine; a GPU or a different CPU changes the absolute latencies (the ratio
  between 640 and 1280 is the portable result).
- No ArcFace/recognition accuracy test here — that belongs to the robustness stage, because
  detection quality only matters through the embedding it feeds.
- Classroom distances (faces 30–80 px tall at the back of a room) are **not** represented;
  this is exactly what gate G7 must re-measure before the pilot.

## Follow-ups created by this measurement

| # | Item | Owner | When |
|---|------|-------|------|
| 1 | Re-run this benchmark on classroom photos (distant faces) and decide whether enrollment needs a different `imgsz` than check-in | A | G7, before the pilot |
| 2 | ~~Deduplicate detector output (merge nested boxes) or enroll only the largest face, so one photo cannot consume several embedding slots~~ **Done 2026-11-01** (D-003: dedupe + single-face enrollment) | A | closed |
| 3 | Confirm `YOLO_IMG_SIZE=640` (now the code default) on the demo/pilot machine and record it in the runbook | B (with A) | G1/G8 |

## Reproduction

```bash
python backend/scripts/yolo_tuning.py --images gambar_percobaan --markdown
python backend/scripts/yolo_tuning.py --images backend/data/faces --sizes 640,1280 --markdown
```
