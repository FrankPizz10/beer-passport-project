# Source and Data Governance Guide

Evidence for each source's access rules, terms, and licenses, checked
2026-10-13 unless noted. robots.txt, API documentation, terms of
service, and dataset licenses are separate signals; one does not
override the others. Nothing here is legal approval. Do not contact
sources on the project's behalf.

## Open Food Facts (in use: packaged products)

- **What**: crowd-sourced packaged-product database (Source C).
- **API docs** (primary): https://openfoodfacts.github.io/openfoodfacts-server/api/
  - Search: 10 req/min/IP (`/api/v*/search` or `/cgi/search.pl`); product
    reads 15 req/min/IP; custom User-Agent required; test on staging;
    bulk CSV/JSONL downloads for more than a few hundred products.
  - License tutorial (primary): https://openfoodfacts.github.io/openfoodfacts-server/api/tutorials/license-be-on-the-legal-side/
- **robots.txt** (primary, checked 2026-10-12, rechecked 2026-10-13 via
  project notes): disallows `/api`, `/cgi`, `/facets` for `User-agent: *`.
  Addressed to general crawlers; the API docs describe programmatic
  access separately. The experiment's position (documented in the main
  README): call `/cgi/search.pl` as the API docs describe. Unresolved
  tension; not production clearance.
- **License**: database under ODbL; contents under DbCL; product images
  under CC BY-SA (label artwork may carry third-party copyright).
  Attribution and share-alike obligations apply to public reuse.
  Terms: https://world.openfoodfacts.org/terms-of-use ;
  contact for reuse questions: reuse@openfoodfacts.org.
- **Current experiment posture**: identified User-Agent, 6s delay,
  small evaluation volume, production search endpoint. Open owner
  questions: file the API usage form, add contact email to User-Agent,
  move to staging, and get a licensing review before any production use.

## Open Brewery DB (in use: producer directory)

- **What**: open brewery/cidery/brewpub directory (Source B). Producers
  only; never counted as beverage discoveries.
- **API docs** (primary): https://www.openbrewerydb.org/documentation
- **robots.txt** (primary, checked 2026-10-12): allows `/` for general
  crawlers.
- **Reuse guidance** (primary, FAQ): free and open-source dataset, free
  API with no authentication, any project may use the dataset **with
  credit to Open Brewery DB**; community-supported, no SLAs, recommended
  for personal projects. What "credit" concretely requires in production
  is an open question.
- **Access note**: the API 403s from the build environment and the
  owner's machine (cause unconfirmed). The experiment therefore evaluates
  producers via a pinned snapshot of the official dataset repository
  (`../data/dataset/SNAPSHOT.md`, retrieved 2026-10-12). The live-API
  adapter is retained (`--brewery-source api`).

## Untappd (researched 2026-10-13, not in use)

- **What**: largest beer check-in database; strong beer coverage,
  weak RTD/spirits coverage.
- **API docs** (primary): https://untappd.com/api/docs
  - Public API at `api.untappd.com/v4`; requires Client ID + Client
    Secret; non-standard User-Agent required.
  - Rate limit: 100 calls/hour per key (default).
  - Venue beer lists are NOT in the public API (Untappd for Business
    only).
- **Assessment** (secondary-source synthesis, needs owner verification):
  useful for beer identity cross-checks, but key-gated, rate-limited,
  and not a packaged-RTD catalog. No terms review done; do not use
  without reading the current API terms and getting owner approval.

## TheCocktailDB (researched 2026-10-13, not in use)

- **What**: free cocktail *recipe* API (https://www.thecocktaildb.com/).
- **Assessment**: recipes, not packaged products. Not a source of
  can/bottle SKUs. Listed only to avoid confusion: it does not cover
  the catalog scope.

## UPCitemdb / barcode lookup vendors (researched 2026-10-13, not in use)

- **What**: commercial barcode-to-product lookup (upcitemdb.com and
  similar). Free tier ~100 lookups/day; paid tiers from ~$25/mo
  (figures from secondary comparisons, 2026; verify before budgeting).
- **Assessment**: could enrich barcode-identified candidates, but it is
  a paid, US-retail-skewed vendor, not an open dataset. No terms review
  done. Owner decision required before any use.

## What remains unresolved

- OFF robots.txt vs API-docs tension for production use.
- ODbL/DbCL share-alike implications of displaying OFF-derived data.
- What "credit to Open Brewery DB" requires in production.
- Whether any key-gated source (Untappd) is worth its terms and limits.
- No spirits/RTD-specific open database found; coverage there rests on
  OFF plus manual curation for now.
