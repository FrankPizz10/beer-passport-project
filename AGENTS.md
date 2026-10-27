# AGENTS.md

Instructions for any AI coding agent working on BeerPassport. These apply whether you are ChatGPT, Claude, Codex, GitHub Copilot, a local coding agent, or any other tool. They are portable: no provider-specific commands unless a documented workflow requires them.

## Before starting substantial work

1. Read `README.md`, `PROJECT_CONTEXT.md`, and `CURRENT_STATE.md` in this repository.
2. Read the relevant portions of `ROADMAP.md`, `REPOSITORIES.md`, and `ARCHITECTURE.md` for the task at hand.
3. Read the affected repository's own README and documentation.
4. Check `TECHNICAL_DECISIONS.md` and `decisions/` before proposing architectural changes.

## Working rules

- **Verify assumptions against actual source code.** Do not trust your memory of the codebase or of this documentation over what the code says. If this documentation and the code disagree, note the discrepancy.
- **Identify the relevant repositories and their dependencies** before proposing cross-repository changes. BeerPassport spans five repositories; a change in one often affects others.
- **Scope tightly.** Avoid unrelated refactors, new dependencies, and speculative infrastructure (no Redis, Kubernetes, microservices, or event-driven systems unless a task explicitly requires them).
- **Never expose secrets.** Do not print, log, or commit credentials, tokens, private keys, or environment-specific configuration. If you find a secret committed to a repository, report it; do not spread it.
- **Git hygiene (Frank, 2026-10-26).** Only commit code and material that needs to be shared or is important to the repo. Generated outputs (test runs, script outputs, CSVs, run artifacts) stay local and are covered by `.gitignore`; if something can be local, it is. Environment files (`.env` and variants) are never committed.
- **Committed-secret protocol (Frank, 2026-10-26).** If a secret is ever committed, by anyone, flag it to Frank immediately. Frank rotates the secret first, because a committed secret is compromised even after history is rewritten; then the agent provides the history-rewrite steps (for example `git filter-repo` plus force push) as a follow-up.
- **Never modify production data, deploy services, or perform destructive operations** without explicit authorization from Frank.
- **Prefer focused branches and reviewable changes.** One task, one branch, one pull request; conclude every change to an existing repository with a PR for Frank's review. Do not push directly to `main`.
- **Run the relevant tests** and report exactly which tests passed, failed, or were not run. Do not claim broader coverage than you ran.
- **Never claim a change was implemented, tested, or deployed without evidence.** Link the branch, commit, or test output.
- **Follow the relaunch constraints:** approximately $0-15/month infrastructure target, no manual SQL for routine catalog work, backward-compatible API changes, lawful image/data provenance.
- **Respect privacy rules:** user data access is governed by server-side authorization and the privacy/visibility rules in `PROJECT_CONTEXT.md`. Do not widen data exposure.

## Documentation duty

- When your work changes the architecture, roadmap, decisions, or project state, update this hub: `ARCHITECTURE.md`, `ROADMAP.md`, `TECHNICAL_DECISIONS.md`, or `CURRENT_STATE.md` as appropriate.
- Record durable architectural or product decisions in `decisions/` using the convention in `decisions/README.md`.
- Record external research in `research/` with sources and dates, per `research/README.md`.
- For substantial cross-repo tasks, write an implementation brief in `issues/` per `issues/README.md`.
- Distinguish verified facts from proposals and open questions. Do not present an unapproved recommendation as an accepted decision, and do not mark work complete that is not done.

## Handoff

When your session ends, leave a handoff using `templates/session-handoff-template.md`: what you actually changed, the repositories/branches/commits involved, test results, decisions made, outstanding issues, and the next recommended action.
