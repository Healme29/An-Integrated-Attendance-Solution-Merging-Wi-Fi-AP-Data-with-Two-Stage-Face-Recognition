# TASK C — Flutter Mobile App (Frontend)

## Summary
You are responsible for the **Flutter mobile application** used by students for attendance check-in. This app takes selfie photos, sends them to the backend, and displays the result.

---

## FILES TO WORK ON

### 1. `mobile/lib/models/student.dart`
**What already exists:** `Student` model + `AttendanceResult` model.

**What must be fixed:**

#### ⚠️ CRITICAL — Fix Data Contract Mismatch (Priority 1, Blocker #4) [EST: 1 hour]
Problem: Flutter's `AttendanceResult` expects the response from `POST /faces/recognize` (fields: `recognized`, `student_id`, `student_name`, `confidence`), **BUT** the endpoint called by `camera_screen.dart` is `POST /attendance/check` which returns a DIFFERENT response (fields: `id`, `student_id`, `schedule_id`, `check_type`, `confidence`, `wifi_verified`, `status`, `timestamp`).

- [ ] **Create new model `AttendanceCheckResponse`:**
  ```dart
  class AttendanceCheckResponse {
    final int id;
    final int studentId;
    final int scheduleId;
    final String checkType;
    final double? confidence;
    final bool wifiVerified;
    final String status;
    final DateTime timestamp;
    final String? studentName;  // Where to get this? coordinate with B

    AttendanceCheckResponse({...});

    factory AttendanceCheckResponse.fromJson(Map<String, dynamic> json) {...}
  }
  ```
- [ ] **Update `camera_screen.dart`** to display `status` ("present", "face_only", "partial", "verified") on the result screen.
- [ ] **Update `attendance_screen.dart`** to accept `AttendanceCheckResponse` instead of `AttendanceResult`.
- [ ] **Keep old `AttendanceResult`** for the `POST /faces/recognize` endpoint (might be used later).

### 2. `mobile/lib/services/api_service.dart`
**What already exists:** HTTP client with methods `getStudents()`, `createStudent()`, `checkAttendance()`, `scanWifi()`, `getSchedules()`.

**What must be fixed & added:**

#### ⚠️ HIGH — Network Error Handling [EST: 2 hours]
- [ ] **Wrap all API calls** with try-catch. Don't let the app crash due to network errors.
- [ ] **Create helper function:**
  ```dart
  static Future<T> _safeRequest<T>(Future<T> Function() request, T fallback) async {
    try {
      return await request();
    } on SocketException {
      throw Exception("No internet connection. Check your network.");
    } on HttpException {
      throw Exception("Server error. Please try again later.");
    } on FormatException {
      throw Exception("Invalid response from server.");
    }
  }
  ```
- [ ] **Timeout handling:** Add `http.Client` with 30-second timeout.
- [ ] **Retry mechanism:** Add automatic retry option (1x retry for timeout).

#### HIGH — Student Login Screen [EST: 3-4 hours]
- [ ] **Create `lib/screens/login_screen.dart`:**
  - TextField for NIM (student ID number)
  - "Login" button
  - Call `GET /students/` → find student with matching NIM
  - Save `student_id` and `student_name` in SharedPreferences
  - If not found, display error "Student not found. Please contact admin."
- [ ] **Update `api_service.dart`:** Add method `getStudentByNim(String nim)` → `GET /students/?nim={nim}` (coordinate with D for this endpoint).
- [ ] **Update `main.dart`:** After login, navigate to `HomeScreen` with `studentId` parameter.

#### HIGH — Enroll Face Screen [EST: 4-5 hours]
- [ ] **Create `lib/screens/enroll_screen.dart`:**
  - Dropdown to select student (from `GET /students/`)
  - Camera preview
  - "Take Photo" button
  - Call `POST /faces/enroll?student_id=X` with multipart upload
  - Show result: "Face enrolled successfully" + embedding count
  - If failed: "No face detected" or error message
- [ ] **Update `home_screen.dart`:** Add "Enroll Face" button on the main page.

#### MEDIUM — Configurable Server URL [EST: 1-2 hours]
- [ ] **Create `lib/screens/settings_screen.dart`:**
  - TextField for backend URL (default: `http://10.0.2.2:8000`)
  - "Save" button
  - Save URL in SharedPreferences
  - Call `ApiService.setBaseUrl(url)` after saving
- [ ] **Update `home_screen.dart`:** Add gear icon in AppBar for navigation to settings.
- [ ] **Update `main.dart`:** Load URL from SharedPreferences at startup.

