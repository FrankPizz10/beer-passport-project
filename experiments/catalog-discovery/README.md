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

**Open Food Facts.** `world.openfoodfacts.org/robots.txt` (rechecked
2026-10-12, unchanged) disallows `/api`, `/cgi`, and `/facets` for
`User-agent: *`. That directive is addressed to general web crawlers. The
published API documentation separately describes programmatic access in
detail: always identify the app with a custom `User-Agent`, respect
**10 req/min/IP for search queries** (`GET /api/v*/search` or
`GET /cgi/search.pl`; 15 req/min/IP for product reads), test against the
staging environment, and use the bulk CSV/JSONL downloads when fetching
more than a few hundred products.

On the tension: robots.txt alone is not a legal conclusion, and the API
docs do not automatically override it either. They are two signals from
the same operator aimed at different audiences (indexing crawlers vs API
consumers). This prototype's position: it calls `/cgi/search.pl` exactly
as the API documentation describes (identified User-Agent, 6s delay for a
10 req/min ceiling, small evaluation volume), which is the documented
intentional interface. That is a judgment call for an experiment, not a
clearance for production. Do not broaden collection until the approved
retrieval path is explicit.

How the current experiment relates to the guidance:
- Within the documented search rate limit (6s delay); backs off on 429/503.
- Small volume (100s of records), not the thousands that trigger the bulk
  download recommendation.
- Uses production search, not the staging environment the docs ask testers
  to use. Staging has a separate account database and HTTP basic auth
  (`off`/`off`).
- Custom User-Agent set, but without the contact email the docs recommend.

**Licenses (Open Food Facts).** Per the API docs and the licensing tutorial
(https://openfoodfacts.github.io/openfoodfacts-server/api/tutorials/license-be-on-the-legal-side/,
checked 2026-10-12): the database is under the Open Database License
(ODbL); individual contents under the Database Contents License (DbCL);
product images under Creative Commons Attribution-ShareAlike (CC BY-SA),
with the caveat that photos may contain label artwork subject to
third-party copyright. OFF points reusers to its Terms of use and reuse,
its wiki attribution guidelines, and a public non-compliance list; legal
questions go to reuse@openfoodfacts.org. ODbL carries attribution and
share-alike obligations that can matter when publicly reusing or
republishing derived data. This experiment evaluates discovery potential
only; **experimental access is not production reuse approval**.

**Open Brewery DB.** `openbrewerydb.org/robots.txt` allows `/` for general
crawlers. The API 403s seen from the build environment *and* the project
owner's machine have an unconfirmed cause; robots.txt does not explain
them and they are not characterized here as a confirmed Cloudflare
decision. Reuse guidance (FAQ, checked 2026-10-12): the dataset is free
and open-source, the API is free with no authentication, any project may
use the dataset **with credit to Open Brewery DB**; the API is
community-supported with no SLAs, recommended for personal projects.
Because API availability is unconfirmed, this experiment evaluates
producers through a pinned snapshot of the official dataset repository
(see `data/dataset/SNAPSHOT.md`) instead of spending the task on access
troubleshooting. The snapshot was retrieved on 2026-10-12; that records
the retrieval date and does not verify that every brewery entry was
current on that date. The live-API adapter is retained
(`--brewery-source api`).

**Open questions for the project owner (do not contact sources on our behalf):**
- Whether to file the OFF API usage form and add a contact email to the
  User-Agent before any further collection.
- Whether to move evaluation traffic to the OFF staging environment.
- Licensing review of ODbL/DbCL share-alike implications for displaying
  OFF-derived product data in the app.
- What "credit to Open Brewery DB" concretely requires for production use.

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
Open Food Facts search terms, `--brewery-pages N` for Open Brewery DB API
coverage (200 records per page), `--brewery-source dataset` to load producers
from the pinned dataset snapshot instead of the live API
(see `data/dataset/SNAPSHOT.md`; snapshot CSV is gitignored, download it
first).

`--limit N` bounds product/API fetching (e.g. `--limit 100` fetches at most
100 Open Food Facts records). It does not truncate the dataset source:
`--brewery-source dataset` intentionally loads the full pinned snapshot
(11,959 producers), because a partial slice of a reference dataset would
skew producer matching.

