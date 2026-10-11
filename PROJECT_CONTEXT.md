# Project Context

Durable product context for BeerPassport. Requirements and accepted constraints live here; ideas under consideration are marked as such.

## Product purpose

BeerPassport is a visually engaging passport for discovering beverages, tracking personal tasting history, completing curated challenges, and sharing progress with friends. It should reward exploration without becoming a clone of an existing beer check-in service.

### Intended user experience

- Discover a beverage.
- Log it as tried, and optionally mark it as liked (tried, liked, and want-to-try are different intentions and should be represented as distinct states).
- See visible progress toward a collection or badge.
- Share activity and see friends' progress.
- Return to discover and log more.

### Proposed primary navigation (from the relaunch plan; not yet implemented)

- **Home:** friends' recent activity, newly earned badges, collection milestones, prominent log-a-beverage action.
- **Discover:** search by name, brewery/producer, and beverage type; clear result cards, images when available, quick path to details.
- **Passport:** personal beverage history, liked beverages, collections, progress, earned badges.
- **Friends / Profile:** friend requests and management, public profile/passport, recent activity, achievements.

## Existing functionality worth preserving

From the original app, these worked and the relaunch keeps them:

- Beverage logging (tried/liked) with a useful lookup that made records easy to find.
- Preset collections that can be completed to earn badges; collections and badges were a compelling part of the concept.
- Friends and a social feed of friends' beverage activity and earned badges.
- Three search modes: beverage name, brewery, and beverage type.
- Admin dashboard managing a catalog of 6,000+ beverages.
- Firebase Authentication (straightforward; no reason to migrate).
- React Native/Expo mobile app, Node.js/Express/TypeScript API, Prisma data access, notifications, error monitoring.

## Original relaunch goals

1. Make the app more attractive, intuitive, and rewarding to use.
2. Improve retention through beverage logging, friend activity, collection progress, and badges.
3. Reduce recurring infrastructure costs from the historical baseline of roughly $50/month. Initial target is approximately $0-15/month where practical, excluding app-store fees and optional paid services. This is a target to validate, not a quote.
4. Replace manual database inserts with a repeatable catalog import, validation, editing, and moderation workflow.
5. Separate the database lifecycle from API compute so the API can scale without creating duplicate databases.
6. Prevent backend deployments from unexpectedly breaking older installed mobile apps.
7. Establish lawful, traceable sourcing for beverage data, product images, logos, and profile imagery.

## Success measures (from the plan)

- Activation: share of new users who log their first beverage.
- Retention: percentage of new users who return the following week; weekly active users.
- Core engagement: beverages logged per active user, collection progress, badges earned, friend interactions.
- Reliability: API error rate and latency; no avoidable client/server compatibility failures.
- Operations: no manual SQL inserts for routine catalog updates; tested deployments, backups, restoration.
- Cost: actual monthly total for compute, database, storage, networking, monitoring, third-party services.

## Historical context

- The original app reached roughly 200 users with a catalog of 6,000+ beverages.
- Hosting cost about $50/month despite low usage; the app became unsustainable when credits ran out.
- Catalog records were added through manual insertion via a poor admin interface.
- MySQL ran in a container alongside the Node.js service; scaling the API could create duplicate database containers and conflicts.
- Backend and mobile releases sometimes became incompatible, leaving older installed apps broken after backend changes.
- The catalog came from a very old free dataset (approximately 2008); its freshness, provenance, and reuse rights need auditing before reuse.
- The app lacked product imagery, brewery visuals, and profile pictures because licensing and sourcing questions were unresolved.

## Requirements

- Routine catalog maintenance must not require manual SQL inserts.
- The database lifecycle must be independent of API containers.
- Backend releases must not silently break older installed mobile apps (versioned API, additive changes, expand-and-contract migrations, contract tests).
- Every image or data asset published in the app must have a documented, acceptable permission basis. Online availability is not permission.
- Privacy and visibility rules must be explicit; stored activity must not automatically become public.
- Badge awarding must be idempotent; retries must not create duplicates.
- Collection and badge definitions should be data-driven, with completion calculated consistently on the backend.

## Non-goals (deferred unless evidence supports them)

- A complete rewrite of the app or backend.
- Kubernetes, microservices, Redis, or elaborate event-driven infrastructure.
- Chat and complex social interactions (defer until the core social loop demonstrates retention value).
- A paid external data API before verifying catalog coverage and business terms.
- Aggressive monetization before retention is demonstrated.

## Verified technologies (current stack, retained where practical)

- Mobile: React Native + Expo.
- API: Node.js + Express + TypeScript.
- Authentication: Firebase Auth, with Firebase Admin verification on the server.
- Data access: Prisma.
- Database: relational MySQL today; MySQL or a compatible managed relational database after hosting/cost evaluation.
- Monitoring: Sentry (retained if the current integration remains appropriate).
- Notifications: Expo Notifications (retained if still needed and cost-effective).

Source: `BeerPassport_2_0_Product_and_Engineering_Plan.docx` (October 2026). Cost figures are historical/plan targets, not quotes.
