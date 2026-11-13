"""Measure InsightFace (buffalo_l) cold load with the real model files present."""
import os
import sys
import time

import numpy as np

sys.path.insert(0, r"D:\NJUPT ( NANJING UNIVERSITY OF POSTS AND TELECOMMUNICATIONS )\STITP\An-Integrated-Attendance-Solution-Merging-Wi-Fi-AP-Data-with-Two-Stage-Face-Recognition\backend")

import psutil  # noqa: E402

proc = psutil.Process(os.getpid())
base_rss = proc.memory_info().rss

t0 = time.perf_counter()
from services.face_recognition import get_face_analyzer  # noqa: E402

print(f"import_s {time.perf_counter()-t0:.2f}")

t0 = time.perf_counter()
analyzer = get_face_analyzer()
load_s = time.perf_counter() - t0
rss = proc.memory_info().rss
print(f"buffalo_l_load_s {load_s:.2f}")
print(f"rss_mb_before {base_rss/2**20:.0f} after {rss/2**20:.0f} delta {(rss-base_rss)/2**20:.0f}")
print("model_names", sorted(analyzer.models.keys()))

icon = r"D:\NJUPT ( NANJING UNIVERSITY OF POSTS AND TELECOMMUNICATIONS )\STITP\An-Integrated-Attendance-Solution-Merging-Wi-Fi-AP-Data-with-Two-Stage-Face-Recognition\mobile\android\app\src\main\res\mipmap-xxxhdpi\ic_launcher.png"
import cv2  # noqa: E402

img = cv2.imread(icon)
print("icon_shape", img.shape)
for i in (1, 2, 3):
    t0 = time.perf_counter()
    faces = analyzer.get(img)
    print(f"analyzer_get_no_face_{i}_ms {(time.perf_counter()-t0)*1000:.0f} faces {len(faces)}")

blank = np.zeros((480, 640, 3), dtype=np.uint8)
for i in (1, 2):
    t0 = time.perf_counter()
    faces = analyzer.get(blank)
    print(f"analyzer_get_blank_{i}_ms {(time.perf_counter()-t0)*1000:.0f} faces {len(faces)}")
