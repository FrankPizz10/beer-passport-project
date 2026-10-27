# Current State

Operational snapshot. Keep this file short and update it after every significant working session.

## Phase

Implementation has begun. Milestone 1 (database available on the Lightsail box) is in progress, executed one step per pull request under the approved deployment proposal (Google Drive, Jarvis/BeerPassport: "BeerPassport Relaunch: Deployment Proposal").

## Work completed so far

- Initial code audit of all five repositories, October 9, 2026, with findings prioritized P0-P3. Source: `BeerPassport_Initial_Code_Audit_Problems_Found.docx` (Google Drive, `Jarvis/BeerPassport`).
- Product and engineering relaunch plan, October 2026. Source: `BeerPassport_2_0_Product_and_Engineering_Plan.docx` (Google Drive, `Jarvis/BeerPassport`).
- This project hub, October 2026: both documents consolidated and reconciled against the current GitHub state.
- Catalog discovery experiment and old-catalog cleanup (PRs #2-#6). Cleanup apply mode ran 2026-10-27; the cleaned catalog (5,894 beers, 1,339 breweries) was reviewed and promoted to the git baseline in `experiments/catalog-discovery/data/` (PR #8), with all source IDs verified preserved.
- Firebase verification, 2026-10-27: project beerpassport-b31d8 (Blaze) holds 309 real Auth accounts (2023-09 to 2026-02, all email/password); Firestore has only a 4-document users collection.
- Milestone 1 step 2 (split across two PRs at Frank's direction): the PostgreSQL schema port landed in `beer-passport-server` (PR targeting `release/2.0`, the server repo's new integration branch), and the scripted catalog import lives in this hub's `db/`. Full local load proof against PostgreSQL 16.2 (exact counts, constraints exercised).

## Confirmed findings

Findings verified against the current repositories during the hub build (October 2026):

- All five repositories exist under `FrankPizz10` and are readable: `beer-passport`, `beer-passport-server`, `beer-passport-admin`, `beer-passport-web`, `beerpassport-cloud-functions`.
- The audit's repository inventory matches the actual repositories.
- The audit's characterization of the stack (React Native/Expo, Express/TypeScript, Prisma, Firebase Auth, admin site, link website, Cloud Functions) matches the repositories.

One security-relevant finding from the hub verification: the cloud-functions repo's `firestore.rules` allows open read/write on `/users/{userId}` for any caller. Whether those rules are deployed is unverified. Tracked as H1 in [ROADMAP.md](ROADMAP.md#new-findings-from-hub-verification-october-2026); the Firestore side holds only 4 user documents (verified 2026-10-27).

## Decisions made

- Relaunch the existing app; do not rewrite it. (Plan, accepted.)
- Retain the proven stack where practical: React Native/Expo, Node/Express/TypeScript, Firebase Auth, Prisma. (Plan, accepted.)
- This project hub is the central source of truth for the relaunch. (Accepted on creation.)
- D1 hosting: single Lightsail instance (TD-9, [decisions/001](decisions/001-hosting-lightsail.md)).
- D2 database: PostgreSQL (TD-10, [decisions/002](decisions/002-database-postgresql.md)).
- User data continuity, not a restart: Firebase and EFS user data migrate with IDs preserved; EFS and Firebase are frozen until the migrated data is verified (TD-11, [decisions/003](decisions/003-user-data-continuity.md)).

## Decisions still open

- D3 Catalog sources and licensing for external data.
- D4 Imagery sourcing and permission basis per source.
- D5 API compatibility window and versioning policy.

See [TECHNICAL_DECISIONS.md](TECHNICAL_DECISIONS.md) and [ROADMAP.md](ROADMAP.md#decisions-awaiting-approval).

## Blockers and risks

- The EFS MySQL data directory's integrity is unverified until the Milestone 1 step 3 recovery spike (temporary EC2 mounts EFS, matching MySQL, full dump). The agreed fallback trigger lives in decisions/003.
- Risk: the legacy catalog (circa 2008 dataset) has unresolved provenance and reuse rights; bulk reuse before the license audit could create legal exposure.
- GitHub Actions for this repo still await the workflow file landing under Frank's own GitHub identity (the Muse app lacks the Workflows permission); test suites run locally in the meantime.

## Next recommended action

Frank reviews and merges the Milestone 1 step 2 PR. Next step: the EFS recovery spike (step 3), run by Frank from a step-by-step guide with Jarvis directing, in parallel with the Firebase Auth UID export for the ghost-user diff.

Relevant links: [ROADMAP.md](ROADMAP.md) for the phased plan, [AUDIT.md](AUDIT.md) for all findings, [REPOSITORIES.md](REPOSITORIES.md) for the repo inventory.
