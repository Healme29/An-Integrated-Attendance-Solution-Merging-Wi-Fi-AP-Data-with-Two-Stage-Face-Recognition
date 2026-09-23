import 'package:flutter/material.dart';
import '../models/student.dart';

class AttendanceScreen extends StatelessWidget {
  final AttendanceResult result;

  const AttendanceScreen({
    super.key,
    required this.result,
  });

  Color get _statusColor {
    if (result.isVerified) return Colors.green;
    if (result.isPartial) return Colors.orange;
    return Colors.deepOrange;
  }

  IconData get _statusIcon {
    if (result.isVerified) return Icons.check_circle;
    if (result.isPartial) return Icons.access_time;
    return Icons.wifi_off;
  }

  String get _statusTitle {
    if (result.isVerified) return "ATTENDANCE VERIFIED";
    if (result.isPartial) return "START CHECK-IN RECORDED";
    return "RECORDED (NO WI-FI)";
  }

  String get _statusDetail {
    if (result.isVerified) {
      return "Both selfies matched and Wi-Fi verified.";
    }
    if (result.isPartial) {
      return "Don't forget to scan again at the end of class.";
    }
    return "Your device was not detected on the class Wi-Fi network.";
  }

  @override
  Widget build(BuildContext context) {
    final bool success = result.isVerified;
    return Scaffold(
      appBar: AppBar(title: const Text("Attendance Result")),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(_statusIcon, size: 100, color: _statusColor),
              const SizedBox(height: 24),
              Text(
                _statusTitle,
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                  color: _statusColor,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                _statusDetail,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 14, color: Colors.grey),
              ),
              const SizedBox(height: 16),
              Text(
                result.studentName ?? "Unknown",
                style: const TextStyle(fontSize: 20),
              ),
              const SizedBox(height: 16),
              _infoRow("Check-in", result.checkType.toUpperCase()),
              _infoRow("Wi-Fi verified", result.wifiVerified ? "Yes" : "No"),
              _infoRow(
                "Confidence",
                "${(result.confidence * 100).toStringAsFixed(1)}%",
              ),
              const SizedBox(height: 32),
              ElevatedButton(
                onPressed: () => Navigator.pop(context),
                child: Text(success ? "Done" : "Back"),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _infoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontSize: 16, color: Colors.grey)),
          Text(value, style: const TextStyle(fontSize: 16)),
        ],
      ),
    );
  }
}
