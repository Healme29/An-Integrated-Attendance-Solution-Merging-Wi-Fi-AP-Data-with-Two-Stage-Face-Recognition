"""Bulk enroll experiment photos into the attendance system.

For each subfolder under --images-dir (e.g. gambar_percobaan/orang_1), this
script creates a student (unless the NIM already exists) and uploads every
image in that subfolder via POST /faces/enroll?student_id=<id>.

Requires the backend server to be running:

    uvicorn backend.main:app --reload

The first enroll request loads YOLOv8 + InsightFace models, so it can take
a while — --timeout controls how long each request may take.

Examples:
    # create students "orang_1/2/3" + enroll all their selfies
    python backend/scripts/bulk_enroll.py --base-url http://127.0.0.1:8000

    # dry run: only print what would happen
    python backend/scripts/bulk_enroll.py --dry-run

    # reuse existing students if the NIM already exists (idempotent re-run)
    python backend/scripts/bulk_enroll.py --reuse-existing
"""
import argparse
import sys
import time
from pathlib import Path

import httpx

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


def image_folders(images_dir: Path) -> list[Path]:
    return sorted(p for p in images_dir.iterdir() if p.is_dir())


def list_images(folder: Path) -> list[Path]:
    return sorted(f for f in folder.iterdir() if f.suffix.lower() in VALID_EXTENSIONS)


def get_student_by_nim(client: httpx.Client, base_url: str, nim: str):
    r = client.get(f"{base_url}/students/", params={"nim": nim})
    if r.status_code == 200 and r.json():
        return r.json()[0]
    return None


def ensure_student(client: httpx.Client, args, folder: Path, nim: str) -> tuple[int, bool]:
    """Return (student_id, reused_existing). Create student if allowed."""
    existing = get_student_by_nim(client, args.base_url, nim)
    if existing:
        if args.reuse_existing or not args.create_students:
            return existing["id"], True
        raise RuntimeError(f"NIM {nim} already exists (use --reuse-existing to reuse)")
    if not args.create_students:
        raise RuntimeError(f"student {nim} not found and --create-students is disabled")

    payload = {"name": args.name_template.format(folder=folder.name) if "{folder}" in args.name_template else folder.name,
               "nim": nim}
    if args.mac:
        payload["mac_address"] = args.mac
    r = client.post(f"{args.base_url}/students/", json=payload)
    if r.status_code == 200:
        return r.json()["id"], False
    # 400 = duplicate NIM (race) -> re-fetch if allowed
    if r.status_code == 400 and args.reuse_existing:
        dup = get_student_by_nim(client, args.base_url, nim)
        if dup:
            return dup["id"], True
    raise RuntimeError(f"create student failed: HTTP {r.status_code} {r.text[:200]}")


def enroll_image(client: httpx.Client, args, student_id: int, image: Path) -> tuple[bool, str]:
    mime = MIME.get(image.suffix.lower(), "application/octet-stream")
    try:
        with image.open("rb") as f:
            r = client.post(
                f"{args.base_url}/faces/enroll",
                params={"student_id": student_id},
                files={"file": (image.name, f.read(), mime)},
            )
    except httpx.HTTPError as e:
        return False, f"request error: {e}"
    if r.status_code == 200:
        data = r.json()
        return True, f"face_count={data.get('face_count')} total={data.get('total_embeddings')}"
    try:
        detail = r.json().get("detail", r.text[:200])
    except Exception:
        detail = r.text[:200]
    return False, f"HTTP {r.status_code}: {detail}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Bulk enroll photos for the threshold experiment")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL")
    parser.add_argument("--images-dir", type=Path, default=Path("gambar_percobaan"),
                        help="Folder whose subfolders contain the photos (default: gambar_percobaan)")
    parser.add_argument("--nim-prefix", default="202600",
                        help="Prefix for auto-generated NIMs (default: 202600)")
    parser.add_argument("--nim-start", type=int, default=1,
                        help="First index for auto NIMs (default: 1)")
    parser.add_argument("--name-template", default="{folder}",
                        help="Student name template; {folder} = subfolder name (default: {folder})")
    parser.add_argument("--mac", default="", help="Optional MAC address for every student")
    parser.add_argument("--max-per-student", type=int, default=5,
                        help="Stop enrolling a student after this many embeddings (default: 5)")
    parser.add_argument("--sleep", type=float, default=0.3, help="Pause between requests (seconds)")
    parser.add_argument("--timeout", type=float, default=600.0,
                        help="Per-request timeout in seconds (models load on first call)")
    parser.add_argument("--create-students", action="store_true",
                        help="POST /students/ for each subfolder (default: off)")
    parser.add_argument("--reuse-existing", action="store_true",
                        help="Reuse a student when its NIM already exists")
    parser.add_argument("--dry-run", action="store_true", help="Only print what would happen")
    args = parser.parse_args()

    if not args.images_dir.is_dir():
        print(f"Images dir not found: {args.images_dir}")
        return 1

    folders = image_folders(args.images_dir)
    if not folders:
        print(f"No subfolders found under {args.images_dir}")
        return 1

    nim = args.nim_start
    summary: list[tuple[str, int, int, list[str]]] = []

    with httpx.Client(timeout=args.timeout) as client:
        for folder in folders:
            images = list_images(folder)
            if not images:
                print(f"[skip] {folder.name}: no jpg/jpeg/png files")
                continue
            student_nim = f"{args.nim_prefix}{nim:04d}"
            nim += 1

            if not args.create_students and not args.reuse_existing:
                print(f"[skip] {folder.name}: --create-students is off and no NIM to reuse for this folder")
                # folder naming must encode the NIM for lookup; keep simple and require creation
                continue

            if args.dry_run:
                print(f"[dry] {folder.name}: student {student_nim}, {len(images)} image(s)")
                for img in images:
                    print(f"      would enroll {img.name}")
                summary.append((folder.name, -1, len(images), []))
                continue

            try:
                student_id, reused = ensure_student(client, args, folder, student_nim)
            except RuntimeError as e:
                print(f"[FAIL] {folder.name}: {e}")
                summary.append((folder.name, -1, 0, [str(e)]))
                continue

            ok, failed = 0, []
            total_embeddings = 0
            print(f"[enroll] {folder.name} -> student_id={student_id} "
                  f"(nim={student_nim}, {'reused' if reused else 'created'})")
            for img in images:
                if total_embeddings >= args.max_per_student:
                    print(f"         skip {img.name}: already at max {args.max_per_student} embeddings")
                    continue
                success, msg = enroll_image(client, args, student_id, img)
                if success:
                    ok += 1
                    # response includes total embeddings for this student
                    # (parsed inside enroll_image msg; approximate with ok count)
                else:
                    failed.append(f"{img.name}: {msg}")
                print(f"         {'OK  ' if success else 'FAIL'} {img.name}: {msg}")
                time.sleep(args.sleep)
            summary.append((folder.name, student_id, ok, failed))

    print("\n===== SUMMARY =====")
    if args.dry_run:
        print(f"Dry run: {len(folders)} folder(s) would be enrolled.")
    for name, sid, ok, failed in summary:
        if sid == -1:
            print(f"{name}: skipped/failed")
        else:
            print(f"{name}: student_id={sid}, {ok} image(s) enrolled, {len(failed)} failed")
            for fmsg in failed:
                print(f"    - {fmsg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())