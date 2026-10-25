import 'dart:async';

import 'api_service.dart';

/// One response of GET /me/prompt (see docs/A/auto_prompt_spec.md).
class CheckInPrompt {
  final bool prompt;
  final bool checkAvailable;
  final bool wifiSeen;
  final String? reason;
  final int? scheduleId;
  final String? className;
  final String? room;
  final String? checkType;
  final String? bssid;

  const CheckInPrompt({
    required this.prompt,
    required this.checkAvailable,
    required this.wifiSeen,
    this.reason,
    this.scheduleId,
    this.className,
    this.room,
    this.checkType,
    this.bssid,
  });

  factory CheckInPrompt.fromJson(Map<String, dynamic> json) => CheckInPrompt(
        prompt: json['prompt'] == true,
        checkAvailable: json['check_available'] == true,
        wifiSeen: json['wifi_seen'] == true,
        reason: json['reason'] as String?,
        scheduleId: json['schedule_id'] as int?,
        className: json['class_name'] as String?,
        room: json['room'] as String?,
        checkType: json['check_type'] as String?,
        bssid: json['bssid'] as String?,
      );

  /// Unique key of the offered stage, e.g. "9:start" — lets the service show
  /// each stage exactly once (start banner once, end banner once).
  String? get stageKey =>
      (scheduleId == null || checkType == null) ? null : "$scheduleId:$checkType";

  String get label => "Class ${className ?? '-'} (${room ?? '-'})";
}

/// Polls GET /me/prompt in the background and emits a [CheckInPrompt] on the
/// stream each time a NEW stage becomes actionable. Read-only: it never
/// changes attendance rules — check-ins still go through the normal camera
/// flow, exactly one tap by the student (banner "Check in now").
class PromptService {
  /// Teacher wants a live classroom feel without hammering the server:
  /// the backend Wi-Fi scan caches ~10 s, so 20 s polling is safe.
  static const Duration interval = Duration(seconds: 20);

  final StreamController<CheckInPrompt> _controller =
      StreamController<CheckInPrompt>.broadcast();
  Timer? _timer;
  int? _studentId;
  String? _lastOffered;

  Stream<CheckInPrompt> get stream => _controller.stream;
  bool get isActive => _timer != null;

  /// Begins polling for [studentId]; the first check runs immediately.
  void start(int studentId) {
    stop();
    _studentId = studentId;
    _poll();
    _timer = Timer.periodic(interval, (_) => _poll());
  }

  void stop() {
    _timer?.cancel();
    _timer = null;
  }

  /// Forgets offered stages so the current one can be shown again
  /// (e.g. after the user re-enables auto check-in in Settings).
  void resetOffered() => _lastOffered = null;

  Future<void> _poll() async {
    final id = _studentId;
    if (id == null) return;
    try {
      final data = await ApiService.getCheckInPrompt(id);
      final p = CheckInPrompt.fromJson(data);
      final key = p.stageKey;
      if (p.prompt && key != null && key != _lastOffered) {
        _lastOffered = key;
        _controller.add(p);
      }
    } on ApiException {
      // Server unreachable: stay silent, retry on the next tick.
    } catch (_) {
      // Never let a polling hiccup crash the app.
    }
  }
}
