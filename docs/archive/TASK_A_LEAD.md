# TASK A — TEAM LEAD: Face Recognition Pipeline (Hardest)

## Summary
You are responsible for the **ML core of the system**: face detection with YOLOv8 and face recognition with InsightFace ArcFace. This part is the most critical because the accuracy of the entire system depends on it. You also manage the team (B, C, D) and ensure smooth integration of all modules.

---

## FILES TO WORK ON

### 1. `backend/services/face_detection.py`
**What already exists:** Basic code is done — YOLOv8-face singleton, `detect_faces()`, `detect_faces_from_bytes()`.

**What you must do & fix:**
- [ ] **Verify model weights:** Make sure `backend/data/models/yolov8m-face.pt` is actually downloaded (50 MB). If not, download from `https://github.com/YapaLab/yolo-face/releases`
- [ ] **Better error handling:** If model is not found, give a clear error message + download instructions. If image is corrupt, throw a specific exception (not generic `ValueError`).
- [ ] **Performance optimization:** Add detection result caching for the same image. `verbose=False` is already set, good.
- [ ] **Multiple face handling:** Currently only takes the highest confidence face in `attendance.py`. Here, return all detected faces sorted by confidence descending.
- [ ] **Face quality filter:** Add minimum bounding box size filter (e.g., crop < 30×30 pixels is discarded). Faces too small cannot be embedded well.
- [ ] **Optional landmarks:** Add eye/nose landmark return if YOLOv8-face provides them (for face rotation).
- [ ] **Model load progress:** Add a log when model finishes loading (load time, file path).

### 2. `backend/services/face_recognition.py`
**What already exists:** InsightFace ArcFace singleton, `get_embedding()`, `compare_faces()`, `is_match()`, save/load embeddings.

**What you must do & fix:**
- [ ] **Fix `get_embedding()`:** InsightFace `app.get(face_image)` needs the full image (not a crop). Currently the code calls `analyzer.get(face_image)` where `faceImage` is a face crop. InsightFace actually needs the full image because it has its own detector. Change the function signature to `get_embedding(full_image: np.ndarray, bbox: tuple) -> np.ndarray | None` — pass the full frame + bounding box, let InsightFace detect in that area.
- [ ] **Fallback embedding:** If InsightFace fails to extract embedding from a specific crop, try again with a resized image or with preprocessing (histogram equalization).
- [ ] **Threshold tuning:** `FACE_SIMILARITY_THRESHOLD = 0.5` is the default. You must test with at least 20 different face photos to determine the optimal threshold. Create a `find_optimal_threshold()` function that calculates FAR (False Acceptance Rate) vs FRR (False Rejection Rate).
- [ ] **Anti-spoofing awareness:** Add documentation that InsightFace `buffalo_l` does not have anti-spoofing. Note it as a known limitation.
- [ ] **Embedding normalization:** Ensure stored embeddings are always L2-normalized. InsightFace is usually already normalized, but add `embedding = embedding / np.linalg.norm(embedding)` as a safety measure.
- [ ] **Load embeddings error handling:** If the pickle file is corrupt, handle with `except EOFError` and return an empty list, don't crash.
- [ ] **Concurrent access protection:** The pickle file can be accessed concurrently (enrollment + attendance at the same time). Add `threading.Lock()` or `asyncio.Lock()` for `save_embeddings()`.

### 3. `backend/routers/faces.py`
**What already exists:** Endpoints `POST /faces/enroll` and `POST /faces/recognize`.

