import 'package:flutter/material.dart';
import 'camera_screen.dart';
import 'package:face_attendance/services/api_service.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<Map<String, dynamic>> _schedules = [];
  int? _selectedScheduleId;
  String _selectedCheckType = "start";

  @override
  void initState() {
    super.initState();
    _loadSchedules();
  }

  Future<void> _loadSchedules() async {
    try {
      final schedules = await ApiService.getSchedules();
      setState(() {
        _schedules = schedules;
      });
    } catch (e) {
      debugPrint("Error loading schedules: $e");
    }
  }

  void _openCamera() {
    if (_selectedScheduleId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Please select a schedule first")),
      );
      return;
    }
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => CameraScreen(
          scheduleId: _selectedScheduleId!,
          checkType: _selectedCheckType,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Face Attendance")),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text("Select Schedule", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 12),
                    DropdownButton<int>(
                      isExpanded: true,
                      value: _selectedScheduleId,
                      hint: const Text("Choose a class schedule"),
                      items: _schedules.map((s) => DropdownMenuItem(
                        value: s['id'],
                        child: Text("${s['class_name']} - ${s['room'] ?? 'N/A'}"),
                      )).toList(),
                      onChanged: (val) => setState(() => _selectedScheduleId = val),
                    ),
                    const SizedBox(height: 12),
                    SegmentedButton<String>(
                      segments: const [
                        ButtonSegment(value: "start", label: Text("Start")),
                        ButtonSegment(value: "end", label: Text("End")),
                      ],
                      selected: {_selectedCheckType},
                      onSelectionChanged: (val) => setState(() => _selectedCheckType = val.first),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: _openCamera,
              icon: const Icon(Icons.camera_alt),
              label: const Text("Open Camera", style: TextStyle(fontSize: 18)),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 20),
              ),
            ),
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: () async {
                final result = await ApiService.scanWifi();
                if (context.mounted) {
                  showDialog(
                    context: context,
                    builder: (_) => AlertDialog(
                      title: const Text("WiFi Scan Result"),
                      content: Text("Found ${result['count']} devices"),
                      actions: [
                        TextButton(onPressed: () => Navigator.pop(context), child: const Text("OK"))
                      ],
                    ),
                  );
                }
              },
              icon: const Icon(Icons.wifi),
              label: const Text("Scan WiFi Network"),
            ),
          ],
        ),
      ),
    );
  }
}
