# Session Handoff: Old-Catalog Cleanup v1 (2026-10-21)

## Objective worked on

Build the approved old-catalog cleanup plan (Frank approved the plan
2026-10-21, after merging PR #5): a scripted, rule-based cleanup of
provable defects in the legacy catalog, on a new branch with a new PR,
with the strategy written down in a doc. Frank's explicit constraint:
do not run anything; he tests it himself and approves the PR.

Added later the same day at Frank's request: GitHub Actions CI for the
repo (lint, typecheck, build, unit tests), included in the same PR.

## Changes actually made

- `docs/09-old-catalog-cleanup-strategy.md`: the strategy. Rules,
  report-first flow, reconciliation requirement, out-of-scope list,
  and the spreadsheet write-back decision (deferred to Frank after he
  reviews a real cleanup report; recommendation recorded as write
  back with the original kept as backup).
- `src/cleanup/rules.py`: pure rule functions R1-R4 plus `reconcile()`.
  R1 drops breweries referenced by zero beers. R2 clears garbage UPCs
  (sentinel 2147483647, all-digit values shorter than 8) to the
  dataset null `0`, and flags other unexpected UPC formats without
  changing them. R3 strips `(discontinued)` markers from names into a
  new `discontinued` column. R4 flags duplicate (name, brewery_id)
  groups, never merges.
- `src/cleanup/cli.py`: `--mode report` (writes only
  `cleanup/CLEANUP_REPORT.md`) and `--mode apply` (also writes
  `CleanedBeers`/`CleanedBreweries` part files, ~90 KB parts, header
  in part 01 only). Inputs are never modified.
- `tests/test_cleanup.py`: 15 unit tests over synthetic rows.
- README documentation list now links docs 07, 08, and 09 (07 and 08
  were added by PR #5 but never linked).
- CI, added 2026-10-21 at Frank's request:
  `.github/workflows/catalog-discovery-ci.yml` at the repo root runs
  ruff, mypy, a byte-compile build check, and the unit tests on pull
  requests into main and on pushes to main, path-filtered to the
  experiment and the workflow file, plus manual dispatch. Tool
  settings are in the experiment's `pyproject.toml` and the tools are
  pinned in `requirements-dev.txt` (ruff 0.17.1, mypy 2.4.0). The
  README gained a Continuous integration section.
- Minimal source fixes so CI starts green on real checks rather than
  suppressed ones: 5 unused imports removed (enrichment.py, main.py,
  images/cli.py), 3 annotation-only fixes (stats dicts in the two
  source adapters, Counter in images/cli.py). No behavior changes.
  The one exception is recorded in `pyproject.toml`: mypy
  `ignore_errors` for `src.main` only, covering 3 pre-existing errors
  (a Path | None dataset argument and a seen_source_ids inference
  conflict with src.state). That is logged type debt; new modules get
  no override.

## Repositories, branches, and commits involved

- Repo: FrankPizz10/beer-passport-project (hub only; no app repos
  touched).
- Branch: `experiment/old-catalog-cleanup`, off main at `243db8d`
  (the PR #5 merge).
- Content commit: `28c2ee3`. PR:
  https://github.com/FrankPizz10/beer-passport-project/pull/6

## Tests and results

Initially none, per Frank's instruction ("Dont run anything until i
test myself and approve the pr"). Later on 2026-10-21 Frank authorized
running the unit tests, and Jarvis ran them (the cleanup script itself
has still never been run):

- `python -m unittest tests.test_cleanup -v`: 15 tests, all pass.
- `python -m unittest discover -s tests`: 101 tests, all pass
  (86 pre-existing plus the 15 new). Note: the sandbox's system
  Python lacks the project dependencies (PEP 668), so the suite was
  run in a venv built from `requirements.txt`. The first attempt
  without it produced 9 import errors, all `rapidfuzz` missing in
  pre-existing modules; none were in the cleanup code.

CI verification, run locally in the venv before pushing (same
commands the workflow runs): ruff check, all checks passed; mypy src,
no issues in 26 source files; compileall, OK; full unit suite, 101
tests OK; the workflow YAML parses. The first live GitHub Actions run
triggers on the PR itself when the CI commit lands.

The report-mode command, for Frank to run from
`experiments/catalog-discovery/`:

    python -m src.cleanup.cli --mode report

Expected counts on the current baseline (from the 2026-10-21 audit):
R1 drops 92, R2 clears 6, R3 normalizes 27, R4 flags 1 group.

## Decisions made

- Spreadsheets are not edited by this work. Cleaned output lands in
  the repo as new part files plus a generated report.
- Cleared UPCs become `0`, matching the baseline's own null
  convention, rather than empty strings.
- The `discontinued` column exists only in cleaned output; the
  baseline schema is unchanged.

## Outstanding issues and risks

- The cleanup script itself has never been run against the real
  baseline (unit tests only, all passing). A defect found when Frank
  runs report mode comes back as a fix commit on this branch before
  merge.
- Open owner decisions unchanged and not blocking: mocktails,
  kombucha, and the bottled-spirits boundary (docs/01).
- The AWS relaunch design (Lightsail core, about $8/mo) is a proposal
  saved to Frank's Drive, not yet approved or built.

## Next recommended action

Frank runs the tests and report mode locally, reviews
`cleanup/CLEANUP_REPORT.md` against the audit counts, and approves or
comments on PR #6. After merge, run apply mode in a follow-up session
and bring the cleaned output and report back for the write-back
decision.
