"""Tests for Wi-Fi subnet detection and bounded ping sweeps.

These cover the real-network finding in docs/B/network_validation.md (F1):
the old code always assumed /24 and pinged .1-.254 of the last octet.
"""
import ipaddress

import pytest

from services import wifi_scanner
from services.wifi_scanner import (
    _parse_ip_neigh_output,
    parse_ip_addr_prefix,
    parse_ipconfig_prefix,
    sweep_hosts,
)


class TestParsePrefix:
    def test_linux_ip_addr_line(self):
        output = (
            "2: wlan0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500\n"
            "    inet 10.163.235.210/17 brd 10.163.255.255 scope global dynamic wlan0\n"
        )
        assert parse_ip_addr_prefix(output, "10.163.235.210") == 17

    def test_linux_ip_addr_ignores_other_interfaces(self):
        output = (
            "    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0\n"
            "    inet 192.168.1.50/24 brd 192.168.1.255 scope global wlan0\n"
        )
        assert parse_ip_addr_prefix(output, "192.168.1.50") == 24

    def test_linux_ip_addr_missing_ip(self):
        assert parse_ip_addr_prefix("    inet 10.0.0.1/8 scope global eth0\n", "192.168.1.5") is None

    def test_windows_ipconfig_block(self):
        output = (
            "Windows IP Configuration\n"
            "\n"
            "Wireless LAN adapter Wi-Fi:\n"
            "\n"
            "   Connection-specific DNS Suffix  . : campus.edu\n"
            "   IPv4 Address. . . . . . . . . . . : 10.163.235.210\n"
            "   Subnet Mask . . . . . . . . . . . : 255.255.128.0\n"
            "   Default Gateway . . . . . . . . . : 10.163.255.254\n"
            "\n"
            "Ethernet adapter Ethernet:\n"
            "\n"
            "   IPv4 Address. . . . . . . . . . . : 192.168.1.20\n"
            "   Subnet Mask . . . . . . . . . . . : 255.255.255.0\n"
        )
        assert parse_ipconfig_prefix(output, "10.163.235.210") == 17
        assert parse_ipconfig_prefix(output, "192.168.1.20") == 24

    def test_windows_ipconfig_without_match(self):
        assert parse_ipconfig_prefix("Windows IP Configuration\n", "10.0.0.5") is None


class TestSweepHosts:
    def test_slash_24_sweeps_254_hosts(self):
        hosts = sweep_hosts("192.168.1.0/24")
        assert len(hosts) == 254
        assert hosts[0] == "192.168.1.1"
        assert hosts[-1] == "192.168.1.254"

    def test_smaller_network_is_honoured(self):
        hosts = sweep_hosts("192.168.1.0/25")
        assert len(hosts) == 126
        assert hosts[0] == "192.168.1.1"
        assert hosts[-1] == "192.168.1.126"

    def test_wide_network_is_capped_to_one_slash_24(self, monkeypatch):
        monkeypatch.setattr(wifi_scanner, "get_local_ipv4", lambda: "10.163.235.210")
        hosts = sweep_hosts("10.163.128.0/17")
        assert len(hosts) == 254
        assert all(host.startswith("10.163.235.") for host in hosts)

    def test_wide_network_without_local_ip_uses_first_slash_24(self, monkeypatch):
        monkeypatch.setattr(wifi_scanner, "get_local_ipv4", lambda: None)
        hosts = sweep_hosts("10.163.128.0/17")
        assert len(hosts) == 254
        assert hosts[0] == "10.163.128.1"

    def test_bare_ip_is_treated_as_slash_24(self):
        hosts = sweep_hosts("192.168.1.0")
        assert len(hosts) == 254


