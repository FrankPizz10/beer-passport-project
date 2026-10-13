"""Deterministic normalization helpers.

All matching operates on normalized values; original values are always kept
intact on the source record for investigation.
"""
from __future__ import annotations

import re
import unicodedata

_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)


# Letters that do not decompose under NFKD get an explicit ASCII mapping.
_ASCII_FOLD = str.maketrans({
    "ø": "o", "Ø": "O",
    "æ": "ae", "Æ": "AE",
    "œ": "oe", "Œ": "OE",
    "ß": "ss", "ẞ": "SS",
    "ł": "l", "Ł": "L",
    "đ": "d", "Đ": "D",
    "þ": "th", "Þ": "TH",
    "ð": "d", "Ð": "D",
})


def normalize_name(value: str | None) -> str:
    """Lowercase, strip accents, remove punctuation, collapse whitespace."""
    if not value:
        return ""
    text = value.translate(_ASCII_FOLD)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = _PUNCT_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()
    return text


def normalize_barcode(value: str | None) -> str:
    """Return the barcode as a digit string, preserving leading zeros.

    Returns "" when the value is missing or contains no digits.
    """
    if value is None:
        return ""
    digits = re.sub(r"\D", "", str(value))
    return digits


def barcode_is_trustworthy(barcode: str) -> bool:
    """A barcode is trustworthy when it looks like a real GTIN/EAN/UPC.

    Accepts 8, 12, 13, or 14 digit strings. Rejects all-zero strings and
    obvious placeholders (e.g. 12345678).
    """
    if len(barcode) not in (8, 12, 13, 14):
        return False
    if set(barcode) == {"0"}:
        return False
    if barcode in {"12345678", "123456789012", "1234567890123"}:
        return False
    return True


def parse_abv(value: object) -> float | None:
    """Parse an ABV value; return None when unknown.

    NOTE: ABV == 0.0 is treated as *unknown*, not as verified zero alcohol,
    per the known data-quality caution in the baseline catalog.
    """
    if value is None:
        return None
    try:
        text = str(value).strip().rstrip("%")
        if not text:
            return None
        abv = float(text)
    except (ValueError, TypeError):
        return None
    if abv <= 0:
        return None  # 0.0 means unknown in the baseline catalog
    if abv > 60:
        return None  # implausible for a beverage; treat as bad data
    return abv


def is_relevant_beverage(name: str, categories: str, brands: str,
                         terms: list[str]) -> tuple[bool, str]:
    """Heuristic relevance filter for packaged-product records.

    Returns (relevant, reason). Records that fail are rejected as irrelevant;
    uncertain ones are kept with a review reason.
    """
    relevance, reason = classify_relevance(name, categories, brands, terms)
    return relevance != "rejected", reason


def classify_relevance(name: str, categories: str, brands: str,
                       terms: list[str]) -> tuple[str, str]:
    """Classify a packaged-product record as term-matched, uncertain, or rejected.

    - "term-matched": a search term appears in the record's name/categories/
      brand. This means the term matched; it does NOT confirm the record is
      a beverage.
    - "uncertain": non-empty record, but no search term matched. Kept as a
      candidate with a review reason; NOT treated as a verified beverage.
    - "rejected": empty name/categories/brand; excluded from candidates.
    """
    blob = normalize_name(" ".join([name or "", categories or "", brands or ""]))
    if not blob:
        return "rejected", "empty name/categories"
    for term in terms:
        if normalize_name(term) in blob:
            return "term-matched", ""
    # Uncertain: keep for review rather than silently dropping.
    return "uncertain", "uncertain category"
