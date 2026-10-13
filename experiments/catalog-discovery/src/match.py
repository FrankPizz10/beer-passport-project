"""Three-stage matching and duplicate detection.

Stage 1: trustworthy barcode exact match.
Stage 2: normalized exact match on (name, producer).
Stage 3: fuzzy match (rapidfuzz) on name+producer, configurable thresholds.

Classifications: existing | new_candidate | needs_review.
Ambiguous records are NEVER auto-merged; they go to needs_review.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field

from rapidfuzz import fuzz

from .normalize import (barcode_is_trustworthy, normalize_barcode,
                        normalize_name, parse_abv)

log = logging.getLogger(__name__)


@dataclass
class Candidate:
    candidate_id: str
    name: str
    normalized_name: str
    brand: str = ""
    producer_name: str = ""
    normalized_producer: str = ""
    category: str = ""
    style: str = ""
    abv: float | None = None
    barcode: str = ""
    country: str = ""
    source_names: list[str] = field(default_factory=list)
    source_record_ids: list[str] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)
    existing_beerpassport_id: str = ""
    match_status: str = "new_candidate"
    match_confidence: float = 0.0
    # term-matched | uncertain | rejected | unclassified (records imported
    # before relevance labeling existed; see README).
    relevance: str = "unclassified"
    missing_fields: list[str] = field(default_factory=list)
    review_reasons: list[str] = field(default_factory=list)


def make_candidate_id(source_name: str, source_record_id: str,
                      name: str, producer: str) -> str:
    """Deterministic candidate id from source identity, falling back to content."""
    seed = source_record_id or f"{normalize_name(name)}|{normalize_name(producer)}"
    digest = hashlib.sha256(f"{source_name}:{seed}".encode("utf-8")).hexdigest()
    return f"cand_{digest[:12]}"


def build_baseline_index(beers: list[dict], baseline) -> dict:
    """Index baseline beers by barcode and by (normalized name, producer)."""
    from .baseline import resolve_beer_labels
    by_barcode: dict[str, dict] = {}
    by_name_producer: dict[tuple[str, str], list[dict]] = {}
    for beer in beers:
        labels = resolve_beer_labels(beer, baseline)
        barcode = normalize_barcode(beer.get("upc"))
        entry = {"id": beer.get("id", ""), "beer": beer, **labels,
                 "abv": parse_abv(beer.get("abv"))}
        if barcode and barcode_is_trustworthy(barcode):
            # Keep the first baseline row per barcode; flag later dupes.
            by_barcode.setdefault(barcode, entry)
        key = (normalize_name(beer.get("name")),
               normalize_name(labels["brewery_name"]))
        by_name_producer.setdefault(key, []).append(entry)
    return {"by_barcode": by_barcode, "by_name_producer": by_name_producer}


def fuzzy_score(name_a: str, prod_a: str, name_b: str, prod_b: str) -> float:
    """Weighted similarity of (name, producer) pairs, 0-100."""
    name_score = fuzz.token_set_ratio(name_a, name_b)
    prod_score = fuzz.token_set_ratio(prod_a, prod_b) if prod_a and prod_b else 50.0
    return 0.7 * name_score + 0.3 * prod_score


def match_record(record: dict, index: dict, cfg) -> tuple[str, str, float, list[str]]:
    """Match one source record against the baseline.

    Returns (status, baseline_id, confidence, review_reasons).
    """
    reasons: list[str] = list(record.get("review_reasons", []))
    barcode = record.get("barcode", "")
    name = record.get("original_name", "")
    producer = record.get("producer_name") or record.get("brand") or ""
    nn, np = normalize_name(name), normalize_name(producer)
    abv = record.get("abv")

    # Stage 1: trustworthy barcode.
    if barcode and barcode_is_trustworthy(barcode):
        hit = index["by_barcode"].get(barcode)
        if hit:
            return _check_conflicts("existing", hit, abv, reasons, 100.0, cfg)
    elif barcode:
        reasons.append(f"suspicious barcode: {barcode!r}")

    # Stage 2: normalized exact on (name, producer).
    if nn:
        hits = index["by_name_producer"].get((nn, np), [])
        if len(hits) == 1:
            return _check_conflicts("existing", hits[0], abv, reasons, 95.0, cfg)
        if len(hits) > 1:
            reasons.append("multiple baseline rows share name+producer")
            return "needs_review", hits[0]["id"], 60.0, reasons

    # Stage 3: fuzzy.
    best, best_score = None, 0.0
    best_bnn, best_bnp = "", ""
    if nn:
        for (bnn, bnp), hits in index["by_name_producer"].items():
            if not bnn:
                continue
            score = fuzzy_score(nn, np, bnn, bnp)
            if score > best_score:
                best, best_score = hits[0], score
                best_bnn, best_bnp = bnn, bnp
    if best and best_score >= cfg.fuzzy_threshold:
        st_threshold = getattr(cfg, "single_token_producer_threshold", 85.0)
        is_single_token = len(best_bnn.split()) <= 1 or len(nn.split()) <= 1
        best_prod_score = fuzz.token_set_ratio(np, best_bnp) if np and best_bnp else 0.0
        if is_single_token and best_prod_score < st_threshold:
            reasons.append(
                f"weak producer agreement ({best_prod_score:.1f}) for single-token name {best_bnn!r}")
            return "needs_review", best["id"], best_score, reasons
        return _check_conflicts("existing", best, abv, reasons, best_score, cfg)
    if best and best_score >= cfg.review_threshold:
        reasons.append(f"possible duplicate (fuzzy score {best_score:.1f})")
        return "needs_review", best["id"], best_score, reasons
    if not nn or not np:
        reasons.append("insufficient evidence: missing name or producer")
        return "needs_review", "", best_score, reasons
    return "new_candidate", "", best_score, reasons


def _check_conflicts(status, hit, abv, reasons, confidence, cfg):
    """Downgrade to needs_review when attributes conflict with the baseline hit."""
    hit_abv = hit.get("abv")
    if abv is not None and hit_abv is not None:
        if abs(abv - hit_abv) >= cfg.abv_conflict:
            reasons.append(
                f"conflicting ABV: source {abv} vs baseline {hit_abv}")
            return "needs_review", hit["id"], confidence, reasons
    return status, hit["id"], confidence, reasons


def missing_fields_for(record: dict) -> list[str]:
    missing = []
    if not record.get("original_name"):
        missing.append("name")
    if not (record.get("producer_name") or record.get("brand")):
        missing.append("producer")
    if not record.get("category") and not record.get("categories"):
        missing.append("category")
    if record.get("abv") is None:
        missing.append("abv")
    if not barcode_is_trustworthy(record.get("barcode", "")):
        missing.append("trustworthy_barcode")
    return missing
