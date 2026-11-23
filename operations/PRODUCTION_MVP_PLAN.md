# BeerPassport production MVP plan

Proposed for CTO approval. This PR selects an architecture and release gates. Provisioning, data transfer, production load, DNS changes, and deployment each require separate approval.

## What ships

Restore the existing mobile loop: Firebase sign-in and onboarding, beverage search and detail, tried/liked logging, collections and badges, friends and privacy-controlled activity, and beer share links. Keep Firebase Auth and the existing app identities. Keep the web share-link surface. Add the new discovery experience only behind the compatible API and tested mobile rollout. Use approved images where available and existing fallback artwork elsewhere. Hold catalog expansion, a new public admin surface, and infrastructure dedicated to scale until the core loop is stable.

## Production footprint and cost

| Component | Initial choice | Monthly estimate |
|---|---|---:|
| Compute and public IPv4 | One Lightsail Linux Micro in us-east-1, 1 GB RAM, 2 vCPUs, 40 GB root disk. Attach a static IPv4 on provisioning. Confirm AZ and a supported Ubuntu LTS image in the console. | $7.00 |
| PostgreSQL storage | Start with 16 GB attached Lightsail block storage, mounted by UUID. PostgreSQL gets an explicit data path independent of the API container. | $1.60 |
| DNS | Reuse the existing authoritative zone. Route 53 hosted-zone cost, if attributable to BeerPassport. | $0.50 plus queries |
| Recovery storage | Incremental snapshots and private encrypted logical backups with lifecycle retention. Budget allowance, based on actual storage. | $1–3 |
| Existing web, images, auth, telemetry | Keep existing static hosting and Firebase Auth. Use minimal traffic and error-only telemetry initially. No new CDN subscription. | Usage-dependent |

Target roughly $10–13/month at pilot traffic, before taxes, domain renewal, and any legacy AWS resources. Verify AWS pricing and actual spend before the public cutover. The earlier $5 quote for the 1 GB IPv4 bundle is stale. Set alerts at $10 actual and $15 forecast, and review legacy ECS, load balancer, EC2, EFS, snapshots, and static hosting separately. Protect the recovery sources until verification and CTO sign-off.

