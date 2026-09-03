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
  final bool recognized;
  final int? studentId;
  final String? studentName;
  final double confidence;

  AttendanceResult({
    required this.recognized,
    this.studentId,
    this.studentName,
    required this.confidence,
  });

  factory AttendanceResult.fromJson(Map<String, dynamic> json) {
    return AttendanceResult(
      recognized: json['recognized'],
      studentId: json['student_id'],
      studentName: json['student_name'],
      confidence: (json['confidence'] ?? 0).toDouble(),
    );
  }
}
