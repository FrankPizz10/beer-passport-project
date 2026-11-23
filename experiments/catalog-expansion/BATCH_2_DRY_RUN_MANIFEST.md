# Catalog Batch 2: Dry-Run Import Manifest (702 records)

Dry run only. Nothing was imported, uploaded, or written to any
database. The record-level batch file (`batch-702.json`, SHA-256
recorded below) stays in the local workstream
(`catalog-expansion-poc/`) per git hygiene; this manifest is the
reviewable record of what a real import would load, and under what
dispositions.

## Batch definition

The measured Catalog Expansion POC batch under decision D-015
(2026-11-23, licensing tiers relaxed): every unique-new record from
the POC, both sources. Open Food Facts 190 (Tier A) and the CraftCans
GitHub dataset 512 (Tier C, valid under D-015). Dedupe verdicts were
reproduced locally for this dry run with the POC pipeline and match
the measured metrics exactly: 702 unique new against the 5,894-beer
baseline, with 71 baseline matches, 50 duplicates, and 260 ambiguous
records excluded and accounted for in `PUBLISHABLE_BATCH.md`.

## Dry-run validation (run 2026-11-23, local, no network)

| Check | Open Food Facts (190) | CraftCans (512) |
|---|---|---|
| Name present | 190 | 512 |
| Brewery present | 175 | 512 |
| Barcode present | 190 | 0 |
| Style present | 121 | 512 |
| ABV present | 106 | 488 |
| Description present | 61 | 0 |
| Source URL and tier recorded | 190 | 512 |

Catalog-match validation is the POC dedupe ladder itself (barcode,
exact normalized name+brewery, fuzzy band), re-run for this manifest:
all 702 records classify as new against the frozen baseline.

## Image disposition (185 import-ready)

Image verification is the 2026-11-23 private preview through the
admin viewer's rendering rules (hosted http(s) URLs render directly;
anything else falls back to initials artwork), with a visual
product-match review of every hosted image:

- **185 images import as hosted URLs**: verified to load and to show
  the correct product. All are Open Food Facts front images (CC
  BY-SA; attribution below).
- **4 images excluded** (the records import without an image):
  - 3080216049250: image is a product specification table, not a
    product photo.
  - 3119780268276: image shows a different product (Heineken boxes)
    than the record (Schweppes lemon).
  - 3272460122272: barcode/back-label-only shot.
  - 3800052314110: image shows no product (a floor scene).
- **517 records import without an image**: the 512 CraftCans records
  (the source carries no images), the 4 exclusions above, and 1 Open
  Food Facts record with no image (barcode 0048000246004).
- **0 records need private S3 signing**: every import-ready image is
  a hosted URL the viewer renders directly. Signing becomes relevant
  only if images are later mirrored into private storage.

## Import blockers and rules

- **15 Open Food Facts records have no brewery name.** Baseline
  beers require a brewery, so these 15 are held out of the import
  until each is resolved to a brewery (matched to an existing
  brewery or a new one created). Import-ready records: 687 of 702.
- New IDs are assigned at import time starting above the current
  maximum beer ID (6,055), in manifest order; baseline IDs are never
  reused or shifted.
- Every record carries provenance (source, source record id, source
  URL, retrieval timestamp, tier). Loading provenance into the
  catalog requires the provenance fields the POC report specifies;
  the current CSV loader does not carry them, so a real import needs
  that loader support first.
- Attribution that must ship with the Open Food Facts data:
  "Contains information from Open Food Facts
  (https://world.openfoodfacts.org), available under the Open
  Database License (ODbL) v1.0; product contents under the Database
  Contents License (DbCL); images under CC BY-SA."
- CraftCans records carry their source URL for traceability; per
  D-015 no attribution text is mandated, and provenance is recorded
  the same way.

## Evidence

- Batch file: `batch-702.json` (local workstream), SHA-256
  `a2ad122a0ce50b6f445537a05615d8379fb4a870706b313f28e1bc59d2f84913`.
- Batch definition and reconciliation: `PUBLISHABLE_BATCH.md` in
  this directory (PR #15).
- Image verification: the workstream preview report
  (`catalog-expansion-poc/preview/PREVIEW_REPORT.md`, local):
  rendered 185, broken 0, mismatched 4, missing 1.

A real import is a database write and waits for Frank's approval,
after the Lightsail step 5 sequence reaches catalog enrichment (M2).
