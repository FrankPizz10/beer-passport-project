# Issue 001: Catalog discovery hub in the admin

Status: open (architecture proposed; awaiting CTO approval)
Date: 2026-11-23
Companion decision: decisions/006-discovery-hub-architecture.md (PROPOSED)

## Objective and problem statement

Turn the admin from a read-only catalog viewer into the review hub for
catalog discovery. Discovery work (harvests, dedupe, origin classification)
already happens off-server and has produced large staged result sets that
today live only as files in a local workstream: batch 2 (702 records), the
Wikidata harvest (15,825 unique new), the Open Food Facts full pull (6,394
unique new), and their cross-deduped, US-classified reassessment (pool
21,438). None of it is reviewable in the admin, none of it has a decision
trail, and none of it can become an import without ad hoc file handling.

The hub provides one flow with three separate approval gates:

    discovery batch -> candidate review -> image review -> import-ready manifest

Candidates stay staged until Frank approves an import. Candidate approval,
image approval, and production-import approval are three distinct
decisions by three distinct mechanisms; no approval implies another.

## Evidence and current behavior

Verified 2026-11-23:

- Production catalog: 5,894 beers, 1,339 breweries, 294 users.
  beverage_images has ZERO rows; the admin image page lists metadata only.
- The admin API (beer-passport-admin) is GET-only; its database role
  beerpassport_admin_viewer is SELECT-only. Admin identity is a Firebase
  custom claim plus a users row; there is no admins table.
- The image approval workflow (admin PR in preparation, branch
  image/approval-workflow) adds the first scoped write path: a separate
  beerpassport_admin_approver role that can update only the decision
  columns of beverage_images and insert into an image_review_events audit
  table, behind POST approve/reject endpoints. It also adds the candidate
  loader pattern (operator identity, content-type verification, dedupe on
  beverage_id + storage_key).
- Staged results (local workstream catalog-expansion-2, nothing imported):
  batch 2 = 702 records (687 importable, 170 verified images, 15 held for
  missing brewery). Reassessment pool after cross-dedupe = 21,438:
  US-produced 6,607, clearly US-market 210, uncertain 14,621, plus 693
  ambiguous cross-source pairs and 1 held match (review file 15,315).
  Every candidate carries provenance (source, source record id, source
  URL, retrieved date, tier), an origin bucket with its evidence string,
  a cross-source match status, and an image status that was preserved,
  never promoted (verified / gate-passed-unverified / failed / none).
