"""Measure recognition robustness per capture condition against enrolled profiles.

Protocol: `docs/A/robustness_test.md`. Folder layout expected under `--images-dir`:

    robustness_captures/<person>/<condition>/*.jpg

`<person>` is an anonymous label (P1, P2, ...) mapped to an enrolled student id with
`--person P1=8`. A person folder that contains photos directly (no condition subfolder)
is reported under the condition name `unlabelled`.

Every probe goes through the same path as `POST /attendance/check`: YOLO detection ->
duplicate-box merge -> tiny-face filter -> multi-face rejection -> ArcFace embedding ->
max cosine similarity against that student's stored embeddings. The script reports, per
condition:

- detection: a usable single face was found;
- accepted: the correct person's top-1 score is >= the threshold;
- rejected: a face was found but the score is below the threshold (false reject);
- false accept: a different enrolled person scores >= the threshold;
- no face / multi face / no embedding: the policy outcomes of the check-in path.

Requires the ML models (`yolov8m-face.pt`, InsightFace `buffalo_l`); use a machine that
already runs the backend. Run it on a copy of the embeddings when it must not touch
production data.

Examples:
    # all persons, all conditions, markdown table for the report
    python backend/scripts/robustness_eval.py \
        --images-dir robustness_captures \
        --person P1=8 --person P2=9 --person P3=11 --markdown

    # one condition only
    python backend/scripts/robustness_eval.py --conditions dim,angled --markdown
"""
import argparse
import pickle
import statistics
import sys
import time
from pathlib import Path

import cv2
import numpy as np

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from config import (  # noqa: E402
    EMBEDDINGS_DIR,
    FACE_SIMILARITY_THRESHOLD,
    MIN_FACE_BBOX_PX,
)
from services.face_detection import (  # noqa: E402
    dedupe_faces,
    detect_faces_from_bytes,
    distinct_people,
)
from services.face_recognition import compare_faces, get_embedding  # noqa: E402

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png"}
NO_FACE = "no_face"
MULTI_FACE = "multi_face"
NO_EMBEDDING = "no_embedding"
ACCEPTED = "accepted"
REJECTED = "rejected"
FALSE_ACCEPT = "false_accept"


def load_profiles(embeddings_dir: Path, person_map: dict[str, int]) -> dict[str, list]:
    profiles: dict[str, list] = {}
    for label, student_id in person_map.items():
        pickle_path = embeddings_dir / f"student_{student_id}.pkl"
        if not pickle_path.exists():
            raise SystemExit(f"no embeddings for {label} (student {student_id}): {pickle_path}")
        with pickle_path.open("rb") as handle:
            embeddings = pickle.load(handle)
        if not embeddings:
            raise SystemExit(f"empty embeddings for {label} (student {student_id})")
        profiles[label] = embeddings
    return profiles


def person_conditions(person_dir: Path) -> list[tuple[str, Path]]:
    """Return (condition, folder) pairs; images directly in person_dir => unlabelled."""
    subdirs = sorted(p for p in person_dir.iterdir() if p.is_dir())
    if subdirs:
        return [(subdir.name, subdir) for subdir in subdirs]
    return [("unlabelled", person_dir)]


def list_images(folder: Path) -> list[Path]:
    return sorted(f for f in folder.iterdir() if f.suffix.lower() in VALID_EXTENSIONS)


def evaluate_image(path: Path, profiles: dict[str, list], person: str,
                   threshold: float) -> dict:
    """Classify one probe photo exactly like the check-in path."""
    started = time.perf_counter()
    raw = path.read_bytes()
    detected = detect_faces_from_bytes(raw)
    faces = [
        face for face in dedupe_faces(detected)
        if (face["bbox"][2] - face["bbox"][0]) >= MIN_FACE_BBOX_PX
        and (face["bbox"][3] - face["bbox"][1]) >= MIN_FACE_BBOX_PX
    ]
    image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    result = {"image": path.name, "outcome": None, "score": None,
              "top1": None, "latency_ms": None}

    if not faces:
        result["outcome"] = NO_FACE
        result["latency_ms"] = (time.perf_counter() - started) * 1000
        return result
    people = distinct_people(faces)
    if len(people) > 1:
        result["outcome"] = MULTI_FACE
        result["latency_ms"] = (time.perf_counter() - started) * 1000
        return result

    embedding = get_embedding(image, people[0]["bbox"])
    if embedding is None:
        result["outcome"] = NO_EMBEDDING
        result["latency_ms"] = (time.perf_counter() - started) * 1000
        return result

    scores = {}
    for label, stored in profiles.items():
        _, score = compare_faces(embedding, stored)
        scores[label] = score
    top1 = max(scores, key=scores.get)
    result["score"] = scores[person]
    result["top1"] = top1
    result["latency_ms"] = (time.perf_counter() - started) * 1000

    if top1 != person and scores[top1] >= threshold:
        result["outcome"] = FALSE_ACCEPT
        result["top1_score"] = scores[top1]
    elif scores[person] >= threshold:
        result["outcome"] = ACCEPTED
    else:
        result["outcome"] = REJECTED
    return result


