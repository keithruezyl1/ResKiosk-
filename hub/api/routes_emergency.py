import asyncio
import json
import logging
import time
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from hub.db.session import get_db
from hub.db import schema
from hub.models.api_models import EmergencyRequest

router = APIRouter()
log = logging.getLogger(__name__)

# Active SSE subscribers — one entry per open console browser tab
_subscribers: list[asyncio.Queue] = []


async def _broadcast(event: dict):
    data = f"data: {json.dumps(event)}\n\n"
    dead = []
    for q in _subscribers:
        try:
            q.put_nowait(data)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        _subscribers.remove(q)


def _alert_to_dict(alert: schema.EmergencyAlert, db: Session) -> dict:
    """Build alert dict; join kiosk_registry for current kiosk_name, fall back to kiosk_location."""
    reg = db.query(schema.KioskRegistry).filter(schema.KioskRegistry.kiosk_id == alert.kiosk_id).first()
    display_name = (reg.kiosk_name or alert.kiosk_location) if reg else alert.kiosk_location
    return {
        "id": alert.id,
        "kiosk_id": alert.kiosk_id,
        "kiosk_location": alert.kiosk_location,
        "kiosk_name": display_name,
        "transcript": alert.transcript,
        "language": alert.language,
        "timestamp": alert.timestamp,
    }


@router.post("/emergency")
async def receive_emergency(payload: EmergencyRequest, db: Session = Depends(get_db)):
    # Resolve hub_id if not provided (current hub)
    hub_id = payload.hub_id
    if not hub_id:
        hi = db.query(schema.HubIdentity).filter(schema.HubIdentity.id == 1).first()
        if hi:
            hub_id = hi.hub_id

    alert = schema.EmergencyAlert(
        kiosk_id=payload.kiosk_id,
        kiosk_location=payload.kiosk_location,
        hub_id=hub_id,
        transcript=payload.transcript or "",
        language=payload.language,
        timestamp=payload.timestamp or int(time.time() * 1000),
        resolved=0,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    # Broadcast for SSE; use same join logic for kiosk_name
    event = _alert_to_dict(alert, db)
    event["type"] = "EMERGENCY_ALERT"
    event["alert_id"] = alert.id
    await _broadcast(event)

    log.warning(f"EMERGENCY from {alert.kiosk_id} @ {alert.kiosk_location}: {alert.transcript}")
    return {"status": "received", "alert_id": alert.id}


@router.get("/emergency/stream")
async def emergency_sse():
    """Console subscribes here. One long-lived connection per browser tab. Sends heartbeat every 30s."""
    q: asyncio.Queue = asyncio.Queue(maxsize=50)
    _subscribers.append(q)

    async def generator():
        try:
            yield "data: {\"type\": \"CONNECTED\"}\n\n"
            while True:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=30.0)
                    yield msg
                except asyncio.TimeoutError:
                    yield "data: {\"type\": \"HEARTBEAT\"}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            try:
                _subscribers.remove(q)
            except ValueError:
                pass

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/emergency/active")
def get_active_emergencies(db: Session = Depends(get_db)):
    alerts = (
        db.query(schema.EmergencyAlert)
        .filter(schema.EmergencyAlert.resolved == 0)
        .order_by(schema.EmergencyAlert.timestamp.desc())
        .all()
    )
    return {
        "alerts": [_alert_to_dict(a, db) for a in alerts],
    }


@router.post("/emergency/{alert_id}/resolve")
def resolve_emergency(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(schema.EmergencyAlert).filter(schema.EmergencyAlert.id == alert_id).first()
    if alert:
        alert.resolved = 1
        alert.resolved_at = int(time.time() * 1000)
        db.commit()
    return {"status": "resolved"}
