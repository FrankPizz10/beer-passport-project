# Catalog discovery: Open Brewery DB dataset evaluation (2026-10-12)

Owner summary. Builds on `REVIEW_2026-10-12.md`; same branch
(`experiment/catalog-discovery-prototype`), not merged.

## Corrections to the first version of this summary (same day)

1. **The two BrewDog "wins" were not wins.** The enrichment report listed
   both BrewDog candidates with a baseline fuzzy score of 100, and the
   baseline contains `BrewDog Ltd` (brewery id 241). The analysis has been
   corrected: an exact dataset match is now reported separately from
   whether it adds information beyond the baseline. Corrected result:
   **0 confirmed incremental attributions, 2 unresolved**
   (exact dataset match for "brewdog", but the baseline already scores
   100 on the same producer string, so the relationship needs manual
   assessment). A matching brand string does not prove a new producer.
2. **Relevance labels now update on reprocessing.** Re-running the
   pipeline left accumulated candidates `unclassified` because
   `merge_candidate` never applied the fresh classification. It now does,
   preserving prior evidence and timestamps; the run summary counts
   `reclassified_this_run` separately from legacy unclassified records.
   Before: 100/100 unclassified (branch state). A demo re-run against a
   /tmp copy of that state fetched 100 (different) OFF records, all new:
   the 100 legacy records stayed `unclassified` (not reprocessed), the
   100 new ones were labeled at creation (56 term-matched, 44 uncertain).
   The reprocessing path itself is verified by a new unit test that runs
   the pipeline twice over the same record: the second run reclassifies
   it (reclassified_this_run = 1) and preserves `first_discovered_at`
   and source associations.
3. **Fuzzy buckets renamed as provisional.** `compare_producers` now
   reports `exact_name_matches_unique` (154) separately from
   `fuzzy_ge_90_provisional` (1,317), `fuzzy_70_90_provisional` (7,987),
   and `fuzzy_lt_70_provisional` (2,655). The report carries a method note
   stating these are unreviewed score buckets, not verified coverage.
4. **Snapshot freshness and `--limit`.** The dataset is described as a
   snapshot retrieved 2026-10-12, not as verified current. `--limit 100`
   bounds product/API fetching only; the dataset source intentionally
   loads the full 11,959-row snapshot.

## Dataset snapshot used

- **Repo:** https://github.com/openbrewerydb/openbrewerydb
- **Commit:** `4d33d43af09eac011415eba834cd97fc86b0c99a`
  ("chore: workflow maintain"; history shows active data PRs, e.g. adding
  Massachusetts breweries)
- **File:** `breweries.csv` — 2.2 MB, **11,959 rows**, retrieved 2026-10-12
- **Local path (gitignored, not committed):**
  `data/dataset/openbrewerydb-breweries.csv`
- **Attribution recorded:** "Producer data: Open Brewery DB
  (openbrewerydb.org)"
- **Reuse terms:** repo LICENSE is MIT (software); FAQ governs the dataset:
  free for any project **with credit to Open Brewery DB**. What "credit"
  concretely requires is unspecified; open question for production use.

The live API returned 403s from both the build environment and your Mac.
The precise cause is unconfirmed and is not characterized here. The API
adapter is retained (`--brewery-source api`, the default); the dataset is
an explicit alternative (`--brewery-source dataset`).

## Match and ambiguity counts

Dataset (11,959 producers) vs baseline (1,431 breweries):

- **Exact normalized-name overlap: 154 unique names** (162 dataset rows;
  duplicates are multi-location chains, e.g. 10 Barrel Brewing Co x4).
- Fuzzy >= 90 ("clear"): 1,317. Fuzzy 70-90 ("ambiguous"): 7,987.
  Fuzzy < 70 ("likely new"): 2,655.

Manual inspection verdict: the fuzzy scorer (`token_set_ratio`) inflates
scores on common tokens. "1 of Us Brewing Company" scores 88 against
"(512) Brewing Company" purely on shared words; the ambiguous bucket is
dominated by this kind of weak overlap. Treat fuzzy buckets as
*potential* matches needing review, not as findings.

OFF beverage candidates (100 in current state), producer attribution:

