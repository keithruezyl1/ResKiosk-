"""
API routes for ESP+LoRa serial/Bluetooth monitoring and hub-to-hub messaging.
"""

import time
import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session

from hub.db.session import get_db
from hub.db import schema
from hub.core.lora_serial import get_lora_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lora", tags=["lora"])


# ── Request models ─────────────────────────────────────────────────────────

class ConnectRequest(BaseModel):
    port: str
    baud: int = 115200
    connection_type: str = "serial"  # "serial" or "bluetooth"


class SendRequest(BaseModel):
    target_hub_id: Optional[int] = None
    category_id: Optional[int] = None
    subject: str
    content: str
    priority: str = "normal"


class RawSendRequest(BaseModel):
    text: str


class AutoConnectRequest(BaseModel):
    enabled: bool


# ── REST endpoints ─────────────────────────────────────────────────────────

@router.get("/status")
def lora_status(db: Session = Depends(get_db)):
    mgr = get_lora_manager()
    status = mgr.get_status()
    # Include DB-persisted auto_connect flag
    try:
        cfg = db.query(schema.LoraConfig).first()
        status["auto_connect"] = bool(cfg.auto_connect) if cfg else False
    except Exception:
        status["auto_connect"] = False
    return status


@router.get("/ports")
def lora_ports():
    mgr = get_lora_manager()
    return {"ports": mgr.list_serial_ports()}


@router.post("/connect")
def lora_connect(req: ConnectRequest, db: Session = Depends(get_db)):
    mgr = get_lora_manager()

    _register_message_callback(mgr, db)

    result = mgr.connect(
        port=req.port,
        baud=req.baud,
        conn_type=req.connection_type,
    )

    if result.get("ok"):
        _save_lora_config(db, req.port, req.baud, req.connection_type)

    return result


@router.post("/disconnect")
def lora_disconnect(db: Session = Depends(get_db)):
    mgr = get_lora_manager()
    result = mgr.disconnect()
    return result


@router.post("/send")
def lora_send(req: SendRequest, db: Session = Depends(get_db)):
    mgr = get_lora_manager()

    this_hub = db.query(schema.Hub).first()
    source_hub_id = this_hub.hub_id if this_hub else None
    source_device_id = this_hub.device_id if this_hub else None

    payload = {
        "type": "msg",
        "from": source_device_id,
        "to": req.target_hub_id,
        "subject": req.subject,
        "content": req.content,
        "priority": req.priority,
    }

    result = mgr.send_message(payload)

    if result.get("ok"):
        now = int(time.time())
        msg = schema.HubMessage(
            category_id=req.category_id,
            source_hub_id=source_hub_id,
            target_hub_id=req.target_hub_id,
            subject=req.subject,
            content=req.content,
            priority=req.priority,
            status="pending",
            sent_at=now,
            received_via="lora",
            created_by="admin",
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        result["message_id"] = msg.id

    return result


class AutoConnectRequest(BaseModel):
    enabled: bool


@router.post("/auto-connect")
def lora_auto_connect(req: AutoConnectRequest, db: Session = Depends(get_db)):
    cfg = db.query(schema.LoraConfig).first()
    if not cfg:
        cfg = schema.LoraConfig(
            port="",
            baud_rate=115200,
            connection_type="serial",
            auto_connect=1 if req.enabled else 0,
            last_connected=int(time.time()),
        )
        db.add(cfg)
    else:
        cfg.auto_connect = 1 if req.enabled else 0
    db.commit()

    mgr = get_lora_manager()
    if req.enabled:
        mgr.enable_auto_reconnect()
    else:
        mgr.disable_auto_reconnect()

    return {"ok": True, "auto_connect": req.enabled}


@router.post("/send_raw")
def lora_send_raw(req: RawSendRequest):
    mgr = get_lora_manager()
    return mgr.send_raw(req.text)


@router.get("/log")
def lora_log(limit: int = 100):
    mgr = get_lora_manager()
    return {"lines": mgr.get_log(limit)}


@router.post("/auto-connect")
def lora_auto_connect(req: AutoConnectRequest, db: Session = Depends(get_db)):
    """Toggle auto-connect on/off. Persists to DB and enables/disables on the manager."""
    mgr = get_lora_manager()

    # Persist to DB
    try:
        cfg = db.query(schema.LoraConfig).first()
        if cfg:
            cfg.auto_connect = 1 if req.enabled else 0
        else:
            cfg = schema.LoraConfig(
                port="",
                baud_rate=115200,
                connection_type="serial",
                auto_connect=1 if req.enabled else 0,
                last_connected=int(time.time()),
            )
            db.add(cfg)
        db.commit()
    except Exception as e:
        logger.warning(f"Could not save auto-connect setting: {e}")

    # Enable/disable on the manager
    if req.enabled:
        mgr.enable_auto_reconnect()
    else:
        mgr.disable_auto_reconnect()

    return {"ok": True, "auto_connect": req.enabled}


# ── WebSocket for real-time serial monitor ─────────────────────────────────

@router.websocket("/ws/lora")
async def ws_lora(websocket: WebSocket):
    await websocket.accept()
    mgr = get_lora_manager()

    queue = asyncio.Queue(maxsize=200)
    mgr.add_ws_listener(queue)

    try:
        for line in mgr.get_log(50):
            await websocket.send_text(line)

        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30)
                await websocket.send_text(msg)
            except asyncio.TimeoutError:
                await websocket.send_text("")
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"LoRa WS closed: {e}")
    finally:
        mgr.remove_ws_listener(queue)


