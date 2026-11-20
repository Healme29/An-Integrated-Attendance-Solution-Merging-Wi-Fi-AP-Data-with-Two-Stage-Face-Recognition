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