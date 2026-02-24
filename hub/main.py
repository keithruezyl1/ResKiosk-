from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from hub.api import routes_system, routes_kb, routes_admin, routes_query, routes_network, routes_emergency
from hub.db.init_db import init_db

app = FastAPI(title="ResKiosk Hub", version="0.1")


class KioskRegistryMiddleware(BaseHTTPMiddleware):
    """Upsert kiosk_registry on any request that has X-Kiosk-ID header. Skip DB write if header missing."""

    async def dispatch(self, request: Request, call_next):
        kiosk_id = request.headers.get("X-Kiosk-ID")
        if not kiosk_id or not kiosk_id.strip():
            return await call_next(request)

        from hub.db.session import SessionLocal
        from hub.db import schema as s

        client_ip = request.client.host if request.client else "unknown"
        db = SessionLocal()
        try:
            hub_row = db.query(s.HubIdentity).filter(s.HubIdentity.id == 1).first()
            hub_id = hub_row.hub_id if hub_row else ""
            reg = db.query(s.KioskRegistry).filter(s.KioskRegistry.kiosk_id == kiosk_id).first()
            now = datetime.utcnow()
            if reg:
                reg.ip_address = client_ip
                reg.hub_id = hub_id
                reg.last_seen = now
                db.add(reg)
            else:
                db.add(s.KioskRegistry(
                    kiosk_id=kiosk_id.strip(),
                    ip_address=client_ip,
                    hub_id=hub_id,
                    first_seen=now,
                    last_seen=now,
                ))
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"[KioskRegistry] upsert failed: {e}")
        finally:
            db.close()

        return await call_next(request)


# CORS (Allow all for development/hub context)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(KioskRegistryMiddleware)

# Startup Event
@app.on_event("startup")
def on_startup():
    from hub.core.logger_stream import setup_log_capture
    setup_log_capture()
    init_db()
    _ensure_hub_identity()
    _embed_missing_articles()
    _prewarm_models()


def _ensure_hub_identity():
    """Ensure this hub has a persistent hub_id (generate on first run). Table + this logic are coupled."""
    import uuid
    from hub.db.session import SessionLocal
    from hub.db import schema as s

    db = SessionLocal()
    try:
        row = db.query(s.HubIdentity).filter(s.HubIdentity.id == 1).first()
        if not row:
            row = s.HubIdentity(id=1, hub_id=str(uuid.uuid4()))
            db.add(row)
            db.commit()
            print(f"[Startup] Generated hub_id: {row.hub_id}")
        else:
            print(f"[Startup] Hub identity: {row.hub_id}")
    except Exception as e:
        print(f"[Startup] Hub identity check failed: {e}")
        db.rollback()
    finally:
        db.close()


def _embed_missing_articles():
    """On startup, generate embeddings for any articles that don't have them."""
    from hub.db.session import SessionLocal
    from hub.db import schema as s
    from hub.retrieval.embedder import load_embedder, serialize_embedding, get_embeddable_text

    db = SessionLocal()
    try:
        missing = db.query(s.KBArticle).filter(
            s.KBArticle.enabled == True,
            (s.KBArticle.embedding == None) | (s.KBArticle.embedding == "")
        ).all()

        if not missing:
            print("[Startup] All articles have embeddings.")
            return

        print(f"[Startup] {len(missing)} articles missing embeddings, generating...")
        embedder = load_embedder()
        count = 0
        for art in missing:
            try:
                text = get_embeddable_text(art)
                vec = embedder.embed_text(text)
                art.embedding = serialize_embedding(vec)
                count += 1
            except Exception as e:
                print(f"[Startup] Failed to embed article {art.id}: {e}")

        db.commit()
        print(f"[Startup] Embedded {count}/{len(missing)} articles.")
    except Exception as e:
        print(f"[Startup] Embedding check failed: {e}")
    finally:
        db.close()

def _prewarm_models():
    """Pre-load embedding model (blocking), init intent classifier, and warm Ollama in background."""
    import time
    import threading

    t0 = time.time()
    try:
        from hub.retrieval.embedder import load_embedder
        from hub.retrieval.intent import IntentClassifier
        from hub.retrieval import search as search_module
        embedder = load_embedder()
        embedder.embed_text("warmup")
        print(f"[Startup] Embedding model warm in {time.time()-t0:.1f}s")
        intent_classifier = IntentClassifier(embedder)
        search_module.set_intent_classifier(intent_classifier)
        print("[Startup] Intent classifier ready.")
    except Exception as e:
        print(f"[Startup] Embedding warmup failed: {e}")

    def _warm_ollama():
        try:
            from hub.retrieval.formatter import check_ollama_available, OLLAMA_URL, MODEL_NAME
            import requests as _req
            if check_ollama_available():
                t1 = time.time()
                _req.post(f"{OLLAMA_URL}/api/chat", json={
                    "model": MODEL_NAME,
                    "messages": [{"role": "user", "content": "hi"}],
                    "stream": False,
                    "options": {"num_predict": 1}
                }, timeout=60)
                print(f"[Startup] Ollama model warm in {time.time()-t1:.1f}s")
            else:
                print("[Startup] WARNING: Ollama not available — LLM features will be degraded.")
        except Exception as e:
            print(f"[Startup] Ollama warmup failed (non-fatal): {e}")

    threading.Thread(target=_warm_ollama, daemon=True).start()


from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os

# Include Routers
app.include_router(routes_system.router)
app.include_router(routes_network.router) # Phase 4
app.include_router(routes_kb.router)
app.include_router(routes_admin.router)
app.include_router(routes_query.router)
app.include_router(routes_emergency.router)

# Static Files (Phase 3)
# Serve console/dist at /console
# Determine path based on run mode (frozen vs dev)
import sys
from pathlib import Path

def get_base_path():
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS if hasattr(sys, '_MEIPASS') else sys.executable).parent
        # Note: In onedir, static files are typically next to exe or in _MEIPASS if onefile. 
        # Our spec puts them in 'console_static'.
        # If onedir, sys._MEIPASS works for onefile, for onedir it is sys.executable dir roughly.
        # But we used --onedir. The spec says `datas=[('console/dist', 'console_static')]`
        # This copies console/dist content TO console_static directory INSIDE the bundle dir.
    
    # Dev mode
    return Path(__file__).parent.parent

base = get_base_path()
static_dir = base / "console_static"
if not static_dir.exists():
    # Dev fallback: try relative to source
    static_dir = Path("console/dist")

if static_dir.exists():
    app.mount("/console", StaticFiles(directory=str(static_dir), html=True), name="console")

@app.get("/")
async def root():
    return RedirectResponse(url="/console/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
