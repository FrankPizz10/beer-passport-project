# 005: Catalog selection is US-first, evidence-based

- **Date:** 2026-11-23
- **Status:** proposed (Frank accepts by merging)
- **Ledger reference:** D-016 in the Decision and Approval Ledger (proposed)

## Context

The discovery expansion harvested 22,219 unique new beverage records
against the 5,894-beer baseline. Cross-deduping the Wikidata and
Open Food Facts batches against each other and against batch 2
leaves a candidate pool of 21,438. The pool's composition is an
artifact of its sources: the Wikidata harvest is dominated by a 2025
Dutch and European craft import, and Open Food Facts origin data is
sparse. Importing the pool in harvest order would tilt the catalog
toward products a US user cannot buy, so the expansion needs a
selection rule before any of it is proposed for import. Decision 004
already settled scope (all canned beverages, not only beer); it did
not settle priority.

## Options considered

- **Import the pool in harvest order:** simplest, and it fills the
  catalog fastest, but the order reflects source availability, not
  the audience, and most of the pool has no evidence of US presence.
- **US-first tiered selection (this decision):** rank by production
  and market evidence; hold everything else for review.
- **US-produced only:** cleanest rule, but it discards imports with
  genuine US distribution (the 210 records with US sales-country
  evidence, the most image-ready slice of the pool) for no
  audience benefit.

## Decision

Adopt the selection strategy in
`experiments/catalog-expansion/SELECTION_STRATEGY.md`. In summary:

- Tier 1 is US-produced beverages (6,607 records in the current
  baseline), ranked on country-of-origin, brewery location, or
  manufacturer and origins evidence.
- Tier 2 is imports with evidence of US market presence (210
  records), ranked on sales-country data today, with TTB COLA label
  approval and US retailer or distributor listings as named future
  evidence signals.
- The broader canned-beverage scope from decision 004 is
  reaffirmed: it applies inside the tiers and never substitutes for
  tier evidence.
- Everything without sufficient evidence (14,621 uncertain-origin
  records, 693 ambiguous cross-source pairs, 1 held match; 15,315
  staged for review) is held for human review and origin research,
  not imported and not deleted.
- Audience fit is judged by market availability and product
  relevance evidence only. No product is excluded, demoted, or
  promoted through assumptions about gender.
- Image readiness and metadata completeness order records inside a
  tier; they never silently exclude a record.

## Rationale

The catalog is for US drinkers, so evidence that a beverage is made
in the US or sold in the US is the strongest available proxy for
whether it belongs in front of them. The evidence standards are
deliberately strict about what counts (a barcode GS1 prefix records
registration country, not production or sale, and is excluded) so
that tier membership stays auditable record by record through each
record's provenance and `origin_evidence`.

## Consequences and affected repositories

- The proposal baseline is set: Tier 1, 6,607; Tier 2, 210; review,
  15,315. These counts change only through a new dry-run manifest.
- Batch 2 (702 records, 687 importable) is unaffected and keeps its
  separate, already-approved path; it is sequenced first and never
  double-counted against the pool.
- Future expansion imports are proposed per tier as dry-run
  manifests under this strategy, each still requiring Frank's
  approval. Accepting this decision approves the selection rule,
  not any import.
- The image quality gate from decision 004 binds selections that
  carry images: verified product match at usable quality, with
  inherited image statuses preserved and never promoted (the
  reassessment kept the primary record's status in all 76
  cross-source merges, including 8 where the non-primary twin held
  the verified image).
- The named next evidence upgrades are a TTB COLA registry sweep
  and an Open Food Facts sales-country enrichment pass, both from
  the source discovery work, aimed at the review bucket.
- Hard lines from decision 004 are unchanged: no bypassing
  authentication, paywalls, or technical access controls, and
  provenance is recorded for every record.