# ── Helpers ────────────────────────────────────────────────────────────────

def _register_message_callback(mgr, db_session: Session):
    """No-op -- DB persistence is now handled directly inside LoRaSerialManager._save_received_message.
    Kept for API compatibility if custom callbacks are needed later."""
    pass


def _save_lora_config(db: Session, port: str, baud: int, conn_type: str):
    """Persist the last-used connection settings."""
    try:
        existing = db.query(schema.LoraConfig).first()
        if existing:
            existing.port = port
            existing.baud_rate = baud
            existing.connection_type = conn_type
            existing.last_connected = int(time.time())
        else:
            cfg = schema.LoraConfig(
                port=port,
                baud_rate=baud,
                connection_type=conn_type,
                auto_connect=1,
                last_connected=int(time.time()),
            )
            db.add(cfg)
        db.commit()
    except Exception as e:
        logger.warning(f"Could not save LoRa config: {e}")


def startup_auto_connect():
    """Called on app startup -- reconnect if auto_connect is enabled (USB serial only)."""
    from hub.db.session import SessionLocal
    db = SessionLocal()
    try:
        cfg = db.query(schema.LoraConfig).first()
        if cfg and cfg.auto_connect:
            mgr = get_lora_manager()
            _register_message_callback(mgr, db)

            mgr._auto_reconnect_enabled = True
            mgr._last_baud = cfg.baud_rate or 115200
            mgr._last_conn_type = cfg.connection_type or "serial"
            mgr._last_port = cfg.port

            usb_ports = mgr.list_usb_serial_ports()
            if not usb_ports:
                logger.warning("LoRa auto-connect: no USB serial device found, starting background scan")
                mgr._start_auto_reconnect()
                return

            # Try saved port if it's a USB device
            if cfg.port and any(p["port"] == cfg.port for p in usb_ports):
                result = mgr.connect(
                    port=cfg.port,
                    baud=cfg.baud_rate,
                    conn_type=cfg.connection_type,
                )
                if result.get("ok"):
                    logger.info(f"LoRa auto-connected to {cfg.port}")
                    return

            # Saved port unavailable — try other USB serial ports
            logger.warning(f"LoRa auto-connect to {cfg.port} failed, scanning USB ports...")
            for p in usb_ports:
                port_name = p["port"]
                if port_name == cfg.port:
                    continue
                result = mgr.connect(
                    port=port_name,
                    baud=cfg.baud_rate or 115200,
                    conn_type=cfg.connection_type or "serial",
                )
                if result.get("ok"):
                    logger.info(f"LoRa auto-connected to {port_name} (fallback)")
                    _save_lora_config(db, port_name, cfg.baud_rate or 115200, cfg.connection_type or "serial")
                    return

            logger.warning("LoRa auto-connect: USB ports found but connect failed, starting background reconnect")
            mgr._start_auto_reconnect()
    except Exception as e:
        logger.debug(f"LoRa auto-connect skipped: {e}")
    finally:
        db.close()