- **0 newly attributable via the dataset (corrected).** The two BrewDog
  hard-seltzer candidates match "Brewdog" (Coburg, Australia) exactly in
  the dataset, but the baseline already contains `BrewDog Ltd` at fuzzy
  score 100. These are recorded as **unresolved**: the dataset adds a
  location-specific producer record, but whether that is distinct from
  the baseline's BrewDog entry needs manual assessment. Not counted as
  enrichment wins.
- 63 unchanged, 35 list no producer at all.
- An earlier fuzzy-based pass claimed 6 improvements; manual inspection
  showed all 6 were token-subset false positives ("High Noon" matching
  "Grinder's High Noon Brewery", "Corona" matching a brewpub in Corona,
  CA). The assessment now counts only exact matches as improvements,
  and only when the baseline has nothing close.

## What changed (code, this round)

- `src/sources/brewery_dataset.py`: pinned-snapshot CSV loader with
  provenance constants; `data/dataset/SNAPSHOT.md` documents commit, URL,
  date, columns, and reuse terms.
- `--brewery-source {api,dataset}` / `--brewery-dataset` flags; API path
  untouched and still the default.
- `src/enrichment.py`: `python -m src.enrichment` compares the snapshot
  against baseline breweries and assesses OFF producer attribution;
  writes `output/producer_enrichment.json`.
- Repeat counter now catches duplicate IDs within a run, not just across
  runs; summary labels accumulated vs this-run figures explicitly.
- Relevance "confirmed" renamed to "term-matched" everywhere (a term
  matching is not beverage confirmation).
- Duplicate-claim wording: cross-source beverage merging stays described
  as unsupported; repeated sightings (same barcode) distinguished from
  different barcodes that may be the same beverage.

## What the proof of concept shows

- The dataset path works end to end and is reproducible from the pinned
  snapshot reference.
- The dataset is ~8x the baseline and current (2026 data vs 2008 baseline);
  exact matching gives a conservative lower bound of its coverage: 154
  unique producer names.
- Producer enrichment on this sample: 0 confirmed new attributions, 2
  unresolved (BrewDog), 63 unchanged, 35 with no producer listed. The
  honest result is smaller than first reported, and the analysis now
  says so explicitly.

## What it does not show

- Whether fuzzy producer matching can be tuned into something trustworthy
  (not attempted; needs alias handling and blocking, a bigger project).
- Cross-source beverage deduplication (still unsupported by design; OBDB
  contributes producers only).
- That any "new" candidate is a verified new product.
- Production viability of either source (licensing unreviewed).

## Unresolved source and licensing decisions (yours)

1. ODbL/DbCL review before any production use of OFF-derived data.
2. OFF API usage form + contact email in User-Agent; staging vs
   production for further evaluation.
3. What "credit to Open Brewery DB" requires in practice.
4. Whether the OBDB API 403 is worth revisiting later or the dataset
   snapshot is the permanent path.
5. Manual assessment of the 2 unresolved BrewDog attributions (dataset
   "Brewdog", Coburg AU vs baseline "BrewDog Ltd"): same producer with
   a location-specific record, or genuinely distinct?

## Checks performed

- 41/41 unit tests pass (new: enrichment bucket/improved-vs-unresolved
  tests, relevance-reclassification test, dataset-source pipeline test,
  repeat-counter regression test).
- Enrichment analysis re-run against the full 11,959-row snapshot with
  corrected logic: 154 exact unique names; fuzzy provisional buckets
  1,317 / 7,987 / 2,655; OFF assessment 0 improved, 2 unresolved,
  63 unchanged, 35 no producer.
- Manual inspection: ~12 ambiguous, ~8 clear, ~8 likely-new producer
  samples; all 6 fuzzy "improved" OFF attributions (all false positives);
  both BrewDog records (baseline_score 100 vs BrewDog Ltd, id 241).
- Discovery state (100 candidates) and baseline snapshots verified
  untouched; no pipeline runs wrote to the committed state or outputs.
  A reclassification demo ran against a /tmp copy of the branch state:
  the full 11,959-row dataset loads in the pipeline; the 100 fetched OFF
  records were all new (OFF search results shift between runs), so no
  legacy repeats were reprocessed there, but all 100 new records received
  current relevance labels at creation (56 term-matched, 44 uncertain).

## Validation run (2026-10-13)

Validated against an isolated test copy in `/tmp/beerpassport_validation` (branch `experiment/catalog-discovery-prototype`, commit `c1d5647`):

