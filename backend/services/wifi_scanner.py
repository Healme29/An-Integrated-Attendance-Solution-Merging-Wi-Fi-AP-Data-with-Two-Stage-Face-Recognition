import socket
import subprocess
import platform
import re
import time
import concurrent.futures
import ipaddress
import logging
from datetime import datetime
from config import WI_FI_SCAN_TIMEOUT, WI_FI_SUBNET

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 10
_scan_cache: dict = {"devices": None, "timestamp": 0.0}

# A ping sweep of more than /24 is not practical from a laptop (a /16 means
# 65k hosts and minutes per scan). Every sweep is therefore capped at 254
# addresses; the range that is actually swept is the one reported by
# resolve_subnet(), never a wider one (see docs/B/network_validation.md F1).
_MAX_SWEEP_HOSTS = 254


def get_local_ipv4() -> str | None:
    """Local IPv4 address the OS would use for outbound traffic.

    Opens a UDP socket to a public IP (no packets are sent) so the kernel
    picks the primary interface. Returns None if no route is available.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()
    except Exception:
        return None


def parse_ip_addr_prefix(output: str, local_ip: str) -> int | None:
    """Parse the prefix length of ``local_ip`` from `ip -4 addr show` output."""
    for line in output.splitlines():
        match = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)/(\d+)", line)
        if match and match.group(1) == local_ip:
            return int(match.group(2))
    return None


def parse_ipconfig_prefix(output: str, local_ip: str) -> int | None:
    """Parse the prefix length of ``local_ip`` from Windows `ipconfig` output.

    Adapter blocks are separated by lines that start in column 0. Inside the
    block that owns ``local_ip`` the `Subnet Mask` line is converted to a
    prefix length (e.g. 255.255.128.0 -> /17).
    """
    for block in re.split(r"\n(?=\S)", output):
        if local_ip not in block:
            continue
        mask_match = re.search(
            r"Subnet Mask[ .]*:\s*(\d+\.\d+\.\d+\.\d+)", block, re.IGNORECASE
        )
        if not mask_match:
            continue
        try:
            return ipaddress.IPv4Network(
                f"0.0.0.0/{mask_match.group(1)}", strict=False
            ).prefixlen
        except ValueError:
            return None
    return None


def detect_local_network() -> ipaddress.IPv4Network | None:
    """Network of the primary interface, using its REAL netmask.

    Campus and some office networks hand out /16-/23 addresses. The old
    implementation always assumed /24, so devices in neighbouring /24s were
    never scanned (docs/B/network_validation.md F1). Falls back to /24 when
    the netmask cannot be read, which keeps the previous behaviour.
    """
    local_ip = get_local_ipv4()
    if not local_ip:
        return None

    prefix = None
    system = platform.system()
    try:
        if system == "Linux":
            result = subprocess.run(
                ["ip", "-4", "addr", "show"],
                capture_output=True, text=True, timeout=2,
            )
            prefix = parse_ip_addr_prefix(result.stdout or "", local_ip)
        elif system == "Windows":
            result = subprocess.run(
                ["ipconfig"], capture_output=True, text=True, timeout=5
            )
            prefix = parse_ipconfig_prefix(result.stdout or "", local_ip)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        prefix = None

    if prefix is None:
        parts = local_ip.split(".")
        return ipaddress.IPv4Network(f"{parts[0]}.{parts[1]}.{parts[2]}.0/24")
    return ipaddress.IPv4Network(f"{local_ip}/{prefix}", strict=False)


def detect_local_subnet() -> str | None:
    """Sweepable subnet of the primary interface (never wider than /24).

    Reports the /24 that contains the local IP, so the value returned by
    `/wifi/scan` is exactly the range that was actually pinged. When the
    interface is wider than /24 a warning is logged with the real network.
    """
    network = detect_local_network()
    if network is None:
        return None
    if network.prefixlen < 24:
        local_ip = get_local_ipv4() or str(network.network_address)
        slice_network = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
        logger.warning(
            "Interface network %s is wider than /24; sweeping only %s. "
            "Set WI_FI_SUBNET explicitly if the clients live elsewhere.",
            network, slice_network,
        )
        return str(slice_network)
    return str(network)


def resolve_subnet() -> str:
    """Sweepable subnet: explicit config wins, else auto-detected, else fallback.

    An explicit WI_FI_SUBNET wider than /24 is reduced to the /24 that
    contains this machine (a /16 sweep is not feasible); the reduction is
    logged so the operator sees what really happened.
    """
    if WI_FI_SUBNET:
        try:
            configured = ipaddress.IPv4Network(WI_FI_SUBNET, strict=False)
        except ValueError:
            logger.warning("WI_FI_SUBNET=%r is not a valid network; auto-detecting", WI_FI_SUBNET)
            return detect_local_subnet() or "192.168.1.0/24"
        if configured.prefixlen < 24:
            local_ip = get_local_ipv4()
            if local_ip and ipaddress.IPv4Address(local_ip) in configured:
                sweep = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
            else:
                first_host = next(configured.hosts(), configured.network_address)
                sweep = ipaddress.IPv4Network(f"{first_host}/24", strict=False)
            logger.warning(
                "WI_FI_SUBNET=%s is wider than /24; sweeping only %s",
                configured, sweep,
            )
            return str(sweep)
        return str(configured)
    return detect_local_subnet() or "192.168.1.0/24"


def normalize_mac(mac: str) -> str:
    """Normalize a MAC address to lowercase colon-separated format.

    Handles 'AA-BB-CC-DD-EE-FF', 'aabbccddeeff', 'AA:BB:CC:DD:EE:FF'.
    Returns the input lowercased if it is not a valid MAC.
    """
    clean = re.sub(r"[^0-9a-f]", "", mac.lower())
    if len(clean) != 12:
        return mac.lower()
    return ":".join(clean[i:i + 2] for i in range(0, 12, 2))


def scan_network_arp(subnet: str | None = None, timeout: int = WI_FI_SCAN_TIMEOUT, use_cache: bool = True) -> list[dict]:
    """Scan local network using ARP requests. Returns list of {ip, mac}.

    Results are cached for 10 seconds to avoid rescanning per check-in.
    Pass use_cache=False to force a fresh scan. If subnet is None it is
    resolved from explicit config or auto-detected.
    """
    now = time.time()
    if use_cache and _scan_cache["devices"] is not None:
        if now - _scan_cache["timestamp"] < _CACHE_TTL_SECONDS:
            return _scan_cache["devices"]

    subnet = subnet or resolve_subnet()
    system = platform.system()

    if system == "Windows":
        devices = _scan_windows(subnet, timeout)
    else:
        devices = _scan_linux(subnet, timeout)

    _scan_cache["devices"] = devices
    _scan_cache["timestamp"] = now
    return devices


def sweep_hosts(subnet: str) -> list[str]:
    """Host addresses to ping for ``subnet``, capped at _MAX_SWEEP_HOSTS.

    Honours the real prefix (a /25 sweeps 126 hosts, not 254) and stays
    bounded for wider ranges (a /16 is cut to the /24 containing this
    machine) so a scan can never take minutes.
    """
    try:
        # Accept bare IP (no prefix) as /24 for backward compatibility
        if "/" not in subnet and re.match(r"^\d+\.\d+\.\d+\.\d+$", subnet.strip()):
            network = ipaddress.IPv4Network(f"{subnet.strip()}/24", strict=False)
        else:
            network = ipaddress.IPv4Network(subnet, strict=False)
    except ValueError:
        network = ipaddress.IPv4Network(f"{subnet}/24", strict=False)

    if network.prefixlen < 24:
        local_ip = get_local_ipv4()
        if local_ip and ipaddress.IPv4Address(local_ip) in network:
            network = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
        else:
            first_host = next(network.hosts(), network.network_address)
            network = ipaddress.IPv4Network(f"{first_host}/24", strict=False)

    return [str(host) for host in network.hosts()][:_MAX_SWEEP_HOSTS]


def _ping_command(ip: str, timeout_ms: int) -> list[str]:
    """Platform-correct single-packet ping command."""
    if platform.system() == "Windows":
        return ["ping", "-n", "1", "-w", str(timeout_ms), ip]
    if platform.system() == "Darwin":
        return ["ping", "-c", "1", "-W", str(timeout_ms), ip]
    return ["ping", "-c", "1", "-W", str(max(1, timeout_ms // 1000)), ip]


def _ping_sweep(subnet: str, timeout_ms: int = 200):
    """Ping every host in the subnet to populate the ARP/neighbour cache.

    Without this, `arp -a` / `ip neigh` only reports entries already in the
    cache (usually just this machine and the gateway).
    """
    def ping(ip: str):
        try:
            subprocess.run(
                _ping_command(ip, timeout_ms),
                capture_output=True,
                timeout=timeout_ms / 1000 + 1,
            )
        except Exception:
            pass

    ips = sweep_hosts(subnet)
    with concurrent.futures.ThreadPoolExecutor(max_workers=64) as pool:
        list(pool.map(ping, ips))


def _scan_windows(subnet: str, timeout: int) -> list[dict]:
    """Windows: ping sweep + 'arp -a'."""
    try:
        _ping_sweep(subnet)
        result = subprocess.run(
            ["arp", "-a"],
            capture_output=True, text=True, timeout=timeout
        )
        return _parse_arp_output(result.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def _scan_linux(subnet: str, timeout: int) -> list[dict]:
    """Linux: scapy ARP scan, with an unprivileged fallback.

    Raw sockets need CAP_NET_RAW (root or file capabilities). On a demo
    machine started by a normal user scapy raises PermissionError, so the
    scanner falls back to a ping sweep + `ip neigh` / `arp -a` parse, which
    needs no privileges. The fallback also covers Docker images without
    NET_RAW.
    """
    try:
        from scapy.all import ARP, Ether, srp
    except ImportError:
        return _scan_linux_neigh(subnet, timeout)

    try:
        arp = ARP(pdst=subnet)
        ether = Ether(dst="ff:ff:ff:ff:ff:ff")
        packet = ether / arp
        answered, _ = srp(packet, timeout=timeout, verbose=0)
        return [
            {"ip": r.psrc, "mac": normalize_mac(r.hwsrc)}
            for _, r in answered
            if _is_unicast_device(normalize_mac(r.hwsrc))
        ]
    except Exception as exc:  # PermissionError, OSError, Scapy_Exception, ...
        logger.warning("scapy ARP scan failed (%s); using ping + neighbour fallback", exc)
        return _scan_linux_neigh(subnet, timeout)


def _scan_linux_neigh(subnet: str, timeout: int) -> list[dict]:
    """Linux without raw-socket privileges: ping sweep + neighbour table."""
    try:
        _ping_sweep(subnet)
        result = subprocess.run(
            ["ip", "neigh", "show"], capture_output=True, text=True, timeout=timeout + 5
        )
        devices = _parse_ip_neigh_output(result.stdout or "")
        if devices:
            return devices
        result = subprocess.run(
            ["arp", "-a"], capture_output=True, text=True, timeout=timeout + 5
        )
        return _parse_arp_output(result.stdout or "")
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []


def _parse_ip_neigh_output(output: str) -> list[dict]:
    """Parse `ip neigh show` output into [{ip, mac}]."""
    devices = []
    pattern = re.compile(r"(\d+\.\d+\.\d+\.\d+)\s+.*lladdr\s+([0-9a-fA-F:]{17})")
    for match in pattern.finditer(output):
        mac = normalize_mac(match.group(2))
        if _is_unicast_device(mac):
            devices.append({"ip": match.group(1), "mac": mac})
    return devices


def _is_unicast_device(mac: str) -> bool:
    """True for real unicast devices; filters broadcast/multicast entries."""
    first_octet = mac.split(":")[0]
    return not (
        mac == "ff:ff:ff:ff:ff:ff"
        or int(first_octet, 16) & 1  # multicast bit set
    )


def _parse_arp_output(output: str) -> list[dict]:
    """Parse Windows arp -a output."""
    devices = []
    pattern = re.compile(r"(\d+\.\d+\.\d+\.\d+)\s+([\w-]{17})")
    for match in pattern.finditer(output):
        mac = normalize_mac(match.group(2))
        if _is_unicast_device(mac):
            devices.append({"ip": match.group(1), "mac": mac})
    return devices


def check_mac_on_network(mac_address: str, devices: list[dict] | None = None) -> bool:
    """Check if a MAC address is present on the network."""
    if not mac_address:
        return False
    if devices is None:
        devices = scan_network_arp()
    target = normalize_mac(mac_address)
    return any(normalize_mac(d["mac"]) == target for d in devices)


_BSSID_CACHE = {"value": None, "ok": False, "timestamp": 0.0}
_BSSID_CACHE_TTL = 10

_MAC_PATTERN = re.compile(r"([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}")


def parse_netsh_bssid(output: str) -> str | None:
    """Parse the associated BSSID from 'netsh wlan show interfaces' output."""
    for line in output.splitlines():
        if "bssid" in line.lower():
            match = _MAC_PATTERN.search(line)
            if match:
                return normalize_mac(match.group(0))
    return None


def parse_iwconfig_bssid(output: str) -> str | None:
    """Parse the associated BSSID from 'iwconfig' output."""
    for line in output.splitlines():
        lowered = line.lower()
        if "access point" in lowered and "not-associated" not in lowered:
            match = _MAC_PATTERN.search(line)
            if match:
                return normalize_mac(match.group(0))
    return None


def get_current_bssid(use_cache: bool = True) -> str | None:
    """BSSID of the AP this machine is currently associated with.

    Used to enforce schedules.ap_bssid: devices found on the network can
    only be attributed to the scheduled AP when the server itself is
    connected to it. Returns None when not on Wi-Fi or unsupported.
    """
    now = time.time()
    if use_cache and _BSSID_CACHE["ok"]:
        if now - _BSSID_CACHE["timestamp"] < _BSSID_CACHE_TTL:
            return _BSSID_CACHE["value"]

    system = platform.system()
    bssid = None
    try:
        if system == "Windows":
            result = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True, text=True, timeout=5
            )
            bssid = parse_netsh_bssid(result.stdout or "")
        elif system == "Linux":
            result = subprocess.run(
                ["iwconfig"], capture_output=True, text=True, timeout=5
            )
            bssid = parse_iwconfig_bssid(result.stdout or "")
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        bssid = None

    _BSSID_CACHE["value"] = bssid
    _BSSID_CACHE["ok"] = True
    _BSSID_CACHE["timestamp"] = now
    return bssid


def is_same_bssid(bssid_a: str | None, bssid_b: str | None) -> bool:
    """Compare two BSSID strings format-agnostically."""
    if not bssid_a or not bssid_b:
        return False
    return normalize_mac(bssid_a) == normalize_mac(bssid_b)


async def log_ap_access(mac_address: str, ip_address: str, bssid: str = None, ssid: str = None):
    """Log AP access to database."""
    from models.database import get_db
    from config import now_local

    db = await get_db()
    await db.execute(
        "INSERT INTO ap_logs (mac_address, ip_address, bssid, ssid, scan_time) VALUES (?, ?, ?, ?, ?)",
        (mac_address, ip_address, bssid, ssid, now_local().strftime("%Y-%m-%d %H:%M:%S"))
    )
    await db.commit()
    await db.close()


async def log_seen_devices(devices: list[dict], bssid: str = None, ssid: str = None, dedupe_seconds: int = 60):
    """Persist discovered devices into the ap_logs table.

    bssid/ssid record which AP the server was associated with during the
    scan. Skips entries already logged for the same MAC+IP within the
    dedupe window, so repeated scans (10 s cache, page refreshes) don't
    flood the table.
    """
    from datetime import timedelta
    from models.database import get_db
    from config import now_local

    if not devices:
        return

    cutoff = (now_local() - timedelta(seconds=dedupe_seconds)).strftime("%Y-%m-%d %H:%M:%S")
    db = await get_db()
    try:
        for device in devices:
            cursor = await db.execute(
                """SELECT 1 FROM ap_logs
                   WHERE mac_address = ? AND ip_address = ? AND scan_time >= ?""",
                (device["mac"], device["ip"], cutoff)
            )
            if await cursor.fetchone():
                continue
            await db.execute(
                "INSERT INTO ap_logs (mac_address, ip_address, bssid, ssid, scan_time) VALUES (?, ?, ?, ?, ?)",
                (device["mac"], device["ip"], bssid, ssid, now_local().strftime("%Y-%m-%d %H:%M:%S"))
            )
        await db.commit()
    finally:
        await db.close()
