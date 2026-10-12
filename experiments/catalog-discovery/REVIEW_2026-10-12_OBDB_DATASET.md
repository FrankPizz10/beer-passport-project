# Catalog discovery: Open Brewery DB dataset evaluation (2026-10-12)

Owner summary. Builds on `REVIEW_2026-10-12.md`; same branch
(`experiment/catalog-discovery-prototype`), not merged.

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

- **2 newly attributable via the dataset (exact match):** both BrewDog
  hard-seltzer candidates -> "Brewdog" (Coburg, Australia). The 2008-era
  baseline has no BrewDog; this is a genuine, if small, enrichment win.
- 63 unchanged, 35 list no producer at all.
- An earlier fuzzy-based pass claimed 6 improvements; manual inspection
  showed all 6 were token-subset false positives ("High Noon" matching
  "Grinder's High Noon Brewery", "Corona" matching a brewpub in Corona,
  CA). The assessment now counts only exact matches as improvements.

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
  exact matching gives a conservative lower bound of its coverage.
- Producer enrichment is real but small on this sample and entirely
  dependent on matching strictness: 2 exact attributions, 0 trustworthy
  fuzzy ones.

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

## Checks performed

- 34/34 unit tests pass (new: dataset-source pipeline test with mocked
  OFF fetch; existing API-failure test updated for the new config fields).
- Enrichment analysis run against the full 11,959-row snapshot:
  comparison and OFF assessment complete in ~16s.
- Manual inspection: ~12 ambiguous, ~8 clear, ~8 likely-new producer
  samples; all 6 fuzzy "improved" OFF attributions (all false positives);
  both exact-match improvements.
- Discovery state (100 candidates) and baseline snapshots verified
  untouched; no new pipeline runs wrote to them.
