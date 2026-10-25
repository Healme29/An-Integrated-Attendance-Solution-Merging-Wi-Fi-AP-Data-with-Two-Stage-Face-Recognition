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
  CameraController? _controller;
  Future<void>? _initFuture;
  bool _isProcessing = false;

  @override
  void initState() {
    super.initState();
    _initFuture = _initCamera();
  }

  Future<void> _initCamera() async {
    final cameras = await availableCameras();
    // Prefer the front camera for selfies.
    final camera = cameras.firstWhere(
      (c) => c.lensDirection == CameraLensDirection.front,
      orElse: () => cameras.first,
    );
    final controller = CameraController(camera, ResolutionPreset.high);
    await controller.initialize();
    if (!mounted) {
      await controller.dispose();
      return;
    }
    setState(() => _controller = controller);
  }

  Future<void> _takePicture() async {
    final controller = _controller;
    if (controller == null || _isProcessing) return;
    setState(() => _isProcessing = true);

    try {
      final tempDir = await getTemporaryDirectory();
      final filePath = "${tempDir.path}/attendance_${DateTime.now().millisecondsSinceEpoch}.jpg";
      final XFile picture = await controller.takePicture();
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
            builder: (_) => AttendanceScreen(result: result),
          ),
        );
      }
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.message), backgroundColor: Colors.red),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Error: $e"), backgroundColor: Colors.red),
        );
      }
    } finally {
      if (mounted) setState(() => _isProcessing = false);
    }
  }

  @override
  void dispose() {
    // Null-safe: the controller may never have been created when camera
    // initialization failed (e.g. permission denied).
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Scan Face (${widget.checkType.toUpperCase()})")),
      body: FutureBuilder<void>(
        future: _initFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError || _controller == null) {
            // Camera init failed (permission denied, camera busy, ...).
            // Show a human message + how to recover instead of a stuck spinner.
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(32),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.photo_camera_front, size: 64, color: Colors.grey),
                    const SizedBox(height: 16),
                    const Text(
                      "Camera unavailable",
                      style: TextStyle(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      "Camera access failed. If you denied the permission, "
                      "allow the camera for this app in system Settings, then retry.",
                      style: TextStyle(color: Colors.grey),
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton(
                      onPressed: () {
                        setState(() => _initFuture = _initCamera());
                      },
                      child: const Text("Retry"),
                    ),
                  ],
                ),
              ),
            );
          }
          return Stack(
            alignment: Alignment.bottomCenter,
            children: [
              CameraPreview(_controller!),
              if (_isProcessing)
                const Padding(
                  padding: EdgeInsets.all(16),
                  child: CircularProgressIndicator(color: Colors.white),
                ),
            ],
          );
        },
      ),
      floatingActionButton: FloatingActionButton.large(
        onPressed: _isProcessing ? null : _takePicture,
        child: const Icon(Icons.camera, size: 48),
      ),
    );
  }
}
