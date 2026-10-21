"""Data model for image candidates.

Product-match confidence, rights status, and approval status are
independent axes. A correct image with bad rights is unusable; a
well-licensed image of the wrong product is unusable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MatchConfidence(str, Enum):
    BARCODE_EXACT = "barcode_exact"          # barcodes match after normalization
    NAME_BRAND_FLAVOR = "name_brand_flavor"  # fuzzy name + brand agreement
    BRAND_ONLY = "brand_only"                # brand matches, product does not
    AMBIGUOUS = "ambiguous"                  # not enough evidence either way
    MISMATCH = "mismatch"                    # evidence of a different product
    NO_CANDIDATE = "no_candidate"            # source returned nothing


class RightsStatus(str, Enum):
    APPROVED = "approved"            # documented reuse basis, terms recorded
    RIGHTS_REVIEW = "rights_review"  # unknown, unverified, or conflicting
    REJECTED = "rejected"            # documented prohibition


class ApprovalStatus(str, Enum):
    APPROVED = "approved"        # experiment-level approval, not production clearance
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"
    FALLBACK = "fallback"        # no acceptable image; beverage stays valid


@dataclass
class ImageCandidate:
    beverage_id: str = ""
    barcode: str = ""
    beverage_name: str = ""
    brand: str = ""
    producer: str = ""
    flavor_variant: str = ""
    packaging: str = ""
    source_type: str = ""            # "openfoodfacts" | "manufacturer"
    source_record_url: str = ""
    image_url: str = ""
    license_name: str = ""
    license_version: str = ""
    license_url: str = ""
    attribution_text: str = ""
    contributor: str = ""
    permission_basis: str = ""       # e.g. "CC BY-SA (OFF project statement)"
    permission_evidence: str = ""    # URL or note supporting the basis
    retrieved_at: str = ""
    match_evidence: list[str] = field(default_factory=list)
    match_confidence: str = MatchConfidence.NO_CANDIDATE.value
    rights_status: str = RightsStatus.RIGHTS_REVIEW.value
    rights_notes: list[str] = field(default_factory=list)
    approval_status: str = ApprovalStatus.NEEDS_REVIEW.value
    reviewer_notes: str = ""
    rejection_reason: str = ""

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["match_evidence"] = list(self.match_evidence)
        d["rights_notes"] = list(self.rights_notes)
        return d
