import cv2
import numpy as np
from pathlib import Path
from ultralytics import YOLO
from config import (
    YOLO_MODEL_PATH,
    YOLO_CONF_THRESHOLD,
    YOLO_IMG_SIZE,
    FACE_DUPLICATE_IO_MIN,
    MULTIPLE_FACES_MIN_RELATIVE_AREA,
)


_detector: YOLO = None


def get_detector() -> YOLO:
    global _detector
    if _detector is None:
        if not YOLO_MODEL_PATH.exists():
            raise FileNotFoundError(
                f"YOLOv8-face model not found at {YOLO_MODEL_PATH}. "
                "Download from: https://github.com/YapaLab/yolo-face/releases"
            )
        _detector = YOLO(str(YOLO_MODEL_PATH))
    return _detector


def detect_faces(image: np.ndarray) -> list[dict]:
    """Detect faces in image. Returns list of {bbox, confidence, landmarks}."""
    model = get_detector()
    results = model(
        image,
        conf=YOLO_CONF_THRESHOLD,
        imgsz=YOLO_IMG_SIZE,
        verbose=False
    )

    faces = []
    for result in results:
        if result.boxes is None:
            continue
        boxes = result.boxes.xyxy.cpu().numpy()
        confs = result.boxes.conf.cpu().numpy()

        for i, (box, conf) in enumerate(zip(boxes, confs)):
            x1, y1, x2, y2 = map(int, box)
            faces.append({
                "bbox": (x1, y1, x2, y2),
                "confidence": float(conf),
                "crop": image[y1:y2, x1:x2]
            })

    return faces


def detect_faces_from_bytes(image_bytes: bytes) -> list[dict]:
    """Detect faces from raw image bytes (e.g., uploaded file)."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Invalid image data")
    return detect_faces(image)


def bbox_area(bbox) -> float:
    """Area in pixels of an (x1, y1, x2, y2) box."""
    x1, y1, x2, y2 = bbox
    return max(0.0, float(x2) - float(x1)) * max(0.0, float(y2) - float(y1))


def intersection_over_min(box_a, box_b) -> float:
    """Intersection area divided by the smaller box area (containment ratio).

    Plain IoU stays low for a small box nested inside a big one; this ratio
    reaches ~1.0, which is what duplicate detections of one face look like.
    """
    x1 = max(box_a[0], box_b[0])
    y1 = max(box_a[1], box_b[1])
    x2 = min(box_a[2], box_b[2])
    y2 = min(box_a[3], box_b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    smaller = min(bbox_area(box_a), bbox_area(box_b))
    return float(inter / smaller) if smaller > 0 else 0.0


def dedupe_faces(faces: list[dict]) -> list[dict]:
    """Collapse duplicate boxes of the same face, largest box first.

    YOLOv8-face sometimes emits nested boxes for a single face (measured on
    upscaled enrollment crops at imgsz=1280). Keeping the largest box gives
    ArcFace the most context and prevents one face from being enrolled or
    counted several times.
    """
    kept: list[dict] = []
    for face in sorted(faces, key=lambda item: bbox_area(item["bbox"]), reverse=True):
        if all(
            intersection_over_min(face["bbox"], other["bbox"]) < FACE_DUPLICATE_IO_MIN
            for other in kept
        ):
            kept.append(face)
    return kept


def distinct_people(faces: list[dict]) -> list[dict]:
    """Faces large enough to be a real second person in the frame.

    Expects deduplicated faces (see `dedupe_faces`). Tiny background faces
    (a poster, someone far behind) are ignored so they do not block a normal
    selfie. The returned list is ordered largest first.
    """
    if not faces:
        return []
    largest = bbox_area(faces[0]["bbox"])
    if largest <= 0:
        return []
    threshold = largest * MULTIPLE_FACES_MIN_RELATIVE_AREA
    return [face for face in faces if bbox_area(face["bbox"]) >= threshold]

