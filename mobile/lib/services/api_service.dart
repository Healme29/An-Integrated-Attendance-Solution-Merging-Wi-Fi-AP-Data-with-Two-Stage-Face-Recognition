import 'dart:io';
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/student.dart';

class ApiService {
  static String baseUrl = "http://10.0.2.2:8000";

  static void setBaseUrl(String url) {
    baseUrl = url;
  }

  static Future<List<Student>> getStudents() async {
    final response = await http.get(Uri.parse("$baseUrl/students/"));
    if (response.statusCode == 200) {
      List<dynamic> data = json.decode(response.body);
      return data.map((json) => Student.fromJson(json)).toList();
    }
    throw Exception("Failed to load students");
  }

  static Future<Student> createStudent(String name, String nim, String? macAddress) async {
    final response = await http.post(
      Uri.parse("$baseUrl/students/"),
      headers: {"Content-Type": "application/json"},
      body: json.encode({
        "name": name,
        "nim": nim,
        "mac_address": macAddress,
      }),
    );
    if (response.statusCode == 200) {
      return Student.fromJson(json.decode(response.body));
    }
    throw Exception("Failed to create student");
  }

  static Future<AttendanceResult> checkAttendance({
    required int scheduleId,
    required String checkType,
    required File imageFile,
  }) async {
    var request = http.MultipartRequest(
      "POST",
      Uri.parse("$baseUrl/attendance/check?schedule_id=$scheduleId&check_type=$checkType"),
    );
    request.files.add(await http.MultipartFile.fromPath("file", imageFile.path));

    var streamedResponse = await request.send();
    var response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode == 200) {
      return AttendanceResult.fromJson(json.decode(response.body));
    }
    throw Exception(json.decode(response.body)["detail"] ?? "Recognition failed");
  }

  static Future<Map<String, dynamic>> scanWifi() async {
    final response = await http.get(Uri.parse("$baseUrl/wifi/scan"));
    if (response.statusCode == 200) {
      return json.decode(response.body);
    }
    throw Exception("Failed to scan WiFi");
  }

  static Future<List<Map<String, dynamic>>> getSchedules() async {
    final response = await http.get(Uri.parse("$baseUrl/schedules/"));
    if (response.statusCode == 200) {
      List<dynamic> data = json.decode(response.body);
      return data.cast<Map<String, dynamic>>();
    }
    throw Exception("Failed to load schedules");
  }
}
