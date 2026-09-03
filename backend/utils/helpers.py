from pathlib import Path
import numpy as np


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def image_bytes_to_array(image_bytes: bytes) -> np.ndarray:
    import cv2
    nparr = np.frombuffer(image_bytes, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
