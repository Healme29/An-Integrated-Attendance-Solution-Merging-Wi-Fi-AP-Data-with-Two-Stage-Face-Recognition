"""Benchmark the YOLOv8-face detector across confidence and image-size settings.

Runs every combination of --confs and --sizes over a folder of photos and reports,
per combination: how many images a face was found in (recall proxy), how many images
contain more than one *distinct* face (two real people, or detector duplicates), the
latency, and the detected face size in pixels.

Two boxes are treated as the same face when the intersection covers at least
--dedupe-iom of the smaller box (containment), which catches nested duplicate boxes
that plain IoU does not merge.

The production detector (backend/services/face_detection.py) reads
YOLO_CONF_THRESHOLD and YOLO_IMG_SIZE from config at import time, so this script calls
the YOLO model directly with explicit conf/imgsz values and leaves production code
untouched.

Examples:
    python backend/scripts/yolo_tuning.py --images gambar_percobaan --markdown
    python backend/scripts/yolo_tuning.py --images gambar_percobaan \
        --confs 0.25,0.30,0.35 --sizes 640,1280 --markdown

No server and no database are needed. The model weights must exist at
backend/data/models/yolov8m-face.pt.
"""
import argparse
import platform
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import YOLO_MODEL_PATH  # noqa: E402

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def collect_images(folders: list[Path]) -> list[Path]:
    """Return every image under the given folders (sorted, recursive)."""
    images: list[Path] = []
    for folder in folders:
        if not folder.exists():
            print(f"warning: folder not found, skipped: {folder}", file=sys.stderr)
            continue
        images.extend(
            path for path in sorted(folder.rglob("*")) if path.suffix.lower() in IMAGE_SUFFIXES
        )
    return images


