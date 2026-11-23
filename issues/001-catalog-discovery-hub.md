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
unique new), and their cross-deduped, US-classified reassessment (22,132
candidate records, plus 693 ambiguous pairs counted as relationships).
None of it is reviewable in the admin, none of it has a decision
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
- Staged results (local workstream catalog-expansion-2, nothing imported).
  Record-level accounting, verified 2026-11-23 against the staged files
  (this corrects the earlier headline figure of 21,438, which silently
  excluded every cross-match-flagged record):
  - Batch 2 = 702 records (687 importable, 170 verified images, 15 held
    for missing brewery), staged separately and not part of the totals
    below.
  - Discovery harvests after cross-dedupe = 22,132 candidate RECORDS in
    five mutually exclusive classes: US-produced 6,607; clearly
    US-market 210; uncertain origin 14,621; ambiguous-pair-flagged 693;
    held-match 1. The classes sum exactly: 6,607 + 210 + 14,621 + 693 +
    1 = 22,132. Closure against the harvests: 15,825 Wikidata + 6,394
    Open Food Facts = 22,219 unique-new, minus 87 cross-source merges
    (76 Wikidata into OFF primaries, 9 Wikidata into batch 2, 2 OFF into
    CraftCans) = 22,132.
  - RELATIONSHIPS are counted separately from records: 693 ambiguous
    pairs (each links one flagged record to a rival staged in batch 2
    or the sibling harvest), 1 held match link, and the 87 merge links
    (survivors carry the merged record as alternate-source provenance).
  - Every candidate carries provenance (source, source record id, source
    URL, retrieved date, tier), an origin bucket with its evidence,
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
- Risk: a decision (candidate selection or image approval) changes after
  a manifest is built from it. Mitigation: manifests are immutable and
  content-hashed (section 4), and the import step re-verifies every
  decision and payload hash before writing anything (section 4, import-
  time checks); any divergence aborts the import for re-approval.
- Risk: bundle files as a transport can drift from the database copy.
  Mitigation: bundles are immutable and content-addressed by SHA-256;
  the database records the bundle hash it ingested; re-ingest of the
  same hash is a no-op.
- Image review timing is settled by CTO directive (2026-11-23):
  candidate images are previewed and approved BEFORE manifest approval,
  bound to the exact image bytes by content hash (section 4). The
  earlier open question (review before the beverage exists) is resolved
  by that directive; the beverage_images queue remains the path for
  images attached to beverages already in the catalog.

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
transiently during ingest. Estimated size: the full 22,132-candidate
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
- discovery_candidate_pairs: id, batch_id, candidate_id_a (the flagged
  record), candidate_id_b (nullable: the rival when it is also staged
  in the hub), external_ref (the rival's source:source_record_id when
  it lives in another batch, e.g. a batch 2 record), comparison, score,
  status (pending / same / distinct), decided_by, decided_at. Seeded
  from the 693 ambiguous relationships plus the 1 held match link.
- discovery_image_decisions: id, candidate_id, image_ref (the direct
  image URL or private storage reference exactly as staged),
  image_sha256 (SHA-256 of the image bytes at decision time),
  image_content_type, image_width, image_height, decision (approved /
  rejected), decided_by, decided_by_uid, decided_at, note. One row per
  decision; the latest row for a candidate is its current image
  decision. This is what binds an approval to the exact image.
- discovery_decisions: id, candidate_id, action (select / hold /
  reject / unhold / mark_duplicate / mark_distinct), from_status,
  to_status, admin_user_id, admin_uid, reason, note, created_at. The
  audit trail, mirroring image_review_events.
- import_manifests: id (the manifest id, format
  mf-<batch-slug>-<yyyymmdd>-<seq>), batch_id, created_by, created_at,
  manifest (JSONB: the canonical content below), sha256 (SHA-256 of the
  canonical serialization), status (draft / approved / imported),
  approved_by, approved_at, approved_sha256 (the hash Frank approved;
  equal to sha256 at approval time and never updated afterward).
  Building a manifest is not an import; status moves to approved only
  by Frank's separate import approval of the exact (id, sha256) pair,
  and to imported only by the operator-run import step recording its
  result.

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
  INSERT and SELECT on discovery_image_decisions; INSERT and SELECT on
  import_manifests; UPDATE (status) on
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
    GET  /admin-api/v1/discovery/candidates/:id/image-preview
         fetch + hash the candidate image; returns the preview URL
         (or a presigned URL for private references), the content
         check, and the image_sha256 a decision will bind to
    POST /admin-api/v1/discovery/candidates/:id/image-decision
         {decision, image_sha256}                   (reviewer role;
         the API refuses when image_sha256 does not match the bytes it
         just hashed, so a decision can never bind to an image the
         reviewer did not see)
    POST /admin-api/v1/discovery/pairs/:id/decision {same | distinct}
    POST /admin-api/v1/discovery/batches/:id/manifest
         builds a draft import manifest from selected candidates
    GET  /admin-api/v1/discovery/manifests/:id      manifest + sha256

Progress shown per batch: candidates by review_status, pairs pending,
images by image_status, and percent reviewed. The Catalog Overview page
gains a discovery section with the same rollups (and its blank-render
bug is fixed in the staged viewer-enhancements PR).

Image flow (review BEFORE the manifest, bound to the exact image):

