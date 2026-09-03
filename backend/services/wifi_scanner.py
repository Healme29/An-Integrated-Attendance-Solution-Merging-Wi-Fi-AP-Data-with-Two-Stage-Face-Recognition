import subprocess
import platform
import re
from datetime import datetime
from config import WI_FI_SCAN_TIMEOUT, WI_FI_SUBNET


def scan_network_arp(subnet: str = WI_FI_SUBNET, timeout: int = WI_FI_SCAN_TIMEOUT) -> list[dict]:
    """Scan local network using ARP requests. Returns list of {ip, mac}."""
    system = platform.system()

    if system == "Windows":
        return _scan_windows(timeout)
    else:
        return _scan_linux(subnet, timeout)


def _scan_windows(timeout: int) -> list[dict]:
    """Windows: use 'arp -a' after a quick ping sweep."""
    try:
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
        return [{"ip": r.psrc, "mac": r.hwsrc} for _, r in answered]
    except ImportError:
        return []


def _parse_arp_output(output: str) -> list[dict]:
    """Parse Windows arp -a output."""
    devices = []
    pattern = re.compile(r"(\d+\.\d+\.\d+\.\d+)\s+([\w-]{17})")
    for match in pattern.finditer(output):
        devices.append({"ip": match.group(1), "mac": match.group(2).lower()})
    return devices


def check_mac_on_network(mac_address: str, devices: list[dict] | None = None) -> bool:
    """Check if a MAC address is present on the network."""
    if devices is None:
        devices = scan_network_arp()
    mac_clean = mac_address.lower().replace("-", ":")
    return any(d["mac"].lower().replace("-", ":") == mac_clean for d in devices)


def log_ap_access(mac_address: str, ip_address: str, bssid: str = None, ssid: str = None):
    """Log AP access to database."""
    from models.database import get_db
    import asyncio

    async def _log():
        db = await get_db()
        await db.execute(
            "INSERT INTO ap_logs (mac_address, ip_address, bssid, ssid) VALUES (?, ?, ?, ?)",
            (mac_address, ip_address, bssid, ssid)
        )
        await db.commit()
        await db.close()

    asyncio.create_task(_log())
