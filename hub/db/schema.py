import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, LargeBinary
from hub.db.session import Base

class KBMeta(Base):
    __tablename__ = "kb_meta"
    id = Column(Integer, primary_key=True, default=1)
    kb_version = Column(Integer, default=1)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class KBArticle(Base):
    __tablename__ = "kb_articles"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False) # English only
    category = Column(String)
    tags = Column(Text, default="[]") # JSON string
    status = Column(String, default="draft") # draft/published
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    embedding = Column(LargeBinary, nullable=True) # Serialized numpy array
    
    # Helper to get/set tags as list
    def get_tags(self):
        try:
            return json.loads(self.tags)
        except:
            return []
            
    def set_tags(self, tags_list):
        self.tags = json.dumps(tags_list)

class StructuredConfig(Base):
    __tablename__ = "structured_config"
    key = Column(String, primary_key=True, unique=True)
    value = Column(Text, nullable=False) # JSON string
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_value(self):
        try:
            return json.loads(self.value)
        except:
            return {}
            
    def set_value(self, val):
        self.value = json.dumps(val)

class QueryLog(Base):
    __tablename__ = "query_logs"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, nullable=True)
    kiosk_id = Column(String)
    transcript_original = Column(Text)
    transcript_english = Column(Text, nullable=True)
    raw_transcript = Column(Text, nullable=True)       # query text passed to retrieve (after translation)
    normalized_transcript = Column(Text, nullable=True)  # after normalize_query
    language = Column(String)
    kb_version = Column(Integer)
    intent = Column(String, nullable=True)
    intent_confidence = Column(Float, nullable=True)
    retrieval_score = Column(Float, nullable=True)
    answer_type = Column(String)
    selected_clarification = Column(String, nullable=True)
    rewrite_applied = Column(Integer, default=0)  # 0=false, 1=true
    latency_ms = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class ClarificationResolution(Base):
    """Gold label when user selects a category after clarification."""
    __tablename__ = "clarification_resolutions"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, nullable=False)
    raw_transcript = Column(Text, nullable=True)
    resolved_intent = Column(String, nullable=False)
    language = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class HubIdentity(Base):
    """Single-row table: this hub's persistent ID. Never exposed to operator editing."""
    __tablename__ = "hub_identity"
    id = Column(Integer, primary_key=True, default=1)
    hub_id = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class EmergencyAlert(Base):
    __tablename__ = "emergency_alerts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    kiosk_id = Column(Text, nullable=False)
    kiosk_location = Column(Text, nullable=False)  # Snapshot at alert time
    hub_id = Column(Text, nullable=True)
    transcript = Column(Text)
    language = Column(Text, default="en")
    timestamp = Column(Integer, nullable=False)
    resolved = Column(Integer, default=0)
    resolved_at = Column(Integer)


class KioskRegistry(Base):
    __tablename__ = "kiosk_registry"
    kiosk_id = Column(Text, primary_key=True)
    kiosk_name = Column(Text)
    ip_address = Column(Text)
    hub_id = Column(Text, nullable=False)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
