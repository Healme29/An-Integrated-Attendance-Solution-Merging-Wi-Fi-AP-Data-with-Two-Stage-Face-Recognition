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
  static const String _defaultBaseUrl = "http://10.0.2.2:8000";
  static const Duration _timeout = Duration(seconds: 15);

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
      throw ApiException("Server took too long to respond.");
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
        final streamed = await request.send().timeout(_timeout);
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

  static Future<Student> createStudent(String name, String nim, String? macAddress) async {
    final data = await _send("POST", "/students/", body: {
      "name": name,
      "nim": nim,
      "mac_address": macAddress,
    });
    return Student.fromJson(data);
  }

  static Future<AttendanceResult> checkAttendance({
    required int scheduleId,
    required String checkType,
    required File imageFile,
  }) async {
    final data = await _send(
      "POST",
      "/attendance/check?schedule_id=$scheduleId&check_type=$checkType",
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

  static Future<Map<String, dynamic>> scanWifi() async {
    return await _get("/wifi/scan");
  }

  static Future<List<Map<String, dynamic>>> getSchedules() async {
    final data = await _get("/schedules/") as List<dynamic>;
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
