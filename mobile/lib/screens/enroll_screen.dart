import 'dart:io';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:path_provider/path_provider.dart';
import '../models/student.dart';
import '../services/api_service.dart';

class EnrollScreen extends StatefulWidget {
  final Student student;

  const EnrollScreen({super.key, required this.student});

  @override
  State<EnrollScreen> createState() => _EnrollScreenState();
}

class _EnrollScreenState extends State<EnrollScreen> {
  CameraController? _controller;
  Future<void>? _initFuture;
  bool _isProcessing = false;
  String? _resultMessage;
  Color _resultColor = Colors.blue;

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

  Future<void> _captureAndEnroll() async {
    final controller = _controller;
    if (controller == null || _isProcessing) return;
    setState(() {
      _isProcessing = true;
      _resultMessage = null;
    });

    try {
      final tempDir = await getTemporaryDirectory();
      final filePath = "${tempDir.path}/enroll_${DateTime.now().millisecondsSinceEpoch}.jpg";
      final XFile picture = await controller.takePicture();
      await picture.saveTo(filePath);

      final message = await ApiService.enrollFace(
        studentId: widget.student.id,
        imageFile: File(filePath),
      );

      setState(() {
        _resultMessage = message;
        _resultColor = Colors.green;
      });
    } on ApiException catch (e) {
      setState(() {
        _resultMessage = e.message;
        _resultColor = Colors.red;
      });
    } catch (e) {
      setState(() {
        _resultMessage = "Enrollment failed: $e";
        _resultColor = Colors.red;
      });
    } finally {
      if (mounted) setState(() => _isProcessing = false);
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Enroll Face")),
      body: FutureBuilder<void>(
        future: _initFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError || _controller == null) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.camera_alt, size: 64, color: Colors.grey),
                  const SizedBox(height: 16),
                  const Text("Camera unavailable", style: TextStyle(color: Colors.grey)),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: () {
                      setState(() => _initFuture = _initCamera());
                    },
                    child: const Text("Retry"),
                  ),
                ],
              ),
            );
          }
          return Stack(
            alignment: Alignment.bottomCenter,
            children: [
              CameraPreview(_controller!),
              Positioned(
                top: 16,
                left: 16,
                right: 16,
                child: Card(
                  color: Colors.black54,
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Text(
                      "Look straight at the camera in good lighting, then capture.\nEnrolling for: ${widget.student.name}",
                      style: const TextStyle(color: Colors.white),
                    ),
                  ),
                ),
              ),
              if (_resultMessage != null)
                Positioned(
                  bottom: 120,
                  left: 16,
                  right: 16,
                  child: Card(
                    color: _resultColor.withValues(alpha: 0.9),
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Text(
                        _resultMessage!,
                        style: const TextStyle(color: Colors.white),
                        textAlign: TextAlign.center,
                      ),
                    ),
                  ),
                ),
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
        onPressed: _isProcessing ? null : _captureAndEnroll,
        child: const Icon(Icons.camera, size: 48),
      ),
    );
  }
}
