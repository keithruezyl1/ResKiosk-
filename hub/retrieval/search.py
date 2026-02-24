import os
import logging
import numpy as np
from sqlalchemy.orm import Session
from typing import List, Optional
from hub.db import schema
from hub.retrieval.embedder import load_embedder, deserialize_embedding
from hub.retrieval.normalizer import normalize_query
from hub.retrieval import inventory as inventory_module
from sentence_transformers import util

logger = logging.getLogger(__name__)

# Intent-based query enrichment keywords (used when intent is recognized with confidence)
INTENT_ENRICHMENT = {
    "greeting": "hello greeting",
    "identity": "kiosk assistant information",
    "capability": "help information services",
    "small_talk": "thanks okay",
    "food": "food meals schedule cafeteria breakfast lunch dinner",
    "medical": "medical doctor nurse health first aid",
    "registration": "registration sign in check in intake",
    "sleeping": "sleeping beds cots rest area",
    "transportation": "bus shuttle transport ride leave",
    "safety": "safety emergency evacuation exit",
    "facilities": "bathroom restroom showers laundry charging wifi",
    "lost_person": "lost missing family reunification",
    "pets": "pets dog cat animal",
    "donations": "donate donations",
    "hours": "hours open close schedule",
    "location": "address location directions building",
    "general_info": "information services help",
    "goodbye": "goodbye bye",
    "inventory": "supplies available stock food water medicine blankets hygiene clothing diapers charging cots",
}

THRESHOLD = float(os.environ.get("RESKIOSK_SIM_THRESHOLD", 0.65))
CLARIFICATION_FLOOR = float(os.environ.get("RESKIOSK_CLARIFICATION_FLOOR", 0.45))

# Intent classifier singleton, set by main.py at startup
_intent_classifier = None


def set_intent_classifier(classifier) -> None:
    global _intent_classifier
    _intent_classifier = classifier

class RetrievalResult:
    """Holds a cached article dict and its similarity score."""
    def __init__(self, article_dict: dict, score: float):
        self.article = article_dict  # plain dict, not ORM object
        self.score = score
        self.category = article_dict.get("category")


def needs_clarification(
    query: str,
    top_k: List[RetrievalResult],
    intent: str,
    intent_confidence: float,
) -> bool:
    """Only clarify when intent is unclear and best retrieval score is below CLARIFICATION_FLOOR."""
    if intent != "unclear" and intent_confidence >= 0.45:
        return False
    if intent in ("greeting", "identity", "capability", "small_talk"):
        return False
    best_retrieval_score = top_k[0].score if top_k else 0.0
    return intent == "unclear" and best_retrieval_score < CLARIFICATION_FLOOR


# --- Fix 6: In-memory corpus cache ---
_corpus_cache = None  # None = stale, needs reload


def invalidate_corpus_cache():
    """Call this after any KB change (publish, create, update, delete)."""
    global _corpus_cache
    _corpus_cache = None
    logger.info("[Cache] Corpus cache invalidated.")


_shelter_config_cache = None


def get_shelter_config(db: Session) -> dict:
    """Load full structured_config as dict; cached and invalidated on publish."""
    global _shelter_config_cache
    if _shelter_config_cache is not None:
        return _shelter_config_cache
    rows = db.query(schema.StructuredConfig).all()
    _shelter_config_cache = {r.key: r.get_value() for r in rows}
    return _shelter_config_cache


def invalidate_shelter_config_cache():
    """Call on POST /admin/publish alongside corpus cache."""
    global _shelter_config_cache
    _shelter_config_cache = None
    logger.info("[Cache] Shelter config cache invalidated.")


def _snapshot_article(art: schema.KBArticle) -> dict:
    """Eagerly copy all needed fields from an ORM object into a plain dict.
    This prevents DetachedInstanceError when the cache outlives the session."""
    return {
        "id": art.id,
        "title": art.title,
        "body": art.body,
        "category": art.category,
        "tags": art.get_tags() if hasattr(art, 'get_tags') else [],
    }


