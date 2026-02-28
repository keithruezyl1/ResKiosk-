from sqlalchemy import (
    Column, Integer, String, Text, Float, LargeBinary, ForeignKey, 
)
from hub.db.session import Base


class QueryLog(Base):
    """Logs every voice query made by kiosks."""
    __tablename__ = "query_logs"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    kiosk_id            = Column(Text, nullable=True)
    transcript_original = Column(Text)
    transcript_english  = Column(Text)
    language            = Column(Text)
    kb_version          = Column(Integer)
    answer_type         = Column(Text)
    latency_ms          = Column(Float)
    created_at          = Column(Integer)  # Unix timestamp


class KBArticle(Base):
    """Main searchable Knowledge Base — all answers come from here."""
    __tablename__ = "kb_articles"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    question     = Column(Text, nullable=False)
    answer       = Column(Text, nullable=False)
    category     = Column(Text)
    tags         = Column(Text)                       # Comma-separated
    enabled      = Column(Integer, default=1)         # 1 = active, 0 = disabled
    source       = Column(Text, default="manual")
    created_at   = Column(Integer)                    # Unix timestamp
    last_updated = Column(Integer)                    # Unix timestamp
    embedding    = Column(LargeBinary, nullable=True) # Serialized vector

    # Alias properties so Pydantic's from_attributes can read 'title' and 'body'
    # from ArticleResponse without changing the API or console contract.
    @property
    def title(self) -> str:
        return self.question or ""

    @property
    def body(self) -> str:
        return self.answer or ""



class EvacInfo(Base):
    """Single-row table for all editable shelter operations data."""
    __tablename__ = "evac_info"

    id                 = Column(Integer, primary_key=True, default=1)
    food_schedule      = Column(Text)
    sleeping_zones     = Column(Text)
    medical_station    = Column(Text)
    registration_steps = Column(Text)
    announcements      = Column(Text)
    emergency_mode     = Column(Text)
    last_updated       = Column(Text)
    info_metadata           = Column(Text)  # JSON for dynamic console forms


class NetworkConfig(Base):
    """Stores the hub's local Wi-Fi and server configuration."""
    __tablename__ = "network_config"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    network_mode = Column(Text)   # 'hotspot' or 'router'
    ip_override  = Column(Text)
    port         = Column(Integer)
    last_updated = Column(Integer)  # Unix timestamp


class SystemVersion(Base):
    """Tracks the current Knowledge Base version so kiosks know when to refresh."""
    __tablename__ = "system_version"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    kb_version     = Column(Integer)
    last_published = Column(Integer)  # Unix timestamp


class User(Base):
    """Admin users who can log in and manage the system."""
    __tablename__ = "user"

    user_id  = Column(Integer, primary_key=True, autoincrement=True)
    fname    = Column(Text)
    mname    = Column(Text)
    lname    = Column(Text)
    password = Column(Text)  # Should be hashed


class Hub(Base):
    """Registry of all Shelter Hubs / evacuation centers."""
    __tablename__ = "hub"

    hub_id     = Column(Integer, primary_key=True, autoincrement=True)
    device_id  = Column(Text, unique=True)   # Unique hardware/device identifier
    hub_name   = Column(Text, nullable=False, unique=True)
    location   = Column(Text)
    created_at = Column(Integer)  # Unix timestamp


class Kiosk(Base):
    """Physical kiosk/tablet devices registered under a hub."""
    __tablename__ = "kiosk"

    kiosk_id   = Column(Integer, primary_key=True, autoincrement=True)
    hub_id     = Column(Integer, ForeignKey("hub.hub_id"), nullable=False)
    kiosk_name = Column(Text)
    location   = Column(Text)
    status     = Column(Text)   # 'online', 'offline', 'maintenance'
    last_seen  = Column(Integer)  # Unix timestamp
    created_at = Column(Integer)  # Unix timestamp


class Category(Base):
    """Preloaded message categories for hub-to-hub messaging."""
    __tablename__ = "categories"

    category_id   = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(Text, nullable=False, unique=True)
    description   = Column(Text)


class HubMessage(Base):
    """Central table for all communication between hubs."""
    __tablename__ = "hub_messages"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    category_id    = Column(Integer, ForeignKey("categories.category_id"))
    source_hub_id  = Column(Integer, ForeignKey("hub.hub_id"))
    target_hub_id  = Column(Integer, ForeignKey("hub.hub_id"), nullable=True)  # NULL = broadcast
    subject        = Column(Text)
    content        = Column(Text)
    priority       = Column(Text)  # 'normal', 'urgent', 'emergency'
    status         = Column(Text)  # 'pending', 'read', 'published', 'rejected'
    sent_at        = Column(Integer)  # Unix timestamp
    received_at    = Column(Integer)  # Unix timestamp
    published_at   = Column(Integer)  # Unix timestamp
    location       = Column(Text)
    created_by     = Column(Text)     # Should eventually be FK to user.user_id
    hop_count      = Column(Integer)
    ttl            = Column(Integer)
    received_via   = Column(Text)     # 'lora', 'manual', 'wifi-local'
    details        = Column(Text)     # JSON for category-specific fields


class LoraConfig(Base):
    """Persisted ESP+LoRa connection settings so the hub can auto-reconnect."""
    __tablename__ = "lora_config"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    port            = Column(Text)
    baud_rate       = Column(Integer, default=115200)
    connection_type = Column(Text, default="serial")   # 'serial' or 'bluetooth'
    auto_connect    = Column(Integer, default=0)        # 1 = reconnect on startup
    last_connected  = Column(Integer)                   # Unix timestamp


class EmergencyAlert(Base):
    """Emergency button activations sent from kiosks."""
    __tablename__ = "emergency_alerts"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    kiosk_id       = Column(Text, nullable=False)
    kiosk_location = Column(Text, nullable=False)  # Snapshot at alert time
    hub_id         = Column(Text, nullable=True)
    transcript     = Column(Text)
    language       = Column(Text, default="en")
    timestamp      = Column(Integer, nullable=False)  # Unix ms
    resolved       = Column(Integer, default=0)       # 0 = open, 1 = resolved
    resolved_at    = Column(Integer, nullable=True)   # Unix ms
