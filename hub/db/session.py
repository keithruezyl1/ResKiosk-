import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

def get_db_url():
    # Phase 0/1: Use env var or default location
    db_path = os.environ.get("RESKIOSK_DB_PATH")
    if not db_path:
        # Fallback for local testing if env not set
        if os.name == 'nt':
            base = Path(os.environ.get('APPDATA')) / "ResKiosk"
        else:
            base = Path.home() / ".local" / "share" / "reskiosk"
        base.mkdir(parents=True, exist_ok=True)
        db_path = str(base / "reskiosk.db")
    
    return f"sqlite:///{db_path}"

SQLALCHEMY_DATABASE_URL = get_db_url()

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
