"""Re-enroll demo students using only photos that contain one person.

Profiles enrolled before 2026-11-01 may contain a friend's embedding: the old
`POST /faces/enroll` stored every face in the frame (see D-003). This script
rebuilds a profile from scratch so that each stored embedding provably came
from a single-person photo:

1. **Scan** every photo in a folder with the same detector path the API uses
   (`detect_faces_from_bytes` -> `dedupe_faces` -> tiny-face filter ->
   `distinct_people`) and classify it as `single`, `multi` or `none`.
2. **Reset** (optional, `--reset --yes`) the student's `faces` rows, pickle and
   crop files, so nothing from the old profile survives.
3. **Enroll** the `single` photos through the running API, up to
   `--max-per-student`, exactly like a phone would.
4. **Verify** the stored row/pickle counts and print before/after numbers.

Back up `backend/attendance.db`, `backend/data/embeddings/` and
`backend/data/faces/` before running with `--reset`; the script does not back
up for you.

Requires the backend server to be running (the first enroll request loads the
ML models):

    uvicorn backend.main:app --port 8010

Examples:
    # look before touching anything
    python backend/scripts/reenroll_clean.py \
        --student orang_1=8 --student orang_2=9 --student orang_3=11 --dry-run

    # rebuild all three demo profiles
    python backend/scripts/reenroll_clean.py \
        --base-url http://127.0.0.1:8010 \
        --student orang_1=8 --student orang_2=9 --student orang_3=11 \
        --reset --yes
"""
import argparse
import pickle
import sqlite3
import sys
import time
from pathlib import Path

import httpx

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from config import (  # noqa: E402
    DATA_DIR,
    DATABASE_PATH,
    MAX_EMBEDDINGS_PER_STUDENT,
    MIN_FACE_BBOX_PX,
    YOLO_CONF_THRESHOLD,
    YOLO_IMG_SIZE,
)
from services.face_detection import (  # noqa: E402
    bbox_area,
    dedupe_faces,
    detect_faces_from_bytes,
    distinct_people,
)

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
FACES_DIR = DATA_DIR / "faces"


