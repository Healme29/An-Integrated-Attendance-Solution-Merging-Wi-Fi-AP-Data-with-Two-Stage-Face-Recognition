import cv2
import numpy as np
from pathlib import Path
from ultralytics import YOLO
from config import YOLO_MODEL_PATH, YOLO_CONF_THRESHOLD, YOLO_IMG_SIZE


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
