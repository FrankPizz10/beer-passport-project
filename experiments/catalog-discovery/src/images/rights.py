"""Rights classification for image candidates.

Independent of product-match evaluation. Unknown or unverifiable rights
status is never permission.

Experiment-level "approved" means the candidate meets the documented
rules below. It is not production clearance: attribution format,
CC BY-SA version, and embedded trademark risk still need legal review
before any production display (see docs/07).
"""
from __future__ import annotations

from .models import ImageCandidate, RightsStatus

# OFF's project-wide image statement, verified 2026-10-13.
OFF_LICENSE_BASIS = "CC BY-SA (OFF project-wide image statement)"

EMBEDDED_ARTWORK_NOTE = (
    "OFF notes product images may contain label artwork, logos, or other "
    "graphical elements subject to third-party rights; the photo license "
    "does not clear embedded rights."
)


def classify_off_rights(candidate: ImageCandidate) -> ImageCandidate:
    """Classify rights for an Open Food Facts candidate."""
    candidate.rights_notes = [EMBEDDED_ARTWORK_NOTE]
    if candidate.permission_basis == OFF_LICENSE_BASIS and candidate.image_url:
        candidate.rights_status = RightsStatus.APPROVED.value
        candidate.rights_notes.append(
            "reuse basis documented; attribution text recorded on candidate")
    else:
        candidate.rights_status = RightsStatus.RIGHTS_REVIEW.value
        candidate.rights_notes.append(
            "reuse basis not established; not permission")
    return candidate


def classify_rights(candidate: ImageCandidate) -> ImageCandidate:
    """Dispatch rights classification by source type."""
    if candidate.source_type == "openfoodfacts":
        return classify_off_rights(candidate)
    # Manufacturer candidates arrive pre-classified by build_candidate:
    # approved only with documented permission, else rights_review.
    if not candidate.rights_status:
        candidate.rights_status = RightsStatus.RIGHTS_REVIEW.value
    return candidate
