# ArcFace Model Cache — Where It Lives and What Actually Warms It (2026-11-12)

> **Owner:** B · **Type:** measurement + correction of our own documents · **Gate:** feeds G1
> (model warm-up row) and G5 (offline fallback) · **Decision:** D-014
> **Why this exists:** three claims B had written down did not match the library that
> `backend/requirements.txt` actually installs. A demo-day warm-up that "succeeds" without
> loading the model is worse than no warm-up, because nobody checks again.

---

## 1. Environment measured

| Item | Value |
|---|---|
| Library | `insightface` **2.1** (requirements: `insightface>=2.0`) |
| Runtime | `onnxruntime==1.18.1`, Python 3.12, CPU provider |
| Model set | `buffalo_l` |
| Host | the B laptop (Linux), not the demo laptop |

## 2. The three claims that were wrong

| # | Where it was written | What it said | What is true |
|---|---|---|---|
| 1 | `offline_fallback.md` §0 | `buffalo_l` is cached in `DATA_DIR` | It is cached in `~/.insightface/models/buffalo_l` (`%USERPROFILE%\.insightface\…` on Windows). `DATA_DIR` holds the YOLO weights, face crops and embeddings |
| 2 | `deployment_guide.md` §7, `offline_fallback.md` §5 row 3 | "any JPEG works" / "any photo" warms the models | The request runs YOLO first; with no face it returns `no_face_detected` and **never initialises ArcFace**. The warm-up photo must contain a detectable face |
| 3 | `backend/Dockerfile`, `docker-compose.yml` | `INSIGHTFACE_HOME` relocates the cache into the mounted volume | insightface 2.x has no `INSIGHTFACE_HOME` lookup at all. In a container the cache goes to `/root/.insightface` — the ephemeral image layer, not the volume |

Claim 3 was the expensive one: after `docker compose down`/rebuild the 326 MB download would
be paid again, and with no internet recognition could not start at all.

## 3. Measurements

All timings are wall clock on this host; nothing was downloaded and the real cache was not
modified.

| # | What was run | Result |
|---|---|---|
| 1 | Size and contents of the real cache | `du -sh` → **326 MB**; five `.onnx`: `w600k_r50` 167 MB, `1k3d68` 137 MB, `det_10g` 17 MB, `2d106det` 4.8 MB, `genderage` 1.3 MB |
| 2 | `detect_faces_from_bytes()` on a 480×640 JPEG with no face, then inspect `face_recognition._app` | **0** boxes in **4.83 s**; `_app is None` → ArcFace **not** loaded |
| 3 | `get_face_analyzer()` with the cache present | **4.21 s**, models `['detection', 'genderage', 'landmark_2d_106', 'landmark_3d_68', 'recognition']` |
| 4 | Same, with `HOME` pointed at a simulated container layout (`.insightface` → real cache) | **3.06 s**; `model_dir` resolved under the new `HOME`, proving `HOME` is what selects the cache |
| 5 | Existing but **empty** `buffalo_l` directory | immediate `AssertionError` at `assert "detection" in self.models` (no message pointing at the cause) |
| 6 | Missing cache, network unreachable (proxy at a closed port, no download attempted) | `requests.exceptions.ProxyError` for `…/model-zoo/buffalo_l.zip` after **3.21 s**; 12 KB of empty directories left, nothing downloaded |
| 7 | Library source | `FaceAnalysis.__init__(root="~/.insightface")`; `grep -rn INSIGHTFACE_HOME` over the installed package → no match |

Peak RSS of the process that ran YOLO and then ArcFace: **~1.4 GB** (ONNX sessions plus the
interpreter), which is worth knowing on a small demo laptop.

## 4. What changed because of this

| File | Change |
|---|---|
| `backend/Dockerfile` | `INSIGHTFACE_HOME=…` → `HOME=/app/data/dbdata`, so `~/.insightface` is on the named volume |
| `docker-compose.yml` | removed the ineffective `INSIGHTFACE_HOME` entry; comment now explains the `HOME` mechanism |
| `docs/B/deployment_guide.md` §7 | real cache paths per run mode; warm-up must use a selfie; verification commands; offline failure mode |
| `docs/B/offline_fallback.md` §0/§5 | same correction in the one-page ladder and the pre-demo checklist |
| `docs/B/demo_runbook.md` §2 | warm-up step states the face requirement and the folder check |
| `docs/B/demo_environment.md` §6 | G1 item 3 now asks for the cache folder, not just a call |
| `backend/tests/test_services.py` | regression test: a no-face request returns `no_face_detected` **and** never calls `get_embedding` |

## 5. What this does **not** prove

| Not covered | Why it matters | Where it closes |
|---|---|---|
| A Docker build/run with the new `HOME` | no daemon on this machine; the mechanism is verified outside Docker only | first Docker build on the demo laptop (optional path, D-001/D-002) |
| The real download time from GitHub | deliberately not measured (326 MB, 1.1 GB free disk) | demo laptop, G1 |
| A full check-in with a real face | still needs a face photo and an enrolled student | dry run #1 |
| Windows path behaviour (`%USERPROFILE%`) | this host is Linux | dry run #1 |

Nothing here claims the Docker image was rebuilt or that an offline check-in was executed.

## 6. How to repeat it

```bash
# 2) faceless image does not load ArcFace
cd backend && python - <<'PY'
import numpy as np, cv2
from services import face_recognition as fr
from services.face_detection import detect_faces_from_bytes
img = np.zeros((480, 640, 3), dtype=np.uint8)
ok, buf = cv2.imencode(".jpg", img)
print(detect_faces_from_bytes(buf.tobytes()), fr._app)
PY

# 3) explicit warm-up with the cache present
cd backend && python -c "import time,sys; sys.path.insert(0,'.'); from services.face_recognition import get_face_analyzer as g; t=time.perf_counter(); g(); print(round(time.perf_counter()-t,2),'s')"

# 6) missing cache with no network: use a throwaway HOME and a dead proxy
HOME=/tmp/if_empty HTTP_PROXY=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 \
  timeout 60 python -c "import sys; sys.path.insert(0,'.'); from services.face_recognition import get_face_analyzer as g; g()"
```
