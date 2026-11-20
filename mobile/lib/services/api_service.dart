import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/student.dart';

class ApiException implements Exception {
  final String message;
  ApiException(this.message);

  @override
  String toString() => message;
}

class ApiService {
  static const String _urlKey = "backend_base_url";

  /// Default points at the laptop's Mobile Hotspot address (Windows always
  /// assigns 192.168.137.1 to the hotspot host). For USB
  /// (`adb reverse tcp:8000 tcp:8000`) override in Settings with
  /// http://127.0.0.1:8000 instead.
  static const String _defaultBaseUrl = "http://192.168.137.1:8000";
  static const Duration _timeout = Duration(seconds: 20);
  static const Duration _uploadTimeout = Duration(seconds: 60);

  static String baseUrl = _defaultBaseUrl;

  static Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    baseUrl = prefs.getString(_urlKey) ?? _defaultBaseUrl;
  }

  static Future<void> setBaseUrl(String url) async {
    baseUrl = url.endsWith("/") ? url.substring(0, url.length - 1) : url;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_urlKey, baseUrl);
  }

  static Map<String, String> get _jsonHeaders => {"Content-Type": "application/json"};

  /// Throws [ApiException] with a user-friendly message on any failure.
  static Future<dynamic> _get(String path) async {
    try {
      final response = await http
          .get(Uri.parse("$baseUrl$path"), headers: _jsonHeaders)
          .timeout(_timeout);
      return _handleResponse(response);
    } on SocketException {
      throw ApiException("Cannot reach server. Check your connection and backend URL.");
    } on TimeoutException {
      throw ApiException(
          "Server took too long to respond. Open Settings and check the server URL "
          "(with USB attached, use http://127.0.0.1:8000 and run: adb reverse tcp:8000 tcp:8000).");
    } on http.ClientException {
      throw ApiException("Cannot reach server. Check the backend URL in Settings.");
    }
  }

  static Future<dynamic> _send(
    String method,
    String path, {
    Map<String, dynamic>? body,
    File? imageFile,
  }) async {
    try {
      http.Response response;
      if (imageFile != null) {
        final request = http.MultipartRequest("POST", Uri.parse("$baseUrl$path"));
        request.files.add(await http.MultipartFile.fromPath("file", imageFile.path));
        final streamed = await request.send().timeout(_uploadTimeout);
        response = await http.Response.fromStream(streamed);
      } else {
        final request = http.Request(method, Uri.parse("$baseUrl$path"));
        request.headers.addAll(_jsonHeaders);
        if (body != null) request.body = json.encode(body);
        final client = http.Client();
        try {
          final streamed = await client.send(request).timeout(_timeout);
          response = await http.Response.fromStream(streamed);
        } finally {
          client.close();
        }
      }
      return _handleResponse(response);
    } on SocketException {
      throw ApiException("Cannot reach server. Check your connection and backend URL.");
    } on TimeoutException {
      throw ApiException("Server took too long to respond.");
    } on http.ClientException {
      throw ApiException("Cannot reach server. Check the backend URL in Settings.");
    }
  }

  static dynamic _handleResponse(http.Response response) {
    dynamic decoded;
    try {
      decoded = json.decode(response.body);
    } catch (_) {
      decoded = null;
    }
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return decoded;
    }
    String detail = "Request failed (${response.statusCode})";
    if (decoded is Map && decoded["detail"] != null) {
      detail = decoded["detail"].toString();
    }
    throw ApiException(detail);
  }

  static Future<List<Student>> getStudents() async {
    final data = await _get("/students/") as List<dynamic>;
    return data.map((json) => Student.fromJson(json)).toList();
  }

  /// Login lookup: returns the student with this NIM, or null if not found.
  static Future<Student?> findStudentByNim(String nim) async {
    final data = await _get("/students/?nim=$nim") as List<dynamic>;
    if (data.isEmpty) return null;
    return Student.fromJson(data.first);
  }

  static Future<Student> createStudent(String name, String nim) async {
    final data = await _send("POST", "/students/", body: {
      "name": name,
      "nim": nim,
    });
    return Student.fromJson(data);
  }

  /// Active QR class session (teacher started it from the dashboard), or null.
  static Future<QRSessionInfo?> getActiveSession() async {
    final data = await _get("/qr-sessions/active");
    if (data is! Map || data["active"] != true) return null;
    return QRSessionInfo(
      sessionId: data["session_id"],
      token: data["token"],
      className: data["class_name"] ?? "Class",
      room: data["room"],
      phase: data["phase"] ?? "start",
      spotRound: data["spot_round"] ?? 0,
    );
  }

  /// Validate a scanned QR token before opening the selfie camera.
  static Future<QRValidateResult> validateQrToken(String token) async {
    final data = await _send("POST", "/qr-sessions/validate", body: {
      "token": token,
    });
    return QRValidateResult.fromJson(Map<String, dynamic>.from(data));
  }

  /// QR-based check-in: the scanned token + a fresh selfie.
  static Future<AttendanceResult> checkInQr({
    required int studentId,
    required String token,
    required File imageFile,
  }) async {
    final data = await _send(
      "POST",
      "/attendance/check-qr?student_id=$studentId&token=$token",
      imageFile: imageFile,
    );
    return AttendanceResult.fromJson(data);
  }

  /// Enroll a face for a student from a captured selfie.
  static Future<String> enrollFace({required int studentId, required File imageFile}) async {
    final data = await _send(
      "POST",
      "/faces/enroll?student_id=$studentId",
      imageFile: imageFile,
    );
    return data["message"] ?? "Face enrolled";
  }

  static Future<List<Map<String, dynamic>>> getAttendanceHistory(int studentId) async {
    final data = await _get("/attendance/student/$studentId") as List<dynamic>;
    return data.cast<Map<String, dynamic>>();
  }

  /// Quick connectivity probe for the Settings screen.
  static Future<bool> pingServer() async {
    try {
      final response = await http
          .get(Uri.parse("$baseUrl/"), headers: _jsonHeaders)
          .timeout(const Duration(seconds: 5));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }
}