- The candidate detail view previews the candidate's image next to the
  beverage data and its provenance: hosted images render from their
  direct URL; private references render through the presigned pattern
  (900s cap, the reference itself never reaches the client as a usable
  key). The same load-gated mechanic as the image workflow applies:
  Approve stays disabled until the image has actually loaded in the
  reviewer's browser, and the recorded content-type check must say
  image/*. This is Frank's quality gate, applied pre-import: the
  correct product visible at usable quality.
- When the reviewer opens the preview, the API fetches the image once
  and records its SHA-256, content type, and dimensions. The approve or
  reject decision writes a discovery_image_decisions row binding the
  decision to that exact image (reference + content hash + provenance
  snapshot: source, source URL, license, attribution).
- A candidate can enter a manifest only with a current approved image
  decision (image attached) or as an explicitly no-image selection.
  The manifest embeds, per record, the image reference and the approved
  image_sha256.
- Carry-through at import: the import step re-fetches each attached
  image and verifies its SHA-256 against the manifest. On a match, it
  writes the beverage_images row directly as status = approved with
  verified_at set and the candidate decision id recorded in the row's
  provenance; the published catalog then serves it through the existing
  approved-image path (hosted URL directly, private via the presigned
  endpoint). The pre-import decision IS the approval; no second
  decision is taken. On a hash mismatch the content changed after
  approval, the decision no longer binds, and the import aborts for
  that manifest (see import-time checks); nothing is silently degraded
  to pending.
- Images for beverages already in the catalog keep using the
  beverage_images approval queue from the image workflow, unchanged.

Import manifests (immutable, hash-approved, verified at import):

- Serialization: a manifest is a single JSON document serialized
  canonically: UTF-8; object keys sorted lexicographically at every
  depth; arrays in recorded order; no insignificant whitespace; strings
  minimally escaped; integers bare; exactly one trailing LF. (For this
  data shape that matches RFC 8785 JCS output.) The manifest id is
  mf-<batch-slug>-<yyyymmdd>-<seq>; once built, a manifest never
  changes. Any change produces a new manifest with a new id.
- Content: header (manifest id, batch slug and bundle sha256,
  created_by, created_at, generator name and version, record counts);
  records[] in candidate_key order, each with candidate_key, the
  SHA-256 of the candidate's canonical payload, its selection decision
  id, and its image disposition (none, or approved with image_ref,
  image_sha256, and image decision id).
- Approval: Frank approves the exact (manifest_id, sha256) pair. The
  approval is recorded on the import_manifests row (approved_by,
  approved_at, approved_sha256). Approval of anything else (a batch, a
  count, an earlier manifest) authorizes nothing.
- Import-time checks (the operator-run import performs all five BEFORE
  writing anything; any failure aborts the whole import with a printed
  diff and imports nothing):
  1. The manifest file's recomputed SHA-256 equals approved_sha256.
  2. Every record's staged payload hash still equals the manifest's
     payload hash (no staged data changed since the build).
  3. Every record's current review_status is still selected and its
     selection decision is unchanged (no decision was reversed or
     superseded after approval).
  4. Every attached image's current decision is still approved, and
     the re-fetched image bytes hash to the manifest's image_sha256.
  5. The target catalog still matches the baseline counts recorded in
     the manifest header (an intervening import makes the approval
     stale).

### 5. Migration of existing staged results

Three ingests seed the hub, in this order. Staging totals are RECORDS;
relationships are staged as pair rows, never as records:

1. batch-2: 702 records. Review starts from its known state: 687
   selectable, 15 pre-held with hold_reason = missing_brewery, 170
   verified images. Its separate approval path is preserved: selecting
   from batch 2 still requires Frank's batch-2 import approval.
2. reassessment-us: 6,817 records (6,607 us_produced, 210 us_market).
3. reassessment-review: 15,315 records (14,621 uncertain origin, 693
   ambiguous-pair-flagged, 1 held-match), the flagged records pre-held
   with hold_reason = duplicate_unresolved (693) or the held-match
   reason (1); 694 pair rows seeded into discovery_candidate_pairs
   (the rivals live in batch 2 or the sibling batch, referenced by
   external_ref until both sides are staged).

Totals reconcile exactly: 702 + 6,817 + 15,315 = 22,834 staged records
across the three batches; the discovery-harvest batches hold 22,132
records and 694 pair relationships, closing against the harvest counts
in the Evidence section. Batch 2 records are not double-counted in the
reassessment totals (the reassessment already excludes them).

### 6. Phased implementation (one PR per phase, CTO merges each)

- Phase 0: this brief and decision 006. No code.
- Phase 1 (MVP): staging schema migration + bundle ingest script +
  read-only hub (batch list with counts and progress, searchable
  candidate list, candidate detail with provenance and hold reasons).
  Seeds the three batches above. Builds directly on the merged image
  workflow (auth, pagination, projections, states).
- Phase 2: review write path (reviewer role SQL, candidate decision
  endpoints, candidate image preview and hash-bound image decisions,
  pair decisions, side-by-side duplicate UI, audit views).
- Phase 3: manifest builder + export (canonical serialization and
  hashing per section 4; a manifest can only include candidates with a
  current selection and, when an image is attached, a current approved
  image decision), overview rollups, and the hand-off contract to the
  import pipeline including the five import-time checks.

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
- [ ] An image decision binds to the exact image: the recorded
      image_sha256 equals the bytes the reviewer previewed; a decision
      request naming a different hash is refused.
- [ ] A manifest cannot include a candidate whose attached image lacks
      a current approved image decision.
- [ ] At import, a changed image (hash mismatch), a changed decision,
      a changed payload, a tampered manifest, or a stale catalog
      baseline each abort the import with a printed diff and zero
      writes (one test case per check).
- [ ] An imported pre-approved image appears in the published catalog
      as an approved beverage_images row whose provenance names the
      candidate decision id, with no second decision taken.
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
  Manifest canonicalization test vectors (key ordering, escaping, the
  trailing LF) with a known-answer SHA-256; image-decision hash binding
  (mismatched hash refused); import-time check fixtures, one per abort
  condition.
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
