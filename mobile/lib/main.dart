import 'package:flutter/material.dart';
import 'screens/home_screen.dart';

void main() {
  runApp(const FaceAttendanceApp());
}

class FaceAttendanceApp extends StatelessWidget {
  const FaceAttendanceApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Face Attendance',
      theme: ThemeData(
        colorSchemeSeed: Colors.blue,
        useMaterial3: true,
      ),
      home: const HomeScreen(),
    );
  }
}