#### MEDIUM — Attendance History Screen [EST: 2-3 hours]
- [ ] **Create `lib/screens/history_screen.dart`:**
  - ListView with all attendance records from the logged-in student
  - Call `GET /attendance/student/{student_id}`
  - Display: class_name, check_type, status, timestamp, confidence
  - Color coding: green for "verified"/"present", yellow for "partial"/"face_only", red for error
- [ ] **Update `home_screen.dart`:** Add "My History" button.

#### LOW — UI Polish [EST: 2-3 hours]
- [ ] **Loading states:** Add shimmer/skeleton loader while data is loading.
- [ ] **Empty states:** Display illustration + text if no data (e.g., no schedules, no history).
- [ ] **Responsive layout:** Ensure UI looks good on small (5") and large (7") screens.
- [ ] **Dark mode:** Support dark theme (via `ThemeData` with `brightness: Brightness.dark`).
- [ ] **Localization:** At minimum support English (use `intl` package).

### 3. `mobile/lib/screens/home_screen.dart`
**What already exists:** Schedule dropdown, segmented button (start/end), camera button, scan WiFi button.

**What must be added:**
- [ ] Display the logged-in student's name (from SharedPreferences).
- [ ] "Enroll Face" button → navigate to `EnrollScreen`.
- [ ] "My History" button → navigate to `HistoryScreen`.
- [ ] Settings (gear icon) button → navigate to `SettingsScreen`.
- [ ] Auto-refresh schedules every time the screen appears (call `_loadSchedules()` in `didChangeDependencies`).

### 4. `mobile/lib/screens/camera_screen.dart`
**What already exists:** Camera preview, capture, upload to API.

**What must be fixed:**
- [ ] **Fix response handling:** Replace `AttendanceResult.fromJson` → `AttendanceCheckResponse.fromJson`.
- [ ] **Better error messages:** If status code 400, show error details from backend: `json.decode(response.body)["detail"]`.
- [ ] **Camera permission handling:** If camera is unavailable or permission denied, show a clear message and "Go Back" button.
- [ ] **Flash toggle:** Add flash on/off button for low light conditions.
- [ ] **Face guide overlay:** Add an oval frame in the center of the screen as a face position guide (similar to Face ID).

### 5. `mobile/lib/screens/attendance_screen.dart`
**What already exists:** Check/cancel icon, "ATTENDANCE RECORDED"/"NOT RECOGNIZED" text.

**What must be fixed:**
- [ ] **Update to accept `AttendanceCheckResponse`** — display:
  - `status`: "present"/"face_only"/"partial"/"verified"
  - `wifi_verified`: WiFi check or cross icon
  - `confidence`: visual progress bar
  - `check_type`: "START" or "END"
  - `timestamp`: check-in time
- [ ] **Animation:** Add circular reveal animation or checkmark animation for a better experience.
- [ ] **Vibration & sound:** Add haptic feedback (vibrate) for success/failure.

### 6. `mobile/pubspec.yaml`
**What needs to be added:**
- `flutter_local_notifications` (optional, for notifications)
- Ensure `camera: ^0.11.0+2` is compatible with target SDK.

---

## DEPENDENCIES

| Package | Version | Function |
|---------|---------|----------|
| `http` | ^1.2.2 | HTTP client |
| `camera` | ^0.11.0+2 | Camera |
| `path_provider` | ^2.1.4 | Temp file path |
| `shared_preferences` | ^2.3.2 | Local storage |
| `intl` | ^0.19.0 | Date formatting |
| `flutter` | >=3.0.0 | Framework |

---

## TEAM INTEGRATION
| Module | Depends on | What to coordinate |
|--------|------------|-------------------|
| api_service.dart | B (attendance router) | Response format of `POST /attendance/check` |
| enroll_screen.dart | A (faces router) | Response format of `POST /faces/enroll` |
| login_screen.dart | D (students router) | Endpoint `GET /students?nim=...` |
| history_screen.dart | B (attendance router) | Response format of `GET /attendance/student/{id}` |

---

## TIME ESTIMATES
| Sub-task | Estimate |
|----------|----------|
| Fix data contract mismatch | 1-2 hours |
| Network error handling | 2-3 hours |
| Login screen | 3-4 hours |
| Enroll face screen | 4-5 hours |
| Configurable URL (settings) | 1-2 hours |
| Attendance history screen | 2-3 hours |
| UI Polish | 2-3 hours |
| **Total** | **15-22 hours** |

---

## PRIORITIES
1. ⚠️ **CRITICAL** — Fix data contract (AttendanceCheckResponse model + camera_screen.dart)
2. ⚠️ **HIGH** — Network error handling (app must not crash)
3. **HIGH** — Login screen (so students can log in)
4. **HIGH** — Enroll face screen (so faces can be registered from phone)
5. **MEDIUM** — Configurable URL + history screen
6. **LOW** — UI Polish, animations, dark mode