def _load_corpus(db: Session) -> dict:
    """Load and cache all enabled article embeddings as a numpy matrix.
    Articles are stored as plain dicts (not ORM objects) so the cache
    survives across different SQLAlchemy sessions."""
    global _corpus_cache
    if _corpus_cache is not None:
        return _corpus_cache
    
    articles = db.query(schema.KBArticle).filter(schema.KBArticle.enabled == True).all()
    embeddings = []
    meta = []
    for art in articles:
        if art.embedding:
            vec = deserialize_embedding(art.embedding)
            if vec is not None:
                embeddings.append(vec)
                # Snapshot to plain dict while session is still open
                meta.append(_snapshot_article(art))
    
    _corpus_cache = {
        "matrix": np.stack(embeddings) if embeddings else None,
        "articles": meta
    }
    logger.info(f"[Cache] Loaded {len(meta)} articles into corpus cache.")
    return _corpus_cache


def retrieve(db: Session, query_english: str, is_retry: bool, selected_category: Optional[str] = None) -> dict:
    normalized_query = normalize_query(query_english)
    logger.info(f"[Retrieve] query='{normalized_query}'")

    # 1. Direct Config Match
    config_match = db.query(schema.StructuredConfig).filter(schema.StructuredConfig.key == normalized_query).first()
    if config_match:
        try:
            val_str = str(config_match.get_value())
            return {
                "answer_text": val_str,
                "answer_type": "DIRECT_MATCH",
                "confidence": 1.0,
                "source_id": None,
                "categories": None,
                "article_data": None,
                "intent": "unclear",
                "intent_confidence": 0.0,
            }
        except Exception as e:
            logger.warning(f"[Retrieve] Config get_value failed for key={normalized_query}: {e}")

    # 2. Inventory check (phrase triggers; no embedding)
    try:
        shelter_config = get_shelter_config(db)
        inventory_answer = inventory_module.check_inventory(normalized_query, shelter_config)
        if inventory_answer:
            return {
                "answer_text": inventory_answer,
                "answer_type": "DIRECT_MATCH",
                "confidence": 1.0,
                "source_id": None,
                "categories": None,
                "article_data": None,
                "intent": "inventory",
                "intent_confidence": 1.0,
            }
    except Exception as e:
        logger.warning(f"[Retrieve] Shelter config/inventory failed: {e}")

    # 3. Classify intent and optionally enrich query
    intent, intent_confidence = "unclear", 0.0
    if _intent_classifier:
        try:
            intent, intent_confidence = _intent_classifier.classify(normalized_query)
            logger.info(f"[Retrieve] intent={intent} confidence={intent_confidence:.4f}")
        except Exception as e:
            logger.warning(f"[Retrieve] Intent classification failed: {e}")

    # 3a. Short-circuit for simple conversational intents (no KB lookup)
    if intent != "unclear" and intent_confidence >= 0.45:
        if intent == "greeting":
            return {
                "answer_text": "Hello. I can help you with questions about registration, food, medical help, sleeping areas, transportation, safety, and other services in this shelter. What would you like to ask?",
                "answer_type": "DIRECT_MATCH",
                "confidence": float(intent_confidence),
                "source_id": None,
                "categories": None,
                "article_data": None,
                "intent": intent,
                "intent_confidence": intent_confidence,
            }
        if intent == "identity":
            return {
                "answer_text": "I'm ResKiosk, an information kiosk for this evacuation center. I can answer questions about registration, food and water, medical help, sleeping areas, transportation, safety, and other basic services.",
                "answer_type": "DIRECT_MATCH",
                "confidence": float(intent_confidence),
                "source_id": None,
                "categories": None,
                "article_data": None,
                "intent": intent,
                "intent_confidence": intent_confidence,
            }
        if intent == "capability":
            return {
                "answer_text": "I can tell you about registration, food and water, medical help, sleeping areas, transportation, safety information, and other services available in this shelter.",
                "answer_type": "DIRECT_MATCH",
                "confidence": float(intent_confidence),
                "source_id": None,
                "categories": None,
                "article_data": None,
                "intent": intent,
                "intent_confidence": intent_confidence,
            }
        if intent == "small_talk":
            return {
                "answer_text": "You're welcome. If you need anything else, you can ask me about registration, food, medical help, sleeping areas, transportation, and other services in this shelter.",
                "answer_type": "DIRECT_MATCH",
                "confidence": float(intent_confidence),
                "source_id": None,
                "categories": None,
                "article_data": None,
                "intent": intent,
                "intent_confidence": intent_confidence,
            }
        if intent == "goodbye":
            return {
                "answer_text": "Okay. If you have more questions later, you can come back and ask me again.",
                "answer_type": "DIRECT_MATCH",
                "confidence": float(intent_confidence),
                "source_id": None,
                "categories": None,
                "article_data": None,
                "intent": intent,
                "intent_confidence": intent_confidence,
            }

    search_query = normalized_query
    if intent != "unclear" and intent_confidence >= 0.45 and intent in INTENT_ENRICHMENT:
        search_query = f"{normalized_query} {INTENT_ENRICHMENT[intent]}"
    if is_retry and selected_category:
        search_query = f"{search_query} {selected_category}"

    # 4. Embedding and corpus (guard so missing models/empty KB don't 500)
    try:
        embedder = load_embedder()
        query_vec = embedder.embed_text(search_query)
        corpus = _load_corpus(db)
    except Exception as e:
        logger.exception("[Retrieve] Embedder or corpus failed")
        return {
            "answer_text": "I'm sorry, I couldn't process that. Please try again.",
            "answer_type": "NO_MATCH",
            "confidence": 0.0,
            "source_id": None,
            "categories": None,
            "article_data": None,
            "intent": intent,
            "intent_confidence": intent_confidence,
        }

    if corpus["matrix"] is None or len(corpus["articles"]) == 0:
        return {
            "answer_text": "No knowledge base entries available.",
            "answer_type": "NO_MATCH",
            "confidence": 0.0,
            "source_id": None,
            "categories": None,
            "article_data": None,
            "intent": intent,
            "intent_confidence": intent_confidence,
        }

    try:
        scores = util.cos_sim(query_vec, corpus["matrix"])[0].numpy()
    except Exception as e:
        logger.exception("[Retrieve] Similarity computation failed")
        return {
            "answer_text": "I'm sorry, I couldn't process that. Please try again.",
            "answer_type": "NO_MATCH",
            "confidence": 0.0,
            "source_id": None,
            "categories": None,
            "article_data": None,
            "intent": intent,
            "intent_confidence": intent_confidence,
        }

    top_indices = np.argsort(scores)[::-1][:5]
    top_k_results = []
    for idx in top_indices:
        art_dict = corpus["articles"][idx]
        score = float(scores[idx])
        top_k_results.append(RetrievalResult(art_dict, score))

    for i, r in enumerate(top_k_results[:3]):
        logger.info(f"[Search] #{i+1} score={r.score:.4f} title='{r.article['title'][:60]}' cat={r.category}")

    best = top_k_results[0]

    # 5. Clarification gating (intent-aware)
    clarify = False
    if not is_retry:
        clarify = needs_clarification(normalized_query, top_k_results, intent, intent_confidence)

    # 6. Gating: >= 0.65 DIRECT_MATCH; 0.45-0.65 use best; < 0.45 + unclear -> clarify; else NO_MATCH
    if best.score >= THRESHOLD:
        return {
            "answer_text": best.article["body"],
            "answer_type": "DIRECT_MATCH",
            "confidence": best.score,
            "source_id": best.article["id"],
            "categories": None,
            "article_data": {
                "title": best.article["title"],
                "body": best.article["body"],
                "category": best.article["category"],
                "tags": best.article.get("tags", [])
            },
            "intent": intent,
            "intent_confidence": intent_confidence,
        }

    if best.score >= CLARIFICATION_FLOOR and clarify:
        cats = sorted(list({r.category for r in top_k_results if r.category}))
        if not cats:
            cats = ["General"]
        return {
            "answer_text": "Please clarify.",
            "answer_type": "NEEDS_CLARIFICATION",
            "confidence": best.score,
            "source_id": best.article["id"],
            "clarification_categories": cats,
            "categories": cats,
            "article_data": None,
            "intent": intent,
            "intent_confidence": intent_confidence,
        }

    # 0.45-0.65: use best match; < 0.45 or no clarify: fixed fallback
    if best.score >= CLARIFICATION_FLOOR:
        return {
            "answer_text": best.article["body"],
            "answer_type": "DIRECT_MATCH",
            "confidence": best.score,
            "source_id": best.article["id"],
            "categories": None,
            "article_data": {
                "title": best.article["title"],
                "body": best.article["body"],
                "category": best.article["category"],
                "tags": best.article.get("tags", [])
            },
            "intent": intent,
            "intent_confidence": intent_confidence,
        }

    return {
        "answer_text": "I am here to answer questions about registration, food, medical help, sleeping areas, transportation, safety, and other services in this shelter. Please ask about one of these topics or see a volunteer for more help.",
        "answer_type": "NO_MATCH",
        "confidence": best.score,
        "source_id": None,
        "categories": None,
        "article_data": None,
        "intent": intent,
        "intent_confidence": intent_confidence,
    }
