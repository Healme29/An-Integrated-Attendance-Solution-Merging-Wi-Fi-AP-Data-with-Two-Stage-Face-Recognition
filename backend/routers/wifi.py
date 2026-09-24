from fastapi import APIRouter
from datetime import datetime
from services.wifi_scanner import (
    scan_network_arp, resolve_subnet, normalize_mac, log_seen_devices, log_ap_access,
    get_current_bssid
)

router = APIRouter(prefix="/wifi", tags=["wifi"])


@router.get("/scan")
async def scan_wifi(subnet: str | None = None):
    resolved = subnet or resolve_subnet()
    devices = scan_network_arp(resolved)
    await log_seen_devices(devices, bssid=get_current_bssid())
    return {
        "devices": devices,
        "subnet": resolved,
        "count": len(devices),
        "bssid": get_current_bssid(),
        "timestamp": datetime.now()
    }


@router.get("/check/{mac_address}")
async def check_mac(mac_address: str):
    devices = scan_network_arp()
    target = normalize_mac(mac_address)
    match = next((d for d in devices if normalize_mac(d["mac"]) == target), None)
    if match:
        await log_ap_access(match["mac"], match["ip"], bssid=get_current_bssid())
    return {
        "mac_address": mac_address,
        "on_network": match is not None,
        "bssid": get_current_bssid()
    }