def parse_student_args(values: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit(f"--student expects folder=id, got {value!r}")
        folder, raw_id = value.split("=", 1)
        try:
            mapping[folder] = int(raw_id)
        except ValueError:
            raise SystemExit(f"--student id must be an integer, got {raw_id!r}")
    return mapping


def filter_tiny(faces: list[dict]) -> list[dict]:
    return [
        face for face in faces
        if (face["bbox"][2] - face["bbox"][0]) >= MIN_FACE_BBOX_PX
        and (face["bbox"][3] - face["bbox"][1]) >= MIN_FACE_BBOX_PX
    ]


def classify_photo(path: Path) -> dict:
    """Return {kind, boxes, ratio, error} for one photo, mirroring the API."""
    try:
        detected = detect_faces_from_bytes(path.read_bytes())
    except Exception as exc:  # noqa: BLE001 - report and keep scanning
        return {"kind": "error", "boxes": 0, "ratio": None, "error": str(exc)}
    faces = filter_tiny(dedupe_faces(detected))
    if not faces:
        return {"kind": "none", "boxes": len(detected), "ratio": None, "error": None}
    people = distinct_people(faces)
    if len(people) > 1:
        second_ratio = bbox_area(people[1]["bbox"]) / bbox_area(people[0]["bbox"])
        return {"kind": "multi", "boxes": len(detected), "ratio": second_ratio, "error": None}
    return {"kind": "single", "boxes": len(detected), "ratio": None, "error": None}


def list_images(folder: Path) -> list[Path]:
    return sorted(f for f in folder.iterdir() if f.suffix.lower() in VALID_EXTENSIONS)


def profile_counts(student_id: int) -> dict:
    """Read the stored profile (SQLite rows + pickle) for one student."""
    rows, crops = 0, 0
    if DATABASE_PATH.exists():
        connection = sqlite3.connect(DATABASE_PATH)
        try:
            rows = connection.execute(
                "SELECT COUNT(*) FROM faces WHERE student_id = ?", (student_id,)
            ).fetchone()[0]
        finally:
            connection.close()
    pickle_path = EMBEDDINGS_DIR / f"student_{student_id}.pkl"
    stored = 0
    if pickle_path.exists():
        try:
            with pickle_path.open("rb") as handle:
                stored = len(pickle.load(handle))
        except Exception:  # noqa: BLE001 - unreadable pickle counts as unknown
            stored = -1
    if FACES_DIR.exists():
        crops = len(list(FACES_DIR.glob(f"student_{student_id}_*.jpg")))
    return {"rows": rows, "pickle": stored, "crops": crops}


def reset_profile(student_id: int, dry_run: bool) -> dict:
    """Delete faces rows, pickle and crops for one student."""
    before = profile_counts(student_id)
    pickle_path = EMBEDDINGS_DIR / f"student_{student_id}.pkl"
    crops = list(FACES_DIR.glob(f"student_{student_id}_*.jpg")) if FACES_DIR.exists() else []
    if dry_run:
        return before
    if DATABASE_PATH.exists():
        connection = sqlite3.connect(DATABASE_PATH)
        try:
            connection.execute("DELETE FROM faces WHERE student_id = ?", (student_id,))
            connection.commit()
        finally:
            connection.close()
    if pickle_path.exists():
        pickle_path.unlink()
    for crop in crops:
        crop.unlink()
    after = profile_counts(student_id)
    if after["rows"] or after["pickle"] or after["crops"]:
        raise RuntimeError(f"reset incomplete for student {student_id}: {after}")
    return before


def enroll_image(client: httpx.Client, base_url: str, student_id: int, image: Path) -> tuple[bool, str]:
    mime = MIME.get(image.suffix.lower(), "application/octet-stream")
    with image.open("rb") as handle:
        payload = handle.read()
    try:
        response = client.post(
            f"{base_url}/faces/enroll",
            params={"student_id": student_id},
            files={"file": (image.name, payload, mime)},
        )
    except httpx.HTTPError as exc:
        return False, f"request error: {exc}"
    if response.status_code == 200:
        data = response.json()
        return True, f"total_embeddings={data.get('total_embeddings')}"
    try:
        detail = response.json().get("detail", response.text[:200])
    except Exception:  # noqa: BLE001 - non-JSON error body
        detail = response.text[:200]
    return False, f"HTTP {response.status_code}: {detail}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reset and re-enroll student profiles using single-person photos only"
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL")
    parser.add_argument("--images-dir", type=Path, default=Path("gambar_percobaan"),
                        help="Folder whose subfolders contain the photos")
    parser.add_argument("--student", action="append", required=True, metavar="FOLDER=ID",
                        help="Map a subfolder to a student id (repeatable)")
    parser.add_argument("--max-per-student", type=int, default=MAX_EMBEDDINGS_PER_STUDENT,
                        help=f"Embeddings to enroll per student (default: {MAX_EMBEDDINGS_PER_STUDENT})")
    parser.add_argument("--reset", action="store_true",
                        help="Delete existing rows/pickle/crops before enrolling (needs --yes)")
    parser.add_argument("--yes", action="store_true", help="Confirm --reset without prompting")
    parser.add_argument("--skip-enroll", action="store_true", help="Scan and reset only")
    parser.add_argument("--sleep", type=float, default=0.3, help="Pause between uploads (seconds)")
    parser.add_argument("--timeout", type=float, default=600.0,
                        help="Per-request timeout (models load on the first call)")
    parser.add_argument("--dry-run", action="store_true", help="Scan only, change nothing")
    args = parser.parse_args()

    if args.reset and not args.yes and not args.dry_run:
        raise SystemExit("--reset deletes faces rows, pickles and crops; pass --yes to confirm")

    mapping = parse_student_args(args.student)
    missing = [folder for folder in mapping if not (args.images_dir / folder).is_dir()]
    if missing:
        raise SystemExit(f"folder(s) not found under {args.images_dir}: {', '.join(missing)}")

    print(f"Detector settings (this process): imgsz={YOLO_IMG_SIZE}, "
          f"conf={YOLO_CONF_THRESHOLD}, min_bbox_px={MIN_FACE_BBOX_PX}, "
          f"max_embeddings={args.max_per_student}")
    print(f"Database: {DATABASE_PATH}")

    scan: dict[str, dict] = {}
    for folder, student_id in mapping.items():
        images = list_images(args.images_dir / folder)
        results = {image: classify_photo(image) for image in images}
        singles = [image for image, result in results.items() if result["kind"] == "single"]
        multi = [image for image, result in results.items() if result["kind"] == "multi"]
        none = [image for image, result in results.items() if result["kind"] == "none"]
        errors = [image for image, result in results.items() if result["kind"] == "error"]
        scan[folder] = {"student_id": student_id, "results": results, "singles": singles}
        print(f"\n[{folder}] student_id={student_id} photos={len(images)} "
              f"single={len(singles)} multi={len(multi)} none={len(none)} error={len(errors)}")
        for image in multi:
            print(f"    multi  {image.name}  second_face_ratio={results[image]['ratio']:.3f}")
        for image in none:
            print(f"    none   {image.name}  raw_boxes={results[image]['boxes']}")
        for image in errors:
            print(f"    error  {image.name}  {results[image]['error']}")
        print(f"    usable for enrollment ({len(singles)}): "
              f"{', '.join(image.name for image in singles[:args.max_per_student])}"
              f"{' ...' if len(singles) > args.max_per_student else ''}")

    if args.dry_run:
        print("\n[dry] no rows, pickles, crops or embeddings were changed")
        return 0

    client = httpx.Client(timeout=args.timeout)
    try:
        try:
            health = client.get(f"{args.base_url}/health")
            if health.status_code != 200:
                print(f"\n[WARN] /health returned HTTP {health.status_code}: {health.text[:200]}")
        except httpx.HTTPError as exc:
            raise SystemExit(f"backend is not reachable at {args.base_url}: {exc}")

        before = {folder: profile_counts(data["student_id"]) for folder, data in scan.items()}

        if args.reset:
            print("\n===== RESET =====")
            for folder, data in scan.items():
                old = reset_profile(data["student_id"], dry_run=False)
                print(f"[{folder}] student {data['student_id']}: removed rows={old['rows']} "
                      f"pickle={old['pickle']} crops={old['crops']}")

        if args.skip_enroll:
            print("\n[skip] --skip-enroll set, stopping after reset")
            return 0

        print("\n===== ENROLL =====")
        for folder, data in scan.items():
            student_id = data["student_id"]
            enrolled, rejected = 0, []
            print(f"[{folder}] student_id={student_id}")
            for image in data["singles"]:
                if enrolled >= args.max_per_student:
                    break
                success, message = enroll_image(client, args.base_url, student_id, image)
                if success:
                    enrolled += 1
                else:
                    rejected.append(f"{image.name}: {message}")
                print(f"    {'OK  ' if success else 'FAIL'} {image.name}: {message}")
                time.sleep(args.sleep)
            data["enrolled"], data["rejected"] = enrolled, rejected

        print("\n===== VERIFY =====")
        for folder, data in scan.items():
            student_id = data["student_id"]
            after = profile_counts(student_id)
            print(f"[{folder}] student {student_id}: before={before[folder]} -> after={after} "
                  f"(enrolled={data.get('enrolled', 0)}, "
                  f"usable_photos={len(data['singles'])})")
            for message in data.get("rejected", []):
                print(f"    rejected {message}")
            if after["rows"] != after["pickle"] or after["rows"] != after["crops"]:
                print("    [WARN] rows, pickle length and crop count disagree")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