- Decision 004: all canned beverages are in scope. Decision 005
  (proposed, PR #21): US-first selection tiers and evidence standards.
- The production host is a 1 GB Lightsail instance. Discovery jobs must
  never run on it.

## Scope and non-goals

In scope:

- A staging data model inside the existing Postgres database, fully
  separate from the production catalog tables (beers, breweries,
  beverage_images), so staged work can never leak into the catalog.
- An ingest path that moves staged results from off-server discovery jobs
  into the staging tables with hash verification and idempotency.
- Admin UI and API for: batch list with progress and counts; searchable,
  filterable candidate lists; candidate review (select / hold / reject)
  with mandatory hold reasons; side-by-side duplicate review for
  ambiguous pairs; image status carried per candidate and handed to the
  image approval workflow at import time.
- A manifest builder that exports an import-ready manifest (JSON) from
  selected candidates; the manifest is the input to the existing gated
  import process.
- Audit: every review decision records who, when, from-state, to-state,
  and the reason.

Non-goals:

- No discovery job (harvest, scrape, dedupe, classification) runs on the
  Lightsail instance or inside the admin server.
- No production import in any phase of this issue. Import stays the
  separate, separately approved pipeline step.
- No change to the viewer role's read-only guarantee and no write access
  to beers, breweries, or users from the admin API.
- No mobile app changes.

## Affected repositories

- beer-passport-admin: staging schema migrations, ingest script, review
  endpoints, hub UI (batches, candidates, duplicates, manifest export).
- beer-passport-project (hub): this brief, decision 006, batch bundle
  format specification, sequencing with decisions 004 and 005.
- beer-passport-server: canonical Prisma schema mirror of the staging
  tables before any migration is applied to production (the admin schema
  copy is downstream; the drift check must stay green).

## Dependencies and risks

- Depends on the image approval workflow PR (the write-path pattern,
  approver role, and audit-table shape are reused, not reinvented).
- Depends on decision 005 for the selection policy the hub implements
  (US-first tiers, evidence standards, no gender-assumption exclusions).
- Risk: staging tables growing stale against the catalog as imports land.
  Mitigation: candidates carry the catalog match state from dedupe, and
  ingest re-checks barcode and normalized (name, brewery) against the
  live catalog, downgrading collisions to the duplicate queue.
- Risk: bundle files as a transport can drift from the database copy.
  Mitigation: bundles are immutable and content-addressed by SHA-256;
  the database records the bundle hash it ingested; re-ingest of the
  same hash is a no-op.
- Unknown: the image review of candidate images before their beverage
  exists. Resolution proposed below: image review happens in two stages
  (candidate-level status carried from the harvest gate; the binding
  approval happens in the beverage_images queue after import, reusing
  the image workflow unchanged).

## Proposed approach

### 1. Batch bundle format (transport)

A discovery job, wherever it runs (agent VM, Frank's Mac, CI), produces
one immutable bundle per batch:

- manifest.json: batch slug, source list with retrieval dates and
  license/attribution notes, record counts by stage (harvested, staged,
  matched, duplicate, ambiguous, unique-new), generator name and
  version, created_at, and the SHA-256 of candidates.jsonl.
- candidates.jsonl: one candidate per line in the reassessment record
  shape: candidate_key (source + source_record_id), name, brewery_name,
  style, category_hint, abv, description, barcode, source_url,
  provenance (source, source_record_id, retrieved_at, tier),
  origin_bucket (us_produced / us_market / uncertain), origin_evidence
  (free-text evidence string), cross_match (matched / ambiguous /
  no_match, with matched catalog beer id or the rival candidate_key),
  image (direct image URL or storage key reference, license,
  attribution) and image_status (verified / gate_passed_unverified /
  failed / none).

Bundles are stored in a private, versioned S3 bucket under
discovery-bundles/<batch-slug>/ and never on the Lightsail disk except
transiently during ingest. Estimated size: the full 21,438-candidate
pool is on the order of 15 MB of JSON; storage cost is effectively $0
(under $0.01 per month at S3 standard rates). No new compute.

### 2. Staging data model (new tables, additive migration)

- discovery_batches: id, slug (unique), title, source_summary,
  manifest (JSONB, the bundle manifest verbatim), bundle_sha256,
  candidates_sha256, status (staged / in_review / ready / imported /
  archived), ingested_by, ingested_at, counts (JSONB, per-status counts
  refreshed by the review endpoints).
- discovery_candidates: id, batch_id (FK), candidate_key (unique per
  batch), payload (JSONB, the candidate record verbatim, provenance
  included), name, brewery_name (denormalized for search), origin_bucket,
  image_status, review_status (staged / selected / held / rejected /
  superseded), hold_reason (required when held or rejected; controlled
  vocabulary below plus free-text note), matched_beer_id (nullable FK to
  beers), duplicate_of_candidate_id (nullable self-FK), created_at,
  updated_at.
- discovery_candidate_pairs: id, batch_id, candidate_id_a,
  candidate_id_b, score, status (pending / same / distinct), decided_by,
  decided_at. Seeded from cross_match = ambiguous (693 pairs today).
- discovery_decisions: id, candidate_id, action (select / hold /
  reject / unhold / mark_duplicate / mark_distinct), from_status,
  to_status, admin_user_id, admin_uid, reason, note, created_at. The
  audit trail, mirroring image_review_events.
- import_manifests: id, batch_id, created_by, created_at, manifest
  (JSONB: the selected candidate keys, their payloads, and the image
  dispositions), sha256, status (draft / approved / imported). Building
  a manifest is not an import; status moves to approved only by
  Frank's separate import approval, and to imported only by the
  operator-run import step recording its result.

Hold-reason vocabulary (extensible, stored as text): missing_brewery,
origin_uncertain, market_fit_uncertain, duplicate_unresolved,
image_unverified, metadata_incomplete, out_of_scope, other (note
required).

### 3. Permissions (narrowly scoped, mirroring the image workflow)

- beerpassport_admin_viewer (existing, unchanged): gains SELECT on the
  five discovery tables only. It still cannot write anything.
- beerpassport_admin_approver (from the image workflow): unchanged;
  image decisions stay on beverage_images.
- beerpassport_discovery_reviewer (new role, same restricted
  attributes, connection limit 5): SELECT (id, batch_id, review_status,
  hold_reason) on discovery_candidates; UPDATE (review_status,
  hold_reason, duplicate_of_candidate_id, updated_at) on
  discovery_candidates; UPDATE (status, decided_by, decided_at) on
  discovery_candidate_pairs; INSERT and SELECT on discovery_decisions;
  INSERT and SELECT on import_manifests; UPDATE (status) on
  import_manifests limited to the draft-to-approved transition being
  performed only by Frank's account is enforced in the API layer by
  checking the caller's users row against an allowlist env var, because
  Postgres cannot see Firebase identity. No INSERT or DELETE on
  candidates or batches, no access to catalog tables beyond the
  viewer's.
- Ingest identity: the operator/migration identity only (the same
  pattern as the candidate loader). The API never ingests.
- The API uses a third connection string, DATABASE_URL_DISCOVERY_WRITE,
  for the review endpoints; unset means review decisions are disabled
  (503) while browsing keeps working, exactly like the image workflow.

### 4. Data flows

Ingest (operator-run, off the API):

    discovery job (anywhere) -> bundle files -> S3 (private, versioned)
      -> ingest script run by the operator (Mac or agent VM) over a
         direct Postgres connection to the box (SSH tunnel or the
         Docker network on the box): verify bundle SHA-256 against the
         manifest, verify candidates SHA-256, parse JSONL, re-run the
         live-catalog collision check (barcode, normalized name +
         brewery), insert batch + candidates + ambiguous pairs in one
         transaction, print counts. Re-ingesting the same bundle hash
         is a no-op. The box never fetches or computes discovery data.

Review (admin UI + API):

    GET  /admin-api/v1/discovery/batches            (viewer role)
    GET  /admin-api/v1/discovery/batches/:id        counts + progress
    GET  /admin-api/v1/discovery/candidates         search + filters:
         q (name/brewery), batch, origin_bucket, image_status,
         review_status, hold_reason; paginated
    GET  /admin-api/v1/discovery/candidates/:id     full payload +
         provenance + decision history
    GET  /admin-api/v1/discovery/pairs              pending ambiguous
         pairs, side by side (both payloads, scores, shared fields)
    POST /admin-api/v1/discovery/candidates/:id/decision
         {action, reason?, note?}                   (reviewer role)
    POST /admin-api/v1/discovery/pairs/:id/decision {same | distinct}
    POST /admin-api/v1/discovery/batches/:id/manifest
         builds a draft import manifest from selected candidates
    GET  /admin-api/v1/discovery/manifests/:id      manifest + sha256

Progress shown per batch: candidates by review_status, pairs pending,
images by image_status, and percent reviewed. The Catalog Overview page
gains a discovery section with the same rollups (and its blank-render
bug is fixed in the staged viewer-enhancements PR).

Image flow (two stages, gate preserved):

- Candidate stage: image_status travels with the candidate. Only
  image_status = verified candidates can be selected into a manifest
  with their image attached; gate_passed_unverified images are flagged
  in the manifest as requiring the binding review after import.
- Post-import stage: the import step inserts the beverage and, for each
  attached image, a pending beverage_images row via the existing
  candidate loader rules (content-type check recorded). The image
  approval workflow then makes the binding approve/reject decision with
  the full quality gate (the correct product visible at usable quality,
  in the reviewer's browser, before approval). Nothing about the image
  workflow changes.

Import (unchanged gate): Frank approves a specific manifest (id +
SHA-256) separately. An operator-run import (the catalog loader with
provenance support, tracked outside this issue) executes it, assigns
new beer ids, writes provenance, and records the manifest as imported
with the id mapping. The admin API never imports.

### 5. Migration of existing staged results

Three ingests seed the hub, in this order:

1. batch-2: the 702-record POC batch (batch-702.json) wrapped in the
   bundle format. Review starts from its known state: 687 selectable,
   15 pre-held with hold_reason = missing_brewery, 170 verified images.
   Its separate approval path is preserved: selecting from batch 2
   still requires Frank's batch-2 import approval.
2. reassessment-us: candidates-us.json (6,817) as one batch
   (origin_bucket pre-filled: 6,607 us_produced, 210 us_market).
3. reassessment-review: candidates-review.json (15,315) as one batch,
   all pre-held: origin_uncertain or market_fit_uncertain per record,
   with the 693 ambiguous pairs seeded into
   discovery_candidate_pairs.

Counts reconcile to the reassessment manifest exactly (pool 21,438
plus batch 2's 702 staged separately, no double counting: the
reassessment already excludes batch 2 records).

### 6. Phased implementation (one PR per phase, CTO merges each)

- Phase 0: this brief and decision 006. No code.
- Phase 1 (MVP): staging schema migration + bundle ingest script +
  read-only hub (batch list with counts and progress, searchable
  candidate list, candidate detail with provenance and hold reasons).
  Seeds the three batches above. Builds directly on the merged image
  workflow (auth, pagination, projections, states).
- Phase 2: review write path (reviewer role SQL, decision endpoints,
  pair decisions, side-by-side duplicate UI, audit views).
- Phase 3: manifest builder + export, overview rollups, and the
  hand-off contract to the import pipeline (manifest schema documented
  for the loader work).

Each phase ships with its own deployment notes and rollback: all
schema is additive and confined to discovery tables; rollback is
revert the deploy, unset DATABASE_URL_DISCOVERY_WRITE (Phase 2+), and
optionally drop the discovery tables, which cannot affect the catalog.

### 7. Costs

- S3 bundle storage: under $0.01 per month at current scale.
- Postgres storage: roughly 37,000 candidate rows with JSONB payloads,
  tens of MB on the existing instance; no tier change.
- No new services, no new secrets beyond one additional database
  password (reviewer role) and the existing S3 writer pattern if
  bundles are uploaded by jobs rather than the operator.
- Total incremental cost: $0 per month within rounding.

### 8. Deployment sequence (per phase, production)

1. Mirror the staging tables into beer-passport-server's canonical
   Prisma schema (separate PR there) so the drift check stays green.
2. Apply the additive migration to production Postgres (operator-run,
   pre-load snapshot first, per standing practice).
3. Apply the role SQL for the phase (viewer grant delta; reviewer role
   in Phase 2) as superuser; run the verify script as the role.
4. Deploy the API with the new env vars; deploy the client.
5. Smoke test from Frank's network: batches list, candidate search,
   one decision (Phase 2+), manifest build (Phase 3).
Rollback per phase as in section 6.

## Acceptance criteria

- [ ] A bundle produced off-server ingests with hash verification;
      re-ingest is a no-op; counts printed match the bundle manifest.
- [ ] The three seed batches appear in the admin with counts reconciled
      to the reassessment manifest and the batch 2 manifest.
- [ ] Candidate search and filters return correct subsets (q, batch,
      origin bucket, image status, review status, hold reason).
- [ ] A held candidate cannot be selected; a rejection or hold without
      a reason is refused by the API.
- [ ] An ambiguous pair shows both candidates side by side; a decision
      records who and when; marking one as duplicate supersedes it.
- [ ] Every decision writes a discovery_decisions row in the same
      transaction as the status change.
- [ ] The viewer role still cannot write any table; the reviewer role
      cannot write outside its column grants (verify scripts prove it).
- [ ] A draft manifest contains exactly the batch's selected
      candidates, carries image dispositions, and has a SHA-256 the
      operator can verify offline.
- [ ] No endpoint returns a bare storage key; private image references
      stay references until the post-import presigned flow.
- [ ] The Lightsail instance runs no discovery job at any point
      (verified by the deployment notes: ingest runs from the
      operator's machine).

## Test plan

- Server unit tests: ingest validation (hash mismatch refuses, schema
  errors counted, collision downgrade), filter construction, decision
  guards (held cannot select, reason required, 409 on stale state),
  audit-in-transaction, projections never emitting storage keys.
- Role verification scripts run against a disposable database copy, in
  the pattern of verify-readonly-role.sql (13 checks) and the approval
  role's script.
- Client tests: batch progress rendering, candidate filters, pair
  side-by-side rendering, decision flows removing rows from queues.
- Live integration suite against a disposable database with the three
  seed batches ingested at reduced size (fixture bundles), asserting
  the reconciled counts.
- Each phase PR carries the standard test report (what ran, where,
  result) per hub convention.

## Documentation updates

- decisions/006-discovery-hub-architecture.md: the architecture
  decisions in this brief, PROPOSED until Frank merges.
- ROADMAP.md: add the discovery hub as the M2 catalog workstream with
  phases 1 to 3.
- CURRENT_STATE.md: note the hub brief and, after Phase 1, the staging
  tables and seed batch counts.
- experiments/catalog-expansion/SELECTION_STRATEGY.md (PR #21): the hub
  is the implementation vehicle for that strategy; no content change
  needed.
- Admin repo docs/DEPLOYMENT_RUNBOOK.md: per-phase sections added by
  each implementation PR (roles, env vars, ingest runbook, rollback).