def summarize(rows: list[dict]) -> dict:
    total = len(rows)
    counts = {
        outcome: sum(1 for row in rows if row["outcome"] == outcome)
        for outcome in (ACCEPTED, REJECTED, FALSE_ACCEPT, NO_FACE, MULTI_FACE, NO_EMBEDDING)
    }
    usable = total - counts[NO_FACE] - counts[MULTI_FACE] - counts[NO_EMBEDDING]
    genuine = [row["score"] for row in rows if row["score"] is not None]
    latencies = [row["latency_ms"] for row in rows if row["latency_ms"] is not None]
    return {
        "total": total,
        "usable": usable,
        **counts,
        "accept_rate": counts[ACCEPTED] / usable if usable else 0.0,
        "false_accept_rate": counts[FALSE_ACCEPT] / usable if usable else 0.0,
        "detection_rate": usable / total if total else 0.0,
        "genuine_min": min(genuine) if genuine else None,
        "genuine_mean": statistics.fmean(genuine) if genuine else None,
        "p50_ms": statistics.median(latencies) if latencies else None,
        "p95_ms": (sorted(latencies)[max(0, int(round(0.95 * (len(latencies) - 1))))]
                   if latencies else None),
    }


def format_summary(label: str, condition: str, summary: dict) -> str:
    def pct(value):
        return f"{value * 100:.0f}%" if value is not None else "-"

    def num(value, digits=3):
        return f"{value:.{digits}f}" if value is not None else "-"

    return (
        f"{label:>6} | {condition:<12} | {summary['total']:>3} | {summary['usable']:>3} | "
        f"{summary['accepted']:>3} | {summary['rejected']:>3} | {summary['false_accept']:>3} | "
        f"{summary['no_face']:>3} | {summary['multi_face']:>3} | "
        f"{summary['no_embedding']:>4} | "
        f"{pct(summary['detection_rate']):>5} | {pct(summary['accept_rate']):>7} | "
        f"{pct(summary['false_accept_rate']):>6} | "
        f"{num(summary['genuine_min'])} | {num(summary['genuine_mean'])} | "
        f"{num(summary['p50_ms'], 0):>7} | {num(summary['p95_ms'], 0):>8}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Robustness evaluation per capture condition")
    parser.add_argument("--images-dir", type=Path, default=Path("robustness_captures"),
                        help="Root folder: <person>/<condition>/*.jpg")
    parser.add_argument("--embeddings-dir", type=Path, default=EMBEDDINGS_DIR,
                        help="Directory holding student_<id>.pkl profiles")
    parser.add_argument("--person", action="append", required=True, metavar="LABEL=ID",
                        help="Map an anonymous person label to an enrolled student id")
    parser.add_argument("--conditions", default="",
                        help="Comma-separated condition names to include (default: all)")
    parser.add_argument("--threshold", type=float, default=FACE_SIMILARITY_THRESHOLD,
                        help=f"Similarity threshold (default: {FACE_SIMILARITY_THRESHOLD})")
    parser.add_argument("--markdown", action="store_true", help="Print a markdown table")
    parser.add_argument("--output", type=Path, default=None, help="Also write the report here")
    args = parser.parse_args()

    if not args.images_dir.is_dir():
        raise SystemExit(f"images dir not found: {args.images_dir}")

    person_map = {}
    for value in args.person:
        if "=" not in value:
            raise SystemExit(f"--person expects LABEL=ID, got {value!r}")
        label, raw_id = value.split("=", 1)
        person_map[label] = int(raw_id)

    allowed = {name.strip() for name in args.conditions.split(",") if name.strip()}
    profiles = load_profiles(args.embeddings_dir, person_map)

    rows_by_key: dict[tuple[str, str], list[dict]] = {}
    missing_people = []
    for label in person_map:
        person_dir = args.images_dir / label
        if not person_dir.is_dir():
            missing_people.append(label)
            continue
        for condition, folder in person_conditions(person_dir):
            if allowed and condition not in allowed:
                continue
            images = list_images(folder)
            if not images:
                continue
            rows = [evaluate_image(image, profiles, label, args.threshold) for image in images]
            rows_by_key[(label, condition)] = rows
            print(f"[scan] {label}/{condition}: {len(rows)} image(s)", file=sys.stderr)

    if missing_people:
        print(f"[warn] no folder for: {', '.join(missing_people)}", file=sys.stderr)
    if not rows_by_key:
        raise SystemExit("no probe images found")

    header = (
        "person | condition    |  n | ok | acc | rej | far | no | mul | nemb |   det |  accept | "
        "farate | gen_min | gen_mean |   p50ms |    p95ms"
    )
    lines = [header, "-" * len(header)]
    condition_totals: dict[str, list[dict]] = {}
    for (label, condition), rows in sorted(rows_by_key.items()):
        lines.append(format_summary(label, condition, summarize(rows)))
        condition_totals.setdefault(condition, []).extend(rows)

    lines.append("")
    lines.append("Per-condition aggregate (all mapped persons):")
    lines.append(header)
    lines.append("-" * len(header))
    for condition, rows in sorted(condition_totals.items()):
        lines.append(format_summary("ALL", condition, summarize(rows)))

    report = "\n".join(lines)
    if args.markdown:
        report = "```\n" + report + "\n```"
    print(report)
    if args.output:
        args.output.write_text(report + "\n", encoding="utf-8")
        print(f"[written] {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
