"""Product-identity evaluation for image candidates.

Determines whether a candidate image depicts the beverage it is
attached to, using barcode, name, brand, and flavor evidence.
Deterministic; no thresholds are tuned here beyond the shared
fuzzy baseline used for name comparison.

A generic image of the correct brand is not the correct product image:
flavor and packaging may differ even when the brand matches.
"""
from __future__ import annotations

from rapidfuzz import fuzz

from ..normalize import normalize_barcode, normalize_name
from .models import ImageCandidate, MatchConfidence

NAME_FUZZY_THRESHOLD = 88.0


def evaluate_off_match(beverage: dict, product: dict) -> tuple[str, list[str]]:
    """Evaluate identity between a beverage record and an OFF product.

    Returns (MatchConfidence value, evidence list).
    """
    evidence: list[str] = []
    bev_barcode = normalize_barcode(beverage.get("barcode", ""))
    off_barcode = normalize_barcode(str(product.get("code") or ""))
    if bev_barcode and off_barcode:
        if bev_barcode == off_barcode:
            evidence.append(f"barcode exact match ({bev_barcode})")
            return MatchConfidence.BARCODE_EXACT.value, evidence
        evidence.append(
            f"barcode mismatch (beverage {bev_barcode} vs product {off_barcode})")
        return MatchConfidence.MISMATCH.value, evidence

    bev_name = normalize_name(beverage.get("beverage_name", ""))
    off_name = normalize_name(product.get("product_name", ""))
    bev_brand = normalize_name(beverage.get("brand", ""))
    off_brands = normalize_name(product.get("brands", ""))

    if not bev_name or not off_name:
        evidence.append("missing product name on one side; cannot compare")
        return MatchConfidence.AMBIGUOUS.value, evidence

    name_score = fuzz.WRatio(bev_name, off_name)
    brand_agrees = bool(bev_brand) and (
        bev_brand == off_brands
        or bev_brand in off_brands
        or off_brands in bev_brand
    )
    evidence.append(f"name fuzzy score {name_score:.1f}")
    if brand_agrees:
        evidence.append(f"brand agrees ({beverage.get('brand')})")

    if name_score >= NAME_FUZZY_THRESHOLD and brand_agrees:
        return MatchConfidence.NAME_BRAND_FLAVOR.value, evidence
    if brand_agrees:
        evidence.append("brand matches but product name does not; "
                        "flavor/packaging may differ")
        return MatchConfidence.BRAND_ONLY.value, evidence
    return MatchConfidence.MISMATCH.value, evidence


def apply_match(candidate: ImageCandidate, beverage: dict,
                product: dict) -> ImageCandidate:
    """Attach the match verdict to a candidate."""
    confidence, evidence = evaluate_off_match(beverage, product)
    candidate.match_confidence = confidence
    candidate.match_evidence = evidence
    return candidate