Pricing and architecture sources include [Lightsail architecture decision](https://github.com/FrankPizz10/beer-passport-project/blob/main/decisions/001-hosting-lightsail.md), [AWS Lightsail pricing](https://aws.amazon.com/lightsail/pricing/), [Route 53 pricing](https://aws.amazon.com/route53/pricing/).

### On the host

- Run one small HTTPS reverse proxy, one API container, and one PostgreSQL 16 container under Compose. Verify installed clients' API hostname before changing DNS. Publish only HTTPS and HTTP for redirects or certificate validation. Restrict SSH to the operator's trusted source addresses and use separate SSH keys, key-only auth, and a dedicated operator login. Keep PostgreSQL and the API's raw port on the private Compose network.
- Make database startup depend on the expected disk mount and data path. A missing mount must stop PostgreSQL startup rather than initialize a new cluster on the root disk. Test host reboot, API replacement, and disk detach or restore behavior on disposable copies.
- Use a separate migration owner and limited API login. Keep Firebase and database credentials outside Git and images in restricted runtime configuration. Use fresh credentials for the new environment and scope the Firebase service identity to the required operations. Inventory and retire replaced credentials only after the new path is verified. Keep the admin viewer local or private until its read-only database role and Firebase admin authorization are verified. Maintain separate catalog mutation access if it is needed.
- Build and test images off-host. deploy a pinned, previously tested image by digest. Pin a supported Node LTS and PostgreSQL patch image. keep Prisma CLI, client, schema, and migration history aligned. Keep the previous compatible image on hand. Leave staging on local or short-lived disposable capacity rather than buying a second permanent host.

## Release sequence

### A. Provision the empty box and harden the release branch in parallel

Frank and Codex handle Lightsail, SSH, firewall, persistent disk, and backup setup. Use the Lightsail console for provisioning if the regional API hostnames still fail DNS resolution from the operator’s terminal. Muse handles application PRs and rehearsals. Configure the box without serving production traffic or moving the recovered data. Demonstrate a fresh boot, disk mount, TLS on the approved test hostname, and off-box backup and restore using synthetic data.

On the server, the current release/2.0 Docker entry point still calls start:prod, which reads Secrets Manager and applies Prisma migrations. src/index.ts also calls seedDatabase(). Split startup into a pure runtime command and separately approved migration/import jobs. remove the startup seed dependency. Reuse secret-free image building, reconcile the release branch's Prisma tooling with the approved PostgreSQL migration chain, and prove a production-like image builds and boots under CI. Add inexpensive health checks for process liveness and local dependency readiness, start with a small API database pool and cap log sizes, drop default full trace/profiling sampling, and verify no request tokens, secrets, or payloads reach logs. Keep legacy /api/* request and response contracts stable and add discovery under /api/v1.

Reviewed sources include [server startup](https://github.com/FrankPizz10/beer-passport-server/blob/release/2.0/src/index.ts), [container](https://github.com/FrankPizz10/beer-passport-server/blob/release/2.0/Dockerfile), [scripts](https://github.com/FrankPizz10/beer-passport-server/blob/release/2.0/package.json), [CI](https://github.com/FrankPizz10/beer-passport-server/blob/release/2.0/.github/workflows/ci.yml), [mobile API client](https://github.com/FrankPizz10/beer-passport/blob/08878d65c54f5a1b28148db31fa5493b46d04dff/Models/Requests.ts).

### B. Rehearse and validate the import

Review hub PRs #11 and #12 at their final heads. Resolve the allowlist contract before opening the production gate: 294 matched UIDs, zero allowlisted UIDs without a recovered profile, and 15 Firebase-only accounts as a separate metric. No production allowlist was written by the in-memory reconciliation. Freeze the approved import input manifest and handle subsequent Firebase registrations through the normal app onboarding flow. Generate the exact allowlist only as an approved step. Transfer only required import inputs through host-key-verified SSH into restricted storage. verify checksums and account for transient copies. Keep the full verified MySQL dump in approved private off-host storage before retiring any recovery resource.

1. Rehearse migration on disposable PostgreSQL with synthetic fixture cases for matched and unmatched profiles, rejected and duplicate rows, relationships, and sequences.
2. On an empty, isolated production target, apply the reviewed migration chain once. Load the frozen catalog first, preserving source IDs. The frozen baseline has 14 categories, 147 styles, 1,339 breweries, and 5,894 beers. Confirm the permission basis for the catalog and every published image before exposing them. If needed, release only an approved subset after reviewing how its missing beer IDs affect the recovered history.
3. Load the 294 matched profiles and eligible dependent records with source IDs preserved. Leave five unmatched MySQL profiles in the verified backup and leave the 15 Firebase-only accounts unchanged. Keep legacy API keys and push tokens out of the initial load. verify token re-registration before enabling push, and require fresh credentials for any operational API keys.
4. Validate catalog and per-table manifest totals, the 294 exact profile matches, collections and badge dependencies, orphan checks, sequence advances, and a sample of history under the correct identity. Account for all source rows as loaded, rejected, deduplicated, or excluded by scope. Pause on unexpected rejects or a changed source inventory. Take and restore-test a post-load logical backup before cutover.

Reviewed sources include [catalog load runbook](https://github.com/FrankPizz10/beer-passport-project/blob/main/db/README.md), [recovery record PR](https://github.com/FrankPizz10/beer-passport-project/pull/11), [rehearsal PR](https://github.com/FrankPizz10/beer-passport-project/pull/12), [user continuity decision](https://github.com/FrankPizz10/beer-passport-project/blob/main/decisions/003-user-data-continuity.md).

### C. Test the whole product and cut over

- **Mobile and API.** test an installed legacy build and the candidate build against the same API. Exercise sign-in, missing and expired tokens, profile creation from verified Firebase UID, catalog search and detail, logging, collections/badges, friend requests, and privacy. Test a matched returning user and a Firebase account without a recovered profile. Confirm legacy requests and errors still work. no forced upgrade solely to restore service.
- **Web.** verify the existing share host and /beers/* route from a real device and a browser, including iOS association document, certificate, and fallback when the app is absent.
- **Admin and Firebase.** confirm every user-scoped and admin action enforces server-side access. The checked-in Firestore rules allow access to users and tried documents. Check deployed rules and supported-client dependencies, then close any public user-data access before release. Preserve Firebase Auth accounts. Verify an intentionally approved admin path for operational work. the admin viewer, image signing, and claim-management rollout can remain private or deferred.
- Release to an internal cohort first. Confirm budget alerts, backup alerts, external HTTPS uptime checks, and support ownership. Rehearse an API container restart with the same database volume. Lower API DNS TTL ahead of cutover, document the prior record and image digest, and obtain Frank's go/no-go before directing traffic. Keep auth, write activity, error rates, and recovery checks under observation during the first day.

Reviewed sources include [web routes](https://github.com/FrankPizz10/beer-passport-web/blob/main/src/App.tsx), [admin runbook PR](https://github.com/FrankPizz10/beer-passport-admin/pull/8), [checked-in Firestore rules](https://github.com/FrankPizz10/beerpassport-cloud-functions/blob/master/firestore.rules).

## Operations and scaling

- Nightly encrypted logical backup off the host to an approved private destination, with upload verification and retention of seven daily copies and four weekly copies. For the first rehearsal use the operator's federated access. approve the narrow automated backup identity before public traffic. Keep instance and data-disk snapshots for host recovery. Alert on missing backups and retain a separately tested restore runbook. Initial targets are a 24-hour recovery point and four-hour recovery time, subject to the drill.
- Roll back application code with the previous tested image and compatible schema. Before customer writes, use the tested restore or cutover reversal if validation fails. After customer writes, take a new backup before any recovery action and preserve those writes by rolling forward or reconciling the delta. avoid restoring over them as a routine deployment rollback.
- Start by tracking CPU, memory, disk, PostgreSQL connections, API latency and errors, and backup age. During the pilot, investigate recurring OOM/restarts, disk above 70%, database connections above 70% of budget, or repeated peak p95 latency over 500 ms. These are investigation thresholds. establish a baseline before turning them into upgrade decisions. Cap retries and connection pools, profile slow queries and indexes, and scale storage if it is the limiting factor.
- For the first capacity step, use the $12/month 2 GB IPv4 tier only after measuring saturation and approving the revised total. Rehearse replacement from backups and moving the static IP. If database operations or recovery targets become the bottleneck, move PostgreSQL to a private encrypted managed service, validate restore and cutover, and keep API compute independent. If API demand still exceeds a box after tuning, add a second stateless API instance and load balancing after pricing and testing. Avoid adding a cache until measurements show which workload needs it.

## Approval and ownership

Frank approves the architecture PR, region/bundle and provisioning, rehearsal database commands, production data transfer/load, and traffic cutover. Codex owns the recovery/hosting runbook, validates release evidence, and coordinates parallel work. Muse owns implementation PRs, fixture rehearsals, and test evidence. A plan merge does not authorize any AWS or production action.
