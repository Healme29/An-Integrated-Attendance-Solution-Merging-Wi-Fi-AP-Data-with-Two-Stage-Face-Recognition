class Student {
  final int id;
  final String name;
  final String nim;
  final String? macAddress;

  Student({
    required this.id,
    required this.name,
    required this.nim,
    this.macAddress,
  });

  factory Student.fromJson(Map<String, dynamic> json) {
    return Student(
      id: json['id'],
      name: json['name'],
      nim: json['nim'],
      macAddress: json['mac_address'],
    );
  }
}

class AttendanceResult {
  final int id;
  final int studentId;
  final String? studentName;
  final int scheduleId;
  final String checkType;
  final double confidence;
  final bool wifiVerified;
  final String status;
  final String timestamp;

  AttendanceResult({
    required this.id,
    required this.studentId,
    this.studentName,
    required this.scheduleId,
    required this.checkType,
    required this.confidence,
    required this.wifiVerified,
    required this.status,
    required this.timestamp,
  });

  factory AttendanceResult.fromJson(Map<String, dynamic> json) {
    return AttendanceResult(
      id: json['id'],
      studentId: json['student_id'],
      studentName: json['student_name'],
      scheduleId: json['schedule_id'],
      checkType: json['check_type'],
      confidence: (json['confidence'] ?? 0).toDouble(),
      wifiVerified: json['wifi_verified'] == true || json['wifi_verified'] == 1,
      status: json['status'] ?? 'pending',
      timestamp: json['timestamp'] ?? '',
    );
  }

  /// Attendance fully confirmed: both selfies matched + Wi-Fi verified.
  bool get isVerified => status == 'verified' || status == 'present';

  /// Start check-in recorded, waiting for the end-of-class selfie.
  bool get isPartial => status == 'partial';
}
