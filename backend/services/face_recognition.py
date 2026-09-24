import os
import pickle
import threading
import numpy as np
from pathlib import Path
from insightface.app import FaceAnalysis
from sklearn.metrics.pairwise import cosine_similarity
from config import INSIGHTFACE_MODEL, FACE_SIMILARITY_THRESHOLD, EMBEDDINGS_DIR


_app: FaceAnalysis = None
_save_lock = threading.Lock()


def _l2_normalize(v: np.ndarray) -> np.ndarray:
    """L2-normalize a vector; zero vectors are returned unchanged."""
    v = np.asarray(v, dtype=np.float32)
    norm = float(np.linalg.norm(v))
    return v / norm if norm > 0 else v


def get_face_analyzer() -> FaceAnalysis:
    global _app
    if _app is None:
        _app = FaceAnalysis(
            name=INSIGHTFACE_MODEL,
            providers=["CPUExecutionProvider"]
        )
        _app.prepare(ctx_id=0, det_size=(640, 640))
    return _app


def _crop_with_margin(image: np.ndarray, bbox: tuple, margin: float = 0.25) -> np.ndarray:
    """Crop a bbox region from the image, expanded by a relative margin."""
    h, w = image.shape[:2]
    x1, y1, x2, y2 = bbox
    mx = int((x2 - x1) * margin)
    my = int((y2 - y1) * margin)
    x1 = max(0, int(x1) - mx)
    y1 = max(0, int(y1) - my)
    x2 = min(w, int(x2) + mx)
    y2 = min(h, int(y2) + my)
    return image[y1:y2, x1:x2]


def get_embedding(image: np.ndarray, bbox: tuple | None = None) -> np.ndarray | None:
    """Extract 512-D embedding using InsightFace ArcFace.

    InsightFace expects a full image (it runs its own detector internally).
    When a YOLO bbox is provided, that region is cropped with a margin so
    ArcFace's detector reliably finds the face without unrelated faces.
    """
    analyzer = get_face_analyzer()
    target = _crop_with_margin(image, bbox) if bbox is not None else image
    faces = analyzer.get(target)
    if not faces:
        return None
    faces = sorted(
        faces,
        key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
        reverse=True,
    )
    return _l2_normalize(faces[0].embedding)


def compare_faces(embedding: np.ndarray, known_embeddings: list[np.ndarray]) -> tuple[int, float]:
    """Compare embedding against known embeddings. Returns (best_index, best_score).

    All vectors are L2-normalized first; zero-norm entries are skipped.
    """
    if not known_embeddings:
        return -1, 0.0

    emb = _l2_normalize(embedding)
    valid = [
        (i, _l2_normalize(known))
        for i, known in enumerate(known_embeddings)
        if np.linalg.norm(known) > 0
    ]
    if not valid:
        return -1, 0.0

    known_matrix = np.array([k for _, k in valid])
    scores = cosine_similarity(emb.reshape(1, -1), known_matrix)[0]
    scores = np.nan_to_num(scores, nan=0.0, posinf=0.0, neginf=0.0)
    best_pos = int(np.argmax(scores))
    return valid[best_pos][0], float(scores[best_pos])


def is_match(score: float) -> bool:
    return score >= FACE_SIMILARITY_THRESHOLD


def load_embeddings(student_id: int) -> list[np.ndarray]:
    """Load stored embeddings for a student. Returns [] on missing/corrupt file."""
    emb_file = EMBEDDINGS_DIR / f"student_{student_id}.pkl"
    if not emb_file.exists():
        return []
    try:
        with open(emb_file, "rb") as f:
            return pickle.load(f)
    except (pickle.UnpicklingError, EOFError, OSError, ValueError, AttributeError):
        return []


def save_embeddings(student_id: int, embeddings: list[np.ndarray]):
    """Save embeddings for a student (atomic write, thread-safe)."""
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    emb_file = EMBEDDINGS_DIR / f"student_{student_id}.pkl"
    tmp_file = emb_file.with_suffix(".tmp")
    with _save_lock:
        with open(tmp_file, "wb") as f:
            pickle.dump(embeddings, f)
        os.replace(str(tmp_file), str(emb_file))


def load_all_embeddings() -> dict[int, list[np.ndarray]]:
    """Load all stored embeddings. Returns {student_id: [embeddings]}.

    Corrupt files are skipped rather than crashing the scan.
    """
    all_embs = {}
    for emb_file in EMBEDDINGS_DIR.glob("student_*.pkl"):
        try:
            with open(emb_file, "rb") as f:
                all_embs[int(emb_file.stem.split("_")[1])] = pickle.load(f)
        except (pickle.UnpicklingError, EOFError, OSError, ValueError, AttributeError):
            continue
    return all_embs