class TestResolveSubnet:
    def test_explicit_slash_24_wins(self, monkeypatch):
        monkeypatch.setattr(wifi_scanner, "WI_FI_SUBNET", "192.168.1.0/24")
        assert wifi_scanner.resolve_subnet() == "192.168.1.0/24"

    def test_explicit_narrower_network_is_kept(self, monkeypatch):
        monkeypatch.setattr(wifi_scanner, "WI_FI_SUBNET", "192.168.1.0/26")
        assert wifi_scanner.resolve_subnet() == "192.168.1.0/26"

    def test_explicit_wide_network_is_reduced_to_local_slash_24(self, monkeypatch):
        monkeypatch.setattr(wifi_scanner, "WI_FI_SUBNET", "10.163.128.0/17")
        monkeypatch.setattr(wifi_scanner, "get_local_ipv4", lambda: "10.163.235.210")
        assert wifi_scanner.resolve_subnet() == "10.163.235.0/24"

    def test_invalid_config_falls_back_to_auto_detect(self, monkeypatch):
        monkeypatch.setattr(wifi_scanner, "WI_FI_SUBNET", "not-a-subnet")
        monkeypatch.setattr(
            wifi_scanner, "detect_local_subnet", lambda: "192.168.50.0/24"
        )
        assert wifi_scanner.resolve_subnet() == "192.168.50.0/24"

    def test_auto_detect_uses_real_netmask(self, monkeypatch):
        monkeypatch.setattr(wifi_scanner, "WI_FI_SUBNET", None)
        monkeypatch.setattr(wifi_scanner, "get_local_ipv4", lambda: "10.163.235.210")
        monkeypatch.setattr(
            wifi_scanner, "detect_local_network",
            lambda: ipaddress.IPv4Network("10.163.128.0/17"),
        )
        # Wider than /24 -> the reported range is exactly what is swept.
        assert wifi_scanner.resolve_subnet() == "10.163.235.0/24"

    def test_auto_detect_keeps_narrower_interface_network(self, monkeypatch):
        monkeypatch.setattr(wifi_scanner, "WI_FI_SUBNET", None)
        monkeypatch.setattr(
            wifi_scanner, "detect_local_network",
            lambda: ipaddress.IPv4Network("192.168.1.0/24"),
        )
        assert wifi_scanner.resolve_subnet() == "192.168.1.0/24"


class TestParseIpNeigh:
    def test_parses_lladdr_entries(self):
        output = (
            "10.163.235.210 dev wlan0 lladdr aa:bb:cc:dd:ee:ff REACHABLE\n"
            "10.163.255.254 dev wlan0 lladdr 70:c6:dd:09:b0:02 STALE\n"
        )
        devices = _parse_ip_neigh_output(output)
        assert len(devices) == 2
        assert devices[0] == {"ip": "10.163.235.210", "mac": "aa:bb:cc:dd:ee:ff"}

    def test_skips_failed_entries(self):
        output = "10.163.235.99 dev wlan0  FAILED\n"
        assert _parse_ip_neigh_output(output) == []


class TestUnprivilegedFallback:
    def test_scapy_permission_error_falls_back_to_neigh(self, monkeypatch):
        scapy_all = pytest.importorskip("scapy.all")

        def deny(*_args, **_kwargs):
            raise PermissionError("Operation not permitted")

        sentinel = [{"ip": "192.168.1.10", "mac": "aa:bb:cc:dd:ee:ff"}]
        monkeypatch.setattr(scapy_all, "srp", deny)
        monkeypatch.setattr(wifi_scanner, "_scan_linux_neigh", lambda *_: sentinel)

        assert wifi_scanner._scan_linux("192.168.1.0/24", 1) == sentinel


