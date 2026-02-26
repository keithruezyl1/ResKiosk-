import time
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from hub.db.session import get_db
from hub.db import schema
from hub.models import api_models
from hub.retrieval.embedder import load_embedder, serialize_embedding, get_embeddable_text
from hub.retrieval.search import invalidate_corpus_cache

router = APIRouter()


def _increment_kb_version(db: Session):
    """Bump the kb_version in system_version and record last_published."""
    sv = db.query(schema.SystemVersion).first()
    if sv:
        sv.kb_version = (sv.kb_version or 0) + 1
        sv.last_published = int(time.time())
        db.add(sv)
        db.commit()


def _embed_article(db: Session, article: schema.KBArticle):
    """Generate and store embedding for an article."""
    try:
        embedder = load_embedder()
        text = get_embeddable_text(article)
        vec = embedder.embed_text(text)
        article.embedding = serialize_embedding(vec)
        db.add(article)
        db.commit()
        invalidate_corpus_cache()
        print(f"[Embedder] Article {article.id} embedded: '{text[:80]}'")
    except Exception as e:
        print(f"[Embedder] WARNING: Failed to embed article {article.id}: {e}")


# ─── KB Articles ────────────────────────────────────────────────────────────

@router.post("/admin/article", response_model=api_models.ArticleResponse, status_code=status.HTTP_201_CREATED)
async def create_article(
    article: api_models.ArticleCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    db_article = schema.KBArticle(
        question=article.title,       # 'title' in API maps to 'question' in DB
        answer=article.body,          # 'body' in API maps to 'answer' in DB
        category=article.category,
        tags=",".join(article.tags) if article.tags else "",
        enabled=1 if article.enabled else 0,
        source="manual",
        created_at=int(time.time()),
        last_updated=int(time.time()),
    )
    db.add(db_article)
    _increment_kb_version(db)
    db.commit()
    db.refresh(db_article)

    background_tasks.add_task(_embed_article, db, db_article)
    return db_article


@router.put("/admin/article/{id}", response_model=api_models.ArticleResponse)
async def update_article(
    id: int,
    update: api_models.ArticleUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    db_article = db.query(schema.KBArticle).filter(schema.KBArticle.id == id).first()
    if not db_article:
        raise HTTPException(status_code=404, detail="Article not found")
    if db_article.source == "evac_sync":
        raise HTTPException(status_code=403, detail="This article is managed by Shelter Config and cannot be edited here.")

    content_changed = False
    if update.title is not None:
        db_article.question = update.title
        content_changed = True
    if update.body is not None:
        db_article.answer = update.body
        content_changed = True
    if update.category is not None:
        db_article.category = update.category
    if update.tags is not None:
        db_article.tags = ",".join(update.tags)
    if update.enabled is not None:
        db_article.enabled = 1 if update.enabled else 0

    db_article.last_updated = int(time.time())
    _increment_kb_version(db)
    db.commit()
    db.refresh(db_article)

    if content_changed:
        background_tasks.add_task(_embed_article, db, db_article)

    return db_article


@router.delete("/admin/article/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(id: int, db: Session = Depends(get_db)):
    db_article = db.query(schema.KBArticle).filter(schema.KBArticle.id == id).first()
    if not db_article:
        raise HTTPException(status_code=404, detail="Article not found")
    if db_article.source == "evac_sync":
        raise HTTPException(status_code=403, detail="This article is managed by Shelter Config and cannot be deleted.")
    db.delete(db_article)
    _increment_kb_version(db)
    db.commit()
    invalidate_corpus_cache()


# ─── Evac Info (Shelter Operations Config) ──────────────────────────────────

@router.get("/admin/evac", response_model=api_models.EvacInfoResponse)
async def get_evac_info(db: Session = Depends(get_db)):
    row = db.query(schema.EvacInfo).filter(schema.EvacInfo.id == 1).first()
    if not row:
        raise HTTPException(status_code=404, detail="Evac info not found")
    return row


@router.put("/admin/evac", response_model=api_models.EvacInfoResponse)
async def update_evac_info(
    update: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    row = db.query(schema.EvacInfo).filter(schema.EvacInfo.id == 1).first()
    if not row:
        row = schema.EvacInfo(id=1)
        db.add(row)

    allowed = ["food_schedule", "sleeping_zones", "medical_station",
               "registration_steps", "announcements", "emergency_mode"]
    for field in allowed:
        if field in update:
            setattr(row, field, update[field])
    
    # Map 'metadata' from request to 'info_metadata' column
    if "metadata" in update:
        row.info_metadata = update["metadata"]
    import datetime
    row.last_updated = datetime.datetime.utcnow().isoformat()

    db.commit()
    db.refresh(row)

    # Sync evac fields → KB articles for semantic search
    from hub.db.evac_sync import sync_evac_to_kb
    sync_evac_to_kb(db)

    return row


# ─── Publish (re-embed all) ──────────────────────────────────────────────────

@router.post("/admin/publish")
async def publish_kb(db: Session = Depends(get_db)):
    """Re-generate embeddings for all enabled articles and bump KB version."""
    print("[Publish] Regenerating all embeddings...")
    embedder = load_embedder()

    articles = db.query(schema.KBArticle).filter(schema.KBArticle.enabled == 1).all()
    count = 0
    errors = 0
    for art in articles:
        try:
            text = get_embeddable_text(art)
            vec = embedder.embed_text(text)
            art.embedding = serialize_embedding(vec)
            count += 1
        except Exception as e:
            print(f"[Publish] Failed to embed article {art.id}: {e}")
            errors += 1

    _increment_kb_version(db)
    db.commit()
    invalidate_corpus_cache()

    print(f"[Publish] Done. {count} embedded, {errors} errors.")
    return {"status": "published", "articles_processed": count, "errors": errors}


# ─── Bulk Import ─────────────────────────────────────────────────────────────

@router.post("/admin/import")
async def import_articles(payload: dict, db: Session = Depends(get_db)):
    """Bulk import articles. Expects: { "articles": [{title, body, category, tags, enabled}, ...] }"""
    articles_data = payload.get("articles", [])
    if not isinstance(articles_data, list) or len(articles_data) == 0:
        raise HTTPException(status_code=400, detail="Expected a non-empty 'articles' array.")

    embedder = None
    try:
        embedder = load_embedder()
    except Exception as e:
        print(f"[Import] Warning: Could not load embedder: {e}")

    imported = 0
    skipped = 0
    errors_list = []
    now = int(time.time())

    for i, data in enumerate(articles_data):
        try:
            question = (data.get("title") or "").strip()
            answer = (data.get("body") or "").strip()
            if not question or not answer:
                skipped += 1
                errors_list.append(f"Item {i+1}: missing title or body — skipped")
                continue

            article = schema.KBArticle(
                question=question,
                answer=answer,
                category=data.get("category", "General"),
                tags=",".join(data.get("tags", [])) if isinstance(data.get("tags"), list) else (data.get("tags") or ""),
                enabled=1 if data.get("enabled", True) else 0,
                source=data.get("source", "import"),
                created_at=now,
                last_updated=now,
            )

            if embedder:
                try:
                    text = get_embeddable_text(article)
                    vec = embedder.embed_text(text)
                    article.embedding = serialize_embedding(vec)
                except Exception as e:
                    print(f"[Import] Warning: embedding failed for '{question[:50]}': {e}")

            db.add(article)
            imported += 1
        except Exception as e:
            errors_list.append(f"Item {i+1} ('{data.get('title', '?')}'): {e}")

    if imported > 0:
        _increment_kb_version(db)
        db.commit()
        invalidate_corpus_cache()

    print(f"[Import] Done. {imported} imported, {skipped} skipped, {len(errors_list)} errors.")
    return {
        "status": "ok",
        "imported": imported,
        "skipped": skipped,
        "errors": errors_list,
        "total_in_payload": len(articles_data),
    }
