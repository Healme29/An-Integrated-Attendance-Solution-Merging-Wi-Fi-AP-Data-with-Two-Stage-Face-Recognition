import 'package:flutter/material.dart';
import 'camera_screen.dart';
import 'enroll_screen.dart';
import 'history_screen.dart';
import 'settings_screen.dart';
import 'login_screen.dart';
import 'package:face_attendance/models/student.dart';
import 'package:face_attendance/services/api_service.dart';
import 'package:face_attendance/services/session_service.dart';

class HomeScreen extends StatefulWidget {
  final Student student;

  const HomeScreen({super.key, required this.student});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<Map<String, dynamic>> _schedules = [];
  int? _selectedScheduleId;
  String _selectedCheckType = "start";
  bool _isLoadingSchedules = true;
  String? _schedulesError;

  @override
  void initState() {
    super.initState();
    _loadSchedules();
  }

  Future<void> _loadSchedules() async {
    setState(() {
      _isLoadingSchedules = true;
      _schedulesError = null;
    });
    try {
      final schedules = await ApiService.getSchedules();
      if (!mounted) return;
      setState(() => _schedules = schedules);
    } on ApiException catch (e) {
      if (mounted) setState(() => _schedulesError = e.message);
    } catch (e) {
      if (mounted) setState(() => _schedulesError = "Unexpected error: $e");
    } finally {
      if (mounted) setState(() => _isLoadingSchedules = false);
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

  Future<void> _scanWifi() async {
    try {
      final result = await ApiService.scanWifi();
      if (!mounted) return;
      showDialog(
        context: context,
        builder: (_) => AlertDialog(
          title: const Text("WiFi Scan Result"),
          content: Text("Found ${result['count']} devices on ${result['subnet']}"),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context), child: const Text("OK"))
          ],
        ),
      );
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.message), backgroundColor: Colors.red),
        );
      }
    }
  }

  Future<void> _logout() async {
    await SessionService.logout();
    if (!mounted) return;
    Navigator.pushAndRemoveUntil(
      context,
      MaterialPageRoute(builder: (_) => const LoginScreen()),
      (route) => false,
    );
  }

  void _openEnroll() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => EnrollScreen(student: widget.student)),
    );
  }

  void _openHistory() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => HistoryScreen(student: widget.student)),
    );
  }

  void _openSettings() async {
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const SettingsScreen()),
    );
    // Schedules may change with a new server URL.
    _loadSchedules();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Face Attendance"),
        actions: [
          IconButton(
            icon: const Icon(Icons.history),
            tooltip: "My Attendance",
            onPressed: _openHistory,
          ),
          PopupMenuButton<String>(
            onSelected: (value) {
              switch (value) {
                case "enroll":
                  _openEnroll();
                  break;
                case "settings":
                  _openSettings();
                  break;
                case "logout":
                  _logout();
                  break;
              }
            },
            itemBuilder: (_) => const [
              PopupMenuItem(value: "enroll", child: ListTile(
                leading: Icon(Icons.face),
                title: Text("Enroll Face"),
              )),
              PopupMenuItem(value: "settings", child: ListTile(
                leading: Icon(Icons.settings),
                title: Text("Settings"),
              )),
              PopupMenuItem(value: "logout", child: ListTile(
                leading: Icon(Icons.logout),
                title: Text("Log Out"),
              )),
            ],
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    const CircleAvatar(
                      child: Icon(Icons.person),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            widget.student.name,
                            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                          ),
                          Text(
                            "NIM: ${widget.student.nim}",
                            style: const TextStyle(color: Colors.grey),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text("Select Schedule", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 12),
                    if (_isLoadingSchedules)
                      const Center(child: CircularProgressIndicator())
                    else if (_schedulesError != null)
                      Column(
                        children: [
                          Text(_schedulesError!, style: const TextStyle(color: Colors.red)),
                          const SizedBox(height: 8),
                          ElevatedButton(onPressed: _loadSchedules, child: const Text("Retry")),
                        ],
                      )
                    else
                      DropdownButton<int>(
                        isExpanded: true,
                        value: _selectedScheduleId,
                        hint: const Text("Choose a class schedule"),
                        items: _schedules.map<DropdownMenuItem<int>>((s) => DropdownMenuItem<int>(
                          value: s['id'] as int,
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
              onPressed: _scanWifi,
              icon: const Icon(Icons.wifi),
              label: const Text("Scan WiFi Network"),
            ),
          ],
        ),
      ),
    );
  }
}
