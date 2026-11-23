# 004: Catalog licensing tiers relaxed; all canned beverages in scope

- **Date:** 2026-11-23
- **Status:** accepted
- **Ledger reference:** D-015 in the Decision and Approval Ledger

## Context

The Catalog Expansion POC measured 702 unique new beverage records
against the 5,894-beer baseline: 190 from Open Food Facts (Tier A,
clear reuse) and 512 from the CraftCans GitHub dataset (Tier C,
unclear licensing), which the standing tier policy excluded from any
publishable set. Batch 1 (PR #15) was therefore defined as the 190
Tier A records only. This is a personal project, and the CTO judged
the Tier C exclusion to be costing more catalog than it protects.

## Options considered

- **Keep the exclusion:** publishable set stays 190; the 512 measured
  CraftCans records remain internal-only forever.
- **Relax the tiers for this project:** all 702 measured records are
  valid; expansion proceeds across more sources, including company
  and brewery websites, Instagram, Facebook, the TTB COLA registry,
  Wikidata, and full Open Food Facts pulls.

## Decision

Relax the tiers. The CraftCans 512 count as valid, so the publishable
batch is the full 702 measured records (batch 2 manifest:
`experiments/catalog-expansion/BATCH_2_DRY_RUN_MANIFEST.md`). All
canned beverages are in scope, not only beer. Source access prefers
free APIs used within their rules; scraping publicly accessible
pages is acceptable where no usable API exists.

## Rationale

The licensing tiers were a self-imposed policy for a personal-use
catalog, not a legal requirement the CTO wishes to keep. The measured
dedupe and provenance work already done on the 512 records should
not be discarded.

## Consequences and affected repositories

- Batch 1 (PR #15) remains accurate under the old policy; batch 2
  supersedes its definition.
- Hard lines are unchanged: never bypass authentication, paywalls,
  or technical access controls; provenance is recorded for every
  record regardless of tier.
- The CTO's image gate applies to every new source: an image counts
  as ready only when it actually displays the correct product and is
  good quality, verified before use.
- Importing any batch into a database remains a separate approval.
