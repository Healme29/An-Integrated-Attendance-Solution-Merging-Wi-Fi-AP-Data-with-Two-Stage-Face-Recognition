import 'package:flutter/material.dart';
import 'package:face_attendance/models/student.dart';
import 'package:face_attendance/services/session_service.dart';
import 'package:face_attendance/services/api_service.dart';
import 'enroll_screen.dart';
import 'history_screen.dart';
import 'settings_screen.dart';
import 'login_screen.dart';
import 'qr_scanner_screen.dart';

class HomeScreen extends StatefulWidget {
  final Student student;

  const HomeScreen({super.key, required this.student});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  QRSessionInfo? _activeSession;
  bool _isLoadingSession = true;
  String? _sessionError;

  @override
  void initState() {
    super.initState();
    _loadActiveSession();
  }

  Future<void> _loadActiveSession() async {
    setState(() {
      _isLoadingSession = true;
      _sessionError = null;
    });
    try {
      final session = await ApiService.getActiveSession();
      if (!mounted) return;
      setState(() {
        _activeSession = session;
        _isLoadingSession = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _activeSession = null;
        _isLoadingSession = false;
        _sessionError = e is ApiException ? e.message : e.toString();
      });
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

  Future<void> _openSettings() async {
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const SettingsScreen()),
    );
    if (mounted) _loadActiveSession();
  }

  void _scanQr() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => QRScannerScreen(studentId: widget.student.id),
      ),
    ).then((_) {
      if (mounted) _loadActiveSession();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Student Attendance"),
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
                child: _isLoadingSession
                    ? const Center(child: CircularProgressIndicator())
                    : _sessionError != null
                        ? Column(
                            children: [
                              const Icon(Icons.cloud_off, size: 44, color: Colors.grey),
                              const SizedBox(height: 8),
                              const Text(
                                "Cannot load the class session",
                                style: TextStyle(fontWeight: FontWeight.bold),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                _sessionError!,
                                textAlign: TextAlign.center,
                                style: const TextStyle(color: Colors.grey),
                              ),
                              TextButton(
                                onPressed: _loadActiveSession,
                                child: const Text("Retry"),
                              ),
                            ],
                          )
                        : _activeSession == null
                        ? const Column(
                            children: [
                              Icon(Icons.event_busy, size: 44, color: Colors.grey),
                              SizedBox(height: 8),
                              Text(
                                "No active class session right now",
                                style: TextStyle(fontWeight: FontWeight.bold),
                              ),
                              SizedBox(height: 4),
                              Text(
                                "Ask your teacher to start a class session, then scan the QR code shown in class.",
                                textAlign: TextAlign.center,
                                style: TextStyle(color: Colors.grey),
                              ),
                            ],
                          )
                        : Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Row(
                                children: [
                                  Icon(Icons.qr_code, size: 20),
                                  SizedBox(width: 8),
                                  Text(
                                    "Class in progress",
                                    style: TextStyle(fontWeight: FontWeight.bold),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 4),
                              Text(
                                "${_activeSession!.className}"
                                "${_activeSession!.room != null ? ' — Room ${_activeSession!.room}' : ''}",
                                style: const TextStyle(color: Colors.grey),
                              ),
                            ],
                          ),
              ),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: _scanQr,
              icon: const Icon(Icons.qr_code_scanner),
              label: const Text("Scan QR Code", style: TextStyle(fontSize: 18)),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 20),
              ),
            ),
          ],
        ),
      ),
    );
  }
}