**What you must do & fix:**
- [ ] **⚠️ CRITICAL BUG — Fix data saving (Priority 1, Blocker #1):**
  - Line 42: `(student_id, b"blob", ...)` — this stores the literal string `b"blob"` to the database, not the actual binary embedding. **REPLACE** with storing pickle bytes of all embeddings:
    ```python
    emb_bytes = pickle.dumps(all_embeddings)
    await db.execute("INSERT INTO faces (student_id, embedding, image_path) VALUES (?, ?, ?)",
                     (student_id, emb_bytes, image_path))
    ```
  - Create directory `backend/data/faces/` if it doesn't exist.
  - Save the original image file to `backend/data/faces/{student_id}_{timestamp}.jpg`.
  - The image path stored in DB must be an absolute or valid relative path.

- [ ] **Input validation:** Ensure the uploaded file is a valid image (check magic bytes / MIME type). Don't assume all files are JPEG.
- [ ] **File size limit:** Reject images > 10 MB to prevent DoS.
- [ ] **Limit embeddings per student:** Maximum 5 embeddings per student. If already at 5, new faces are rejected (unless admin override).
- [ ] **More informative response:** Add `confidence_avg`, `num_faces_detected` in the response.
- [ ] **Bulk enrollment:** Consider adding an endpoint that accepts multiple images at once later (stretch goal).

### 4. `backend/config.py`
**What you must review & set:**
- [ ] **Face detection threshold:** `YOLO_CONF_THRESHOLD = 0.25` — is this optimal? Try 0.3 or 0.35.
- [ ] **Image size:** `YOLO_IMG_SIZE = 1280` — this is large. Could try 640 for speed, but recall may drop.
- [ ] **Face similarity threshold:** After testing, update `FACE_SIMILARITY_THRESHOLD` to the optimal value (maybe 0.45-0.55).
- [ ] **Grace period:** `ATTENDANCE_CHECK_WINDOW_MINUTES = 15` — agree with B before changing.

### 5. Integration with Other Modules
- [ ] **Coordinate with B:** Make sure `recognize_face()` in `attendance.py` receives compatible parameters with your service. If you change function signatures, tell B.
- [ ] **Coordinate with D:** Make sure test mocks for face detection & recognition in `conftest.py` remain relevant after your changes.
- [ ] **Real testing:** At least 5x testing with real photos from a laptop camera. Check:
  - Face detected in various lighting conditions
  - Embedding successfully extracted
  - Two photos of the same person produce similarity > threshold
  - Two photos of different people produce similarity < threshold

### 6. Technical Documentation
- [ ] Update `AGENTS.md` if there are architecture changes.
- [ ] Record threshold tuning results (FAR/FRR values) in file `docs/threshold_report.md`.

---

## DEPENDENCIES
- `ultralytics==8.2.100` (YOLOv8)
- `insightface>=2.0` (ArcFace)
- `onnxruntime==1.18.1` (InsightFace runtime)
- `opencv-python==4.10.0.84` (image processing)
- `numpy==1.26.4` (math)
- `scikit-learn==1.5.1` (cosine similarity)
- `Pillow==10.4.0` (image handling)
- Model file: `yolov8m-face.pt` ~50 MB (not included in repo, download manually)

---

## RESPONSIBILITIES AS TEAM LEAD
1. **Divide tasks** and ensure all members understand what to work on.
2. **Monitor progress** of each member — ask for updates at least 1x/day (via chat group).
3. **Help unblock** members who are stuck. If technical issues are beyond your ability, find a solution together.
4. **Code review** all pull requests before merging.
5. **Integration testing** after all modules are complete — run the entire pipeline end-to-end.
6. **Final documentation** — ensure all changes are properly recorded.

---

## TIME ESTIMATES
| Sub-task | Estimate |
|----------|----------|
| Fix face_detection.py error handling | 1-2 hours |
| Fix face_recognition.py get_embedding signature | 2-3 hours |
| Fix enrollment data saving (CRITICAL) | 3-4 hours |
| Threshold tuning & testing | 4-6 hours |
| Integration & real testing | 3-4 hours |
| **Total** | **13-19 hours** |

---

## PRIORITIES
1. ⚠️ **CRITICAL** — Fix enrollment data saving (the single most critical blocker)
2. ⚠️ **HIGH** — Fix `get_embedding()` signature
3. **HIGH** — Threshold tuning with real data
4. **MEDIUM** — Error handling & quality filters
5. **LOW** — Performance optimization & documentation