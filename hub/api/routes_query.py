import time
import asyncio
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from hub.db.session import get_db
from hub.db import schema
from hub.models import api_models
from hub.retrieval import search, formatter, translator
from hub.retrieval import rewriter as query_rewriter
from hub.retrieval.normalizer import normalize_query

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory session store: maps session_id → list of {user, assistant} dicts
session_history = {}


@router.post("/query", response_model=api_models.QueryResponse)
async def submit_query(query: api_models.QueryRequest, db: Session = Depends(get_db)):
    start_time = time.time()
    try:
        user_language = query.language or "en"
        raw_text = (query.transcript_english or query.transcript_original).strip()
        logger.info(f"[Query] Incoming: lang={user_language} raw='{raw_text[:80]}'")

        # Translate to English if needed
        if user_language != "en":
            try:
                text = translator.translate(raw_text, user_language, "en")
                logger.info(f"[Query] Translated ({user_language}→en): '{text[:80]}'")
            except Exception as e:
                logger.error(f"[Query] Inbound translation failed: {e}")
                text = raw_text
        else:
            text = raw_text

        normalize_query(text)  # kept for side-effects / logging

        try:
            t1 = time.time()
            result = search.retrieve(db, text, query.is_retry, query.selected_category)
            logger.info(f"[Query] Retrieval took {(time.time() - t1) * 1000:.0f}ms")
        except Exception as e:
            logger.error(f"[Query] Retrieval error: {e}")
            result = {
                "answer_text": "I am here to answer questions about registration, food, medical help, sleeping areas, transportation, safety, and other services in this shelter. Please ask about one of these topics or see a volunteer for more help.",
                "answer_type": "NO_MATCH",
                "confidence": 0.0,
                "source_id": None,
                "categories": None,
                "article_data": None,
                "intent": "unclear",
                "intent_confidence": 0.0,
            }

        # Query rewrite on low-confidence results
        if result["answer_type"] in ("NO_MATCH", "NEEDS_CLARIFICATION"):
            rewritten = query_rewriter.maybe_rewrite(
                text,
                result.get("intent", "unclear"),
                result["confidence"],
            )
            if rewritten != text:
                try:
                    retry_result = search.retrieve(db, rewritten, False, None)
                    logger.info(f"[Query] Rewrite: '{text[:40]}' → '{rewritten[:40]}' → {retry_result['answer_type']}")
                    result = retry_result
                except Exception as e:
                    logger.warning(f"[Query] Rewrite retry failed: {e}")

        answer_type = result["answer_type"]
        confidence = result["confidence"]

        if answer_type == "DIRECT_MATCH" and result.get("article_data"):
            history_str = ""
            if query.session_id and query.session_id in session_history:
                import json
                history_str = json.dumps(session_history[query.session_id][-3:], ensure_ascii=False)
            import json
            article_json = json.dumps(result["article_data"], ensure_ascii=False)
            try:
                answer_text = await asyncio.to_thread(formatter.format_response, article_json, text, history_str)
            except Exception as e:
                logger.error(f"[Query] Formatter error: {e}")
                answer_text = result["article_data"].get("answer", result["answer_text"])
        else:
            answer_text = result.get("answer_text") or ""

        if not (answer_text and answer_text.strip()):
            answer_text = "I am here to answer questions about registration, food, medical help, sleeping areas, transportation, safety, and other services in this shelter. Please ask about one of these topics or see a volunteer for more help."

        latency = (time.time() - start_time) * 1000
        logger.info(f"[Query] {answer_type} in {latency:.0f}ms | conf={confidence:.2f} | lang={user_language}")

        # Translate answer back to user's language
        answer_text_localized = None
        if user_language != "en" and answer_text:
            try:
                answer_text_localized = translator.translate(answer_text, "en", user_language)
                logger.info(f"[Query] Translated to {user_language}: '{answer_text_localized[:80]}...'")
            except Exception as e:
                logger.error(f"[Query] Translation failed: {e}")

        # Log to query_logs
        try:
            import time as _time
            log_entry = schema.QueryLog(
                kiosk_id=query.kiosk_id or "",
                transcript_original=query.transcript_original,
                transcript_english=text,
                language=user_language,
                kb_version=query.kb_version,
                answer_type=answer_type,
                latency_ms=round(latency, 2),
                created_at=int(_time.time()),
            )
            db.add(log_entry)
            db.commit()
        except Exception:
            logger.exception("[Query] DB log/commit failed")
            db.rollback()

        if query.session_id:
            if query.session_id not in session_history:
                session_history[query.session_id] = []
            session_history[query.session_id].append({"user": text, "assistant": answer_text})

        return api_models.QueryResponse(
            answer_text_en=answer_text,
            answer_text_localized=answer_text_localized,
            answer_type=answer_type,
            confidence=float(confidence),
            kb_version=query.kb_version,
            source_id=result.get("source_id"),
            clarification_categories=result.get("categories"),
        )

    except Exception:
        logger.exception("Query failed")
        return api_models.QueryResponse(
            answer_text_en="I am here to answer questions about registration, food, medical help, sleeping areas, transportation, safety, and other services in this shelter. Please ask about one of these topics or see a volunteer for more help.",
            answer_text_localized=None,
            answer_type="NO_MATCH",
            confidence=0.0,
            kb_version=getattr(query, "kb_version", 1),
            source_id=None,
            clarification_categories=None,
        )


@router.delete("/query/session/{session_id}")
async def end_session(session_id: str):
    if session_id in session_history:
        del session_history[session_id]
        logger.info(f"Session {session_id} deleted.")
        return {"status": "success", "message": "Session ended."}
    return {"status": "ok", "message": "Session not found."}
