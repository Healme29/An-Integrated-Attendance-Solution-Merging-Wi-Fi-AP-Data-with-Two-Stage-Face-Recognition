import 'dart:async';

import 'package:flutter/material.dart';
import 'package:zhen_dao/models/student.dart';
import 'package:zhen_dao/services/session_service.dart';
import 'package:zhen_dao/services/api_service.dart';
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
  Timer? _pollTimer;

  @override
  void initState() {
    super.initState();
    _loadActiveSession();
    // Lightweight notification for the demo: when the teacher changes phase,
    // the open app updates its instructions within a few seconds.
    _pollTimer = Timer.periodic(
      const Duration(seconds: 5),
      (_) => _loadActiveSession(silent: true),
    );
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadActiveSession({bool silent = false}) async {
    if (!silent && mounted) {
      setState(() {
        _isLoadingSession = true;
        _sessionError = null;
      });
    }
    try {
      final session = await ApiService.getActiveSession();
      if (!mounted) return;
      setState(() {
        _activeSession = session;
        _isLoadingSession = false;
        _sessionError = null;
      });
    } catch (e) {
      if (!mounted || silent) return;
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
    final session = _activeSession;
    if (session == null) return;
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => QRScannerScreen(studentId: widget.student.id),
      ),
    ).then((_) {
      if (mounted) _loadActiveSession();
    });
  }

  Widget _sessionCard() {
    if (_isLoadingSession) {
      return const Padding(
        padding: EdgeInsets.all(20),
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (_sessionError != null) {
      return _messageCard(
        icon: Icons.cloud_off,
        title: 'Cannot load the class session',
        detail: _sessionError!,
        action: TextButton.icon(
          onPressed: _loadActiveSession,
          icon: const Icon(Icons.refresh),
          label: const Text('Retry'),
        ),
      );
    }
    final session = _activeSession;
    if (session == null) {
      return _messageCard(
        icon: Icons.event_available,
        title: 'No active class session',
        detail: 'Your teacher has not opened attendance yet. This page updates automatically.',
      );
    }

    final isFinal = session.phase == 'end';
    final isSpot = session.phase == 'spot';
    final color = isFinal ? Colors.green.shade700 : isSpot ? Colors.deepPurple : Colors.orange.shade800;
    final instruction = isFinal
        ? 'Scan the NEW final QR, then take your final selfie. Start + final selfies make your attendance Verified.'
        : isSpot
            ? 'Your teacher opened a spot check. Scan the QR and take another selfie to confirm you are still in class.'
            : 'Scan the start QR and take your first selfie. Your status will be Partial until the final check-in.';

    return Padding(
      padding: const EdgeInsets.all(18),
      child: Column(
        children: [
          Icon(isFinal ? Icons.verified : isSpot ? Icons.fact_check : Icons.qr_code_2,
              size: 46, color: color),
          const SizedBox(height: 10),
          Text(
            session.phaseTitle,
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: color),
          ),
          const SizedBox(height: 6),
          Text(
            '${session.className}${session.room != null ? ' · Room ${session.room}' : ''}',
            textAlign: TextAlign.center,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 10),
          Text(
            instruction,
            textAlign: TextAlign.center,
            style: const TextStyle(color: Colors.black54, height: 1.35),
          ),
          if (isSpot) ...[
            const SizedBox(height: 6),
            Text('Spot check #${session.spotRound}', style: const TextStyle(color: Colors.black45)),
          ],
        ],
      ),
    );
  }

  Widget _messageCard({
    required IconData icon,
    required String title,
    required String detail,
    Widget? action,
  }) {
    return Padding(
      padding: const EdgeInsets.all(18),
      child: Column(
        children: [
          Icon(icon, size: 46, color: Colors.grey),
          const SizedBox(height: 10),
          Text(title, textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
          const SizedBox(height: 6),
          Text(detail, textAlign: TextAlign.center, style: const TextStyle(color: Colors.black54)),
          if (action != null) action,
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final session = _activeSession;
    return Scaffold(
      appBar: AppBar(
        title: const Text('真到'),
        actions: [
          IconButton(
            icon: const Icon(Icons.history),
            tooltip: 'My Attendance',
            onPressed: _openHistory,
          ),
          PopupMenuButton<String>(
            onSelected: (value) {
              if (value == 'enroll') _openEnroll();
              if (value == 'settings') _openSettings();
              if (value == 'logout') _logout();
            },
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'enroll', child: ListTile(leading: Icon(Icons.face), title: Text('Enroll Face'))),
              PopupMenuItem(value: 'settings', child: ListTile(leading: Icon(Icons.settings), title: Text('Settings'))),
              PopupMenuItem(value: 'logout', child: ListTile(leading: Icon(Icons.logout), title: Text('Log Out'))),
            ],
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadActiveSession,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Card(
              child: ListTile(
                leading: const CircleAvatar(child: Icon(Icons.person)),
                title: Text(widget.student.name, style: const TextStyle(fontWeight: FontWeight.bold)),
                subtitle: Text('NIM: ${widget.student.nim}'),
              ),
            ),
            const SizedBox(height: 12),
            Card(child: _sessionCard()),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: session == null ? null : _scanQr,
              icon: const Icon(Icons.qr_code_scanner, size: 28),
              label: Text(
                session?.scanButtonLabel ?? 'Waiting for teacher',
                style: const TextStyle(fontSize: 18),
              ),
              style: FilledButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 20)),
            ),
            const SizedBox(height: 10),
            const Text(
              'Two steps: start QR + selfie now, final QR + selfie before class ends.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.black45, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }
}
