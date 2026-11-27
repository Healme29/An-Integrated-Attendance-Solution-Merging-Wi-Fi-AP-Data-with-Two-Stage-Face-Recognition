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

/// What the session card and the scan button should show for the running
/// phase, given the student's *own* check-in status for that session.
class _PhaseView {
  final bool done; // the student already checked in for this phase
  final bool hideButton; // no button at all (final check-in completed)
  final Color color;
  final IconData icon;
  final String title;
  final String detail;
  final String buttonLabel; // label used while the button is active

  const _PhaseView({
    required this.done,
    required this.hideButton,
    required this.color,
    required this.icon,
    required this.title,
    required this.detail,
    required this.buttonLabel,
  });
}

class _HomeScreenState extends State<HomeScreen> {
  QRSessionInfo? _activeSession;
  SessionCheckInState? _checkState;
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
      // A failure to read the student's own history must never break the home
      // screen; it simply falls back to "nothing recorded yet".
      SessionCheckInState? checkState;
      if (session != null) {
        checkState = await _loadCheckState(session.sessionId);
      }
      if (!mounted) return;
      setState(() {
        _activeSession = session;
        _checkState = checkState;
        _isLoadingSession = false;
        _sessionError = null;
      });
    } catch (e) {
      if (!mounted || silent) return;
      setState(() {
        _activeSession = null;
        _checkState = null;
        _isLoadingSession = false;
        _sessionError = e is ApiException ? e.message : e.toString();
      });
    }
  }

  Future<SessionCheckInState?> _loadCheckState(int sessionId) async {
    try {
      final rows = await ApiService.getAttendanceHistory(widget.student.id);
      return SessionCheckInState.fromHistory(rows, sessionId);
    } catch (_) {
      return null;
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

  /// Map the active phase + the student's own check-in status to the card text
  /// and the scan button behaviour.
  _PhaseView _phaseView(QRSessionInfo session, SessionCheckInState? state) {
    final green = Colors.green.shade700;

    if (session.phase == 'end') {
      if (state?.endDone ?? false) {
        return _PhaseView(
          done: true,
          hideButton: true,
          color: green,
          icon: Icons.verified,
          title: 'Attendance complete',
          detail: 'You are marked present. No further check-in is needed.'
              '${state?.endTime != null ? '\nFinal check-in: ${state!.endTime}' : ''}',
          buttonLabel: '',
        );
      }
      return _PhaseView(
        done: false,
        hideButton: false,
        color: green,
        icon: Icons.verified,
        title: 'Final attendance is open',
        detail: 'Scan the NEW final QR, then take your final selfie to complete your attendance.',
        buttonLabel: 'Scan Final QR',
      );
    }

    if (session.phase == 'spot') {
      if (state?.spotDone(session.spotRound) ?? false) {
        return _PhaseView(
          done: true,
          hideButton: false,
          color: green,
          icon: Icons.check_circle,
          title: 'Spot check recorded',
          detail: 'Your selfie for spot check #${session.spotRound} was accepted.',
          buttonLabel: '',
        );
      }
      return const _PhaseView(
        done: false,
        hideButton: false,
        color: Colors.deepPurple,
        icon: Icons.fact_check,
        title: 'Spot check is open',
        detail: 'Your teacher opened a spot check. Scan the QR and take another selfie to confirm you are still in class.',
        buttonLabel: 'Scan Spot-Check QR',
      );
    }

    // phase == 'start'
    if (state?.startDone ?? false) {
      return _PhaseView(
        done: true,
        hideButton: false,
        color: green,
        icon: Icons.check_circle,
        title: 'You have successfully checked in',
        detail: 'Start attendance recorded'
            '${state?.startTime != null ? ' at ${state!.startTime}.' : '.'}'
            '\nBefore class ends, scan the final QR to become Verified.',
        buttonLabel: '',
      );
    }
    return _PhaseView(
      done: false,
      hideButton: false,
      color: Colors.orange.shade800,
      icon: Icons.qr_code_2,
      title: 'Start attendance is open',
      detail: 'Scan the start QR and take your first selfie. Your status will be Partial until the final check-in.',
      buttonLabel: 'Scan Start QR',
    );
  }

  Widget _sessionCard(QRSessionInfo session, _PhaseView view) {
    return Padding(
      padding: const EdgeInsets.all(18),
      child: Column(
        children: [
          Icon(view.icon, size: 46, color: view.color),
          const SizedBox(height: 10),
          Text(
            view.title,
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: view.color),
          ),
          const SizedBox(height: 6),
          Text(
            '${session.className}${session.room != null ? ' · Room ${session.room}' : ''}',
            textAlign: TextAlign.center,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 10),
          Text(
            view.detail,
            textAlign: TextAlign.center,
            style: const TextStyle(color: Colors.black54, height: 1.35),
          ),
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

  Widget _buildCard(_PhaseView? view) {
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
    return _sessionCard(session, view!);
  }

  Widget _buildButton(_PhaseView? view) {
    final session = _activeSession;

    // No running session: keep the original disabled "Waiting for teacher".
    if (session == null) {
      return FilledButton.icon(
        onPressed: null,
        icon: const Icon(Icons.qr_code_scanner, size: 28),
        label: const Text('Waiting for teacher', style: TextStyle(fontSize: 18)),
        style: FilledButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 20)),
      );
    }

    // Final check-in already done: the button disappears for good.
    if (view!.hideButton) return const SizedBox.shrink();

    // Already checked in for this phase: greyed out so the student knows.
    if (view.done) {
      return FilledButton.icon(
        onPressed: null,
        icon: const Icon(Icons.check_circle, size: 28),
        label: const Text('Already checked in', style: TextStyle(fontSize: 18)),
        style: FilledButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 20)),
      );
    }

    return FilledButton.icon(
      onPressed: _scanQr,
      icon: const Icon(Icons.qr_code_scanner, size: 28),
      label: Text(view.buttonLabel, style: const TextStyle(fontSize: 18)),
      style: FilledButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 20)),
    );
  }

  @override
  Widget build(BuildContext context) {
    final session = _activeSession;
    final view = session == null ? null : _phaseView(session, _checkState);

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
            Card(child: _buildCard(view)),
            const SizedBox(height: 20),
            _buildButton(view),
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
