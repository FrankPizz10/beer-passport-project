# Image-Sourcing Implementation Plan

Status: PROPOSED (Stage 1). No code written. Awaiting owner approval
before Stage 2 implementation.

## Purpose and scope

Find suitable product images for beverages in the BeerPassport catalog,
evaluate product-match accuracy and reuse permissions, and produce
structured outputs that can eventually support storing approved images
in S3. This is an experiment: no S3 uploads, no production storage, no
app integration.

Image sourcing is logically independent of beverage discovery. A valid
beverage is never rejected for lacking a suitable image.

## Architecture

New module `src/images/` inside the existing experiment, separate from
discovery:

```
src/images/
    __init__.py
    models.py        # ImageCandidate dataclass + status enums
    off_images.py    # Open Food Facts image source adapter
    manufacturer.py  # Manufacturer image discovery (metadata only)
    match.py         # Product-identity evaluation for image candidates
    rights.py        # Licensing/permission classification
    review.py        # Review queue + approval rules
    export.py        # CSV/JSON outputs
tests/test_images_*.py
```

It reads beverage records (the 17-row curated CSV first, then catalog
samples), queries approved sources, and writes to `output/images/`.
It never touches `data/state/discovery_state.json` or existing outputs.

## Source paths

**Source 1: Open Food Facts.** Barcode-first lookup via the product API
(`GET /api/v2/product/<barcode>.json`), falling back to name/brand
search. Captures `image_url`, `image_front_url`, per-upload `uploader`,
and source product URL. Respects the documented 10 req/min search
limit, identified User-Agent, and the existing cache client. Verified
2026-10-13: one curated product (Nordic Wolf 7350071700563) has no OFF
images at all; Topo Chico (5449000294708) has front/nutrition views
with uploader `kiliweb`.

**Source 2: Manufacturer images.** Metadata-only discovery: record
official product page URLs and candidate image URLs with their source
pages. Approval requires documented permission (license statement or
grant) covering commercial app use and hosting, with scope,
attribution, modification, and expiry terms recorded. No automated
scraping without checking the site's terms; discovery is not
authorization.

**Fallback.** Products with no acceptable image are listed for
original category-based artwork (beer, NA beer, cider/perry, hard
seltzer, FMB, spirit RTD, wine). No artwork generated in this phase.

Untappd and Unsplash are explicitly excluded per owner direction.

## Candidate record (core fields)

beverage_id, barcode, beverage_name, brand, producer, flavor_variant,
packaging, source_type (off/manufacturer), source_record_url,
image_url, license_name, license_version, license_url,
attribution_text, contributor, permission_basis, permission_evidence,
retrieved_at, match_evidence, match_confidence, rights_status,
match_review_status, approval_status, reviewer_notes, rejection_reason.

## Statuses (independent axes)

- `match_confidence`: barcode_exact / name_brand_flavor / brand_only /
  ambiguous / mismatch
- `rights_status`: approved / rights_review / rejected
- `approval_status`: approved / needs_review / rejected / fallback
  (fallback = no acceptable image; the beverage stays valid)

Rules: unknown rights are never approval. Brand-only image matches
never auto-approve (flavor/packaging may differ). Correct match with
bad rights is unusable; good license on the wrong product is unusable.

## Pilot

1. Run against the 17 curated useful additions
   (`pilot/curated_useful_additions.csv`).
2. Then a representative sample of existing catalog beverages.
3. Outputs: candidate CSV, structured JSON metadata, coverage summary,
   match-accuracy summary, licensing-outcome summary, approved list,
   human-review list, fallback-artwork list.

Success criteria: the workflow runs repeatably on the 17, every
candidate carries provenance and independent match/rights verdicts,
and the review/fallback lists are actionable. Coverage numbers are
reported, not treated as proof of broad accuracy.

## Testing

Mocks/fixtures for all source adapters; no live-API dependence in
tests. Distinguish "source returned nothing" from "source failed".
Deterministic matching. Follow existing `unittest` conventions.

## What approval unlocks (Stage 2)

Implement `src/images/`, adapters, matching, rights classification,
tests, run the 17-product pilot, and update docs + handoff. Still no
S3, no app changes, no merges without review.

## Related

- Licensing assessment: `07-image-licensing-assessment.md`
- Image readiness checklist: `06-image-readiness-checklist.md`
- Curated input: `../pilot/curated_useful_additions.csv`
- Existing pipeline: `../src/`
