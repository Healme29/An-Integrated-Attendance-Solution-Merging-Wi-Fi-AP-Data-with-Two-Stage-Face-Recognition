import 'package:flutter/material.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'models/student.dart';
import 'services/api_service.dart';
import 'services/session_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ApiService.init();
  final Student? student = await SessionService.getStudent();
  runApp(FaceAttendanceApp(initialStudent: student));
}

class FaceAttendanceApp extends StatelessWidget {
  final Student? initialStudent;

  const FaceAttendanceApp({super.key, this.initialStudent});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Face Attendance',
      theme: ThemeData(
        colorSchemeSeed: Colors.blue,
        useMaterial3: true,
      ),
      home: initialStudent != null
          ? HomeScreen(student: initialStudent!)
          : const LoginScreen(),
    );
  }
}
