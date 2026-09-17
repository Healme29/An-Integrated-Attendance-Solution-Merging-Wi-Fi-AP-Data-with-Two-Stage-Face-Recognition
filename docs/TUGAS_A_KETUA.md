# TUGAS A — KETUA TIM: Face Recognition Pipeline (Tersulit)

## Ringkasan
Kamu bertanggung jawab atas **inti ML sistem**: deteksi wajah dengan YOLOv8 dan pengenalan wajah dengan InsightFace ArcFace. Bagian ini paling kritis karena akurasi seluruh sistem bergantung padanya. Kamu juga mengelola tim (B, C, D) dan memastikan integrasi semua modul berjalan lancar.

---

## FILE YANG HARUS DIKERJAKAN

### 1. `backend/services/face_detection.py`
**Apa yang sudah ada:** Kode dasar sudah jadi — YOLOv8-face singleton, `detect_faces()`, `detect_faces_from_bytes()`.

**Yang harus kamu lakukan & perbaiki:**
- [ ] **Verifikasi model weights:** Pastikan `backend/data/models/yolov8m-face.pt` benar-benar terunduh (50 MB). Jika tidak, download dari `https://github.com/YapaLab/yolo-face/releases`
- [ ] **Error handling lebih baik:** Jika model tidak ditemukan, beri pesan error jelas + instruksi download. Jika gambar corrupt, beri exception spesifik (bukan `ValueError` generik).
- [ ] **Optimasi performa:** Tambahkan caching hasil deteksi untuk gambar yang sama. Setel `verbose=False` sudah ada, bagus.
- [ ] **Multiple face handling:** Saat ini hanya ambil wajah dengan confidence tertinggi di `attendance.py`. Di sini, return semua wajah yang terdeteksi dengan urutan confidence descending.
- [ ] **Face quality filter:** Tambahkan filter ukuran minimum bounding box (misal crop < 30×30 pixel langsung discard). Wajah terlalu kecil tidak bisa di-embedding dengan baik.
- [ ] **Landmark opsional:** Tambahkan return landmark mata/hidung jika YOLOv8-face menyediakannya (untuk rotasi wajah).
- [ ] **Load model progress:** Tambahkan log saat model selesai di-load (waktu loading, path file).

### 2. `backend/services/face_recognition.py`
**Apa yang sudah ada:** InsightFace ArcFace singleton, `get_embedding()`, `compare_faces()`, `is_match()`, save/load embeddings.

**Yang harus kamu lakukan & perbaiki:**
- [ ] **Fix `get_embedding()`:** InsightFace `app.get(face_image)` butuh gambar penuh (bukan crop). Saat ini kode panggil `analyzer.get(face_image)` dengan `faceImage` adalah crop wajah. InsightFace sebenarnya butuh gambar penuh karena dia punya detektor sendiri. Ubah function signature jadi `get_embedding(full_image: np.ndarray, bbox: tuple) -> np.ndarray | None` — beri full frame + bounding box, biarkan InsightFace mendeteksi di area itu.
- [ ] **Fallback embedding:** Jika InsightFace gagal extract embedding dari crop tertentu, coba lagi dengan gambar yang di-resize atau dengan preprocessing (equalize histogram).
- [ ] **Threshold tuning:** `FACE_SIMILARITY_THRESHOLD = 0.5` adalah default. Kamu harus melakukan testing dengan minimal 20 foto wajah berbeda untuk menentukan threshold optimal. Buat fungsi `find_optimal_threshold()` yang menghitung FAR (False Acceptance Rate) vs FRR (False Rejection Rate).
- [ ] **Anti-spoofing awareness:** Tambahkan dokumentasi bahwa InsightFace `buffalo_l` tidak punya anti-spoofing. Catat sebagai known limitation.
- [ ] **Normalisasi embedding:** Pastikan embedding yang disimpan selalu L2-normalized. InsightFace biasanya sudah normalized, tapi tambahkan `embedding = embedding / np.linalg.norm(embedding)` sebagai jaga-jaga.
- [ ] **Load embeddings error handling:** Jika file pickle corrupt, tangani dengan `except EOFError` dan return empty list, jangan crash.
- [ ] **Concurrent access protection:** File pickle bisa diakses concurrent (enrollment + attendance bersamaan). Tambahkan `threading.Lock()` atau `asyncio.Lock()` untuk `save_embeddings()`.

### 3. `backend/routers/faces.py`
**Apa yang sudah ada:** Endpoint `POST /faces/enroll` dan `POST /faces/recognize`.