class TestBssidParsers:
    def test_iw_link_connected(self):
        output = (
            "Connected to 50:98:b8:c9:2b:e2 (on wlp3s0)\n"
            "\tSSID: ClassroomAP\n"
            "\tfreq: 5180.0\n"
        )
        assert wifi_scanner.parse_iw_link_bssid(output) == "50:98:b8:c9:2b:e2"

    def test_iw_link_not_connected(self):
        assert wifi_scanner.parse_iw_link_bssid("Not connected.\n") is None

    def test_iw_link_ignores_neighbouring_ap_list(self):
        # 'iw dev <iface> link' only reports the current link, but make sure a
        # BSSID from an unrelated line is not picked up as the association.
        output = (
            "Not connected.\n"
            "    bss aa:bb:cc:dd:ee:ff\n"
        )
        assert wifi_scanner.parse_iw_link_bssid(output) is None

    def test_nmcli_active_row(self):
        output = (
            "no:11:22:33:44:55:66\n"
            "yes:50:98:B8:C9:2B:E2\n"
            "no:aa:bb:cc:dd:ee:01\n"
        )
        assert wifi_scanner.parse_nmcli_bssid(output) == "50:98:b8:c9:2b:e2"

    def test_nmcli_real_terse_output_escapes_colons(self):
        # Captured verbatim from `nmcli -t -f ACTIVE,BSSID device wifi` on
        # Ubuntu 24.04: terse mode backslash-escapes ':' inside values.
        output = (
            "no:50\\:98\\:B8\\:C9\\:2B\\:F0\n"
            "no:50\\:98\\:B8\\:C9\\:2B\\:F2\n"
            "yes:50\\:98\\:B8\\:C9\\:2B\\:E2\n"
            "no:F4\\:74\\:88\\:70\\:C2\\:F3\n"
        )
        assert wifi_scanner.parse_nmcli_bssid(output) == "50:98:b8:c9:2b:e2"

    def test_nmcli_without_active_row(self):
        output = "no:11:22:33:44:55:66\nno:aa:bb:cc:dd:ee:01\n"
        assert wifi_scanner.parse_nmcli_bssid(output) is None

    def test_nmcli_handles_empty_bssid_field(self):
        # nmcli prints an empty BSSID for hidden/placeholder rows: 'no:'
        assert wifi_scanner.parse_nmcli_bssid("no:\n") is None


