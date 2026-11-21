# BeerPassport 2.0: Agentic Development Transformation, Audit and Proposal

Prepared 2026-11-21. Status: proposal for Frank's review. No repository changes were made for this audit.

## Executive summary

Our implementation speed is not the bottleneck. Our queueing is. Every completed step so far was built in a single working session: the catalog cleanup, the cleanup apply and baseline promotion, the Postgres schema port, and the import tooling with its load proof. What takes the time is everything around the building: sequential gating (nothing starts until the previous step merges), Frank's review queue, and mechanical tasks that only Frank can perform (the CI workflow paste took a week of calendar time and two troubleshooting rounds). The clearest evidence: server PR #39 has been open since October 27, twenty five days at the time of writing, fully implemented and verified, waiting on review. The hub half of the same step merged on November 4.

The person who built a polished app in one night had no legacy users, no data migration, no security debt, and nothing to lose. BeerPassport has 309 real user accounts, irreplaceable user data on a dormant EFS volume, and open P0 security findings. We cannot copy that workflow's risk profile, but we can copy its structure: one agent organization working in parallel against clear contracts, with the human acting as CTO and final approver rather than as the scheduler, messenger, and merge queue for every micro-step.

The proposal in one paragraph: keep Frank's authority over merges, deployments, and escalated decisions exactly as it is. Change everything upstream of that. Work in feature-sized increments instead of layer-sized steps. Run independent workstreams in parallel under an orchestrator (me) with explicit file and branch ownership. Add an independent QA and review pass inside the agent organization so Frank reviews a verified result, not a first draft. Relax the data sourcing policy for private development as Frank directed, with provenance tiers that keep a future public launch possible. Pilot the whole model on one real feature, measure it, and only then make it the default.

## 1. Current state assessment

### What exists (verified from the repositories, November 2026)

- **beer-passport-project (hub)**: planning, catalog data pipeline, import tooling, decision records. Active. Python, with CI live and green on main (lint, typecheck, and two unit test suites). Catalog baseline: 5,894 beers, 1,339 breweries, 147 styles, 14 categories.
- **beer-passport-server**: Express 4 and TypeScript API, Prisma, Firebase Admin, Sentry, Jest configured with a test directory. Default branch master (last commit August 2024). The relaunch integration branch release/2.0 exists and holds one open PR: #39, the PostgreSQL schema port and baseline migration.
- **beer-passport (mobile)**: React Native with Expo SDK 51, React Navigation, 20 screens, Firebase client. Last commit November 2024. No test script at all. README is 84 bytes; required environment variables are undocumented.
- **beer-passport-admin** (last commit April 2024), **beer-passport-web** (October 2024), **beerpassport-cloud-functions** (July 2023, and the source of the open Firestore rules finding H1).
- **Firebase project beerpassport-b31d8**: 309 real Auth accounts. **AWS**: old backend shut down; the EFS volume holds the dormant MySQL datadir with the irreplaceable user tables; both are frozen until the migration is verified.
- **Architecture decisions on record**: TD-1 targeted relaunch not rewrite, TD-2 retain the proven stack, TD-3 server-side authorization is the security boundary, TD-5 separate database lifecycle from API compute, TD-6 versioned backward-compatible API, TD-7 image fallback hierarchy, TD-8 catalog import as an explicit operation, TD-9 Lightsail, TD-10 PostgreSQL, TD-11 user data continuity.

### How we currently develop

One step at a time, in a strict sequence, where a "step" is usually one layer of one feature (a schema change, or an import script, or a cleanup). Each step is a branch and PR that Frank reviews and merges before the next begins. Frank also performs every action the agent tooling cannot: pasting workflow files, creating cloud resources, entering one-time codes. Planning documents are thorough; the hub is a genuine source of truth.

### The bottlenecks, ranked by calendar cost

