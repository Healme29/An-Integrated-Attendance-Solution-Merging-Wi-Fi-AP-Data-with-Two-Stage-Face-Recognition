import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/student.dart';
import '../services/api_service.dart';

class HistoryScreen extends StatefulWidget {
  final Student student;

  const HistoryScreen({super.key, required this.student});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<Map<String, dynamic>> _records = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final records = await ApiService.getAttendanceHistory(widget.student.id);
      if (!mounted) return;
      setState(() => _records = records);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } catch (e) {
      if (mounted) setState(() => _error = "Unexpected error: $e");
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Color _statusColor(String status) {
    switch (status) {
      case "verified":
      case "present":
        return Colors.green;
      case "partial":
        return Colors.orange;
      case "face_only":
        return Colors.deepOrange;
      default:
        return Colors.grey;
    }
  }

  String _formatTimestamp(String raw) {
    final parsed = DateTime.tryParse(raw);
    if (parsed == null) return raw;
    return DateFormat("dd MMM yyyy, HH:mm").format(parsed);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("My Attendance")),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(_error!, textAlign: TextAlign.center, style: const TextStyle(color: Colors.red)),
                      const SizedBox(height: 16),
                      ElevatedButton(onPressed: _loadHistory, child: const Text("Retry")),
                    ],
                  ),
                )
              : _records.isEmpty
                  ? const Center(
                      child: Text("No attendance records yet", style: TextStyle(color: Colors.grey)),
                    )
                  : RefreshIndicator(
                      onRefresh: _loadHistory,
                      child: ListView.separated(
                        padding: const EdgeInsets.all(12),
                        itemCount: _records.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 8),
                        itemBuilder: (context, index) {
                          final record = _records[index];
                          final status = (record["status"] ?? "pending").toString();
                          final confidence = (record["confidence"] as num? ?? 0) * 100;
                          return Card(
                            child: ListTile(
                              leading: CircleAvatar(
                                backgroundColor: _statusColor(status),
                                child: Icon(
                                  status == "verified" || status == "present"
                                      ? Icons.check
                                      : status == "partial"
                                          ? Icons.access_time
                                          : Icons.wifi_off,
                                  color: Colors.white,
                                ),
                              ),
                              title: Text(
                                record["class_name"]?.toString() ?? "Class",
                                style: const TextStyle(fontWeight: FontWeight.bold),
                              ),
                              subtitle: Text(
                                "${_formatTimestamp(record["timestamp"]?.toString() ?? "")}\n"
                                "${record["check_type"]?.toString().toUpperCase()} - "
                                "Wi-Fi: ${record["wifi_verified"] == 1 || record["wifi_verified"] == true ? "Yes" : "No"} - "
                                "Confidence: ${confidence.toStringAsFixed(1)}%",
                              ),
                              isThreeLine: true,
                              trailing: Chip(
                                label: Text(status, style: const TextStyle(color: Colors.white, fontSize: 12)),
                                backgroundColor: _statusColor(status),
                              ),
                            ),
                          );
                        },
                      ),
                    ),
    );
  }
}
