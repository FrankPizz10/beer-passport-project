# Technical Decisions

Only decisions actually made and supported by the source material or repository state. Recommendations that have not been approved are proposals; they live in [ROADMAP.md](ROADMAP.md), not here.

Status values: **accepted** (made and standing), **proposed** (working default awaiting validation), **superseded** (replaced).

## Accepted

### TD-1: Targeted relaunch, not a rewrite

- **Status:** accepted
- **Decision:** Relaunch the existing app with a product and operations redesign rather than a ground-up rewrite.
- **Context:** The original app's core architecture and basic functionality worked well (beverage lookup, friends, collections/badges, Firebase Auth, responsive app and API). The failures were product experience, cost, catalog operations, deployment coupling, and API compatibility.
- **Consequences:** All five repositories remain the codebase of record; work focuses on the audit findings and the feature plan, not replacement.
- **Source:** `BeerPassport_2_0_Product_and_Engineering_Plan.docx`, section 1 (Executive Summary) and section 10 (Initial Priorities).

### TD-2: Retain the proven stack

- **Status:** accepted
- **Decision:** Keep React Native + Expo (mobile), Node.js + Express + TypeScript (API), Firebase Authentication, and Prisma (data access) where practical.
- **Context:** These components worked in the original app; the audit explicitly recommends keeping Prisma.
- **Consequences:** Affects all five repositories. Hosting decided in TD-9, database provider in TD-10.
- **Source:** Plan section 6; audit executive summary.

### TD-3: Server-side authorization is the security boundary

- **Status:** accepted
- **Decision:** Client-side checks (e.g., the admin sign-in page's `admin` claim check) improve UX only; every administrative and user-scoped API route must enforce authorization on the server.
- **Context:** The audit found admin claim checks present on both client and server but recommended end-to-end verification that every admin route uses server-side authorization.
- **Consequences:** Affects `beer-passport-server` and `beer-passport-admin`. P0.4 covers the verification and fixes.
- **Source:** Audit section 3.2.

### TD-4: This hub is the central source of truth

- **Status:** accepted
- **Decision:** `beer-passport-project` consolidates the plan, audit, and verified repository state for all agents and developers; the Google Drive documents are preserved as archival sources and are not edited.
- **Context:** Planning material lived in Drive; code lives in five repos; agents need one consistent starting point.
- **Source:** Project hub creation, October 2026.

### TD-9: Hosting is a single Lightsail instance (closes D1)

- **Status:** accepted
- **Decision:** Production runs on one AWS Lightsail instance (Docker: Postgres + Express API), static IP, automatic snapshots, Route 53 for DNS, S3 + CloudFront for images. About $8/month. Full record: [decisions/001-hosting-lightsail.md](decisions/001-hosting-lightsail.md).
- **Context:** The old deployment died when AWS credits ran out under ECS/ELB/RDS-class costs. Serverless alternatives cost more at this scale and deploy slower; plain EC2 is the same shape with worse billing predictability.
- **Consequences:** Single box is a single point of failure, accepted at this scale. Upgrade path is the $10 Lightsail tier, then RDS only if ever needed. Jarvis administers the box over SSH as a dedicated user with key-only auth; state-changing commands need Frank's approval.
- **Source:** Frank's decision, 2026-10-26/27; "BeerPassport Relaunch: Deployment Proposal" (Drive, Jarvis/BeerPassport).

### TD-10: Database provider is PostgreSQL (closes D2)

- **Status:** accepted
- **Decision:** The relaunch database is PostgreSQL. The Prisma schema is ported from MySQL (`db/schema.prisma`) with audit fixes F-1, F-2, F-4, F-5, F-7, F-9, F-11, F-13 applied at port time. Full record: [decisions/002-database-postgresql.md](decisions/002-database-postgresql.md).
- **Context:** The server is Prisma-only (no raw SQL), and the catalog import is greenfield from CSVs, so the switch costs an evening now and would cost a live-data migration later. Postgres offers stronger search (tsvector/pg_trgm), JSON (jsonb), and geo (PostGIS) for the planned catalog work.
- **Consequences:** All data lands in Postgres from day one; no MySQL is ever deployed in the new stack. The MySQL data on EFS is recovered read-only and transformed, never run again as a server.
- **Source:** Frank's decision, 2026-10-27.

### TD-11: User data continuity, not a restart

- **Status:** accepted
- **Decision:** Existing users keep their accounts and data. Firebase Auth accounts and the EFS MySQL user tables (users, user_beers, user_badges, friends, collections) migrate to Postgres with all IDs preserved. The EFS volume and Firebase project are frozen (no deletion or modification) until the migrated data is verified on the box. Full record: [decisions/003-user-data-continuity.md](decisions/003-user-data-continuity.md).
- **Context:** Firebase verification (2026-10-27) found 309 real Auth accounts created 2023-09 to 2026-02, all email/password; the app gates on server reachability, so accounts map to server profiles. The only unrecoverable-if-lost assets are users' personal beer logs, badge progress, and the collection definitions, which exist only in the EFS database.
- **Consequences:** Catalog IDs are load-bearing and are preserved as primary keys in the import. Fallback trigger agreed in advance: if the EFS data proves unrecoverable after a clean InnoDB recovery attempt, or Firebase had held only test accounts, the plan switches to a catalog-only restart on evidence presented to Frank.
- **Source:** Frank's decision, 2026-10-27.

## Proposed (working defaults, validation needed)

### TD-5: Separate database lifecycle from API compute

- **Status:** proposed
- **Decision:** The database must be persistent and managed independently from API containers; API instances are stateless and disposable.
- **Context:** The current deployment runs MySQL alongside the backend container; scaling the API can create competing database instances.
- **Consequences:** Affects `beer-passport-server` deployment and D1/D2 (hosting and database provider).
- **Source:** Plan section 6; audit sections 1.3 and 7 (P0).

### TD-6: Versioned, backward-compatible API

- **Status:** proposed
- **Decision:** Use versioned API routes (e.g., `/api/v1`), prefer additive backward-compatible changes, use expand-and-contract database migrations, and keep API contract tests for supported mobile releases.
- **Context:** Backend releases have broken older installed mobile apps; mobile clients may remain installed for months.
- **Consequences:** Affects `beer-passport-server` and `beer-passport` release processes.
- **Source:** Plan section 7; audit sections 4 (deep links) and 6.2.

### TD-7: Image fallback hierarchy

- **Status:** proposed
- **Decision:** UI fallback order for beverage imagery: approved product image, then original category illustration, then polished text/initials treatment. Anything without a known, acceptable permission basis is not published.
- **Context:** Licensing and sourcing for product images was never resolved in the original app.
- **Consequences:** Affects `beer-passport` UI and the catalog import workflow; requires the image provenance metadata fields.
- **Source:** Plan section 5.

### TD-8: Catalog import as an explicit operation

- **Status:** proposed
- **Decision:** Catalog seeding and import become explicit scripts or admin jobs with validation, duplicate detection, and import reports; never a side effect of API startup.
- **Context:** The backend currently invokes `seedDatabase()` during startup.
- **Consequences:** Affects `beer-passport-server` and `beer-passport-admin`.
- **Source:** Audit section 1.4 (P1).

## Superseded

None.
