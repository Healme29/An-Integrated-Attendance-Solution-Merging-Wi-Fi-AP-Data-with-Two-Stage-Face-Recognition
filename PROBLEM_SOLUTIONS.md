# Problem & Solution Log

This file records every technical problem encountered during the project, its root cause, and the fix applied. Keep it for reference when similar issues recur.

---

## 1. App renamed to "真到" (Zhen Dao)

**Problem:** App needed rebranding from "Face Attendance" / "Student Attendance" to "真到".

**Solution:**
- `mobile/pubspec.yaml`: `name: face_attendance` → `name: zhen_dao`
- `mobile/pubspec.yaml`: `description` → "Face recognition attendance system with rotating QR code verification"
- Import paths `package:face_attendance/...` → `package:zhen_dao/...` in 4 Dart files
- Display name "Student Attendance" → "真到" in `main.dart`, `home_screen.dart`, `login_screen.dart`, `AndroidManifest.xml`, `Info.plist` (CFBundleDisplayName → "真到", CFBundleName → "zhen_dao")
- Backend FastAPI title `"Face Attendance API"` → `"真到 API"`; root message updated
- Dashboard `backend/static/dashboard.html`: `<title>` and `<h1>` → "真到"

**Note:** Bundle identifier kept as `com.attendance.attendance_app` (Android) / `com.attendance.attendanceApp` (iOS) to avoid fresh-install requirement.

---

## 2. App icon replaced

**Problem:** Default Flutter icon needed replacement with "Blue Checkmark Volunteer App Icon.png".

**Solution:** Source PNG (1254×1254) resized with Pillow (LANCZOS) into:
- Android mipmap-*: mdpi 48×48, hdpi 72×72, xhdpi 96×96, xxhdpi 144×144, xxxhdpi 192×192
- iOS AppIcon.appiconset: all 16 sizes from 20×20@1x to 1024×1024@1x

Script `generate_icons.py` used once, then deleted.

---

## 3. Home screen — permanent check-in confirmation

**Problem:** After a student scanned QR + took selfie and returned to Home, there was no visual confirmation that check-in succeeded. Students worried "did my attendance register?"

**Solution:**
- `mobile/lib/models/student.dart`: Added `SessionCheckInState` class + `fromHistory(rows, sessionId)` factory. Summarizes a student's own check-in rows for one session: `startDone`, `endDone`, `spotRounds`, `startTime`, `endTime`, `spotDone(round)`.
- `mobile/lib/screens/home_screen.dart`: Home polls `/qr-sessions/active` AND `GET /attendance/student/{id}` every 5s, matches rows to the active `qr_session_id`, then shows:
  - `start` phase, not yet checked in: "Start attendance is open" + active "Scan Start QR" button
  - `start` phase, already checked in: 🟢 **"You have successfully checked in"** (with time) + button **disabled** ("Already checked in")
  - `spot` phase, not yet: active "Scan Spot-Check QR"
  - `spot` phase, done: 🟢 "Spot check recorded" + button disabled
  - `end` phase, not final: active "Scan Final QR"
  - `end` phase, final done: 🟢 **"Attendance complete — you are marked present."** + button **removed permanently**
- `mobile/test/session_check_in_state_test.dart`: 4 unit tests covering empty history, cross-session filtering, start/end/spot parsing, missing check_type fallback.

**Backend:** No schema change. Reuses existing `GET /attendance/student/{id}`.

---

## 4. QR scanner camera fails on Android 16 (ROOT CAUSE FOUND & FIXED)

**Problem:** Scan QR screen showed "Camera unavailable — The camera could not start..." on every attempt, despite:
- CAMERA permission granted (`runtime permissions: CAMERA granted=true`)
- No other app holding the camera
- Enroll Face (plugin `camera`) working perfectly — proving hardware + permissions were fine

**Root cause:** Build **release** mode uses **R8 code shrinking**. `mobile_scanner` depends on **MLKit** for barcode detection, and MLKit instantiates its internal registrars via **reflection by class name**:

```
W/ComponentDiscovery: Could not instantiate com.google.mlkit.common.internal.CommonComponentRegistrar
   Caused by: java.lang.NoSuchMethodException: com.google.mlkit.common.internal.CommonComponentRegistrar.<init> []
W/ComponentDiscovery: Could not instantiate com.google.mlkit.vision.barcode.internal.BarcodeRegistrar
   Caused by: java.lang.NoSuchMethodException: com.google.mlkit.vision.barcode.internal.BarcodeRegistrar.<init> []
E/MethodChannel#dev.steenbakker.mobile_scanner/scanner/method:
   java.lang.NullPointerException: ... 'java.lang.Class java.lang.Object.getClass()' on a null object reference
```

R8 removed the MLKit constructors that are only reached by reflection → MLKit failed to initialize → `mobile_scanner` threw `MobileScannerErrorCode.genericError` → camera preview never opened.

**Why Enroll worked:** Enroll uses plugin `camera` (CameraX directly), no MLKit → unaffected.

**Fix:** Added ProGuard keep rules so R8 preserves MLKit's reflection-loaded classes:
- New file: `mobile/android/app/proguard-rules.pro`
  ```
  -keep class com.google.mlkit.** { *; }
  -keep class com.google.android.gms.internal.mlkit_vision_barcode.** { *; }
  -keep class com.google.android.gms.internal.mlkit_common.** { *; }
  -keep class com.google.android.gms.internal.mlkit_vision_common.** { *; }
  -dontwarn com.google.mlkit.**
  ```
- `mobile/android/app/build.gradle.kts`: `release { proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro") }`

**Verification:**
- `flutter analyze`: No issues
- `flutter test`: All tests pass (5/5)
- Build APK release: success, size rose from 64.4 MB → 64.5 MB (MLKit classes retained)
- `adb logcat` after fix: `ComponentDiscovery ... Could not instantiate ...` warnings **disappeared** from app startup
- Remaining step: user to physically test scanning QR on the device

**Temporary diagnostics (to be removed after confirmation):**
- `mobile/lib/screens/qr_scanner_screen.dart`: Added `debugPrint('MOBILE_SCANNER_ERROR ...')` lines in `initState`, `_buildCameraError`, `_restartScanner`, and `_onDetect` catch blocks. Filter with `adb logcat | findstr MOBILE_SCANNER_ERROR`. Remove before final release.

---

## 5. Backend server "address already in use" (port 8000)

**Problem:** Repeated `uvicorn` launches failed with `OSError: [Errno 10048] only one usage of each socket address`.

**Cause:** Previous uvicorn process still bound to port 8000 (sometimes as zombie/TIME_WAIT).

**Fix:** Kill stale PID then restart:
```
netstat -ano | findstr :8000 | findstr LISTENING
taskkill /PID <pid> /F
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
Do **not** use `--reload` for production demo (file watcher can trigger unwanted restarts).

---

## 6. Stale `student_id` in phone cache → "Student not found"

**Problem:** Phone's `shared_preferences` held `{id: 8}` from an old login after the database was reset/reseeded (IDs shifted). App kept sending `student_id=8` which no longer existed → `404 Student not found`.

**Fix:** User must **Log Out → Log In again** with a valid NIM (`F25040126`, `F25040128`, `F25040131` in current DB). Long-term: app should re-validate NIM against `/students/?nim=` on startup instead of trusting cached `id`.

---

## 7. Sisi siswa vs sisi guru — class enrollment mismatch

**Problem:** Active QR session tied to class 5 ("Demo Class", empty) while students 7/9/10 enrolled in class 6 ("Math 999"). Check-in rejected `403 You are not enrolled in this class`.

**Fix:** Teacher must start the session for the **correct class** that contains the students (class 6 "Math 999" or class 7 "Physics", depending on current DB state).

---

## How to reproduce / verify fixes

**QR scanner fix (most important):**
1. Install the new APK (with proguard rules).
2. Log in with a valid NIM (F25040126 / F25040128 / F25040131).
3. Tap **Scan Start QR** → camera should open and show the scanner square.
4. Scan the projected QR → should proceed to selfie camera, then check-in success card.
5. (Optional) Watch logcat: `adb logcat | findstr MOBILE_SCANNER_ERROR` should show only `screen_opened`, no `genericError`.

**Check-in confirmation fix:**
1. After successful start check-in, return to Home.
2. Expect 🟢 green card "You have successfully checked in" and button disabled/greyed.
3. After final check-in, expect 🟢 "Attendance complete" and scan button removed.

---

*Updated: Sat Nov 28 2026*
