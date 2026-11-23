# Catalog Selection Strategy: US-First, Evidence-Based

Status: PROPOSED, companion to decision
[005: Catalog selection is US-first, evidence-based](../../decisions/005-catalog-selection-us-first.md).
The counts in this document are a proposal baseline taken from the
2026-11-23 American-first reassessment dry run. Nothing in this
document imports anything; every import remains a separate dry-run
manifest and a separate CTO approval.

## Purpose and audience

BeerPassport is a beverage discovery catalog for adults 21 and over,
primarily young men and secondarily young women. The catalog succeeds
when a user can actually find and drink what it shows them, so
selection is governed by where a beverage is produced and where it is
sold, not by where a data source happened to harvest it. The
discovery expansion is dominated by a 2025 Dutch and European craft
import in Wikidata, which is a poor default order for a US audience.

Audience fit is judged only on market availability and product
relevance evidence: production country, sales-country data, federal
label approval, and retailer or distributor presence. No product is
excluded, demoted, or promoted through assumptions about gender.
Category and style relevance follow the approved scope in decision
004 (all canned beverages, not only beer).

## Inputs

- **Baseline (untouched):** 5,894 beers and 1,339 breweries, the
  frozen catalog. Nothing in this strategy changes it.
- **Batch 2 (separate path):** 702 measured records (190 Open Food
  Facts + 512 CraftCans) under decision 004, with 687 importable
  records, 170 importable verified images, and 15 records held for a
  missing brewery. Batch 2 follows its own already-approved path
  (`BATCH_2_DRY_RUN_MANIFEST.md` in this directory; record file
  `batch-702.json`, SHA-256
  `a2ad122a0ce50b6f445537a05615d8379fb4a870706b313f28e1bc59d2f84913`,
  held locally in the `catalog-expansion-poc` workstream). It is not
  part of the candidate pool below and is never double-counted: the
  11 expansion records that matched batch 2 were excluded from the
  candidates for exactly that reason.
