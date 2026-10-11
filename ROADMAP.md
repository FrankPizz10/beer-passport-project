# Roadmap

Phased relaunch roadmap consolidating the improvement plan (`BeerPassport_2_0_Product_and_Engineering_Plan.docx`) and the initial code audit (`BeerPassport_Initial_Code_Audit_Problems_Found.docx`).

**Current stage:** planning and audit are complete. Implementation has not begun. Nothing below is approved for implementation except the audit and planning work already done; the P0 items are recommended before any data migration or production cutover, and the items flagged "decision required" need Frank's approval first.

## Work completed

- [x] Initial code audit of all five repositories (October 9, 2026) with prioritized findings (P0-P3).
- [x] Product and engineering relaunch plan (October 2026): goals, feature plan, architecture principles, phased roadmap.
- [x] This project hub, consolidating both documents with repository verification (October 2026).

## Phase 1: Audit and product design (from the plan)

- [ ] Review repository, schema, endpoints, current hosting, deployment process, third-party services. (Partially done: the audit reviewed selected entry points, routes, schema/configuration, auth/deep-link code, and admin UI code; a full review is still open.)
- [ ] Record actual recurring costs and identify each cost driver.
- [ ] Back up the existing database and audit legacy catalog provenance, quality, and reuse rights.
- [ ] Map current features and migration risks.
- [ ] Wireframe navigation, search, logging, passport, collections, badges, and friend activity.

Audit P0 items that gate data migration or production cutover (do these first, in this order):

- [ ] **P0.1** Back up current data; record table row counts.
- [ ] **P0.2** Eliminate `.env` from the Docker build; verify `.dockerignore` excludes secrets, local config, dependency folders, and build artifacts.
- [ ] **P0.3** Confirm database persistence independent of API containers; document backups, restore steps, connection limits, and rollback before migrating production data.
- [ ] **P0.4** Fix auth error statuses and server-side authorization: return 401 for missing/invalid authentication, 403 for forbidden; enforce privacy/friendship checks server-side; verify every admin route uses server-side authorization.
- [ ] **P0.5** Run a restore test.

Acceptance criteria (from the audit): backup exists with row counts recorded; Docker build contains no `.env` or secrets; database survives API container replacement; auth failures return 401/403 with a consistent error shape; a restore drill has been executed and documented.

## Phase 2: Infrastructure and catalog

- [ ] Choose hosting based on total cost and migration effort (compare lean managed hosting vs AWS-native; see open decision D1).
- [ ] Separate the database lifecycle from API compute.
- [ ] Set up migrations, backups, restore testing, and cost alerts.
- [ ] Build bulk import, validation, duplicate detection, edit/merge tools, and import reports for the catalog.
- [ ] Add image provenance metadata and a controlled approval workflow (fields: beverageId, sourceType, sourceUrl, storageKey, licenseType, attribution, licenseUrl, verifiedAt, status).
- [ ] Introduce API compatibility checks and automated deployment tests.

Audit P1 items that gate public relaunch:

- [ ] **P1.1** Fix Express error middleware order (after route registration); test sync errors and rejected async handlers; confirm errors reach Sentry.
- [ ] **P1.2** Move catalog seeding/import out of API startup into explicit scripts or admin jobs; make imports repeatable, validated, and reported.
- [ ] **P1.3** Align Prisma CLI and `@prisma/client` versions; pin Node/runtime and package-manager versions; commit the lockfile.
- [ ] **P1.4** Resolve the MySQL vs PostgreSQL decision (D2) and, if migrating, execute the migration checklist: backup, test database, row-count and relationship verification, integration tests, rollback plan.
- [ ] **P1.5** Fix Universal Links / app links end-to-end (serve the Apple association file as raw JSON, canonical URL per beverage, useful web fallback, no-app-installed path); verify Android App Links separately.
- [ ] **P1.6** Add API compatibility tests for supported mobile releases.

## Phase 3: Product relaunch

- [ ] Implement the design system and redesigned navigation.
- [ ] Improve search and beverage logging (server-side search, pagination, filters; minimize steps to log).
- [ ] Polish the personal passport, collections, badge progress, and completion moments.
- [ ] Improve friend feed, profiles, and privacy controls.
- [ ] Add licensed images where available and original fallback artwork everywhere else (fallback hierarchy: approved product image, then original category illustration, then polished text/initials treatment).

