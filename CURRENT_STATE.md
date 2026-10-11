# Current State

Operational snapshot. Keep this file short and update it after every significant working session.

## Phase

Planning and code audit complete. Implementation has not begun.

## Work completed so far

- Initial code audit of all five repositories, October 9, 2026, with findings prioritized P0-P3. Source: `BeerPassport_Initial_Code_Audit_Problems_Found.docx` (Google Drive, `Jarvis/BeerPassport`).
- Product and engineering relaunch plan, October 2026, covering goals, feature plan, architecture principles, and a four-phase roadmap. Source: `BeerPassport_2_0_Product_and_Engineering_Plan.docx` (Google Drive, `Jarvis/BeerPassport`).
- This project hub, October 2026: both documents consolidated and reconciled against the current GitHub state.

## Confirmed findings

Findings verified against the current repositories during the hub build (October 2026):

- All five repositories exist under `FrankPizz10` and are readable: `beer-passport`, `beer-passport-server`, `beer-passport-admin`, `beer-passport-web`, `beerpassport-cloud-functions`.
- The audit's repository inventory matches the actual repositories.
- The audit's characterization of the stack (React Native/Expo, Express/TypeScript, Prisma, Firebase Auth, admin site, link website, Cloud Functions) matches the repositories.

## Unresolved findings (from the audit, not independently re-verified)

The audit labeled several items "observed in code" and several "needs verification." The hub build spot-checked ten key claims against the current repositories and confirmed all of them (Dockerfile `.env` copy, Secrets Manager to `.env` write, `seedDatabase()` at startup, error middleware ordering, auth status codes, Prisma version mismatch, friend/upc/notification schema concerns, the `<pre>`-rendered association file, and the deep-link mismatch). The remainder should be treated as audit-reported, not independently confirmed. Full list with severity in [AUDIT.md](AUDIT.md); the items still needing verification are listed in [ROADMAP.md](ROADMAP.md#awaiting-investigation).

One new security-relevant finding came out of the hub verification and was not in the original audit: the cloud-functions repo's `firestore.rules` allows open read/write on `/users/{userId}` for any caller. Whether those rules are deployed is unverified. Tracked as H1 in [ROADMAP.md](ROADMAP.md#new-findings-from-hub-verification-october-2026).

## Decisions made

- Relaunch the existing app; do not rewrite it. (Plan, accepted.)
- Retain the proven stack where practical: React Native/Expo, Node/Express/TypeScript, Firebase Auth, Prisma. (Plan, accepted.)
- This project hub is the central source of truth for the relaunch. (Accepted on creation.)

## Decisions still open

- D1 Hosting: lean managed hosting vs AWS-native/serverless.
- D2 Database provider: stay on MySQL or migrate to PostgreSQL before relaunch.
- D3 Catalog sources and licensing for external data.
- D4 Imagery sourcing and permission basis per source.
- D5 API compatibility window and versioning policy.

See [TECHNICAL_DECISIONS.md](TECHNICAL_DECISIONS.md) and [ROADMAP.md](ROADMAP.md#decisions-awaiting-approval).

## Blockers and risks

- No blockers on documentation. The next phase (implementation) is blocked on Frank's review of this hub and approval of the P0 items and open decisions.
- Risk: audit items marked "needs verification" are hypotheses; acting on them as confirmed incidents could waste effort.
- Risk: the legacy catalog (circa 2008 dataset) has unresolved provenance and reuse rights; bulk reuse before the license audit could create legal exposure.
- Risk: database lifecycle is still coupled to API compute in the current deployment design; any production cutover before P0.3 risks data persistence problems.

## Next recommended action

Frank reviews this hub, then approves or adjusts the P0 priority list and the five open decisions (D1-D5). After approval, the first implementation session runs the audit checklist items: back up the database, fix the Docker/secret handling, and correct auth error statuses.

Relevant links: [ROADMAP.md](ROADMAP.md) for the phased plan, [AUDIT.md](AUDIT.md) for all findings, [REPOSITORIES.md](REPOSITORIES.md) for the repo inventory.
