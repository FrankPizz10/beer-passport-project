# Catalog Expansion POC: Largest Publishable Batch

> Hub copy of the workstream analysis in
> `~/workspace/workstreams/catalog-expansion-poc/` (local). The batch
> data file (`publishable-batch.json`, 190 records) and the derivation
> script stay in the workstream per git hygiene; this document is the
> batch definition, counts, and attribution of record. Loading this
> batch into the catalog is an M2 step and needs Frank's approval.


Date: 2026-11-22. Workstream: Data, Catalog Expansion track.
Status: local analysis only. Nothing was loaded, uploaded, pushed, or
published. The batch file is `publishable-batch.json` in this directory.

## Headline result

**190 records are publishable today, all from Open Food Facts
(Tier A), and 189 of them carry a usable, provenance-tracked image.**
That is the entire publishable batch. The other 512 unique new records
from the POC are CraftCans (Tier C, internal-only forever) and are
excluded no matter how clean their match status is.

## Batch definition

A record is in the batch only if ALL of these hold:

1. **Documented provenance with a publishable license tier.** The
   record carries source, source record id, source URL, retrieval
   timestamp, and tier, and the tier is A (clear reuse permission or a
   suitable open license). Tier C material is excluded unconditionally.
2. **Reviewed match status "new".** The POC dedupe ladder (barcode
   equality, then exact normalized name-plus-brewery key, then fuzzy
   scoring) classified the record as a unique new record: not matched
   to the 5,894-beer baseline, not a duplicate of a record already
   accepted as new in the run (within or across sources), and NOT in
   the ambiguous band (combined fuzzy score 78 to 90, or name score at
   least 75), which was never auto-merged and never loaded as new.
3. **Attribution available.** The source's attribution requirement is
   known and recorded (see Attribution below), so the batch can be
   published with the required credit.

## Counts

### Ready records, by source

| Source | Tier | Ready records | Ready images |
|---|---|---:|---:|
| Open Food Facts | A | 190 | 189 |
| CraftCans GitHub dataset | C | 0 (excluded by tier) | 0 |
| **Total** | | **190** | **189** |

Ready images: 189 of the 190 ready records carry a front image URL
stored in the POC's image_provenance with image source
"openfoodfacts" and image tier A. The one ready record without an
image is barcode 0048000246004. CraftCans provides no images at all.

### Review items (held back for human review)

All 260 held records are the ambiguous queue: fuzzy candidates that
scored in the ambiguous band against either the baseline or the set of
records already accepted as new. They were neither merged nor loaded.

| Source | Ambiguous vs baseline | Ambiguous vs accepted-new | Total held |
|---|---:|---:|---:|
| Open Food Facts | 40 | 37 | 77 |
| CraftCans GitHub dataset | 147 | 36 | 183 |
| **Total** | **187** | **73** | **260** |

Note: even after review, the 183 CraftCans items can only ever be
confirmed as matches or as internal-only new records; Tier C keeps
them out of any published batch regardless of the review outcome. The
77 Open Food Facts items are the only review items that could grow the
publishable batch.

### Reconciliation with the POC totals

| Category | Open Food Facts | CraftCans | Total |
|---|---:|---:|---:|
| Staged | 283 | 800 | 1,083 |
| Unique new, Tier A (this batch) | 190 | 0 | 190 |
| Unique new, Tier C (excluded, internal only) | 0 | 512 | 512 |
| Matched to baseline (excluded) | 1 | 70 | 71 |
| Duplicate within/across sources (excluded) | 15 | 35 | 50 |
| Ambiguous, held for review | 77 | 183 | 260 |
| **Accounted** | **283** | **800** | **1,083** |

Cross-checks: unique new records total 702 (190 + 512), matched plus
duplicates plus ambiguous total 381 (71 + 50 + 260), and
702 + 381 = 1,083 staged. Every staged record is accounted for exactly
once.

## Methodology

The POC's PostgreSQL instance was ephemeral and no longer exists, so
the batch was re-derived rather than queried:

- `src/derive_publishable.py` re-runs the POC's exact in-memory
  pipeline (baseline load from the hub CSVs, both ingestors, the same
  deterministic sort order, the same Deduper) with PostgreSQL skipped
  and network access hard-disabled. Both ingestors serve from the disk
  cache in `data/` (the three cached Open Food Facts pages and the two
  CraftCans CSVs), so the re-derivation is fully local and repeatable.
- Before writing anything, the script asserts that the reproduced
  verdicts equal `output/metrics.json` exactly: baseline 5,894, every
  per-source status count, 702 unique new, 189 images with provenance.
  The assertion passed, so the batch rests on the measured POC run,
  not on a re-interpretation of it.
- The batch file contains the ready records with exactly the fields
  the POC stores for a catalog beer (name, brewery_name, style, abv,
  ibu, description, barcode, source, source_record_id, source_url,
  retrieved_at, tier) plus the image provenance fields (image_url,
  image_source, image_tier). No fields were invented.

Batch composition notes: all 190 records carry a barcode; 121 carry a
style, 106 carry an ABV, and 61 carry a description. Styles and ABVs
are partial because Open Food Facts community data is partial (see
Caveats).

## Attribution

### Open Food Facts (the batch's only source)

Documented licensing in this workstream (POC_REPORT.md and
src/sources.py): the Open Food Facts database is under the Open
Database License (ODbL), product contents under the Database Contents
License (DbCL), and images under CC BY-SA. Attribution and share-alike
duties are part of the Tier A clearance.

Required attribution text, to ship with any publication of this batch:

> Contains information from Open Food Facts
> (https://world.openfoodfacts.org), available under the Open
> Database License (ODbL) v1.0; product contents under the Database
> Contents License (DbCL); images under CC BY-SA.

Publication duties that follow from the documented licenses: credit
Open Food Facts as above, link the licenses, and honor share-alike
(ODbL for a database built on this data, CC BY-SA for the images).
Each record's source_url points at its Open Food Facts product page
for per-record traceability.

### CraftCans GitHub dataset (excluded; recorded for completeness)

No attribution text can clear this source. The GitHub mirror
(ilyakats/CUNY-R-Bridge-Workshop) carries no license; the dataset was
collected from CraftCans.com in January 2017 and published on Kaggle
by Jean-Nicholas Hould, with upstream terms unclear. Tier C: internal
measurement only, never published, per the standing tier policy.

## Image licensing notes

- Image provenance is tracked separately from record provenance in
  this workstream because the reuse conditions differ: for Open Food
  Facts the record data is ODbL/DbCL while each image is CC BY-SA on
  its own. All 189 ready images are image tier A with image source
  "openfoodfacts", so they clear for publication with the CC BY-SA
  attribution above and share-alike on the images.
- The batch stores image URLs (references to the images as hosted by
  Open Food Facts), exactly as the POC stored them in
  image_provenance. No image files were downloaded or copied in this
  analysis.
- A Tier C record must never silently acquire a Tier A looking image
  or the reverse; since CraftCans contributes no images and no
  records to this batch, no mixed-tier image risk exists in the batch.

## Caveats

- **retrieved_at is re-stamped.** The POC database is gone, so the
  `retrieved_at` values in publishable-batch.json carry the
  re-derivation date (2026-11-22), not the original POC run date
  (2026-11-21). Every other field reproduces the POC staging exactly,
  and the verdicts were verified identical to the measured run. Each
  record's source_url preserves traceability to the source.
- **Open Food Facts data quality carries over.** As POC_REPORT.md
  records: brand and name fields are community data and are sometimes
  inverted, multi-product pack listings appear, and category tags used
  as styles include origin labels such as "Beers From Germany". The
  190 records are publishable as licensed, deduplicated data; they
  have not had the brand/name cleanup pass the POC report recommends
  before any production import.
- **The ambiguous split (vs baseline / vs accepted-new) is a
  read-only probe.** The held-against labels were derived by probing
  the baseline index after classification; the verdicts themselves
  come from the POC's own Deduper and match metrics.json exactly.
- **Publishable here means license-clear and dedupe-clean.** It does
  not mean imported: loading this batch into the production catalog
  still needs the provenance columns and staged/review workflow the
  POC report recommends for the hub db package, and any actual
  publication or database write needs Frank's approval.