The run summary distinguishes accumulated totals (all candidates ever
discovered) from this-run figures (`incremental`: new, updated, repeated
source records, and reclassified relevance labels this run).

To evaluate producer enrichment without a full discovery run:
```bash
python -m src.enrichment --limit 2000   # bounded comparison; full snapshot by default
```
This compares the dataset snapshot against the baseline breweries and
assesses producer attribution for the OFF candidates in the current
discovery state, writing `output/producer_enrichment.json`. Breweries are
never counted as beverage discoveries.

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

## Continuous integration

GitHub Actions (`.github/workflows/catalog-discovery-ci.yml`) runs on pull
requests into `main` and on pushes to `main` that touch this experiment:
lint (ruff), typecheck (mypy), a byte-compile build check, and the unit
tests. Tool settings live in `pyproject.toml`; the tools themselves are
pinned in `requirements-dev.txt`. Run the same checks locally with:

```bash
pip install -r requirements.txt -r requirements-dev.txt
ruff check src tests
mypy src
python -m compileall -q src tests
python -m unittest discover -s tests -v
```

## Interpreting metrics

- `new_candidate` means *unmatched against the baseline*, not *verified new
  product*. Absence from the baseline alone does not prove novelty.
- `relevance` separates **term-matched** records (a search term matched the
  record's name/categories/brand; this means the term matched, *not* that the
  record is confirmed to be a beverage) from **uncertain** ones (kept for
  review, not verified beverages) and **rejected** ones (excluded). Records
  imported before relevance labeling show as `unclassified`.
- `needs_review` is expected to be non-trivial: seasonal releases, vintages,
  reformulations, and package variants may be distinct products.
- **Candidate identity.** A candidate merges repeat sightings of the same
  source record (same barcode/product code, e.g. under two search terms);
  the summary counts these as repeated source records. Cross-*source*
  product merging is unsupported and undescribed: Open Brewery DB
  contributes producer records only, never beverage candidates, so nothing
  in this experiment demonstrates cross-source beverage deduplication.
  Different barcodes that may describe the same beverage (or package
  variants) are intentionally *not* auto-merged; those sit in the review
  queue as possible variants or data-entry duplicates.
- Evaluate Open Brewery DB by **producer coverage** (does it improve product
  matching?), not by beverage count.
- Cross-source agreement is useful evidence, not proof of correctness.

## Documentation (`docs/`)

How to resume and expand this work responsibly:

- [Product scope and taxonomy](docs/01-product-scope-and-taxonomy.md) -
  what the catalog should contain, explicit boundaries, open decisions.
- [Expansion runbook](docs/02-expansion-runbook.md) - safe repeatable
  discovery runs, sampling, error tracking, expansion gates.
- [Source and data governance](docs/03-source-and-data-governance.md) -
  access rules, terms, and licenses per source, with evidence links.
- [Alias and review procedure](docs/04-alias-and-review-procedure.md) -
  adding and maintaining brand-to-producer aliases; manual-review
  outcomes.
- [Promotion and provenance plan](docs/05-promotion-and-provenance-plan.md) -
  what moving reviewed records into BeerPassport would require.
- [Image readiness checklist](docs/06-image-readiness-checklist.md) -
  metadata an eventual image pilot must capture.
- [Image licensing assessment](docs/07-image-licensing-assessment.md) -
  rights analysis for Open Food Facts imagery.
- [Image sourcing plan](docs/08-image-sourcing-plan.md) - barcode-first
  automated image pipeline design (implemented in `src/images/`).
- [Old-catalog cleanup strategy](docs/09-old-catalog-cleanup-strategy.md) -
  v1 cleanup rules for the legacy catalog, report-first flow, and the
  spreadsheet write-back decision (implemented in `src/cleanup/`).

Prior evidence: [pilot report](pilot/PILOT_REPORT_2026-10-13.md),
[alias fix notes](pilot/BRAND_ALIAS_FIX_2026-10-13.md),
[session handoff](SESSION_HANDOFF_2026-10-13_PILOT.md).

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