def intersection_over_min(box_a: np.ndarray, box_b: np.ndarray) -> float:
    """Intersection area divided by the smaller box area (containment ratio)."""
    x1 = max(box_a[0], box_b[0])
    y1 = max(box_a[1], box_b[1])
    x2 = min(box_a[2], box_b[2])
    y2 = min(box_a[3], box_b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    smaller = min(area_a, area_b)
    return float(inter / smaller) if smaller > 0 else 0.0


def distinct_boxes(boxes: np.ndarray, confs: np.ndarray, iom_threshold: float) -> list[int]:
    """Indices of boxes that are not a duplicate of a higher-confidence box."""
    kept: list[int] = []
    for index in np.argsort(-confs):
        if all(intersection_over_min(boxes[index], boxes[other]) < iom_threshold for other in kept):
            kept.append(int(index))
    return kept


def benchmark_config(
    model,
    images: list[Path],
    conf: float,
    imgsz: int,
    dedupe_iom: float,
) -> dict:
    """Run one (conf, imgsz) combination and return its statistics."""
    warmup = np.zeros((480, 640, 3), dtype=np.uint8)
    model(warmup, conf=conf, imgsz=imgsz, verbose=False)

    latencies: list[float] = []
    raw_per_image: list[int] = []
    distinct_per_image: list[int] = []
    top_confidences: list[float] = []
    top_heights: list[float] = []
    unreadable = 0

    for path in images:
        image = cv2.imread(str(path))
        if image is None:
            unreadable += 1
            continue

        started = time.perf_counter()
        results = model(image, conf=conf, imgsz=imgsz, verbose=False)
        latencies.append((time.perf_counter() - started) * 1000.0)

        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            raw_per_image.append(0)
            distinct_per_image.append(0)
            continue

        xyxy = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        kept = distinct_boxes(xyxy, confs, dedupe_iom)

        raw_per_image.append(len(xyxy))
        distinct_per_image.append(len(kept))

        best = max(kept, key=lambda index: float(confs[index]))
        top_confidences.append(float(confs[best]))
        top_heights.append(float(xyxy[best][3] - xyxy[best][1]))

    total = len(distinct_per_image)
    if total == 0:
        return {"conf": conf, "imgsz": imgsz, "total": 0, "unreadable": unreadable}

    found = sum(1 for count in distinct_per_image if count >= 1)
    one_face = sum(1 for count in distinct_per_image if count == 1)
    many_faces = sum(1 for count in distinct_per_image if count > 1)
    duplicates = sum(raw - distinct for raw, distinct in zip(raw_per_image, distinct_per_image))

    return {
        "conf": conf,
        "imgsz": imgsz,
        "total": total,
        "unreadable": unreadable,
        "found": found,
        "one_face": one_face,
        "many_faces": many_faces,
        "duplicates": duplicates,
        "found_pct": 100.0 * found / total,
        "median_ms": float(np.median(latencies)),
        "p95_ms": float(np.percentile(latencies, 95)),
        "median_face_px": float(np.median(top_heights)) if top_heights else 0.0,
        "mean_confidence": float(np.mean(top_confidences)) if top_confidences else 0.0,
    }


def format_table(rows: list[dict]) -> str:
    """Render the benchmark rows as a markdown table."""
    header = (
        "| conf | imgsz | faces found | one distinct face | more than one | duplicate boxes | "
        "median ms | p95 ms | median face height px | mean confidence |\n"
        "|------|-------|-------------|-------------------|---------------|-----------------|"
        "-----------|--------|------------------------|------------------|"
    )
    body = []
    for row in rows:
        if row["total"] == 0:
            body.append(
                f"| {row['conf']} | {row['imgsz']} | no readable images | - | - | - | - | - | - | - |"
            )
            continue
        body.append(
            "| {conf} | {imgsz} | {found_pct:.1f}% ({found}/{total}) | {one_face}/{total} | "
            "{many_faces} | {duplicates} | {median_ms:.0f} | {p95_ms:.0f} | "
            "{median_face_px:.0f} | {mean_confidence:.3f} |".format(**row)
        )
    return header + "\n" + "\n".join(body)


def format_environment(images: list[Path], folders: Counter) -> str:
    """Render the environment block that makes the numbers reproducible."""
    import torch
    import ultralytics

    model_mb = YOLO_MODEL_PATH.stat().st_size / (1024 * 1024) if YOLO_MODEL_PATH.exists() else 0.0
    folder_lines = "\n".join(f"- `{name}`: {count} images" for name, count in sorted(folders.items()))
    return (
        f"- Measured: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"- Model: `{YOLO_MODEL_PATH.name}` ({model_mb:.1f} MB)\n"
        f"- Total images: {len(images)}\n"
        f"{folder_lines}\n"
        f"- Versions: ultralytics {ultralytics.__version__}, torch {torch.__version__}, "
        f"numpy {np.__version__}, opencv {cv2.__version__}\n"
        f"- Machine: {platform.system()} {platform.release()}, "
        f"{platform.processor() or 'unknown CPU'}, torch threads: {torch.get_num_threads()}"
    )


def parse_floats(raw: str) -> list[float]:
    return [float(value) for value in raw.split(",") if value.strip()]


def parse_ints(raw: str) -> list[int]:
    return [int(value) for value in raw.split(",") if value.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--images",
        action="append",
        required=True,
        help="Folder with test photos (repeatable). Recursive.",
    )
    parser.add_argument("--confs", default="0.25,0.30,0.35", help="Comma-separated confidence values")
    parser.add_argument("--sizes", default="640,1280", help="Comma-separated inference image sizes")
    parser.add_argument(
        "--dedupe-iom",
        type=float,
        default=0.6,
        help="Boxes overlapping this fraction of the smaller box count as the same face",
    )
    parser.add_argument("--output", type=Path, help="Write the markdown report to this file")
    parser.add_argument("--markdown", action="store_true", help="Print the markdown report")
    args = parser.parse_args()

    if not YOLO_MODEL_PATH.exists():
        print(f"error: model weights not found at {YOLO_MODEL_PATH}", file=sys.stderr)
        return 1

    folders = [Path(folder) for folder in args.images]
    images = collect_images(folders)
    if not images:
        print("error: no images found in the given folders", file=sys.stderr)
        return 1

    per_folder = Counter(path.parent.name for path in images)

    from ultralytics import YOLO

    model = YOLO(str(YOLO_MODEL_PATH))
    confs = parse_floats(args.confs)
    sizes = parse_ints(args.sizes)

    rows: list[dict] = []
    for imgsz in sizes:
        for conf in confs:
            row = benchmark_config(model, images, conf, imgsz, args.dedupe_iom)
            rows.append(row)
            if row["total"]:
                print(
                    f"conf={conf:.2f} imgsz={imgsz}: found {row['found_pct']:.1f}% "
                    f"({row['found']}/{row['total']}), one face {row['one_face']}, "
                    f"many {row['many_faces']}, duplicates {row['duplicates']}, "
                    f"median {row['median_ms']:.0f} ms, p95 {row['p95_ms']:.0f} ms",
                    file=sys.stderr,
                )

    report = (
        "## Measured results\n\n"
        + format_table(rows)
        + "\n\n## Measurement environment\n\n"
        + format_environment(images, per_folder)
        + f"\n- Duplicate detection: intersection-over-minimum-area >= {args.dedupe_iom}\n"
    )

    if args.markdown or not args.output:
        print(report)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"report written to {args.output}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
