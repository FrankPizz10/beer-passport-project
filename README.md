# BeerPassport Project Hub

Central source of truth for the BeerPassport 2.0 relaunch. This repository is documentation only: it holds the product context, the improvement plan, the code audit findings, the roadmap, and the operating instructions any agent or developer needs to work on the project.

## What BeerPassport is

BeerPassport is a social beverage discovery and collection app. Users track beverages they have tried and liked, complete curated collections, earn badges, add friends, and see friends' beverage activity and achievements. Search supports beverage name, brewery/producer, and beverage type.

The original app (around 200 users, a 6,000+ beverage catalog) worked but stalled: the interface felt basic, hosting cost roughly $50/month until the credits ran out, catalog maintenance required manual database inserts, the database lifecycle was coupled to API compute, backend releases occasionally broke older installed mobile apps, and the catalog's data provenance was never audited. The relaunch is a targeted product and operations redesign, not a ground-up rewrite.

## Why this repository exists

Five application repositories (`beer-passport`, `beer-passport-server`, `beer-passport-admin`, `beer-passport-web`, `beerpassport-cloud-functions`) hold the code. The relaunch planning material lived in Google Drive documents. This hub consolidates the plan, the audit, and the verified repository state into one place so that ChatGPT, Claude, Codex, GitHub Copilot, local coding agents, and human developers all start from the same facts. It distinguishes verified facts from audit findings, proposals, and open questions.

## Document map

| File | What it contains |
|---|---|
| [README.md](README.md) | This entry point |
| [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) | Durable product context: purpose, features worth preserving, goals, constraints, non-goals |
| [CURRENT_STATE.md](CURRENT_STATE.md) | Operational snapshot: phase, completed work, findings, decisions, blockers, next action |
| [ROADMAP.md](ROADMAP.md) | Phased relaunch roadmap consolidating the improvement plan and the code audit |
| [AUDIT.md](AUDIT.md) | Full preservation of the initial code audit findings with severity and verification status |
| [REPOSITORIES.md](REPOSITORIES.md) | Inventory of the five existing repositories: purpose, tech, entry points, commands, gaps |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Current system architecture, verified against the repositories |
| [TECHNICAL_DECISIONS.md](TECHNICAL_DECISIONS.md) | Decisions actually made, with status, rationale, and evidence |
| [AGENTS.md](AGENTS.md) | Instructions every AI coding agent must follow when working on BeerPassport |
| [decisions/](decisions/) | Durable per-decision records |
| [research/](research/) | External research with sources, dates, and licensing notes |
| [issues/](issues/) | Implementation briefs for substantial cross-repo tasks |
| [templates/](templates/) | Task and session-handoff templates |

## How to begin

1. If you are an AI coding agent, read [AGENTS.md](AGENTS.md) first and follow it exactly.
2. Read [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md), then [CURRENT_STATE.md](CURRENT_STATE.md), then [ROADMAP.md](ROADMAP.md).
3. Consult [REPOSITORIES.md](REPOSITORIES.md) and [ARCHITECTURE.md](ARCHITECTURE.md) for the repositories your task touches.
4. Check [TECHNICAL_DECISIONS.md](TECHNICAL_DECISIONS.md) and the [decisions/](decisions/) folder before proposing architectural changes.
5. Use the templates in [templates/](templates/) for new tasks and session handoffs.

## Source material

This hub was built from two primary sources, preserved unchanged in Google Drive (`Jarvis/BeerPassport`):

- `BeerPassport_2_0_Product_and_Engineering_Plan.docx` (October 2026): the relaunch and engineering plan.
- `BeerPassport_Initial_Code_Audit_Problems_Found.docx` (October 9, 2026): the initial code audit of the five repositories.

Verified against the five GitHub repositories under `FrankPizz10` in October 2026. Where the documents and the repositories disagree, the discrepancy is documented rather than silently resolved.
