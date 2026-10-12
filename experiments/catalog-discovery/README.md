# BeerPassport Multi-Source Catalog Discovery Prototype

A small, locally runnable Python experiment that tests how effectively
BeerPassport can expand its beverage catalog by combining the existing catalog
with brewery directories and packaged-product databases.

**This is a research experiment, not a production ingestion system.** It does
not connect to or modify the production database, deploy infrastructure, or
change any BeerPassport application.

## The question

How many useful beverage candidates can we discover beyond the existing
BeerPassport catalog by combining our current catalog with brewery directories
and packaged-product databases, and how much cleanup or manual review will
those discoveries require?

## Sources

| Source | Role | Docs |
|---|---|---|
| BeerPassport baseline (4 CSV snapshots in `data/`) | Baseline catalog | `data/README.md` |
| Open Brewery DB | Producer directory (Source B). Breweries are **never** counted as beverage discoveries; producer candidates are reported separately. | https://www.openbrewerydb.org/documentation |
| Open Food Facts | Packaged-product database (Source C) | https://openfoodfacts.github.io/openfoodfacts-server/api/ |

**Licensing:** the Open Food Facts database is ODbL-licensed. This experiment
evaluates discovery potential only; incorporating records into production
requires a licensing review. No images are downloaded, stored, or processed
(explicitly out of scope).

## Setup

```bash
cd experiments/catalog-discovery
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running

```bash
# Limited initial test (validates CSV loading, API access, matching, exports)
python -m src.main --limit 100

# Full run (bounded by --brewery-pages and search coverage)
python -m src.main

# Refresh cached source data and refetch
python -m src.main --refresh

# Print a concise summary of the last run
python -m src.main --summary

# Reset local discovery state (destructive: previously discovered candidates
# are forgotten, so the next run counts everything as new again)
python -m src.main --reset-state
```

Useful options: `--search-terms beer cider "hard seltzer"` to override the
Open Food Facts search terms, `--brewery-pages N` for Open Brewery DB coverage
(200 records per page).

After the limited test succeeds, broaden the search by raising `--limit`,
adding `--brewery-pages`, and extending `--search-terms`.

## How it works

1. **Load baseline** — the four CSVs; brewery/category/style ids resolved to
   labels. Original values are kept intact; normalized copies are used only
   for matching.
2. **Fetch sources** — Open Brewery DB (paginated, max 200/page) and Open
   Food Facts (search terms, paginated). Responses are cached under
   `data/cache/`; requests are rate-limited and retried. **If one source
   fails, the others still run and export.**
3. **Normalize** — Unicode/case/punctuation normalization; barcodes kept as
   strings with leading zeros preserved; `ABV = 0.0` treated as *unknown*,
   not verified zero alcohol.
4. **Match (3 stages)** — (1) trustworthy barcode exact match, (2) normalized
   exact match on name+producer, (3) fuzzy match via rapidfuzz with
   configurable thresholds. Classifications: `existing`, `new_candidate`,
   `needs_review`. Ambiguous records are never auto-merged.
5. **Incremental state** — seen source ids and merged candidates persist in
   `data/state/`. Reprocessing unchanged data is idempotent; a record seen in
   a second source updates source associations instead of creating a
   duplicate.
6. **Export** — CSVs (UTF-8 with BOM, open cleanly in Excel/Sheets) plus a
   JSON run summary.

## Outputs (`output/`)

- `beverage_candidates.csv` — one row per normalized candidate
- `source_records.csv` — one row per source-specific product record
- `producer_candidates.csv` — one row per normalized producer candidate
- `review_queue.csv` — candidates needing manual review, with evidence
- `run_summary.json` — run timestamp, counts, field completeness, errors

## Tests

```bash
python -m unittest discover -s tests -v
```

Tests use mocked API responses; no network access required. They cover name
normalization, ABV 0.0 handling, barcode leading zeros, exact matching with
producer context, fuzzy thresholds, review classification, no auto-merge of
same-name/different-producer products, idempotent repeat runs, second-source
association updates, graceful single-source failure, and CSV lookup joins.

## Interpreting metrics

- `new_candidate` means *unmatched against the baseline*, not *verified new
  product*. Absence from the baseline alone does not prove novelty.
- `needs_review` is expected to be non-trivial: seasonal releases, vintages,
  reformulations, and package variants may be distinct products.
- Evaluate Open Brewery DB by **producer coverage** (does it improve product
  matching?), not by beverage count.
- Cross-source agreement is useful evidence, not proof of correctness.

## Known limitations

- Open Brewery DB blocked automated requests from the build environment
  (bot protection); the client implements the documented API and the runner
  records the failure gracefully, but producer enrichment could not be
  exercised end to end here.
- Open Food Facts rate-limits aggressively; the client backs off on 429s and
  caches everything, but full-coverage runs take a while.
- ABV coverage in Open Food Facts is sparse (`nutriments.alcohol_value` is
  often absent); many candidates will list ABV as unknown.
- The baseline catalog is a 2026-10-12 snapshot; rerun after re-exporting the
  live sheets to pick up catalog changes.
