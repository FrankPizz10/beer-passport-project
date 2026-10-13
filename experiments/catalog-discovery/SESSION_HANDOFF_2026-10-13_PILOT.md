# Session Handoff: catalog-quality pilot (2026-10-13)

## Objective worked on

Run the catalog-quality pilot Frank requested: a reproducible seeded
sample of up to 30 candidates (20 new_candidate / 5 needs_review / 5
existing, shortfalls reallocated), classify each as Useful addition /
Already represented / Not a useful beverage candidate / Uncertain, and
produce a pilot report plus a curated CSV of only the Useful additions,
with a recommendation on whether to proceed to an image-sourcing pilot.

## Changes actually made

Pushed to `experiment/catalog-discovery-prototype` (PR #2, not merged):

- `experiments/catalog-discovery/pilot/PILOT_REPORT_2026-10-13.md` -
  per-record review of all 30 sampled candidates, summary by pipeline
  status, key finding, recommendation, limitations.
- `experiments/catalog-discovery/pilot/curated_useful_additions.csv` -
  17 records: candidate_id, product_name, producer, brand, category,
  country, barcode, abv, source_url. All rows verified against the
  report (17/17 match).
- `experiments/catalog-discovery/pilot/sample_manifest.json` - seed
  (20261013), method, pool counts, sample counts, candidate IDs.
- This handoff file.

No matcher code changed. No discovery state/outputs touched (the pilot
ran on an isolated copy at /tmp/pilot_work, since deleted).

## Repositories, branches, and commits involved

- Repository: FrankPizz10/beer-passport-project
- Branch: experiment/catalog-discovery-prototype
- Base at start: 0bb2f43 ("Updated gitignore")
- New commit: <SHA after push> (pilot artifacts)
- PR: https://github.com/FrankPizz10/beer-passport-project/pull/2
  (updated with pilot findings + recommendation; NOT merged, per Frank's
  rule)

## Tests and results

- Unit tests: not re-run (no code changed in this pilot). The branch's
  documented state remains 45 tests passing after the Oct 13 fuzzy
  matcher correction.
- Verification checks run for this pilot:
  - All 30 report entries present; 17 useful-addition IDs in the report
    match the CSV rows exactly (script-verified).
  - sample_manifest.json parses as valid JSON.
  - No em-dash characters in any pilot artifact (Frank's writing rule).
  - No images fetched or evaluated (out of scope).
  - git status clean except the new pilot/ directory (no normal state,
    outputs, baseline snapshots, or .vscode changes).

## Decisions made

- Final classifications: 17 Useful addition, 9 Already represented,
  4 Uncertain, 0 Not a useful beverage candidate.
- Useful-addition rate among sampled new_candidates: 16/24 (67%).
- Nutrl Pineapple (vodka-based) kept as Useful: the baseline already
  covers vodka-seltzer lines (High Noon, Cutwater, Stateside), so it is
  in-scope by the baseline's own precedent. Whether spirits-based
  seltzers belong in BeerPassport remains Frank's product decision.
- Recommendation: proceed to image-sourcing pilot using the curated
  set only (16 producers, 8 regions, enough variety); do NOT feed the
  raw new_candidate pool until brand-alias matching is fixed (21% of
  sampled new candidates were already in the baseline under the brewery
  name: White Claw/Mark Anthony Brewing, Truly/Boston Beer Company,
  High Noon/E. & J. Gallo Winery).

## Outstanding issues and risks

- The systematic false-"new" pattern (OFF consumer-brand name vs
  baseline corporate-brewery name) is the main precision leak. Fix
  needed: brand-alias handling in producer matching (map consumer brands
  to producing brewery) before broader ingestion.
- 4 records classified Uncertain (Vizzy thin/invalid identifier data;
  generic Truly with no flavor; Aldi generic with anomalous 1.36% abv;
  producerless "Premium hard seltzer"). They stay out of the curated set.
- Directional pilot only (n=30, seltzer-heavy because that is what the
  discovery run returned); not statistically conclusive.

## Next recommended action

Frank reviews PR #2's pilot findings. If he approves, the next step is
an image-sourcing pilot on the 17 curated records only; in parallel,
add brand-alias handling to producer matching on the same branch.