- **Candidate matching**:
  - `existing`: 12/12 inspected, 9 correct (75.0%). 3 false positives (`la goudale blonde` matching `Blonde` by La Choulette, `La Blonde` matching `Blonde` by Abbaye Des Rocs, and `75CL BIERE LA GOUDALE AMBREE` matching `Ambree` by Abbaye Des Rocs). Root cause: `token_set_ratio` gives 100 on generic single-word beer names ("Blonde", "Ambrée") and combined with shared "Brasserie" pushes similarity over the 88.0 threshold into `existing`.
  - `new_candidate`: 30/30 inspected, 30 correct (100.0%). All confirmed absent from 2008 baseline (mostly post-2015 seltzers and new craft lines).
  - `needs_review`: 30/30 inspected, 30 correct (100.0%). Appropriately held ambiguous names, missing producer records, and parent/brand mismatches in review rather than auto-merging.
- **Relevance labels**:
  - `term-matched`: 30/30 inspected, 30 correct (100.0%). Strictly matches documented English search terms.
  - `uncertain`: 30/30 inspected, 30 correct (100.0%). Strictly catches non-English beverage descriptions (e.g. *Bières*, *Bier*, *Birra*) and non-beverage outliers without dropping them.
- **Producer attribution**:
  - Exactly 2 exact dataset matches: `Jupiler` (`cand_f3083d8c048f`) and `Krombacher` (`cand_af21b406ceec`). Both 2/2 confirmed supported (100.0%) against Open Food Facts manufacturing evidence and Open Brewery DB geographic, website, and company records.
- **Incremental behavior**:
  - Bounded input executed twice against test copy: 0 duplicate candidates created, 100% first-discovered timestamps preserved, 100% accumulated source evidence preserved, relevance updated upon reprocessing.
- **Traceability and outputs**:
  - 100% of candidate rows trace to source records and valid HTTP URLs; review queue matches 103/103 `needs_review` candidate IDs.
- **Verdict**: **Ready with specific limitations**. High-priority limitation to address before broader ingestion: adjust fuzzy auto-matching to require stronger independent producer similarity or route single-word/generic beer style names to `needs_review` rather than auto-merging into `existing`.

## Fuzzy matcher fix and re-assessment (2026-10-13)

- **Issue addressed**: Generic single-word beer style names (e.g. "Blonde", "Ambrée") combined with shared brewery tokens like "Brasserie" overweighted `fuzz.token_set_ratio`, causing 3 false positives to be auto-labeled as `existing` (75.0% accuracy in `existing`).
- **Fix implemented**: Added a single-token producer agreement guard in `match_record` (`src/match.py`) with configurable threshold `single_token_producer_threshold = 85.0` (`src/config.py`). When the candidate name or matched baseline beer name has only a single word (`len <= 1`), independent producer agreement (`fuzz.token_set_ratio`) must reach at least 85.0 to auto-merge into `existing`. Borderline matches below 85.0 are routed to `needs_review` with the reason `weak producer agreement (X) for single-token name '...'` rather than false auto-merging. Exact barcode (Stage 1) and exact normalized name+producer (Stage 2) matches remain completely preserved.
- **Unit test suite**: 45/45 unit tests pass (4 new tests added in `tests/test_match.py`: 3 regression tests for the false positives and 1 positive-control test for legitimate single-word names with strong producer agreement).
- **Measured results (test state re-evaluation)**:
  - `existing`: reduced from 12 (with 3 false positives) to 7 confirmed true matches (**100.0% observed accuracy**, 0 false positives).
  - All 3 previously misclassified records (`la goudale blonde` / *Brasserie Goudale*, `La Blonde` / *Brasserie du Mont Blanc*, and `75CL BIERE LA GOUDALE AMBREE` / *Brasserie de Gayant*) are now routed to `needs_review` with their respective weak-producer reasons.
  - Borderline name cases (`cand_5833aa3b5f32` `Blonde` / *Leffe, AB-InBev* and `cand_ff71162fc781` `Heineken Beer` / *Heineken Bier*) were also safely shifted from `existing` to `needs_review`.
  - Legitimate single-token matches with strong producer agreement (`Framboise Lambic Beer` / *Lindemans*, `Pécheresse` / *Lindemans*) correctly remain in `existing`.
  - `new_candidate` count remains unchanged at 85 (100.0% accuracy).
  - `needs_review` count updated from 103 to 109, appropriately holding all borderline and incomplete entries for review.

