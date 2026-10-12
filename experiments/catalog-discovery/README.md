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

### Source access policy (checked 2026-10-12)

**Open Food Facts.** `world.openfoodfacts.org/robots.txt` disallows `/api`,
`/cgi`, and `/facets` for general crawlers (`User-agent: *`). That directive
targets web crawlers (search-engine indexers). The published API documentation
separately and explicitly describes programmatic access: always identify the
app with a custom `User-Agent`, respect **10 req/min/IP for search queries**
(`GET /api/v*/search` or `GET /cgi/search.pl`; 15 req/min/IP for product
reads), test against the staging environment (`world.openfoodfacts.net`,
user/password `off`), and use the bulk CSV/JSONL downloads when fetching
more than a few hundred products. robots.txt alone is not a legal conclusion;
the documented API is the intentional interface and its terms govern. This
prototype calls `/cgi/search.pl` per those documented API rules, with a 6s
request delay (10 req/min ceiling) and a custom User-Agent.

**Open Brewery DB.** `openbrewerydb.org/robots.txt` allows `/` for general
crawlers. The 403 responses seen from the build environment are Cloudflare bot
protection (the FAQ confirms Cloudflare sits in front of the API), not a
robots.txt denial; treat as an access issue to investigate (e.g. retry from a
residential IP), not a policy refusal. Reuse guidance (FAQ, checked
2026-10-12): the dataset is free and open-source, the API is free with no
authentication, any project may use the dataset **with credit to Open Brewery
DB**; the API is community-supported with no SLAs and recommended for
personal projects.

**Licenses (Open Food Facts).** Database: Open Database License (ODbL).
Individual contents: Database Contents License (DbCL). Product images:
Creative Commons Attribution-ShareAlike (CC BY-SA); product photos may also
contain label artwork subject to third-party copyright. ODbL carries
attribution and share-alike obligations that can matter when publicly reusing
or republishing derived data. This experiment evaluates discovery potential
only; **experimental access is not production reuse approval**. A licensing
review is required before any production ingestion.

**Open questions for the project owner (do not contact sources on our behalf):**
- Whether to file the OFF API usage form and add a contact email to the
  User-Agent before any further collection.
- Whether the Open Brewery DB 403 is specific to datacenter IPs (test from a
  residential IP before concluding).
- Licensing review of ODbL share-alike implications for displaying OFF-derived
  product data in the app.

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
- `relevance` separates **confirmed** records (a search term matched the
  record's name/categories/brand) from **uncertain** ones (kept for review,
  not verified beverages) and **rejected** ones (excluded). Records imported
  before relevance labeling show as `unclassified`.
- `needs_review` is expected to be non-trivial: seasonal releases, vintages,
  reformulations, and package variants may be distinct products.
- **Candidate identity.** A candidate merges repeat sightings of the same
  source record (same barcode/product code, e.g. under two search terms).
  Cross-*source* product merging is unproven with the current sources: Open
  Brewery DB yields producers only, never product candidates. When source
  record IDs are missing, the same product from two sources would not merge
  (follow-up design: content-based fallback identity). Same normalized
  name+producer across different barcodes is intentionally *not* auto-merged;
  those sit in the review queue as possible variants or data-entry duplicates.
- Evaluate Open Brewery DB by **producer coverage** (does it improve product
  matching?), not by beverage count.
- Cross-source agreement is useful evidence, not proof of correctness.

## Known limitations

- Open Brewery DB blocked automated requests from the build environment
  (403, Cloudflare bot protection — not a robots.txt denial; robots.txt
  allows `/`). The client implements the documented API and the runner
  records the failure gracefully, but producer enrichment could not be
  exercised end to end here. Retry from a residential IP before concluding.
- Open Food Facts rate-limits aggressively (documented: 10 req/min/IP for
  search); the client now waits 6s between requests, backs off on 429s, and
  caches everything. The docs ask for bulk CSV/JSONL downloads beyond a few
  hundred products and testing on the staging environment; this prototype
  uses production search within the documented rate limit.
- ABV coverage in Open Food Facts is sparse (`nutriments.alcohol_value` is
  often absent); many candidates will list ABV as unknown.
- The baseline catalog is a 2026-10-12 snapshot; rerun after re-exporting the
  live sheets to pick up catalog changes.
- The custom User-Agent does not yet include a contact email as the OFF docs
  recommend; the API usage form has not been filed. Both are open questions
  for the project owner (see Source access policy).
