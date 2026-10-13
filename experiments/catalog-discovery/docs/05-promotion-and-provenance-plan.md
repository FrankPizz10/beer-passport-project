# Promotion and Provenance Plan

What it would take to move reviewed experiment records into the
BeerPassport database. This is a plan only: **do not implement an
importer and do not modify the application database** from this
experiment.

## Preconditions (all required)

1. **Licensing approval.** ODbL/DbCL share-alike review for OFF-derived
   data; "credit to Open Brewery DB" defined for producer data. Owner
   signs off; see `03-source-and-data-governance.md` for open questions.
2. **Scope sign-off.** Owner resolves the open product decisions
   (mocktails, kombucha, bottled-spirits boundary) in
   `01-product-scope-and-taxonomy.md`.
3. **Human review.** Every promoted record was manually classified
   Useful addition under `04-alias-and-review-procedure.md`. No bulk
   promotion of unreviewed `new_candidate` output.

## Per-record requirements

- **Identity**: product name, brand, producer, flavor/variant, barcode,
  ABV, package size, country/region.
- **Provenance**: source name, source record ID, source URL, retrieval
  date, and the matcher version/commit that classified it.
- **Source attribution**: stored per record so attribution can be
  rendered and audited later.
- **Duplicate check**: re-run against the live baseline immediately
  before import (the baseline moves; experiment-time matching goes
  stale). Barcode exact-match first, then name+producer, then the
  alias-aware fuzzy path. Anything ambiguous stays out.
- **Category/style mapping**: map to the app's taxonomy; flag records
  needing a new label for owner approval instead of inventing one.

## Reversible import

- Import as a single batch with a batch ID, timestamp, and the
  experiment commit SHA.
- Dry-run first: produce the exact insert list for review without
  writing.
- Keep the source experiment artifacts (sample manifest, review notes,
  per-record rationale) linked from the batch record.
- Provide a batch rollback (delete by batch ID) and a reconciliation
  report: promoted vs skipped vs conflicts found at import time.

## Auditability

Every promoted beer must answer: where did this come from, who reviewed
it, when, under which license, and what baseline did it match against.
If any answer is missing, the record does not promote.

## Explicitly out of scope here

- Writing the importer.
- Touching the BeerPassport database, migrations, or application code.
- Backfilling images (see `06-image-readiness-checklist.md`).
