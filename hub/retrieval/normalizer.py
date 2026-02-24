"""
Hub-side query normalizer. Run once before intent classification and embedding.
Handles duplicate words and known STT artifacts that may survive kiosk-side processing.
"""
import re

_DUPLICATE_WORD = re.compile(r"\b(\w+)( \1)+\b", re.IGNORECASE)
_WHITESPACE = re.compile(r"\s+")

_HUB_CORRECTIONS = {
    "where where": "where",
    "i i": "i",
    "the the": "the",
    "is is": "is",
    "twelve noon": "12 noon",
    "seven am": "7 am",
    "seven a m": "7 am",
    "six pm": "6 pm",
    "six p m": "6 pm",
    "nine am": "9 am",
    "nine pm": "9 pm",
    "eight am": "8 am",
    "eight pm": "8 pm",
}


def normalize_query(text: str) -> str:
    """Lowercase, trim, collapse whitespace, then duplicated words, apply hub corrections."""
    if not text or not text.strip():
        return ""
    result = text.lower().strip()
    result = _WHITESPACE.sub(" ", result).strip()
    result = _DUPLICATE_WORD.sub(r"\1", result)
    for wrong, right in _HUB_CORRECTIONS.items():
        result = result.replace(wrong, right)
    result = _WHITESPACE.sub(" ", result).strip()
    return result
