import os
from sqlalchemy import text
from hub.db.session import engine, Base, SessionLocal, get_db_url
from hub.db import schema  # Import to register models
from hub.db.seed import seed_data

# Columns the QueryLog model expects (id is primary key). Add any that are missing in old DBs.
QUERY_LOGS_COLUMNS = [
    ("session_id", "TEXT"),
    ("kiosk_id", "TEXT"),
    ("transcript_original", "TEXT"),
    ("transcript_english", "TEXT"),
    ("raw_transcript", "TEXT"),
    ("normalized_transcript", "TEXT"),
    ("language", "TEXT"),
    ("kb_version", "INTEGER"),
    ("intent", "TEXT"),
    ("intent_confidence", "REAL"),
    ("retrieval_score", "REAL"),
    ("answer_type", "TEXT"),
    ("selected_clarification", "TEXT"),
    ("rewrite_applied", "INTEGER"),
    ("latency_ms", "REAL"),
    ("created_at", "TEXT"),
]


def _ensure_query_logs_columns():
    """Add any missing columns to query_logs (migration for DBs created before schema updates)."""
    with engine.connect() as conn:
        # Only migrate if table already exists (create_all may have just created it with full schema)
        r = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='query_logs'"
        ))
        if r.fetchone() is None:
            return
        r = conn.execute(text("PRAGMA table_info(query_logs)"))
        rows = r.fetchall()
        names = [str(row[1]).strip() for row in rows] if rows else []
        added = []
        for col_name, col_type in QUERY_LOGS_COLUMNS:
            if col_name not in names:
                conn.execute(text(f"ALTER TABLE query_logs ADD COLUMN {col_name} {col_type}"))
                added.append(col_name)
        if added:
            conn.commit()
            db_path = get_db_url().replace("sqlite:///", "")
            print(f"Migration: added query_logs columns: {', '.join(added)} (DB: {db_path})")


def init_db():
    db_path = get_db_url().replace("sqlite:///", "")
    print(f"Initializing Database: {db_path}")
    Base.metadata.create_all(bind=engine)

    # Migrations for existing DBs (add columns that were added after initial schema)
    _ensure_query_logs_columns()

    db = SessionLocal()
    try:
        seed_data(db)
    finally:
        db.close()
    print("Database Initialized.")
