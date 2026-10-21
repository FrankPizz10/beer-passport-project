# Session Handoff: image-sourcing experiment Stage 1+2 (2026-10-13)

## Objective worked on

Plan and implement a Python image-sourcing workflow under
experiments/catalog-discovery/: find product images for beverages,
evaluate product-match accuracy and reuse permissions independently,
and produce structured outputs that could eventually support S3
storage. No S3, no production storage, no app integration.

## Changes actually made

On branch `experiment/image-sourcing-plan` (PR #5, not merged):

Stage 1 (docs only):
- `docs/07-image-licensing-assessment.md` - OFF license tiers verified
  2026-10-13 (ODbL / DbCL / CC BY-SA), per-image API metadata
  confirmed, rules R1-R7, unresolved legal questions flagged.
- `docs/08-image-sourcing-plan.md` - proposed module, source paths,
  statuses, pilot scope.

Stage 2 (implemented after owner approval of the plan, with two
owner decisions: OFF-only automation, no manual lookups; no OFF
usage form yet):
- `src/images/` - models, off_images (barcode-first OFF adapter),
  manufacturer (schema-only, no automated discovery), match, rights,
  review, export, cli (`python -m src.images.cli --input <csv>`).
- `tests/test_images.py` - 23 tests, all mocked, no live API.
- `pilot/IMAGE_PILOT_REPORT_2026-10-13.md` - 17-product pilot results.
- This handoff file.

No discovery code, state, or outputs modified. No image binaries
downloaded. Untappd and Unsplash explicitly excluded per owner.

## Repositories, branches, and commits involved

- Repository: FrankPizz10/beer-passport-project
- Branch: experiment/image-sourcing-plan (off main at bd0ad3a)
- PR: https://github.com/FrankPizz10/beer-passport-project/pull/5 (NOT merged)

## Tests and results

- Full suite: 86 tests pass (63 existing + 23 new), `python -m unittest
  discover -s tests`. Two initial failures in the new brand-agreement
  check (single-token only) were fixed.
- Pilot: 17 beverages, 12 approved (all barcode-exact + rights
  approved), 5 fallback (no OFF image: Nordic Wolf, Stelz, Doort,
  Ravini, Vista Bay), 0 errors, 0 needs_review.

## Decisions made

- Owner: Stage 2 is OFF-only automation; manufacturer path is
  schema-only (no manual lookups at 10k+ scale, no unrestricted
  scraping assumed).
- Owner: no OFF API usage form yet; pilot volume is within limits.
- Implementer: OFF candidates with the documented CC BY-SA basis are
  rights-approved at experiment level; unknown/unverifiable rights are
  never permission; match and rights are independent statuses.

## Known issues and unresolved questions

- Approval is experiment-level, not production clearance (attribution
  format, BY-SA version, trademark risk need legal review).
- Approved images not visually spot-checked.
- OFF wiki attribution guidelines unverifiable (bot-blocked); OFF
  manufacturer-picture guidance unverifiable (page 500).

## Next recommended action

Frank reviews PR #5. If approved: visual spot-check of the 12 approved
images, then run against a representative sample of existing catalog
beverages.

## Update (2026-10-21): catalog refresh measurement

At Frank's direction ("best path forward to production with a
noticeable catalog improvement"), ran one bounded discovery run on an
isolated copy (fresh state; committed state/outputs untouched):
1,480 OFF records, truncated by 503s on 3 terms. Results: 728
new_candidate, 705 needs_review, 46 existing; image presence 82%
among new candidates; image workflow validated 40/40 approved;
seeded sample (n=30) classified 17 useful / 11 not useful / 2
uncertain, with the not-useful dominated by non-beverages from the
cider/malt terms (relevance-filter gap). Full report:
pilot/REFRESH_MEASUREMENT_2026-10-21.md. Artifacts:
pilot/refresh_new_candidates_2026-10-21.csv (728 rows),
pilot/refresh_sample30_classified.csv.

Confirmed blocker for backfill: baseline has 0/5,894 trustworthy
barcodes, so the refresh path (new OFF-sourced records) is the
viable route to a visibly better catalog.

Next recommended action: relevance negative-category filters + retry
truncated terms in 2-3 more bounded runs; then promotion planning
(schema image fields are a known 2.0 blocker). Backend/domain
restoration needs Frank's AWS write access.
