import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/student.dart';

class SessionService {
  static const String _studentKey = "logged_in_student";
  static const String _autoPromptKey = "auto_check_in_on";

  /// Auto check-in prompt toggle (Settings). ON by default.
  static Future<bool> getAutoPromptOn() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_autoPromptKey) ?? true;
  }

  static Future<void> setAutoPromptOn(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_autoPromptKey, value);
  }

  static Future<void> saveStudent(Student student) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_studentKey, json.encode({
      "id": student.id,
      "name": student.name,
      "nim": student.nim,
      "mac_address": student.macAddress,
    }));
  }

  static Future<Student?> getStudent() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_studentKey);
    if (raw == null) return null;
    try {
      return Student.fromJson(json.decode(raw));
    } catch (_) {
      return null;
    }
  }

  static Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_studentKey);
  }
}
