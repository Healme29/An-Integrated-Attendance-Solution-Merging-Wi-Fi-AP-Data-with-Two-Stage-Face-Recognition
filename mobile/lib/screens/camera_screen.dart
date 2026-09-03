import 'dart:io';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:path_provider/path_provider.dart';
import '../services/api_service.dart';
import 'attendance_screen.dart';

class CameraScreen extends StatefulWidget {
  final int scheduleId;
  final String checkType;

  const CameraScreen({
    super.key,
    required this.scheduleId,
    required this.checkType,
  });

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> {
  late CameraController _controller;
  late Future<void> _initFuture;
  bool _isProcessing = false;

  @override
  void initState() {
    super.initState();
    _initFuture = _initCamera();
  }

  Future<void> _initCamera() async {
    final cameras = await availableCameras();
    _controller = CameraController(cameras.first, ResolutionPreset.high);
    await _controller.initialize();
  }

  Future<void> _takePicture() async {
    if (_isProcessing) return;
    setState(() => _isProcessing = true);

    try {
      final tempDir = await getTemporaryDirectory();
      final filePath = "${tempDir.path}/attendance_${DateTime.now().millisecondsSinceEpoch}.jpg";
      final XFile picture = await _controller.takePicture();
      await picture.saveTo(filePath);

      final result = await ApiService.checkAttendance(
        scheduleId: widget.scheduleId,
        checkType: widget.checkType,
        imageFile: File(filePath),
      );

      if (mounted) {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(
            builder: (_) => AttendanceScreen(result: result, checkType: widget.checkType),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Error: $e")),
        );
      }
    } finally {
      if (mounted) setState(() => _isProcessing = false);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Scan Face (${widget.checkType.toUpperCase()})")),
      body: FutureBuilder<void>(
        future: _initFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.done) {
            return Stack(
              alignment: Alignment.bottomCenter,
              children: [
                CameraPreview(_controller),
                if (_isProcessing)
                  const Padding(
                    padding: EdgeInsets.all(16),
                    child: CircularProgressIndicator(color: Colors.white),
                  ),
              ],
            );
          }
          return const Center(child: CircularProgressIndicator());
        },
      ),
      floatingActionButton: FloatingActionButton.large(
        onPressed: _isProcessing ? null : _takePicture,
        child: const Icon(Icons.camera, size: 48),
      ),
    );
  }
}
