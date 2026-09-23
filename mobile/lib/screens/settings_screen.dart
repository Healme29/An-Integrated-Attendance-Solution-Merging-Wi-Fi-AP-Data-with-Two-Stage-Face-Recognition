import 'package:flutter/material.dart';
import '../services/api_service.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late final TextEditingController _urlController;
  bool _isTesting = false;
  bool? _lastPingOk;

  @override
  void initState() {
    super.initState();
    _urlController = TextEditingController(text: ApiService.baseUrl);
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final url = _urlController.text.trim();
    if (url.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("URL cannot be empty"), backgroundColor: Colors.red),
      );
      return;
    }
    await ApiService.setBaseUrl(url);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Server URL saved: ${ApiService.baseUrl}")),
      );
    }
  }

  Future<void> _testConnection() async {
    setState(() => _isTesting = true);
    final ok = await ApiService.pingServer();
    if (mounted) {
      setState(() => _lastPingOk = ok);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(ok ? "Connected to server" : "Could not reach server"),
          backgroundColor: ok ? Colors.green : Colors.red,
        ),
      );
    }
    if (mounted) setState(() => _isTesting = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Settings")),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text("Backend server URL", style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          const SizedBox(height: 4),
          const Text(
            "Android emulator: http://10.0.2.2:8000\n"
            "Real phone: http://<school-server-ip>:8000",
            style: TextStyle(color: Colors.grey, fontSize: 13),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _urlController,
            keyboardType: TextInputType.url,
            decoration: InputDecoration(
              hintText: "http://192.168.1.100:8000",
              border: const OutlineInputBorder(),
              suffixIcon: _lastPingOk == null
                  ? null
                  : Icon(
                      _lastPingOk! ? Icons.check_circle : Icons.cancel,
                      color: _lastPingOk! ? Colors.green : Colors.red,
                    ),
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: FilledButton(
                  onPressed: _save,
                  child: const Text("Save"),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: OutlinedButton(
                  onPressed: _isTesting ? null : _testConnection,
                  child: _isTesting
                      ? const SizedBox(
                          height: 18,
                          width: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text("Test Connection"),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
