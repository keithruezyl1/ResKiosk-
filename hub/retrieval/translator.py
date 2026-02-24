"""
Server-side translation using Facebook NLLB-200-distilled-600M.
Loaded from local hub_models/nllb/ directory — fully offline.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_pipeline = None
_tokenizer = None
_model = None

# NLLB BCP-47 language code mapping (ISO 639-1 -> NLLB)
LANG_CODES = {
    "en":  "eng_Latn",
    "es":  "spa_Latn",
    "tl":  "tgl_Latn",  # Filipino/Tagalog
    "fr":  "fra_Latn",
    "zh":  "zho_Hans",  # Simplified Chinese
    "ar":  "arb_Arab",
    "vi":  "vie_Latn",
    "hi":  "hin_Deva",
    "ko":  "kor_Hang",
    "ja":  "jpn_Jpan",
    "pt":  "por_Latn",
    "id":  "ind_Latn",
    "ms":  "zsm_Latn",  # Malay
    "th":  "tha_Thai",
    "de":  "deu_Latn",
    "ru":  "rus_Cyrl",
}

def get_nllb_model_path() -> str:
    path = os.environ.get("RESKIOSK_NLLB_PATH")
    if not path:
        path = os.path.join("packaging", "hub_models", "nllb")
    return path


def _load_pipeline():
    """Lazy-load NLLB pipeline once."""
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    from transformers import pipeline as hf_pipeline

    model_path = get_nllb_model_path()
    if not os.path.exists(model_path):
        logger.warning(f"NLLB model not found at {model_path}. Translation unavailable.")
        return None

    logger.info(f"Loading NLLB-200 from {model_path}...")
    try:
        _pipeline = hf_pipeline(
            "translation",
            model=model_path,
            tokenizer=model_path,
            device=-1,           # CPU
            local_files_only=True,
        )
        logger.info("NLLB-200 loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load NLLB model: {e}")
        _pipeline = None

    return _pipeline


def translate(text: str, src_lang: str, tgt_lang: str, max_length: int = 512) -> str:
    """
    Translate text from src_lang to tgt_lang.
    Language codes are ISO 639-1 (e.g. 'en', 'es', 'tl').
    Returns original text if translation fails or languages match.
    """
    if not text or src_lang == tgt_lang:
        return text

    src_nllb = LANG_CODES.get(src_lang)
    tgt_nllb = LANG_CODES.get(tgt_lang)

    if not src_nllb or not tgt_nllb:
        logger.warning(f"Unsupported language pair: {src_lang} -> {tgt_lang}. Returning original.")
        return text

    pipe = _load_pipeline()
    if pipe is None:
        return text

    try:
        # NLLB requires src_lang and tgt_lang in the pipeline call
        result = pipe(
            text,
            src_lang=src_nllb,
            tgt_lang=tgt_nllb,
            max_length=max_length
        )
        translated = result[0]["translation_text"].strip()
        logger.info(f"Translated ({src_lang}->{tgt_lang}): '{text[:50]}...' -> '{translated[:50]}...'")
        return translated
    except Exception as e:
        logger.error(f"Translation error ({src_lang}->{tgt_lang}): {e}")
        return text


def is_supported_language(lang_code: str) -> bool:
    return lang_code in LANG_CODES