class TestLinuxBssidProbes:
    """The BSSID must not depend on 'iwconfig', which current distros drop."""

    @pytest.fixture(autouse=True)
    def _reset_state(self):
        wifi_scanner._BSSID_CACHE.update({"value": None, "ok": False, "timestamp": 0.0})
        wifi_scanner._BSSID_WARNED["value"] = False
        yield
        wifi_scanner._BSSID_CACHE.update({"value": None, "ok": False, "timestamp": 0.0})
        wifi_scanner._BSSID_WARNED["value"] = False

    @staticmethod
    def _fake_run(handlers):
        """Build a subprocess.run replacement from {'iw dev': output, ...}.

        A key that maps to FileNotFoundError simulates a missing binary, which
        is exactly the 'iwconfig is gone' case on a minimal install.
        """
        calls = []

        def run(cmd, **_kwargs):
            calls.append(cmd)
            joined = " ".join(cmd)
            # Longest prefix first so 'iw dev wlp3s0 link' wins over 'iw dev'.
            for prefix in sorted(handlers, key=len, reverse=True):
                if joined.startswith(prefix):
                    response = handlers[prefix]
                    if isinstance(response, Exception):
                        raise response
                    return type("R", (), {"stdout": response, "stderr": "", "returncode": 0})()
            raise FileNotFoundError(f"No such file or directory: {cmd[0]}")

        run.calls = calls
        return run

    def test_iw_preferred_over_iwconfig(self, monkeypatch):
        run = self._fake_run({
            "iw dev": "phy#0\n\tInterface wlp3s0\n",
            "iw dev wlp3s0 link": "Connected to 50:98:b8:c9:2b:e2 (on wlp3s0)\n",
            "iwconfig": "wlp3s0  Access Point: 11:22:33:44:55:66\n",
        })
        monkeypatch.setattr(wifi_scanner.subprocess, "run", run)
        monkeypatch.setattr(wifi_scanner.platform, "system", lambda: "Linux")

        assert wifi_scanner.get_current_bssid(use_cache=False) == "50:98:b8:c9:2b:e2"
        assert "iw dev wlp3s0 link" in [" ".join(c) for c in run.calls]

    def test_falls_back_to_nmcli_when_iw_missing(self, monkeypatch):
        run = self._fake_run({
            "iw dev": FileNotFoundError("iw"),
            "nmcli": "yes:50:98:B8:C9:2B:E2\n",
        })
        monkeypatch.setattr(wifi_scanner.subprocess, "run", run)
        monkeypatch.setattr(wifi_scanner.platform, "system", lambda: "Linux")

        assert wifi_scanner.get_current_bssid(use_cache=False) == "50:98:b8:c9:2b:e2"

    def test_falls_back_to_iwconfig_last(self, monkeypatch):
        run = self._fake_run({
            "iw dev": FileNotFoundError("iw"),
            "nmcli": FileNotFoundError("nmcli"),
            "iwconfig": (
                'wlp3s0  IEEE 802.11  ESSID:"ClassroomAP"\n'
                "          Mode:Managed  Access Point: A4:2B:B0:12:34:56\n"
            ),
        })
        monkeypatch.setattr(wifi_scanner.subprocess, "run", run)
        monkeypatch.setattr(wifi_scanner.platform, "system", lambda: "Linux")

        assert wifi_scanner.get_current_bssid(use_cache=False) == "a4:2b:b0:12:34:56"

    def test_not_associated_returns_none_without_warning(self, monkeypatch, caplog):
        run = self._fake_run({
            "iw dev": "\tInterface wlp3s0\n",
            "iw dev wlp3s0 link": "Not connected.\n",
            "nmcli": "no:11:22:33:44:55:66\n",
            "iwconfig": "wlp3s0  ESSID:off/any  Access Point: Not-Associated\n",
        })
        monkeypatch.setattr(wifi_scanner.subprocess, "run", run)
        monkeypatch.setattr(wifi_scanner.platform, "system", lambda: "Linux")

        with caplog.at_level("WARNING"):
            assert wifi_scanner.get_current_bssid(use_cache=False) is None
        assert "Cannot read the current BSSID" not in caplog.text

    def test_no_tool_available_warns_once(self, monkeypatch, caplog):
        run = self._fake_run({
            "iw dev": FileNotFoundError("iw"),
            "nmcli": FileNotFoundError("nmcli"),
            "iwconfig": FileNotFoundError("iwconfig"),
        })
        monkeypatch.setattr(wifi_scanner.subprocess, "run", run)
        monkeypatch.setattr(wifi_scanner.platform, "system", lambda: "Linux")

        with caplog.at_level("WARNING"):
            assert wifi_scanner.get_current_bssid(use_cache=False) is None
            assert wifi_scanner.get_current_bssid(use_cache=False) is None

        # Degradation is visible in the log, but only once per process.
        assert caplog.text.count("Cannot read the current BSSID") == 1
        assert "face_only" in caplog.text


class TestPingCommand:
    def test_darwin_uses_bsd_compatible_flags(self, monkeypatch):
        monkeypatch.setattr(wifi_scanner.platform, "system", lambda: "Darwin")
        cmd = wifi_scanner._ping_command("192.168.1.1", 200)
        # BSD ping has no portable millisecond per-packet flag; -W must not
        # be passed (it is the Linux-only seconds variant).
        assert cmd == ["ping", "-c", "1", "192.168.1.1"]

    def test_linux_uses_second_granularity_timeout(self, monkeypatch):
        monkeypatch.setattr(wifi_scanner.platform, "system", lambda: "Linux")
        cmd = wifi_scanner._ping_command("192.168.1.1", 200)
        assert cmd == ["ping", "-c", "1", "-W", "1", "192.168.1.1"]

    def test_windows_uses_milliseconds(self, monkeypatch):
        monkeypatch.setattr(wifi_scanner.platform, "system", lambda: "Windows")
        cmd = wifi_scanner._ping_command("192.168.1.1", 200)
        assert cmd == ["ping", "-n", "1", "-w", "200", "192.168.1.1"]
