from fastapi import APIRouter
from datetime import datetime
from services.wifi_scanner import scan_network_arp

router = APIRouter(prefix="/wifi", tags=["wifi"])


@router.get("/scan")
async def scan_wifi(subnet: str = "192.168.1.0/24"):
    devices = scan_network_arp(subnet)
    return {
        "devices": devices,
        "subnet": subnet,
        "count": len(devices),
        "timestamp": datetime.now()
    }


@router.get("/check/{mac_address}")
async def check_mac(mac_address: str):
    from services.wifi_scanner import check_mac_on_network
    found = check_mac_on_network(mac_address)
    return {"mac_address": mac_address, "on_network": found}