1. **Serialization.** Independent work waits behind unrelated gates. The EFS recovery guide, the server Phase 0 hardening, catalog enrichment development, and mobile UX work have no technical dependency on PR #39, yet none of them have started because the roadmap is executed as a single queue.
2. **Frank's review bandwidth spent on the wrong granularity.** Layer-sized PRs force Frank to review plumbing (a schema port) with the same attention as product decisions. Small PRs did not reduce his total review load; they multiplied the number of review events.
3. **Human-only mechanical tasks.** Anything behind the GitHub App's missing Workflows permission, AWS console actions, and code-gated logins routes through Frank. Each one is small; together they add days.
4. **No verification layer before Frank.** Frank is currently the QA department. There is no independent review pass, no CI on the server or mobile repos, and no automated check that a change behaves correctly in the running app. His review is doing defect detection that an agent QA pass should catch first.
5. **The mobile app is a cold start waiting to happen.** Two years untouched, Expo SDK 51 (several SDK generations old), zero tests, undocumented environment. When M3 arrives, the first mobile task will secretly be an archaeology and upgrade project unless we start warming it up now, in parallel.
6. **Data policy friction.** The catalog work proceeded under near-commercial licensing caution for what is currently a personal application. That made image and data acquisition slower and narrower than the actual risk required. (Addressed in section 6, per Frank's direction.)

### What is working and should be preserved

The hub as source of truth, decision records (TDs), the evidence rule (verified vs inferred), test reports in PR descriptions, CI placement discipline, git hygiene (branch and PR, never direct to main, secrets never committed), the freeze on EFS and Firebase, and Frank's merge and deploy authority. The new workflow keeps all of it.

## 2. Recommended agent architecture

These are workstreams I run, not separate products. I already operate with delegated subagents, a live browser, local build tooling, and the GitHub connector; the change is making the structure explicit and standing, with ownership rules.

- **Orchestrator (Tech Lead)**: me, in the main working thread. Owns the roadmap, decomposes objectives into task briefs with contracts and acceptance criteria, assigns workstreams, resolves conflicts, integrates results, and assembles the single review packet Frank sees. Owns the hub repo's planning documents and the project board.
- **Backend workstream**: server repo only. APIs, Prisma schema and migrations, auth, integrations. Works on feature branches off release/2.0. Never touches mobile or hub data files.
- **Frontend/UX workstream**: mobile repo (and later admin/web). Screens, navigation, state, design exploration and prototypes. Works against agreed API contracts, using a mock server until the real endpoints land. Never touches server code.
- **Data workstream**: hub repo's experiments and db directories only. Discovery, ingestion, matching, normalization, image association, quality reports. Works on isolated data copies; promotes to the baseline only through the existing verified pipeline.
- **QA workstream**: independent of whoever built the feature. Writes and runs tests, exercises the running app (local server plus Expo web preview in a browser), checks acceptance criteria, and files defects back to the owning workstream. QA sign-off is required before anything reaches Frank.
- **Review workstream**: a separate pass over every PR diff for correctness, security (especially TD-3 authorization boundaries), maintainability, and consistency with the TDs. This is a distinct agent from the author, every time. Frank's Nov 16 experience in another project is the standing lesson: the agent that made a change must not be the only one checking it.

**Coordination rules**

- One owner per file area at a time (the ownership split above). Shared interfaces (API contracts, Prisma schema, catalog CSV formats) are owned by the Orchestrator and change only through a contract note in the hub that all workstreams read first.
- Every workstream works on its own branch; integration happens in the open, in the PR, not in chat summaries.
- A shared status board (the BeerPassport Project Board space, already live) is updated as work lands, so Frank can see all workstreams at a glance instead of asking.
- Parallel agents multiply token cost roughly linearly per workstream. The discipline is: parallelize only genuinely independent work, and keep workstream briefs tight. (Benefit: calendar compression. Cost: more tokens per feature. Risk: conflicting assumptions, mitigated by contract-first briefs. Tradeoff accepted for feature work, not for small fixes, which stay single-agent.)

## 3. Workflow redesign: idea to production-ready PR

1. **Objective brief (Orchestrator, no Frank approval needed for reversible work)**: user experience intent, dependencies, API and data contracts, acceptance criteria, and a parallelization plan (what can be built simultaneously, what must wait).
2. **Contract first**: endpoints, payloads, and schema changes are written down in the hub before code. Frontend builds against the contract with mocks; backend builds to the contract; data prepares fixtures matching it.
3. **Parallel build**: workstreams implement concurrently on separate branches in separate repos. Database, backend, frontend, and tests for one feature land as one coherent feature PR per repo (or a single PR where the feature lives in one repo), cross-linked, instead of four sequential layer PRs.
4. **Independent QA**: the QA workstream runs the full test suites, then validates behavior in the running application, not just the diff. Defects loop back to the author workstream.
5. **Independent review**: the Review workstream audits the final diff. Its findings are fixed or explicitly listed as known limitations.
6. **Frank's review packet**: one PR (or one cross-linked set) with a plain-language summary of the user-visible change, screenshots or a short capture for UI work, the test report (what ran, where, results), QA and review outcomes, and known limitations. Frank approves and merges; deployment remains his call, always.
7. **Board and hub updated** as part of the same task, not as an afterthought.

Escalation stays as Frank defined it: significant architecture changes, destructive database operations, data migrations, security-sensitive functionality, material cost increases, paid services, and irreversible production changes come to him before execution, with evidence and options. Everything reversible and low-risk proceeds on engineering judgment, and is reported in the packet.

**PR sizing rule, revised**: a PR should be one independently testable product increment. Split only when a split genuinely reduces risk (for example, a schema migration that must land before data exists, like PR #39) or when reviewability truly suffers. Expected benefit: fewer, more meaningful review events for Frank and features that actually work end to end when merged. Risk: a larger diff per review. Mitigation: QA and review passes happen before Frank, and the packet leads with behavior, not code.

## 4. Parallelization opportunities in the current roadmap

None of these wait on PR #39 unless noted:

- **EFS recovery spike preparation (Data/Orchestrator)**: the step-by-step EC2 and MySQL recovery guide can be written, and the Firebase Auth export process rehearsed against the console, now. Only the execution benefits from PR #39 being merged; the preparation does not. This removes the guide-writing latency from the critical path entirely.
- **Server Phase 0 hardening (Backend)**: P0.2 (secrets out of the Docker build), P0.4 (401/403 correctness and server-side authorization), and the Prisma CLI/client version alignment are independent of the Postgres port's review. They can be built as a stacked branch on top of PR #39's branch, so they merge cleanly after it, or rebased onto release/2.0. Security debt stops waiting for a database decision.
- **Server CI (Backend/QA)**: the server repo has Jest configured but no CI in our workflow. A workflow file for release/2.0 (Frank pastes it once, same constraint as the hub) plus a baseline test run gives every later server PR automated verification. One Frank paste now saves manual verification on every future server change.
- **Catalog enrichment pipeline (Data)**: relevance filters, the promotion pipeline into Postgres, and coverage reporting can be developed and tested against a local Postgres loaded with the baseline (already proven possible) while the box does not exist yet. M2's engineering can be mostly done before M1 finishes; only the final load waits.
- **Mobile warm-up and UX prototypes (Frontend)**: environment documentation, a reproducible local run, an Expo SDK upgrade assessment, and discovery/search prototypes against a mock API. All independent of the backend. This converts the M3 cold start into a running start and produces the design exploration Frank asked for in section 5 of his brief.
- **Image pipeline build (Data)**: S3 and CloudFront structure, the beverage_images population flow, and the TD-7 fallback hierarchy can be implemented against local fixtures now; only the bucket creation needs Frank's AWS hands, once.

## 5. UX improvements and design autonomy

Current state: the 2.0 plan includes wireframing navigation, search, logging, passport, collections, badges, and friend activity as an unfinished Phase 1 item. The app itself is a 2024 design. Proposal:

- **Design exploration as a standard step** for every substantial surface: the Frontend workstream researches comparable modern apps (beer and beverage discovery, collection and passport mechanics, social activity feeds), builds two or three functional prototypes of the key surface in the real codebase against mock data, and brings Frank a recommendation with the alternatives runnable, not just described. Frank picks direction; the prototypes are cheap because they share the component scaffolding.
- **Priority surfaces**, in order: beverage discovery and search/filtering (the core loop), beverage and brewery profiles, collections and badges, onboarding (309 returning users need a "welcome back" path, not a new-user funnel), social activity, then navigation and the loading/empty/error states across all of them.
- **Validation by interaction**: prototypes are exercised in an Expo web preview in a real browser, checking flows end to end, rather than judged from static screenshots alone. Screenshots still go in Frank's review packet.
- **A small design system first**: tokens for color, type, and spacing plus the handful of shared components (cards, list rows, buttons, empty states) so parallel frontend work stays visually consistent and prototypes are fast to build. This is a modest upfront cost that pays for itself by the second surface.

Benefit: product quality becomes a designed outcome instead of an accident of implementation order. Complexity: medium (prototype discipline plus design tokens). Risk: exploration sprawl. Mitigation: prototypes are time-boxed to the key surface of the feature being built, and Frank's pick ends the exploration.

## 6. Data strategy, reassessed under the expanded sourcing policy

Frank's direction: BeerPassport is currently a personal-use application. Licensing uncertainty should flag, not block, research and private development. Hard lines that stay: no bypassing authentication, paywalls, or technical access controls, and provenance is recorded for everything, so any future public launch can filter the catalog by rights tier.

**Source inventory, with what each is good for**

- **Open Brewery DB**: open, free API of brewery records (names, locations, types, websites). Best available bootstrap for brewery enrichment (addresses, geocoding seeds, brewery websites) which our catalog largely lacks. Low risk for any use.
- **Open Food Facts** (already integrated): packaged beverages with barcodes and images (database ODbL, contents DbCL, images CC BY-SA). Remains the packaged-product backbone; our barcode coverage problem stands (the legacy catalog has effectively no usable UPCs), so OFF helps mainly for new discoveries, as measured: roughly 400 genuinely new in-scope products per partial run.
- **Wikidata and Wikimedia Commons**: structured brewery and beverage data plus freely licensed images and logos. Good for notable breweries and brands; sparse for small craft products.
- **Brewery and brand websites**: the authoritative source for lineups, descriptions, and official product images. For private development, crawlable where publicly accessible and not access-controlled; every asset gets provenance (source URL, retrieval date) and a rights tier of "private use only" by default.
- **Public catalogs and search engines**: discovery and cross-checking (finding that a beverage exists, its brewery, its style), feeding the matching pipeline rather than being copied wholesale.
- **The legacy catalog itself**: 5,894 beers remain the core. Enrichment (brewery details, descriptions, images) matters more than raw growth.

**Provenance tiers (new)**: Tier A, openly licensed or public domain (usable anywhere). Tier B, publicly accessible, rights unclear (private use; flagged, excluded from any future public build by a single filter). Tier C, terms-restricted (metadata only, no asset copying). The existing beverage_images model already stores source, license, and attribution, so tiers slot into the current schema design.

**Automated pipeline**: discovery runs feed a staging area; automated matching (name normalization, brewery matching, duplicate detection against the baseline, the R4 report-only rule preserved); normalization of styles and ABV/IBU formats; image association with tier tagging; a sampled human (agent QA) quality report per batch; promotion in verified batches with rollback, exactly as the current import tooling already works. Benefit: the catalog grows and enriches itself between Frank's sessions instead of during them. Complexity: medium, most components exist in embryo in the catalog-discovery experiment. Risk: data quality drift. Mitigation: nothing promotes without the validation gates and coverage report that already exist.

## 7. Tooling assessment

**Available now, verified in use**

- Delegated subagents for parallel workstreams, with the main thread as orchestrator.
- GitHub via the official connector: branches, pushes, PRs, reviews data, CI status reads. CI exists and runs on the hub repo.
- A live browser (console work, Expo web previews, Firebase console verification), local Node 24 and Python environments, and a proven local PostgreSQL load-test setup.
- The project board space for status, plus Drive documents for plans and guides.

**Limitations, stated plainly**

- The GitHub App has no Workflows permission: I cannot create or edit workflow files or manage Actions. Every new repo's CI file is a one-time Frank paste. I also cannot merge PRs or administer repos; merges stay with Frank by design as well as by tooling.
- AWS access is read-only. Lightsail, EC2 (for the EFS spike), S3, and Route 53 changes are Frank's hands, with my guides. This caps how autonomous the infrastructure steps can be, and is a policy choice Frank can revisit separately; the current proposal works within it.
- No iOS simulator or device farm: mobile validation is Expo web preview plus Frank's phone for native checks. Native-only behavior (push notifications, deep links) cannot be fully verified by agents.
- No direct access to Frank's local machines or network; anything there is guided, not automated.
- Parallel subagents cost tokens roughly per workstream. Velocity metrics (section 8) include cost so we can see whether parallelization is paying for itself.

## 8. Measuring whether this works

Per feature, tracked on the project board and in the hub:

- Request to review-ready PR: calendar days and agent working time.
- Frank interventions per feature: count of decisions, pastes, codes, and reviews he had to perform. Target: only escalations and the final review.
- Defects found by QA and Review passes vs defects Frank finds. Target: Frank finds product issues, not bugs.
- Test results per PR (already in our PR test reports) and, for the server, coverage trend once CI exists there.
- Rework: follow-up fix PRs per feature within two weeks.
- Parallel workstreams active per feature, and token cost per feature where measurable.

We judge the pilot against the baseline we already have: steps 1 and 2 under the old workflow took one session to build and, for step 2's server half, twenty five days and counting to clear review.

## 9. Pilot project recommendation

**Pilot: the beverage discovery vertical slice.** One feature, built end to end under the new workflow:

- Data: a discovery-ready slice of the catalog in Postgres (baseline subset loaded locally, with brewery enrichment for the top breweries from Open Brewery DB).
- Backend: search and browse endpoints (query, style and brewery filters, pagination) built to a written contract, on a branch off release/2.0 (stacked on PR #39), with Jest tests and the authorization rules from TD-3 applied.
- Frontend: the discovery and search experience in the mobile app against the contract, with two prototype directions for the main surface, Frank picks one, then the full implementation including loading, empty, and error states.
- QA and Review: independent passes, behavior validated against the running server and the Expo web preview.
- Deliverable: cross-linked PRs (server and mobile) with one combined review packet, screenshots, and a test report.

Why this pilot: it exercises every workstream and every new rule (contracts, parallel build, feature-sized PRs, independent QA, design exploration, expanded data sourcing) on the product's core loop, while touching nothing irreversible: no user data, no production, no migration. If PR #39 has not merged when we start, the server work stacks on its branch; nothing is blocked.

Runner-up, if Frank prefers a smaller pilot: the Phase 0 server hardening as a single feature PR (P0.2 plus P0.4 plus Prisma alignment plus server CI). Lower product value, lower risk, and it still tests the workflow's backend, QA, and review lanes.

## 10. Implementation roadmap (transition without interrupting progress)

- **Phase A, adopt the operating rules (immediately, zero disruption)**: this document's coordination rules, PR sizing rule, QA and Review passes, and packet format become the default for new work. M1 continues exactly as planned: PR #39, then the EFS spike, box setup, and load. Nothing in flight changes.
- **Phase B, parallel preparation (starts on Frank's approval, runs alongside M1)**: EFS guide written, server CI file prepared for Frank's paste, enrichment pipeline developed locally, mobile warm-up begun. These are the section 4 items; each lands as its own reviewable PR under the new rules.
- **Phase C, the pilot (starts when Phase B's mobile warm-up and the local data slice exist)**: the discovery vertical slice, measured per section 8.
- **Phase D, review and decide**: Frank and I compare pilot metrics against the old workflow's baseline and decide what becomes permanent, what adjusts, and what drops. The board and this document get updated with the outcome.

## Decisions requested from Frank

1. Approve or amend the workflow model (sections 2, 3, and 10).
2. Pick the pilot: the discovery vertical slice (recommended) or Phase 0 hardening.
3. Confirm the data sourcing tiers in section 6 as the standing policy for private development.
4. Confirm the escalation list remains as defined in his brief (architecture, destructive data operations, migrations, security-sensitive work, material cost, paid services, irreversible production changes).

Until Frank approves, no repository work under this proposal begins. The existing M1 plan remains the active path.
