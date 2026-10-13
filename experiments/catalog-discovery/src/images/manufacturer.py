"""Manufacturer image records (schema only in Stage 2).

No automated manufacturer discovery is implemented: with 10,000+
products, manual lookups are infeasible, and unrestricted automated
scraping of brand sites is not assumed appropriate. This module only
builds and validates a manufacturer candidate from supplied data, so
permission evidence can be recorded if a documented source emerges
later.

A manufacturer image is NEVER approved merely for being hosted on an
official site. Approval requires documented permission covering
commercial app use and hosting copies, with scope, attribution,
modification, and expiry terms recorded.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .models import ImageCandidate, RightsStatus


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


REQUIRED_PERMISSION_FIELDS = (
    "permission_basis",
    "permission_evidence",
    "permission_scope",
)


def build_candidate(beverage: dict, image: dict) -> ImageCandidate:
    """Build a manufacturer ImageCandidate from supplied data.

    `image` must carry image_url, source_page_url, and permission
    fields. Missing permission evidence leaves the candidate in
    rights_review; it is never auto-approved.
    """
    permission_basis = image.get("permission_basis", "")
    permission_evidence = image.get("permission_evidence", "")
    scope = image.get("permission_scope", "")
    has_permission = all([permission_basis, permission_evidence, scope])
    rights = (RightsStatus.APPROVED.value if has_permission
              else RightsStatus.RIGHTS_REVIEW.value)
    notes = []
    if not has_permission:
        notes.append("no documented permission; discovery is not authorization")
    return ImageCandidate(
        beverage_id=beverage.get("beverage_id", ""),
        barcode=beverage.get("barcode", ""),
        beverage_name=beverage.get("beverage_name", ""),
        brand=beverage.get("brand", ""),
        producer=beverage.get("producer", ""),
        flavor_variant=beverage.get("flavor_variant", ""),
        packaging=beverage.get("packaging", ""),
        source_type="manufacturer",
        source_record_url=image.get("source_page_url", ""),
        image_url=image.get("image_url", ""),
        license_name=image.get("license_name", ""),
        license_version=image.get("license_version", ""),
        license_url=image.get("license_url", ""),
        attribution_text=image.get("attribution_text", ""),
        contributor=image.get("contributor", ""),
        permission_basis=permission_basis,
        permission_evidence=permission_evidence,
        retrieved_at=utcnow(),
        rights_status=rights,
        rights_notes=notes,
    )
