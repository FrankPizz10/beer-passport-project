"""Three-stage matching and duplicate detection.

Stage 1: trustworthy barcode exact match.
Stage 2: normalized exact match on (name, producer).
Stage 3: fuzzy match (rapidfuzz) on name+producer, configurable thresholds.

Brand aliases (data/brand_aliases.json) let a consumer brand name (e.g.
"White Claw") count as producer evidence for its producing company (e.g.
"Mark Anthony Brewing"). An alias is evidence, not proof: a record is only
classified as `existing` when product-level identity (flavor signature)
also matches. Alias-supported but flavor-uncertain pairs go to
needs_review.

Classifications: existing | new_candidate | needs_review.
Ambiguous records are NEVER auto-merged; they go to needs_review.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from rapidfuzz import fuzz

from .normalize import (barcode_is_trustworthy, normalize_barcode,
                        normalize_name, parse_abv)

log = logging.getLogger(__name__)

# Tokens that describe the beverage category or base, not the flavor.
# Stripped when comparing flavor signatures so "High Noon Pineapple" can
# match "High Noon Vodka - Pineapple" on the shared flavor token.
DESCRIPTOR_TOKENS = frozenset(
    {"hard", "seltzer", "seltzers", "vodka"})


def load_brand_aliases(data_dir: str | Path) -> list[dict]:
    """Load non-ambiguous brand -> producer aliases from data_dir.

    Returns a list of {"brand", "producer", "evidence", "note"} dicts.
    Entries marked ambiguous in the file are documented but never used
    for matching. Missing file -> empty list (no alias behavior).
    """
    path = Path(data_dir) / "brand_aliases.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Could not load brand aliases from %s: %s", path, exc)
        return []
    aliases = []
    for entry in data.get("aliases", []):
        if entry.get("ambiguous"):
            continue
        if entry.get("brand") and entry.get("producer"):
            aliases.append(entry)
    return aliases


def resolve_producer_alias(producer: str, aliases: list[dict]) -> str | None:
    """Return the canonical producer for a brand, or None when unknown.

    Handles multi-brand strings (e.g. "Hard Seltzer Beverage Company LLC,
    Truly, Truly Unruly") by checking each comma/semicolon-separated part.
    """
    if not producer:
        return None
    needles = {normalize_name(producer)}
    needles.update(normalize_name(p) for p in re.split(r"[,;]", producer))
    needles.discard("")
    for alias in aliases:
        if normalize_name(alias["brand"]) in needles:
            return alias["producer"]
    return None


def producer_agreement_score(prod_a: str, prod_b: str,
                             aliases: list[dict]) -> tuple[float, bool]:
    """Score producer agreement 0-100, using brand aliases as evidence.

    Returns (score, via_alias). A brand whose alias resolves to the other
    side's producer (after normalization) scores 100. Otherwise falls back
    to the direct fuzzy score. via_alias is True only when the 100 came
    from an alias resolution.
    """
    if not prod_a or not prod_b:
        return 50.0, False
    direct = fuzz.token_set_ratio(prod_a, prod_b)
    resolved_a = resolve_producer_alias(prod_a, aliases)
    resolved_b = resolve_producer_alias(prod_b, aliases)
    canon_a = normalize_name(resolved_a) if resolved_a else prod_a
    canon_b = normalize_name(resolved_b) if resolved_b else prod_b
    if canon_a and canon_b and canon_a == canon_b:
        if resolved_a or resolved_b:
            return 100.0, True
        return 100.0, False
    return direct, False


def flavor_signature(name: str, brand: str) -> frozenset[str]:
    """Extract flavor-identifying tokens from a product name.

    Removes the brand tokens and generic category/base descriptors, leaving
    the tokens that distinguish one flavor from another (e.g. {natural,
    lime} vs {lemon}). Used to require product-level identity before an
    alias-supported match can become `existing`.
    """
    tokens = set(normalize_name(name).split())
    tokens -= set(normalize_name(brand).split())
    tokens -= DESCRIPTOR_TOKENS
    return frozenset(tokens)


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


def build_baseline_index(beers: list[dict], baseline,
                        aliases: list[dict] | None = None) -> dict:
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
    return {"by_barcode": by_barcode, "by_name_producer": by_name_producer,
            "aliases": aliases or []}


def fuzzy_score(name_a: str, prod_a: str, name_b: str, prod_b: str,
                brand_a: str = "", aliases: list[dict] | None = None) -> float:
    """Weighted similarity of (name, producer) pairs, 0-100.

    The record's brand is included in its name because source product names
    (e.g. Open Food Facts) often omit the brand that the baseline embeds
    in its beer name ("Hard Seltzer Natural Lime" + brand "White Claw" vs
    baseline "White Claw - Natural Lime"). Producer scoring is alias-aware.
    """
    full_a = normalize_name(f"{name_a} {brand_a}") if brand_a else name_a
    name_score = fuzz.token_set_ratio(full_a, name_b)
    prod_score, _ = producer_agreement_score(prod_a, prod_b, aliases or [])
    return 0.7 * name_score + 0.3 * prod_score


def match_record(record: dict, index: dict, cfg) -> tuple[str, str, float, list[str]]:
    """Match one source record against the baseline.

    Returns (status, baseline_id, confidence, review_reasons).
    """
    reasons: list[str] = list(record.get("review_reasons", []))
    barcode = record.get("barcode", "")
    name = record.get("original_name", "")
    brand = record.get("brand") or ""
    producer_raw = record.get("producer_name") or brand
    # Brand alias: map a consumer brand to its producing company using the
    # RAW producer string (normalization strips the commas in multi-brand
    # strings like "Hard Seltzer Beverage Company LLC, Truly, Truly Unruly").
    alias_target = resolve_producer_alias(producer_raw, index.get("aliases", []))
    producer = alias_target if alias_target else producer_raw
    via_alias = alias_target is not None
    nn, np = normalize_name(name), normalize_name(producer)
    abv = record.get("abv")
    aliases = index.get("aliases", [])

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
    best_flavor_match = False
    if nn:
        for (bnn, bnp), hits in index["by_name_producer"].items():
            if not bnn:
                continue
            score = fuzzy_score(nn, np, bnn, bnp, brand_a=brand,
                                aliases=aliases)
            if score > best_score:
                best, best_score = hits[0], score
                best_bnn, best_bnp = bnn, bnp
                best_flavor_match = (
                    flavor_signature(name, brand)
                    == flavor_signature(hits[0]["beer"].get("name", ""), brand))
    if best and best_score >= cfg.fuzzy_threshold:
        st_threshold = getattr(cfg, "single_token_producer_threshold", 85.0)
        is_single_token = len(best_bnn.split()) <= 1 or len(nn.split()) <= 1
        if np and best_bnp:
            best_prod_score, _ = producer_agreement_score(np, best_bnp, aliases)
        else:
            best_prod_score = 0.0
        if is_single_token and best_prod_score < st_threshold:
            reasons.append(
                f"weak producer agreement ({best_prod_score:.1f}) for single-token name {best_bnn!r}")
            return "needs_review", best["id"], best_score, reasons
        if via_alias and not best_flavor_match:
            # Alias proves the producer relationship, not the product.
            # Without matching flavor identity, do not auto-merge.
            reasons.append(
                "producer matched via brand alias but flavor identity uncertain")
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
