from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from hub.db.session import get_db
from hub.db import schema
from hub.models import api_models

router = APIRouter()

@router.get("/kb/version", response_model=api_models.KBVersionResponse)
async def get_kb_version(db: Session = Depends(get_db)):
    meta = db.query(schema.KBMeta).first()
    if not meta:
        raise HTTPException(status_code=500, detail="KB Meta missing")
    return meta

@router.get("/kb/snapshot", response_model=api_models.KBSnapshot)
async def get_kb_snapshot(db: Session = Depends(get_db)):
    meta = db.query(schema.KBMeta).first()
    articles = db.query(schema.KBArticle).filter(schema.KBArticle.enabled == True).all()
    configs = db.query(schema.StructuredConfig).all()
    
    config_dict = {c.key: c.get_value() for c in configs}
    
    return api_models.KBSnapshot(
        kb_version=meta.kb_version if meta else 0,
        articles=articles,
        structured_config=config_dict
    )
