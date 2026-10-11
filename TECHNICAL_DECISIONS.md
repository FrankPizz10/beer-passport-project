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
- **Consequences:** Affects all five repositories. Hosting and database provider choices are still open (D1, D2).
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