- **Discovery expansion (this strategy's subject):** 22,219 unique
  new records (Wikidata 15,825 + Open Food Facts full pull 6,394),
  cross-deduped against each other and against batch 2 with the POC
  dedupe ladder into a candidate pool of 21,438. Source report and
  staged files are local, not in GitHub:
  `~/workspace/workstreams/catalog-expansion-2/reassessment/REASSESSMENT_MANIFEST.md`,
  `candidates-us.json` (SHA-256
  `3fac5162193fb4d79280570c1a992f08ae72e5220980cb8708269c906499f6ed`),
  and `candidates-review.json` (SHA-256
  `30d040590a4e8b6317d29efa1ab1d2caa473098bb55a45a2baba6c8711522870`).

## Selection principles, in priority order

1. **US-produced beverages first.** A record with evidence of United
   States production outranks everything else in the expansion.
2. **Imports with evidence of US market presence.** A foreign-produced
   record is selected when there is evidence it is sold or consumed
   in the United States.
3. **The approved broader canned-beverage scope.** Within the tiers
   above, all canned beverages are in scope per decision 004, not
   only beer. Scope never substitutes for the tier evidence: a canned
   beverage with no US evidence sits in the review bucket like any
   other record.
4. **Image readiness and metadata completeness order a tier; they do
   not filter it.** Verified images first, then gate-passed images,
   then brewery, style, and ABV completeness. A record with no image
   or a thin description is sequenced later in its tier, never
   silently excluded.

## Evidence standards

Every selected record keeps its provenance (source, source record
id, source URL, retrieved date, tier) and its full `origin_evidence`
list, with each signal named and its raw value recorded.

**US production evidence (any one suffices):**

- Country-of-origin data naming the United States. In the current
  pool this is the Wikidata `country` field, harvested as P495
  (country of origin) with a P17 fallback, recorded on each record
  as the signal `wikidata_country_p495_else_p17`.
- The producing brewery located in the United States.
- Open Food Facts `origins_tags` or `origins` naming the United
  States, or `manufacturing_places` naming the United States, a US
  state, or a USA suffix, recorded verbatim.
- For a record merged across sources, the alternate source's country
  counts as production evidence unless the primary source's origins
  explicitly contradict it; a contradiction sends the record to the
  review bucket with the conflict recorded.

**US market evidence (no US production evidence required):**

- Sales-country data listing the United States. In the current pool
  this is Open Food Facts `countries_tags` including
  `en:united-states` (signal `off_countries_tags_sales_country`).
- US federal label approval (TTB COLA). Not yet harvested; named
  below as a future enrichment signal, because a COLA approval is
  direct evidence a product is labeled for US sale.
- US retailer or distributor listings. Also a future signal, from
  the source discovery work.

**What does NOT count as evidence:**

- A barcode GS1 prefix. It records where the barcode was registered,
  not where the product is made or sold.
- Open Food Facts `emb_codes` as harvested: only 33 of 6,394 records
  carry one and all are EU-style packer codes, so no US signal can
  be read from them.
- The language of a product name, or a brewery name that sounds
  American.
- Assumed popularity, fame, or audience fit without availability
  evidence.

## Tier table (proposal baseline, from the reassessment)

| Tier | Definition | Records | Wikidata | Open Food Facts |
|---|---|---|---|---|
| 1 | US-produced | 6,607 | 6,585 | 22 |
| 2 | Clearly US-market | 210 | 0 | 210 |
| Review | Uncertain origin, ambiguous pairs, held match | 15,315 | see below | see below |

US-selected total (tiers 1 + 2): **6,817**.

The review bucket is 14,621 uncertain-origin records (Wikidata
8,500, Open Food Facts 6,121), plus 693 ambiguous cross-source pairs
held unmerged, plus 1 record that matched a held Open Food Facts
record. It is staged in `candidates-review.json`, each record with a
`review_reason`.

Image readiness inside the selected tiers (statuses inherited from
the source batches and preserved verbatim; unverified images were
never promoted, including across merges):

| Bucket | Verified | Gate-passed, unverified | Failed | None |
|---|---|---|---|---|
| Tier 1: US-produced (6,607) | 7 | 16 | 1 | 6,583 |
| Tier 2: US-market (210) | 64 | 122 | 6 | 18 |
| US total (6,817) | 71 | 138 | 7 | 6,601 |

Flagged merge stat from the reassessment: in 8 of the 76
cross-source merges, the Wikidata twin carried a verified image but
the Open Food Facts primary did not. The primary's lesser status was
kept in every case, and those 8 images count as verified nowhere in
these outputs.

Known limits on the baseline counts, from the reassessment: Open
Food Facts origin fields are sparse (`origins_tags` populated for
775 of 6,394 records, `manufacturing_places` for 355), so the Tier 1
Open Food Facts count of 22 is a floor, not a census. The Wikidata
country field merges P495 and P17 without separating them. The 693
ambiguous pairs are inflated by dense same-brewery name families and
are likely mostly distinct products, but they stay unmerged pending
review. US state-name matching in `manufacturing_places` is a text
signal recorded verbatim (a value such as "Georgia" is ambiguous
between the US state and the country).

## Sequencing proposal

1. **Batch 2 first**, on its existing approval path: 687 importable
   records and 170 verified images; the 15 held records join once
   their breweries resolve. Its manifest already records the
   prerequisite that the catalog loader must carry provenance fields
   before a real import.
2. **Tier 1 (US-produced, 6,607).** Order inside the tier: verified
   images first (7 records), then gate-passed images (16), then by
   metadata completeness (brewery, then style, then ABV present).
   Harvest-reported completeness for the Wikidata majority is
   brewery 95.0%, style 80.9%, ABV 90.6%, so most of the tier is
   import-shaped once a dry-run manifest confirms it.
3. **Tier 2 (US-market, 210).** The most image-ready slice of the
   pool (64 verified, 122 gate-passed): order verified images first,
   then gate-passed, then completeness.
4. **Review bucket (15,315) last, and only after review.** Two cheap
   evidence upgrades come first, both already identified in source
   discovery (`~/workspace/workstreams/catalog-expansion-2/SOURCE_DISCOVERY.md`):
   a TTB COLA registry sweep (free, CC0, and a label approval is
   direct US market evidence) and an Open Food Facts sales-country
   enrichment pass over the uncertain records. The 693 ambiguous
   pairs need human review before any merge. Records promoted out of
   the review bucket enter through a new dry-run manifest, never by
   editing these counts.

Each stage is its own dry-run manifest and its own approval. A stage
may be split further (for example Tier 1 by image readiness) without
changing this strategy, as long as the manifest accounts for every
record it draws from the pool.

## Governance

- The counts above are a proposal baseline. They change only
  through a new dry-run manifest that reconciles against them.
- Nothing imports without Frank's approval. Accepting this strategy
  (decision 005) approves the selection rule, not any import.
- The image quality gate from decision 004 binds every selection
  that carries an image: an image counts as ready only when it is
  verified to show the correct product at usable quality. Inherited
  image statuses are preserved as recorded and never promoted.
- Provenance is recorded for every record regardless of tier, and
  the hard lines from decision 004 are unchanged: no bypassing
  authentication, paywalls, or technical access controls.
