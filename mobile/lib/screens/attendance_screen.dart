import 'package:flutter/material.dart';
import '../models/student.dart';

class AttendanceScreen extends StatelessWidget {
  final AttendanceResult result;

  const AttendanceScreen({
    super.key,
    required this.result,
  });

  Color get _statusColor => result.isVerified ? Colors.green : Colors.deepOrange;

  IconData get _statusIcon => result.isVerified ? Icons.verified : Icons.check_circle_outline;

  String get _statusTitle {
    if (result.checkType == 'spot') return 'SPOT CHECK RECORDED';
    return result.isVerified ? 'ATTENDANCE VERIFIED' : 'START CHECK-IN RECORDED';
  }

  String get _statusDetail {
    if (result.checkType == 'spot') {
      return 'Your spot-check selfie was accepted. Remember to complete the final check-in before class ends.';
    }
    return result.isVerified
        ? 'Both start and final selfies matched. Your attendance is complete.'
        : 'Your first selfie was accepted. Before class ends, scan the final QR and take another selfie to become Verified.';
  }

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
              _infoRow("Stage", switch (result.checkType) {
                'end' => 'Final check-in',
                'spot' => 'Spot check #${result.spotRound}',
                _ => 'Start check-in',
              }),
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