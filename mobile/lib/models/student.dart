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

  QRSessionInfo({
    required this.sessionId,
    required this.token,
    required this.className,
    this.room,
  });
}

class QRValidateResult {
  final bool valid;
  final int? sessionId;
  final String? className;
  final String? room;
  final String? message;

  QRValidateResult({
    required this.valid,
    this.sessionId,
    this.className,
    this.room,
    this.message,
  });

  factory QRValidateResult.fromJson(Map<String, dynamic> json) {
    return QRValidateResult(
      valid: json['valid'] == true,
      sessionId: json['session_id'],
      className: json['class_name'],
      room: json['room'],
      message: json['message'],
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
    );
  }

  /// Attendance confirmed: QR session valid + face matched.
  bool get isVerified => status == 'verified' || status == 'present';
}