# 002: Database provider is PostgreSQL

- **Date:** 2026-10-27
- **Status:** accepted
- **Closes:** decision D2 (database provider)

## Context

The server (`beer-passport-server`) is Prisma-only; the schema audit found no raw SQL. The original database is MySQL, dormant on EFS. The relaunch loads the catalog greenfield from CSVs, so no live data constrains the engine choice today.

## Options considered

- **Stay on MySQL:** zero porting effort; weaker full-text/fuzzy search, weaker JSON, thinner geo support; carries the schema's integer-UPC defect class forward.
- **Migrate to PostgreSQL now:** provider change plus a native-type pass while the import is greenfield; buys tsvector + pg_trgm search, jsonb, and PostGIS headroom for the discovery/enrichment roadmap.
- **Migrate later:** the same port performed against live production data, strictly harder and riskier.

## Decision

PostgreSQL. The ported schema lives in `beer-passport-server` (`prisma/schema.prisma`), landed by that repo's Milestone 1 step 2 PR targeting its `release/2.0` integration branch; the initial DDL is generated from it by Prisma (`prisma/migrations/20261027000001_init/`). This hub holds the import tooling that loads data into that schema.

Audit fixes applied at port time (full detail in the schema header): F-2 (upc becomes String), F-5 (destructive cascades on user_beers/user_badges become Restrict), F-4 (api_keys unique key, revocation fields), F-7 (beverage_images provenance model), F-11 (users timestamps), F-1 (friends canonical-order CHECK constraint in the migration SQL), plus the discontinued column from the catalog cleanup. Deferred to the Milestone 3 schema pass: F-3, F-6, F-8, F-12.

## Rationale

The migration is at its cheapest possible moment: the data moves as CSVs, there is no live traffic, and the codebase has no raw SQL to rewrite. Every month of delay converts an evening of work into a production data migration.

## Consequences and affected repositories

- MySQL is never deployed in the new stack; the EFS MySQL data directory is only ever mounted read-only for recovery and dumped.
- `beer-passport-server` received the provider switch and the ported schema in step 2 (into release/2.0); its Prisma version alignment remains Milestone 3 work. Server step branches merge into release/2.0, never directly into master (Frank, 2026-10-27).
- IDs from the source data are preserved as primary keys (required by decision 003).
