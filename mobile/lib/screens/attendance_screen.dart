import 'package:flutter/material.dart';
import '../models/student.dart';

class AttendanceScreen extends StatelessWidget {
  final AttendanceResult result;
  final String checkType;

  const AttendanceScreen({
    super.key,
    required this.result,
    required this.checkType,
  });

  @override
  Widget build(BuildContext context) {
    final bool success = result.recognized;
    return Scaffold(
      appBar: AppBar(title: const Text("Attendance Result")),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                success ? Icons.check_circle : Icons.cancel,
                size: 100,
                color: success ? Colors.green : Colors.red,
              ),
              const SizedBox(height: 24),
              Text(
                success ? "ATTENDANCE RECORDED" : "NOT RECOGNIZED",
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                  color: success ? Colors.green : Colors.red,
                ),
              ),
              const SizedBox(height: 16),
              if (success) ...[
                Text(result.studentName ?? "Unknown", style: const TextStyle(fontSize: 20)),
                const SizedBox(height: 8),
                Text(
                  "Check-in Type: ${checkType.toUpperCase()}",
                  style: const TextStyle(fontSize: 16, color: Colors.grey),
                ),
                const SizedBox(height: 8),
                Text(
                  "Confidence: ${(result.confidence * 100).toStringAsFixed(1)}%",
                  style: const TextStyle(fontSize: 16, color: Colors.grey),
                ),
              ],
              const SizedBox(height: 32),
              ElevatedButton(
                onPressed: () => Navigator.pop(context),
                child: const Text("Back"),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
