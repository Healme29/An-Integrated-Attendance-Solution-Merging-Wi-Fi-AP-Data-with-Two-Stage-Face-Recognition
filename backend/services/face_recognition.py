import pickle
import numpy as np
from pathlib import Path
from insightface.app import FaceAnalysis
from sklearn.metrics.pairwise import cosine_similarity
from config import INSIGHTFACE_MODEL, FACE_SIMILARITY_THRESHOLD, EMBEDDINGS_DIR


_app: FaceAnalysis = None


def get_face_analyzer() -> FaceAnalysis:
    global _app
    if _app is None:
        _app = FaceAnalysis(
            name=INSIGHTFACE_MODEL,
            providers=["CPUExecutionProvider"]
        )
        _app.prepare(ctx_id=0, det_size=(640, 640))
    return _app


def get_embedding(face_image: np.ndarray) -> np.ndarray | None:
    """Extract 512-D embedding from a face crop using InsightFace ArcFace."""
    analyzer = get_face_analyzer()
    faces = analyzer.get(face_image)
    if not faces:
        return None
    return faces[0].embedding


def compare_faces(embedding: np.ndarray, known_embeddings: list[np.ndarray]) -> tuple[int, float]:
    """Compare embedding against known embeddings. Returns (best_index, best_score)."""
    if not known_embeddings:
        return -1, 0.0

    known_matrix = np.array(known_embeddings)
    scores = cosine_similarity(embedding.reshape(1, -1), known_matrix)[0]
    best_idx = int(np.argmax(scores))
    return best_idx, float(scores[best_idx])


def is_match(score: float) -> bool:
    return score >= FACE_SIMILARITY_THRESHOLD


def load_embeddings(student_id: int) -> list[np.ndarray]:
    """Load stored embeddings for a student."""
    emb_file = EMBEDDINGS_DIR / f"student_{student_id}.pkl"
    if not emb_file.exists():
        return []
    with open(emb_file, "rb") as f:
        return pickle.load(f)


def save_embeddings(student_id: int, embeddings: list[np.ndarray]):
    """Save embeddings for a student."""
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    emb_file = EMBEDDINGS_DIR / f"student_{student_id}.pkl"
    with open(emb_file, "wb") as f:
        pickle.dump(embeddings, f)


def load_all_embeddings() -> dict[int, list[np.ndarray]]:
    """Load all stored embeddings. Returns {student_id: [embeddings]}."""
    all_embs = {}
    for emb_file in EMBEDDINGS_DIR.glob("student_*.pkl"):
        student_id = int(emb_file.stem.split("_")[1])
        with open(emb_file, "rb") as f:
            all_embs[student_id] = pickle.load(f)
    return all_embs
