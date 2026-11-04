# Session Handoff: Milestone 1, step 2 (PostgreSQL schema and catalog import)

## Objective worked on

Milestone 1 step 2 of the approved deployment proposal: port the database schema from MySQL to PostgreSQL with the agreed audit fixes, and build the scripted catalog import (no manual SQL) that loads the cleaned baseline. Plus the decision records for D1, D2, and user-data continuity, which the repo convention reserved for this moment.

At Frank's direction during the session, the step was split by the nature of the work: the schema and its migration live in `beer-passport-server` (their real home), while the import tooling and the planning records stay in this hub. Frank also established the server repo's integration flow: a `release/2.0` branch now exists, and all relaunch step branches merge into it, never directly into master.

## Changes actually made

In `beer-passport-server` (branch `m1-step2-postgres-schema`, PR #39, base `release/2.0`):

- `prisma/schema.prisma`: full PostgreSQL port (14 models incl. the new beverage_images), model/field names unchanged. Fixes: F-2 upc String, discontinued column, F-7 beverage_images, F-5 cascades to Restrict, F-4 api_keys, F-11 users timestamps (with @default(now()) alongside @updatedAt so raw SQL loads work), F-9 magic defaults, F-13. Two MySQL naming collisions resolved for Postgres (unique constraint "name" x2 renamed; FK/index name reuse given "_idx" index suffixes).
- `prisma/migrations/`: reset to the single baseline `20261027000001_init` (Prisma-generated DDL, 6.19.3, plus the hand-added F-1 CHECK constraint on friends, user_1 < user_2), a postgresql `migration_lock.toml`, and a README recording the lineage. The 15 MySQL migrations were deleted in the PR; they remain in git history on master (9b19504c and earlier).

In this hub (branch `m1-step2-postgres-import`):

- `db/src/catalog_import.py` + `db/tests/` (10 tests): validated transform of the baseline CSVs into Postgres COPY files, an initial-load-only `load.psql` (guard refuses to run over user/enrichment data), sequence resets, and an import manifest with source SHA-256s. `db/README.md` documents the layout and points at the server repo for the schema and DDL.
- `decisions/001-hosting-lightsail.md`, `002-database-postgresql.md`, `003-user-data-continuity.md`; TECHNICAL_DECISIONS.md gains TD-9/TD-10/TD-11 and TD-2 is updated; CURRENT_STATE.md refreshed.

## Repositories, branches, and commits involved

- beer-passport-server: `release/2.0` created from master (9b19504c); step branch `m1-step2-postgres-schema`, PR #39 targeting release/2.0.
- beer-passport-project: branch `m1-step2-postgres-import`, PR opened this session.

## Tests and results

- `prisma validate` (6.19.3): schema valid. Note: the sandbox proxy resets Prisma's engine CDN downloads; engines were fetched manually from binaries.prisma.sh for the engines-version commit and supplied via PRISMA_SCHEMA_ENGINE_BINARY / PRISMA_QUERY_ENGINE_LIBRARY.
- db unit tests: 10/10 pass (`python -m unittest discover -s db/tests`).
- Import run on the real baseline: counts 14 / 147 / 1,339 / 5,894, matching the frozen v1 expectations; manifest stats: add_user nulled 1,339, ibu nulled 172, descript nulled 3,795, discontinued true 27.
- Live load proof on PostgreSQL 16.2 (throwaway local instance), using the exact DDL now in the server PR: applied cleanly; load committed with exact counts on two consecutive runs (idempotent while no user data exists); discontinued = 27; upc NOT NULL count = 0; MAX(id) beers 6,055 / breweries 1,442 with next insert taking 6,056; reversed friend insert rejected by friends_user_order_check; deleting a user-logged beer rejected by fk_user_beers_beer_id (Restrict); deleting a user cascaded their user_beers and friends; load.psql guard raised "initial load only" once user rows existed.
- The experiment suite (experiments/catalog-discovery) was re-run at the end of this session as a regression check: 101/101 OK. No experiment code changed in this step.

## Decisions made

Recorded this session (all Frank's, 2026-10-26/27): Lightsail hosting, PostgreSQL, user-data continuity (decisions/001-003, TD-9 to TD-11). Process decisions this session: step 2 split across the two repos by the nature of the work; beer-passport-server integrates through release/2.0.

## Outstanding issues and risks

- Deferred schema items for the Milestone 3 pass (documented in db/README.md): F-3, F-6, F-8, F-12.
- The CI workflow's path filter covers only experiments/catalog-discovery/**; db/ tests are not yet in CI scope. Extending the workflow file is a Frank-paste action (the Muse app lacks the Workflows permission).
- EFS data integrity remains unverified until step 3 by design.

## Next recommended action

Frank reviews and merges both step 2 PRs (server PR #39 into release/2.0; the hub PR into main). Then Milestone 1 step 3: the EFS recovery spike, Frank at the AWS console with a Jarvis-written guide, plus the Firebase Auth UID export for the ghost-user diff.
