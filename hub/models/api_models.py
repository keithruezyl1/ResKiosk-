from typing import List, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime
import json

class NetworkInfo(BaseModel):
    ip: str
    port: int

class ArticleBase(BaseModel):
    title: str
    body: str
    category: str
    tags: List[str] = []
    status: str = "draft"
    enabled: bool = True

    @field_validator('tags', mode='before')
    @classmethod
    def parse_tags(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except ValueError:
                return []
        return v

class ArticleCreate(ArticleBase):
    pass

class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    enabled: Optional[bool] = None

class ArticleResponse(ArticleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ConfigUpdate(BaseModel):
    value: Any # JSON

class ConfigResponse(BaseModel):
    key: str
    value: Any
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class KBSnapshot(BaseModel):
    kb_version: int
    articles: List[ArticleResponse]
    structured_config: Dict[str, Any]

class KBVersionResponse(BaseModel):
    kb_version: int
    updated_at: datetime

class QueryRequest(BaseModel):
    center_id: str
    kiosk_id: str
    transcript_original: str
    transcript_english: Optional[str] = None
    language: str
    kb_version: int
    is_retry: bool = False
    selected_category: Optional[str] = None
    session_id: Optional[str] = None

class QueryResponse(BaseModel):
    answer_text_en: str
    answer_text_localized: Optional[str] = None
    answer_type: str
    confidence: float
    kb_version: int
    source_id: Optional[int] = None
    clarification_categories: Optional[List[str]] = None


class EmergencyRequest(BaseModel):
    kiosk_id: str
    kiosk_location: str
    hub_id: Optional[str] = None
    transcript: Optional[str] = None
    language: str = "en"
    timestamp: Optional[int] = None
