from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from hub.db.session import get_db
from hub.db import schema
from hub.core.network_manager import network_manager

router = APIRouter()

@router.get("/network/info")
async def get_network_info(db: Session = Depends(get_db)):
    # 1. Detect IP
    detected_ip = network_manager.detect_ip()
    port = 8000 # Hardcoded for now per plan
    
    # 2. Check Config for Overrides
    config_map = {}
    configs = db.query(schema.StructuredConfig).filter(
        schema.StructuredConfig.key.in_(["network_mode", "static_ip_override_enabled", "static_ip_override_value", "hotspot_ssid"])
    ).all()
    
    for c in configs:
        config_map[c.key] = c.get_value()
        
    network_mode = config_map.get("network_mode", "router")
    ssid = config_map.get("hotspot_ssid", "ResKiosk-Network")
    
    # Static IP Logic
    final_ip = detected_ip
    if config_map.get("static_ip_override_enabled") == True:
        override_val = config_map.get("static_ip_override_value")
        if override_val:
            final_ip = override_val

    hub_id = ""
    hub_row = db.query(schema.HubIdentity).filter(schema.HubIdentity.id == 1).first()
    if hub_row:
        hub_id = hub_row.hub_id
            
    connected_count = network_manager.get_connected_count()
    raw_list = network_manager.get_connected_kiosks()
    # Join with kiosk_registry for kiosk_name; prefer registry ip when available
    kiosk_ids = [k["kiosk_id"] for k in raw_list]
    registry_map = {}
    if kiosk_ids:
        for reg in db.query(schema.KioskRegistry).filter(schema.KioskRegistry.kiosk_id.in_(kiosk_ids)).all():
            registry_map[reg.kiosk_id] = {"kiosk_name": reg.kiosk_name or "", "ip_address": reg.ip_address or ""}
    kiosks_list = []
    for k in raw_list:
        kid = k["kiosk_id"]
        rec = registry_map.get(kid, {})
        kiosks_list.append({
            "kiosk_id": kid,
            "kiosk_name": rec.get("kiosk_name") or kid,
            "ip": rec.get("ip_address") or k.get("ip", ""),
            "last_seen": k.get("last_seen", ""),
            "status": k.get("status", "online"),
        })

    return {
        "ip": final_ip,
        "hub_ip": final_ip,
        "hub_id": hub_id,
        "port": port,
        "network_mode": network_mode,
        "ssid": ssid,
        "connected_kiosks": connected_count,
        "hub_url": f"http://{final_ip}:{port}",
        "kiosks_list": kiosks_list,
    }

from pydantic import BaseModel

class KioskHeartbeat(BaseModel):
    kiosk_id: str
    status: str
    center_id: str = "center_1" # Optional/Default to avoid 422 if extra fields are forbidden

@router.post("/register_kiosk")
async def register_kiosk(heartbeat: KioskHeartbeat, request: Request):
    client_ip = request.client.host
    network_manager.register_heartbeat(heartbeat.kiosk_id, client_ip, heartbeat.status)
    return {"status": "ok"}


class KioskNameUpdate(BaseModel):
    kiosk_name: str


@router.put("/network/kiosk/{kiosk_id}/name")
def update_kiosk_name(kiosk_id: str, body: KioskNameUpdate, db: Session = Depends(get_db)):
    reg = db.query(schema.KioskRegistry).filter(schema.KioskRegistry.kiosk_id == kiosk_id).first()
    if reg:
        reg.kiosk_name = body.kiosk_name
        db.commit()
        return {"status": "ok", "kiosk_id": kiosk_id, "kiosk_name": body.kiosk_name}
    # If not in registry yet, create a minimal row so the name is stored for when they next heartbeat
    hub_row = db.query(schema.HubIdentity).filter(schema.HubIdentity.id == 1).first()
    hub_id = hub_row.hub_id if hub_row else ""
    from datetime import datetime
    now = datetime.utcnow()
    db.add(schema.KioskRegistry(kiosk_id=kiosk_id, kiosk_name=body.kiosk_name, ip_address="", hub_id=hub_id, first_seen=now, last_seen=now))
    db.commit()
    return {"status": "ok", "kiosk_id": kiosk_id, "kiosk_name": body.kiosk_name}

