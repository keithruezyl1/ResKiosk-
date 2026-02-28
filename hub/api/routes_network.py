import time
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from hub.db.session import get_db
from hub.db import schema
from hub.core.network_manager import network_manager
from pydantic import BaseModel

router = APIRouter()


@router.get("/network/info")
async def get_network_info(db: Session = Depends(get_db)):
    detected_ip = network_manager.detect_ip()

    # Pull network config from NetworkConfig table
    config = db.query(schema.NetworkConfig).first()
    network_mode = config.network_mode if config else "router"
    port = config.port if config else 8000
    final_ip = config.ip_override if (config and config.ip_override) else detected_ip

    # Hub name from Hub table
    hub_row = db.query(schema.Hub).first()
    hub_id = str(hub_row.hub_id) if hub_row else ""

    connected_count = network_manager.get_connected_count()
    raw_list = network_manager.get_connected_kiosks()

    # Join with Kiosk table for display names
    kiosk_ids = [k["kiosk_id"] for k in raw_list]
    kiosk_map = {}
    if kiosk_ids:
        for kiosk in db.query(schema.Kiosk).filter(schema.Kiosk.kiosk_name.in_(kiosk_ids)).all():
            kiosk_map[str(kiosk.kiosk_id)] = {
                "kiosk_name": kiosk.kiosk_name or "",
            }

    kiosks_list = []
    for k in raw_list:
        kid = k["kiosk_id"]
        rec = kiosk_map.get(kid, {})
        kiosks_list.append({
            "kiosk_id": kid,
            "kiosk_name": rec.get("kiosk_name") or kid,
            "ip": k.get("ip", ""),
            "last_seen": k.get("last_seen", ""),
            "status": k.get("status", "online"),
        })

    return {
        "ip": final_ip,
        "hub_ip": final_ip,
        "hub_id": hub_id,
        "device_id": device_id,
        "port": port,
        "network_mode": network_mode,
        "connected_kiosks": connected_count,
        "hub_url": f"http://{final_ip}:{port}",
        "kiosks_list": kiosks_list,
    }


class KioskHeartbeat(BaseModel):
    kiosk_id: str
    status: str
    center_id: str = "center_1"


@router.post("/register_kiosk")
async def register_kiosk(heartbeat: KioskHeartbeat, request: Request):
    client_ip = request.client.host
    network_manager.register_heartbeat(heartbeat.kiosk_id, client_ip, heartbeat.status)
    return {"status": "ok"}


class KioskNameUpdate(BaseModel):
    kiosk_name: str


@router.put("/network/kiosk/{kiosk_id}/name")
def update_kiosk_name(kiosk_id: int, body: KioskNameUpdate, db: Session = Depends(get_db)):
    kiosk = db.query(schema.Kiosk).filter(schema.Kiosk.kiosk_id == kiosk_id).first()
    if kiosk:
        kiosk.kiosk_name = body.kiosk_name
        db.commit()
        return {"status": "ok", "kiosk_id": kiosk_id, "kiosk_name": body.kiosk_name}
    return {"status": "not_found", "kiosk_id": kiosk_id}