Audit P2 items for the relaunch build:

- [ ] **P2.1** Bulk catalog import/duplicate tools; paginated search.
- [ ] **P2.2** Barcode representation review (evaluate storing barcodes as strings).
- [ ] **P2.3** Friend-relationship integrity (define directional vs mutual; prevent reverse duplicates).
- [ ] **P2.4** Notification event semantics (decide which types deduplicate vs record separately).
- [ ] **P2.5** Profile privacy tests (private profiles, non-friends, friends, unauthenticated callers).
- [ ] **P2.6** Sentry sampling review (environment-specific sampling, budget-conscious default).

## Phase 4: Controlled relaunch

- [ ] Test migrations, login, search, logging, collections, friendships, and old-client compatibility.
- [ ] Release to a small test group before wider distribution.
- [ ] Track activation, week-one retention, engagement, errors, and infrastructure spend.
- [ ] Use actual user behavior to prioritize follow-up features.

Audit P3: additional product features and polish not needed to safely relaunch the core discovery/logging/collections/friends loop; schedule after the foundation is stable.

## Awaiting investigation

These are hypotheses or unknowns from the audit, not confirmed production incidents. Validate before treating them as facts:

- Express error middleware ordering (1.5) and its effect on Sentry capture.
- Catalog and history endpoints: whether large list endpoints return unbounded results (2.5).
- Admin claim checks end-to-end: non-admin users calling admin API routes directly (3.2).
- Backups, restore drills, and spend alerts: not evidenced in the code reviewed (6.3); verify in the hosting account.
- Sentry sampling cost/coverage: sampling rates set to 1.0 observed in config; actual cost and coverage need verification (6.1).
- Whether friendships can actually be stored twice (depends on application logic and existing data) (2.2).
- Barcode values currently stored and their sources before changing the field type (2.3).
- Whether the open Firestore rules observed in the cloud-functions repo are the deployed rules, and what the app stores in Firestore (new hub finding H1).

## New findings from hub verification (October 2026)

Found while verifying the repositories for this hub; not in the original audit. Treat as observed-in-code until verified against the deployed environment.

- [ ] **H1** `beerpassport-cloud-functions/firestore.rules` allows open read/write on `/users/{userId}` for any caller. Verify the deployed rules, determine what the app stores in Firestore, and restrict before any relaunch. Priority: P0-level security item, pending Frank's review.

## Decisions awaiting approval

- **D1** Hosting: lean managed hosting vs AWS-native/serverless. Compare total monthly cost, migration effort, reliability, backups, connections, storage, networking, likely growth.
- **D2** Database provider: stay on MySQL or migrate to PostgreSQL before relaunch. Migration is less disruptive now than later, but requires the full migration checklist and cost comparison.
- **D3** Catalog sources: hybrid curated-plus-external model. External sources (Open Food Facts, Open Brewery DB, manufacturer media kits) require license, attribution, API-limit, and cost review before import. See [research/image-licensing.md](research/image-licensing.md).
- **D4** Imagery: licensed product photos where possible with original category art as fallback. Each source needs a documented permission basis.
- **D5** API compatibility window: versioned routes (`/api/v1`), supported/minimum app-version policy, and when an update-required screen is justified.

## Dependencies

- P0.1 (backup) precedes P0.3 (database persistence work) and P1.4 (any provider migration).
- D1 (hosting) and D2 (database provider) precede Phase 2 infrastructure work.
- P1.1 (error middleware order) precedes meaningful Sentry verification (P2.6).
- P1.2 (seeding out of startup) precedes the Phase 2 catalog import tooling; both precede any bulk import.
- D3/D4 (catalog sources and imagery licensing) precede bulk catalog imports.
- P1.6 (compatibility tests) and the versioned API contract precede Phase 3 mobile work that changes request/response shapes.
- Phase 4 (controlled relaunch) requires all P0 and P1 items complete.

No estimates or deadlines are set; the plan explicitly avoids inventing them.
