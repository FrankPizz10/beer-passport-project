# Decision 006: Catalog discovery hub architecture

Date: 2026-11-23
Status: PROPOSED (Frank accepts by merging; implementation brief in
issues/001-catalog-discovery-hub.md)
Ledger reference: D-017 (proposed)

## Context

Discovery harvests (batch 2, Wikidata, Open Food Facts) and their
cross-deduped, US-classified reassessment (pool 21,438) exist only as
files in a local workstream. They are not reviewable in the admin, carry
no decision trail, and cannot become imports without ad hoc handling.
The admin is read-only today; the image approval workflow introduces
the first scoped write path. The production host is a 1 GB Lightsail
instance that must never run discovery jobs.

## Decision (proposed)

Build the catalog discovery hub in the admin, per
issues/001-catalog-discovery-hub.md:

1. Staging lives in new discovery_* tables in the existing Postgres
   database, fully separate from the production catalog tables.
   Candidates stay staged until Frank approves an import.
2. The flow is discovery batch -> candidate review -> image review ->
   import-ready manifest, with three separate approval gates:
   candidate selection, image approval, and Frank's production-import
   approval of a specific manifest (id + SHA-256). No gate implies
   another.
3. Discovery jobs run off-server. Their results travel as immutable,
   SHA-256-checksummed batch bundles (manifest.json + candidates.jsonl)
   through a private S3 bucket and are loaded by an operator-run ingest
   script. The admin API never ingests and the Lightsail instance never
   runs discovery work.
4. Review decisions use a dedicated beerpassport_discovery_reviewer
   role scoped to the decision columns of the staging tables plus
   INSERT on the discovery_decisions audit table, mirroring the image
   workflow's approver pattern. The viewer role stays read-only and
   gains only SELECT on the discovery tables. Every decision records
   who, when, from-state, to-state, and reason in the same transaction.
5. Selection policy is decision 005 (US-first tiers, evidence
   standards, no gender-assumption exclusions); scope is decision 004
   (all canned beverages). Uncertain market relevance is a hold state
   with a recorded reason, never a silent exclusion.
6. Image review is two-stage: candidate image status (from the harvest
   quality gate) travels with the candidate; the binding approval
   happens after import in the existing beverage_images workflow,
   unchanged, with the full quality gate.

## Consequences

- The staged batches become reviewable with progress counts, search,
  side-by-side duplicate review, and an audit trail, at $0 incremental
  monthly cost (S3 bundle storage under $0.01, staging rows are tens of
  MB on the existing instance).
- Import remains a separate operator-run, separately approved step;
  the hub can prepare manifests but can never write the catalog.
- The canonical Prisma schema in beer-passport-server must mirror the
  staging tables before any migration is applied to production.
- Phasing: Phase 1 read-only hub + ingest; Phase 2 review write path;
  Phase 3 manifest builder. Each phase is its own PR and deployment.
