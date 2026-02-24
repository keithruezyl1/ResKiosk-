from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from hub.db.session import get_db
from hub.db import schema
from hub.models import api_models
from hub.retrieval.embedder import load_embedder, serialize_embedding, get_embeddable_text
from hub.retrieval.search import invalidate_corpus_cache, invalidate_shelter_config_cache

router = APIRouter()


def increment_kb_version(db: Session):
    meta = db.query(schema.KBMeta).first()
    if meta:
        meta.kb_version += 1
        meta.updated_at = datetime.utcnow()
        db.add(meta)
        db.commit()


def _embed_article(db: Session, article: schema.KBArticle):
    """Generate and store embedding for an article. Called immediately on create/update.
    Uses the canonical get_embeddable_text() (title + tags, not body).
    """
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


# Articles
@router.post("/admin/article", response_model=api_models.ArticleResponse, status_code=status.HTTP_201_CREATED)
async def create_article(
    article: api_models.ArticleCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    db_article = schema.KBArticle(
        title=article.title,
        body=article.body,
        category=article.category,
        status=article.status,
        enabled=article.enabled
    )
    db_article.set_tags(article.tags)

    db.add(db_article)
    increment_kb_version(db)
    db.commit()
    db.refresh(db_article)

    # Auto-embed in background so the API responds immediately
    background_tasks.add_task(_embed_article, db, db_article)

    return db_article


@router.put("/admin/article/{id}", response_model=api_models.ArticleResponse)
async def update_article(
    id: int,
    update: api_models.ArticleUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    db_article = db.query(schema.KBArticle).filter(schema.KBArticle.id == id).first()
    if not db_article:
        raise HTTPException(status_code=404, detail="Article not found")

    content_changed = False
    if update.title is not None:
        db_article.title = update.title
        content_changed = True
    if update.body is not None:
        db_article.body = update.body
        content_changed = True
    if update.category is not None:
        db_article.category = update.category
    if update.tags is not None:
        db_article.set_tags(update.tags)
    if update.status is not None:
        db_article.status = update.status
    if update.enabled is not None:
        db_article.enabled = update.enabled

    increment_kb_version(db)
    db.commit()
    db.refresh(db_article)

    # Only re-embed if text changed
    if content_changed:
        background_tasks.add_task(_embed_article, db, db_article)

    return db_article


@router.delete("/admin/article/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(id: int, db: Session = Depends(get_db)):
    db_article = db.query(schema.KBArticle).filter(schema.KBArticle.id == id).first()
    if not db_article:
        raise HTTPException(status_code=404, detail="Article not found")

    db.delete(db_article)
    increment_kb_version(db)
    db.commit()
    invalidate_corpus_cache()


# Config
@router.put("/admin/config/{key}", response_model=api_models.ConfigResponse)
async def update_config(key: str, update: api_models.ConfigUpdate, db: Session = Depends(get_db)):
    db_config = db.query(schema.StructuredConfig).filter(schema.StructuredConfig.key == key).first()

    if not db_config:
        db_config = schema.StructuredConfig(key=key)
        db.add(db_config)

    db_config.set_value(update.value)
    increment_kb_version(db)
    db.commit()
    db.refresh(db_config)
    return db_config


@router.post("/admin/publish")
async def publish_kb(db: Session = Depends(get_db)):
    """
    Re-generates embeddings for ALL enabled articles and increments KB version.
    Use this to bulk re-index after importing articles or changing the embedding model.
    """
    print("[Publish] Regenerating all embeddings...")
    embedder = load_embedder()

    articles = db.query(schema.KBArticle).filter(schema.KBArticle.enabled == True).all()

    count = 0
    errors = 0
    for art in articles:
        try:
            text = get_embeddable_text(art)
            vec = embedder.embed_text(text)
            art.embedding = serialize_embedding(vec)
            count += 1
            print(f"[Publish] Embedded article {art.id}: '{text[:60]}'")
        except Exception as e:
            print(f"[Publish] Failed to embed article {art.id}: {e}")
            errors += 1

    increment_kb_version(db)
    db.commit()
    invalidate_corpus_cache()
    invalidate_shelter_config_cache()

    print(f"[Publish] Done. {count} embedded, {errors} errors.")
    return {"status": "published", "articles_processed": count, "errors": errors}


@router.post("/admin/import")
async def import_articles(payload: dict, db: Session = Depends(get_db)):
    """
    Bulk import articles from JSON. Expects: { "articles": [ { title, body, category, tags, status, enabled }, ... ] }
    Each article is validated, saved, and embedded immediately.
    Returns a summary of imported / skipped / failed counts.
    """
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

    for i, data in enumerate(articles_data):
        try:
            title = (data.get("title") or "").strip()
            body = (data.get("body") or "").strip()
            if not title or not body:
                skipped += 1
                errors_list.append(f"Item {i+1}: missing title or body — skipped")
                continue

            article = schema.KBArticle(
                title=title,
                body=body,
                category=data.get("category", "General"),
                status=data.get("status", "published"),
                enabled=data.get("enabled", True),
            )
            article.set_tags(data.get("tags", []))

            # Generate embedding using canonical function
            if embedder:
                try:
                    text = get_embeddable_text(article)
                    vec = embedder.embed_text(text)
                    article.embedding = serialize_embedding(vec)
                except Exception as e:
                    print(f"[Import] Warning: embedding failed for '{title[:50]}': {e}")

            db.add(article)
            imported += 1
        except Exception as e:
            errors_list.append(f"Item {i+1} ('{data.get('title', '?')}'): {e}")

    if imported > 0:
        increment_kb_version(db)
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