**Yang harus kamu lakukan & perbaiki:**
- [ ] **⚠️ CRITICAL BUG — Fix data saving (Priority 1, Blocker #1):**
  - Baris 42: `(student_id, b"blob", ...)` — ini menyimpan literal string `b"blob"` ke database, bukan binary embedding yang sebenarnya. **GANTI** dengan menyimpan pickle bytes dari semua embeddings:
    ```python
    emb_bytes = pickle.dumps(all_embeddings)
    await db.execute("INSERT INTO faces (student_id, embedding, image_path) VALUES (?, ?, ?)",
                     (student_id, emb_bytes, image_path))
    ```
  - Buat direktori `backend/data/faces/` jika belum ada.
  - Simpan file image asli ke `backend/data/faces/{student_id}_{timestamp}.jpg`.
  - Image path yang disimpan di DB harus path absolut atau relatif valid.

- [ ] **Validasi input:** Pastikan file upload adalah gambar valid (cek magic bytes / MIME type). Jangan asumsikan semua file adalah JPEG.
- [ ] **Batas ukuran file:** Tolak gambar > 10 MB untuk mencegah DoS.
- [ ] **Limit jumlah embedding per student:** Maksimal 5 embedding per student. Jika sudah 5, wajah baru ditolak (kecuali admin override).
- [ ] **Response lebih informatif:** Tambahkan `confidence_avg`, `num_faces_detected` di response.
- [ ] **Bulk enrollment:** Pertimbangkan untuk nanti menambahkan endpoint yang menerima multiple images sekaligus (stretch goal).

### 4. `backend/config.py`
**Yang harus kamu review & setel:**
- [ ] **Threshold face detection:** `YOLO_CONF_THRESHOLD = 0.25` — apakah optimal? Coba 0.3 atau 0.35.
- [ ] **Image size:** `YOLO_IMG_SIZE = 1280` — ini besar. Bisa coba 640 untuk kecepatan, tapi recall mungkin turun.
- [ ] **Face similarity threshold:** Setelah testing, update `FACE_SIMILARITY_THRESHOLD` ke nilai optimal (mungkin 0.45-0.55).
- [ ] **Grace period:** `ATTENDANCE_CHECK_WINDOW_MINUTES = 15` — setuju dengan B sebelum diubah.

### 5. Integrasi dengan Modul Lain
- [ ] **Koordinasi dengan B:** Pastikan `recognize_face()` di `attendance.py` menerima parameter yang kompatibel dengan service kamu. Jika kamu ubah signature function, beri tahu B.
- [ ] **Koordinasi dengan D:** Pastikan test mock untuk face detection & recognition di `conftest.py` tetap relevan setelah perubahan kamu.
- [ ] **Test real:** Minimal 5x testing dengan foto asli dari kamera laptop. Cek:
  - Wajah terdeteksi di berbagai kondisi pencahayaan
  - Embedding berhasil di-extract
  - Dua foto orang yang sama menghasilkan similarity > threshold
  - Dua foto orang berbeda menghasilkan similarity < threshold

### 6. Dokumentasi Teknis
- [ ] Update `AGENTS.md` jika ada perubahan arsitektur.
- [ ] Catat hasil threshold tuning (nilai FAR/FRR) di file `docs/threshold_report.md`.

---

## DEPENDENCIES
- `ultralytics==8.2.100` (YOLOv8)
- `insightface>=2.0` (ArcFace)
- `onnxruntime==1.18.1` (runtime InsightFace)
- `opencv-python==4.10.0.84` (image processing)
- `numpy==1.26.4` (matematika)
- `scikit-learn==1.5.1` (cosine similarity)
- `Pillow==10.4.0` (image handling)
- File model: `yolov8m-face.pt` ~50 MB (belum termasuk di repo, download manual)

---

## TANGGUNG JAWAB SEBAGAI KETUA
1. **Membagi tugas** dan memastikan semua anggota paham apa yang harus dikerjakan.
2. **Memantau progress** setiap anggota — minta update minimal 1x sehari (via chat grup).
3. **Membantu unblock** anggota yang stuck. Jika masalah teknis di luar kemampuanmu, cari solusi bersama.
4. **Code review** semua pull request sebelum di-merge.
5. **Integration testing** setelah semua modul selesai — jalankan seluruh pipeline end-to-end.
6. **Dokumentasi final** — pastikan semua perubahan tercatat dengan baik.

---

## ESTIMASI WAKTU
| Sub-task | Estimasi |
|----------|----------|
| Fix face_detection.py error handling | 1-2 jam |
| Fix face_recognition.py get_embedding signature | 2-3 jam |
| Fix enrollment data saving (CRITICAL) | 3-4 jam |
| Threshold tuning & testing | 4-6 jam |
| Integrasi & testing real | 3-4 jam |
| **Total** | **13-19 jam** |

---

## PRIORITAS
1. ⚠️ **CRITICAL** — Fix enrollment data saving (satu-satunya blocker paling kritis)
2. ⚠️ **HIGH** — Fix `get_embedding()` signature
3. **HIGH** — Threshold tuning dengan real data
4. **MEDIUM** — Error handling & quality filters
5. **LOW** — Optimasi performa & dokumentasi