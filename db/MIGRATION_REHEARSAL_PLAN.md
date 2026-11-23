# Milestone 1 Migration Rehearsal Plan: User-Data Import and Validation

Status: PREPARED for CTO approval. Nothing in this plan authorizes a
database command. The end-to-end rehearsal steps (R2 onward) run only
after Frank approves them, and the production load (Milestone 1 step 5)
remains a separate, separately approved step.

## Purpose

Rehearse the step 5 user-data load end to end against the existing
PostgreSQL schema and catalog loader, using synthetic fixtures only, so
the production load is a repeat of a proven run rather than a first
attempt. The rehearsal exercises the one new behavior step 5 needs that
the recovery pipeline does not already have: scoping the import to the
294 matched profiles from the UID reconciliation.

## Verified inputs

- Recovery (step 3, verified 2026-11-22): isolated test restore passed;
  14 tables, exact row counts (10,016 total), CHECK TABLE clean, 13
  foreign-key checks with zero orphans.
- UID reconciliation (completed 2026-11-22, SHA-256 fingerprint
  comparison): 309 Firebase Auth accounts; 299 recovered MySQL users;
  294 matched; 15 Firebase-only; 5 MySQL-only. Accounting closes exactly.
- Catalog (step 2, verified): hub loader produces 14 categories, 147
  styles, 1,339 breweries, 5,894 beers with source IDs preserved as
  primary keys (max beer ID 6,055, max brewery ID 1,442).
- Existing migration pipeline (local workstream, proven on a synthetic
  890-row fixture): mysqldump parser, per-table transforms (friend pair
  normalization, mojibake repair, zero dates to NULL, NOT NULL timestamp
  fill), single-transaction load in foreign-key order, sequence resets
  to MAX(id), nine post-load orphan and ordering checks, and the
  accounting invariant source = loaded + rejected + deduped, asserted
  per table. 18 of 18 tests passed, including the end-to-end fixture
  run (857 loaded, 18 rejected, 15 deduped).

## Scope decisions (CTO, 2026-11-22)

- The load scope is the 294 matched profiles and their dependent data.
- The 5 MySQL-only profiles are not loaded. They stay in the verified
  backup (the checksummed user-tables dump) and can be revisited later
  without re-running the recovery.
- Firebase is never written to. The 15 Firebase-only accounts are left
  exactly as they are; the migration only reads the reconciliation
  result.
- Source IDs are preserved for every loaded row, as in the catalog load.
  No remapping table exists or is needed.

## The scope mechanism (this PR)

`db/src/user_scope.py` adds one stage between the pipeline's parser and
its transform stage:

    parsed = parse_dump(sql_text)
    scoped, accounting = apply_matched_scope(parsed, matched_uids)
    clean, rejects, stats = transform_all(scoped, ...)

Rules:

| Table | Rule |
|---|---|
| users | Kept iff its uid is in the matched set. |
| user_beers, user_badges, notifications | Excluded iff their user_id belongs to a known excluded user. Rows referencing a user_id absent from the users table are kept, so the transform stage's orphan checks still see and report them. |
| friends | Excluded iff either endpoint is a known excluded user; a pair loads only when both profiles migrate. Pair-order normalization and duplicate collapse remain the transform stage's job, unchanged. |
| collections, collection_beers | Unscoped. They are shared badge definitions, not per-user data, and user_badges references them. |
| api_keys | Not in the user-tables dump and never migrated (existing decision: old keys are compromised material; new keys are issued fresh). |

The accounting invariant extends by one category, asserted per table:

    source = loaded + rejected + deduped + excluded_unmatched

The scope stage also reports `matched_uids_without_profile`, which must
equal the Firebase-only count (15) in the production run; a mismatch
stops the load for review before anything is written.

The matched-UID allowlist is a plain local file (one UID per line)
produced by the reconciliation tooling on Frank's Mac. It is never
committed to git, emailed, or pasted into chat. How it reaches the box
for step 5 is an open decision (see below); the rehearsal uses synthetic
allowlists only.

## Catalog references

user_beers.beer_id and collection_beers.beer_id are validated against
the beer ID set of the catalog actually loaded in the target database
(the pipeline's existing valid_beer_ids mechanism). Because source IDs
are preserved end to end, a recovered reference either resolves to the
same beer it meant in MySQL or is rejected and reported as an orphan
reference. References are never remapped and catalog rows are never
invented to satisfy them.

## Validation plan

Pre-load gates (any failure stops the run):

- Dump SHA-256 verified against its checksum file before parsing
  (existing pipeline behavior).
- Catalog counts in the target database equal the frozen baseline
  (14 / 147 / 1,339 / 5,894) and the beer ID set is loaded before any
  user table is touched.
- Allowlist count equals the expected matched count (294 for
  production; the fixture's own count in rehearsal), and
  matched_uids_without_profile equals the expected Firebase-only count.

Post-load checks (existing pipeline, unchanged):

- Per-table database counts equal the manifest's loaded counts.
- All nine orphan and ordering checks return zero (user_beers,
  user_badges, notifications, friends endpoints; friend pair ordering;
  collection references; beer references).
- Sequence reset verified: MAX(id) per table equals the sequence state,
  so the next inserted row takes MAX(id) + 1.
- Spot checks: for a sample of matched users, per-user user_beers and
  user_badges counts in PostgreSQL equal their counts in the dump;
  every loaded users.uid is in the matched set; no loaded user belongs
  to the MySQL-only set.
- Rejects and exclusions are reported with table, source ID, and reason.
  Nothing is silently dropped.

## Rehearsal steps

- R1 (this PR, no database): the scope module and its synthetic unit
  tests. 10 new tests, all passing; the full db test suite (20 tests)
  passes. Evidence is in the PR description.
- R2 (needs Frank's approval; state-changing against the local
  disposable PostgreSQL only): wire the scope stage into the local
  pipeline behind a --matched-uids flag and re-run the existing 890-row
  fixture end to end with a synthetic allowlist, verifying the extended
  accounting and all post-load checks.
- R3 (same approval): a production-shape synthetic fixture (299 users,
  294 matched, dependent rows across every table, deliberate edge cases
  mirroring the existing fixture's) loaded into the disposable migration
  test database; full validation plan executed and reported.
- R4: rehearsal report in this hub (counts, checks, timing, any
  surprises), forming the step 5 runbook. Step 5 itself (box setup is
  step 4) still needs its own approval, on the box, with the real dump.

Rollback in rehearsal is trivial (the databases are disposable copies).
For step 5, the load runs in one transaction into empty user tables;
an abort is a truncate and re-run, and the checksummed dump in the
verified backup remains the source of truth throughout.

## Open decisions for Frank

1. Approve R2 and R3 (state-changing commands against the local
   disposable PostgreSQL instance only; no production system involved).
2. The step 5 allowlist route: how the matched-UID file produced on
   Frank's Mac reaches the Lightsail box (the recovery runbook's
   transfer constraints apply: never email, never git, never chat).
3. Whether the 5 MySQL-only profiles' dependent data needs any
   preservation beyond the verified backup before step 5 (current
   decision: the backup is sufficient).
