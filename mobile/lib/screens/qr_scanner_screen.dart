import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:zhen_dao/services/api_service.dart';
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

  /// Restart the scanner camera after a failure (permission granted late,
  /// camera still held by another app, or the preview was unbound).
  Future<void> _restartScanner() async {
    if (_scannerDisposed) return;
    try {
      await _controller.stop();
    } catch (_) {/* not running */}
    try {
      await _controller.start();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Still cannot open the camera: $e"), backgroundColor: Colors.red),
      );
    }
  }

  /// Shown instead of the default black screen with an error icon, so a student
  /// can see *why* the camera did not start and recover without reinstalling.
  Widget _buildCameraError(
    BuildContext context,
    MobileScannerException error,
    Widget? child,
  ) {
    final denied = error.errorCode == MobileScannerErrorCode.permissionDenied;
    final unsupported = error.errorCode == MobileScannerErrorCode.unsupported;
    final message = denied
        ? "Camera permission is blocked. Open Settings > Apps > Zhen Dao > "
            "Permissions, allow Camera, then press Retry."
        : unsupported
            ? "This device cannot scan QR codes with its camera."
            : "The camera could not start. Close other apps that use the "
                "camera (or lock and unlock the screen), then press Retry.";
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.no_photography, size: 64, color: Colors.grey),
            const SizedBox(height: 16),
            const Text(
              "Camera unavailable",
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
            ),
            const SizedBox(height: 8),
            Text(
              message,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: _restartScanner,
              icon: const Icon(Icons.refresh),
              label: const Text("Retry"),
            ),
          ],
        ),
      ),
    );
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
            phase: result.phase,
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
      // The framing square and the hint would sit on top of the error message,
      // so they are hidden while the scanner reports a camera problem.
      body: ValueListenableBuilder<MobileScannerState>(
        valueListenable: _controller,
        builder: (context, state, _) {
          final hasError = state.error != null;
          return Stack(
            children: [
              MobileScanner(
                controller: _controller,
                onDetect: _onDetect,
                errorBuilder: _buildCameraError,
              ),
              if (!hasError)
                Center(
                  child: Container(
                    width: 260,
                    height: 260,
                    decoration: BoxDecoration(
                      border: Border.all(color: Colors.white, width: 3),
                      borderRadius: BorderRadius.circular(18),
                      boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 8)],
                    ),
                  ),
                ),
              if (!hasError)
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
                      "Fit the classroom QR inside the square.\nHold still until it is detected.",
                      textAlign: TextAlign.center,
                      style: TextStyle(color: Colors.white),
                    ),
                  ),
                ),
              if (_isProcessing)
                const Center(child: CircularProgressIndicator(color: Colors.white)),
            ],
          );
        },
      ),
    );
  }
}