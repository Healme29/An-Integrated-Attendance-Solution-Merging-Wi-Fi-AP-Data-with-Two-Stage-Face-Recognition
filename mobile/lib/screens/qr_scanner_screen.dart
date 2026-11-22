import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:face_attendance/services/api_service.dart';
import 'camera_screen.dart';

/// QR scanner screen: the student scans the rotating QR code that the teacher
/// projects in the classroom. A valid token (server-side check, grace period
/// included) opens the selfie camera; an invalid or expired token shows why.
class QRScannerScreen extends StatefulWidget {
  final int studentId;

  const QRScannerScreen({super.key, required this.studentId});

  @override
  State<QRScannerScreen> createState() => _QRScannerScreenState();
}

class _QRScannerScreenState extends State<QRScannerScreen> {
  final MobileScannerController _controller = MobileScannerController(
    detectionSpeed: DetectionSpeed.noDuplicates,
  );
  bool _isProcessing = false;
  bool _scannerDisposed = false;

  /// Release the scanner camera *before* the selfie screen opens its own
  /// controller. Both plugins share the process-wide CameraX provider, so
  /// closing the scanner late (from [dispose]) unbinds the selfie camera's
  /// use cases right after they attach and the preview stays blank.
  Future<void> _releaseScanner() async {
    if (_scannerDisposed) return;
    _scannerDisposed = true;
    try {
      await _controller.stop();
    } catch (_) {/* already stopped */}
    await _controller.dispose();
  }

  @override
  void dispose() {
    if (!_scannerDisposed) {
      _scannerDisposed = true;
      _controller.dispose();
    }
    super.dispose();
  }

  Future<void> _onDetect(BarcodeCapture capture) async {
    if (_isProcessing) return;
    final raw = capture.barcodes.firstOrNull?.rawValue;
    if (raw == null || raw.isEmpty) return;
    if (!mounted) return;
    setState(() => _isProcessing = true);

    try {
      // The QR payload is JSON {"session_id":N,"token":"XXXXXX",...} from the
      // dashboard; fall back to the whole string for plain-token QR codes.
      String token = raw;
      try {
        final payload = json.decode(raw);
        if (payload is Map && payload["token"] is String) {
          token = payload["token"];
        }
      } catch (_) {/* plain token QR: use raw value */ }

      final result = await ApiService.validateQrToken(token);
      if (!mounted) return;
      if (!result.valid) {
        setState(() => _isProcessing = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result.message ?? "Invalid or expired QR code. Scan again."),
            backgroundColor: Colors.orange.shade800,
          ),
        );
        return;
      }

      // Valid: release this screen's camera first so the selfie controller is
      // not torn down by CameraX while it is still attaching.
      await _releaseScanner();
      if (!mounted) return;
      await Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) => CameraScreen(
            studentId: widget.studentId,
            qrToken: token,
            qrSessionId: result.sessionId,
            className: result.className,
          ),
        ),
      );
    } on ApiException catch (e) {
      if (mounted) {
        setState(() => _isProcessing = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.message), backgroundColor: Colors.red),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isProcessing = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Unexpected error: $e"), backgroundColor: Colors.red),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Scan Class QR Code")),
      body: Stack(
        children: [
          MobileScanner(
            controller: _controller,
            onDetect: _onDetect,
          ),
          Align(
            alignment: Alignment.bottomCenter,
            child: Container(
              margin: const EdgeInsets.all(24),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: Colors.black54,
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Text(
                "Point the camera at the QR code shown in class",
                style: TextStyle(color: Colors.white),
              ),
            ),
          ),
          if (_isProcessing)
            const Center(child: CircularProgressIndicator(color: Colors.white)),
        ],
      ),
    );
  }
}