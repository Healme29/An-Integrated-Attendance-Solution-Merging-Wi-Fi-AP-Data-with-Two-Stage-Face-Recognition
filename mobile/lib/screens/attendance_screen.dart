import 'package:flutter/material.dart';
import '../models/student.dart';

class AttendanceScreen extends StatelessWidget {
  final AttendanceResult result;

  const AttendanceScreen({
    super.key,
    required this.result,
  });

  Color get _statusColor => result.isVerified ? Colors.green : Colors.deepOrange;

  IconData get _statusIcon => result.isVerified ? Icons.check_circle : Icons.error_outline;

  String get _statusTitle => result.isVerified ? "ATTENDANCE RECORDED" : "CHECK-IN FAILED";

  String get _statusDetail => result.isVerified
      ? "QR code valid, face matched, and your device is on the school network."
      : "The check-in was not recorded. Please try again.";

  @override
  Widget build(BuildContext context) {
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
              if (result.className != null) ...[
                const SizedBox(height: 8),
                Text(
                  "${result.className}${result.room != null ? ' — Room ${result.room}' : ''}",
                  style: const TextStyle(color: Colors.grey),
                ),
              ],
              const SizedBox(height: 16),
              _infoRow("Time", result.timestamp),
              _infoRow(
                "Confidence",
                "${(result.confidence * 100).toStringAsFixed(1)}%",
              ),
              const SizedBox(height: 32),
              ElevatedButton(
                onPressed: () => Navigator.pop(context),
                child: Text(result.isVerified ? "Done" : "Back"),
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
          Flexible(child: Text(value, style: const TextStyle(fontSize: 16))),
        ],
      ),
    );
  }
}