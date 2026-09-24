import socket
import subprocess
import platform
import re
import time
import concurrent.futures
from datetime import datetime
from config import WI_FI_SCAN_TIMEOUT, WI_FI_SUBNET

_CACHE_TTL_SECONDS = 10
_scan_cache: dict = {"devices": None, "timestamp": 0.0}


def detect_local_subnet() -> str | None:
    """Detect the /24 subnet of the machine's primary network interface.

    Opens a UDP socket to a public IP (no packets actually sent) to learn
    the local IP the OS would use, then derives its /24 network address.
    Returns None if no route is available.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        finally:
            s.close()
        parts = local_ip.split(".")
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
    except Exception:
        return None


def resolve_subnet() -> str:
    """Subnet to scan: explicit config wins, else auto-detected, else fallback."""
    if WI_FI_SUBNET:
        return WI_FI_SUBNET
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


def _ping_sweep(subnet: str, timeout_ms: int = 200):
    """Ping every host in the subnet to populate the ARP cache.

    Without this, 'arp -a' only reports entries already in the cache
    (usually just this machine and the gateway).
    """
    prefix = subnet.split("/")[0].rsplit(".", 1)[0]

    def ping(ip: str):
        try:
            subprocess.run(
                ["ping", "-n", "1", "-w", str(timeout_ms), ip],
                capture_output=True,
                timeout=timeout_ms / 1000 + 1,
            )
        except Exception:
            pass

    ips = [f"{prefix}.{i}" for i in range(1, 255)]
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
    """Linux: use scapy ARP scan."""
    try:
        from scapy.all import ARP, Ether, srp
        arp = ARP(pdst=subnet)
        ether = Ether(dst="ff:ff:ff:ff:ff:ff")
        packet = ether / arp
        answered, _ = srp(packet, timeout=timeout, verbose=0)
        return [
            {"ip": r.psrc, "mac": r.hwsrc}
            for _, r in answered
            if _is_unicast_device(normalize_mac(r.hwsrc))
        ]
    except ImportError:
        return []


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
