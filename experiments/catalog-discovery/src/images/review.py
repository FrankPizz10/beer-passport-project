"""Approval rules combining product-match and rights verdicts.

- approved: strong identity evidence AND documented reuse basis.
- needs_review: ambiguous identity or unverified rights.
- rejected: identity mismatch or documented rights prohibition.
- fallback: no candidates found; the beverage record stays valid.

A beverage is never rejected for lacking a suitable image.
"""
from __future__ import annotations

from .models import (ApprovalStatus, ImageCandidate, MatchConfidence,
                     RightsStatus)

STRONG_MATCH = {
    MatchConfidence.BARCODE_EXACT.value,
    MatchConfidence.NAME_BRAND_FLAVOR.value,
}


def decide(candidate: ImageCandidate) -> ImageCandidate:
    """Set approval_status from match_confidence and rights_status."""
    match = candidate.match_confidence
    rights = candidate.rights_status

    if rights == RightsStatus.REJECTED.value:
        candidate.approval_status = ApprovalStatus.REJECTED.value
        candidate.rejection_reason = "rights rejected: documented prohibition"
        return candidate
    if match == MatchConfidence.MISMATCH.value:
        candidate.approval_status = ApprovalStatus.REJECTED.value
        candidate.rejection_reason = "product mismatch: image depicts a different product"
        return candidate
    if match in STRONG_MATCH and rights == RightsStatus.APPROVED.value:
        candidate.approval_status = ApprovalStatus.APPROVED.value
        return candidate
    candidate.approval_status = ApprovalStatus.NEEDS_REVIEW.value
    reasons = []
    if match not in STRONG_MATCH:
        reasons.append(f"identity {match}")
    if rights != RightsStatus.APPROVED.value:
        reasons.append(f"rights {rights}")
    candidate.reviewer_notes = (
        "needs human review: " + "; ".join(reasons) if reasons
        else candidate.reviewer_notes)
    return candidate


def fallback_record(beverage: dict) -> ImageCandidate:
    """A record for a beverage with no acceptable image candidate."""
    return ImageCandidate(
        beverage_id=beverage.get("beverage_id", ""),
        barcode=beverage.get("barcode", ""),
        beverage_name=beverage.get("beverage_name", ""),
        brand=beverage.get("brand", ""),
        producer=beverage.get("producer", ""),
        match_confidence=MatchConfidence.NO_CANDIDATE.value,
        rights_status=RightsStatus.RIGHTS_REVIEW.value,
        approval_status=ApprovalStatus.FALLBACK.value,
        reviewer_notes="no acceptable image candidate; use category fallback artwork",
    )
