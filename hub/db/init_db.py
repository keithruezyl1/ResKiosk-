from hub.db.session import engine, Base, SessionLocal


def init_db():
    """Create all tables and seed default rows (safe to call on every startup)."""
    from hub.db import schema  # noqa: F401 — registers all models with Base
    from hub.db.seed import seed_data

    print("Initializing database...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        seed_data(db)
    finally:
        db.close()

    print("Database initialized.")
