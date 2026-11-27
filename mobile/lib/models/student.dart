class Student {
  final int id;
  final String name;
  final String nim;

  Student({
    required this.id,
    required this.name,
    required this.nim,
  });

  factory Student.fromJson(Map<String, dynamic> json) {
    return Student(
      id: json['id'],
      name: json['name'],
      nim: json['nim'],
    );
  }
}

/// Active QR class session returned by the backend.
class QRSessionInfo {
  final int sessionId;
  final String token;
  final String className;
  final String? room;
  final String phase;
  final int spotRound;

  QRSessionInfo({
    required this.sessionId,
    required this.token,
    required this.className,
    this.room,
    this.phase = 'start',
    this.spotRound = 0,
  });

  String get phaseTitle {
    switch (phase) {
      case 'end':
        return 'Final attendance is open';
      case 'spot':
        return 'Spot check is open';
      default:
        return 'Start attendance is open';
    }
  }

  String get scanButtonLabel {
    switch (phase) {
      case 'end':
        return 'Scan Final QR';
      case 'spot':
        return 'Scan Spot-Check QR';
      default:
        return 'Scan Start QR';
    }
  }
}

/// A student's own check-in status for one class session.
///
/// Built from `GET /attendance/student/{id}` (rows carry `qr_session_id`,
/// `check_type`, `spot_round`, `timestamp`). The home screen uses it to show a
/// permanent success card and to disable the scan button once the student has
/// already checked in for the current phase.
class SessionCheckInState {
  final bool startDone;
  final bool endDone;
  final Set<int> spotRounds;
  final String? startTime;
  final String? endTime;

  const SessionCheckInState({
    this.startDone = false,
    this.endDone = false,
    this.spotRounds = const <int>{},
    this.startTime,
    this.endTime,
  });

  bool spotDone(int round) => spotRounds.contains(round);

  /// Keep only the rows belonging to [sessionId] and summarise them.
  factory SessionCheckInState.fromHistory(
    List<Map<String, dynamic>> rows,
    int sessionId,
  ) {
    var start = false;
    var end = false;
    String? startTime;
    String? endTime;
    final spots = <int>{};

    for (final row in rows) {
      final rowSession = row['qr_session_id'];
      if (rowSession is! num || rowSession.toInt() != sessionId) continue;

      final type = (row['check_type'] ?? 'start').toString();
      final timestamp = row['timestamp']?.toString();
      if (type == 'end') {
        end = true;
        endTime ??= timestamp;
      } else if (type == 'spot') {
        final round = row['spot_round'];
        spots.add(round is num ? round.toInt() : 0);
      } else {
        start = true;
        startTime ??= timestamp;
      }
    }

    return SessionCheckInState(
      startDone: start,
      endDone: end,
      spotRounds: spots,
      startTime: startTime,
      endTime: endTime,
    );
  }
}

class QRValidateResult {
  final bool valid;
  final int? sessionId;
  final String? className;
  final String? room;
  final String? message;
  final String phase;
  final int spotRound;

  QRValidateResult({
    required this.valid,
    this.sessionId,
    this.className,
    this.room,
    this.message,
    this.phase = 'start',
    this.spotRound = 0,
  });

  factory QRValidateResult.fromJson(Map<String, dynamic> json) {
    return QRValidateResult(
      valid: json['valid'] == true,
      sessionId: json['session_id'],
      className: json['class_name'],
      room: json['room'],
      message: json['message'],
      phase: json['phase'] ?? 'start',
      spotRound: json['spot_round'] ?? 0,
    );
  }
}

class AttendanceResult {
  final int id;
  final int studentId;
  final String? studentName;
  final int qrSessionId;
  final double confidence;
  final String status;
  final String timestamp;
  final String? className;
  final String? room;
  final String checkType;
  final int spotRound;

  AttendanceResult({
    required this.id,
    required this.studentId,
    this.studentName,
    required this.qrSessionId,
    required this.confidence,
    required this.status,
    required this.timestamp,
    this.className,
    this.room,
    this.checkType = 'start',
    this.spotRound = 0,
  });

  factory AttendanceResult.fromJson(Map<String, dynamic> json) {
    return AttendanceResult(
      id: json['id'],
      studentId: json['student_id'],
      studentName: json['student_name'],
      qrSessionId: json['qr_session_id'],
      confidence: (json['confidence'] ?? 0).toDouble(),
      status: json['status'] ?? 'verified',
      timestamp: json['timestamp'] ?? '',
      className: json['class_name'],
      room: json['room'],
      checkType: json['check_type'] ?? 'start',
      spotRound: json['spot_round'] ?? 0,
    );
  }

  bool get isVerified => status == 'verified' || status == 'present';
  bool get isPartial => status == 'partial';
}