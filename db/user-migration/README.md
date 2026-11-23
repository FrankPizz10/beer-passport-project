# user-migration/: the rehearsed MySQL to PostgreSQL user-data pipeline

This package is the migration pipeline that carries the recovered
MySQL user data into PostgreSQL for Milestone 1 step 5, packaged as a
reviewable Git revision. It is the exact code that passed the R2/R3
rehearsal on 2026-11-23 (`../REHEARSAL_REPORT_2026-11-23.md`), run
under the commands in `../REHEARSAL_RUNBOOK.md`.

## Contents

- `dump_parser.py`: parser for the mysqldump user-tables format.
- `transform.py`: row transforms and validation (friend pairs
  normalized to user_1 < user_2, conservative mojibake repair, zero
  dates to NULL, uniqueness and orphan pre-checks, reject accounting).
- `user_scope.py`: the matched-profile scope stage. VENDORED copy of
  `../src/user_scope.py` (the canonical copy, PR #12) so this package
  runs standalone on the box; `tests/test_vendored_scope.py` fails if
  the two copies ever drift.
- `migrate.py`: the CLI. Verifies the dump SHA-256 before parsing,
  applies the scope stage when `--matched-uids <file>` is given, loads
  in a single transaction, resets sequences, runs the nine post-load
  validation checks, and writes a manifest whose accounting closes:
  source = loaded + rejected + deduped + excluded_unmatched.
  Production modes: `--dry-run` reports aggregate counts and rejects
  without writing to PostgreSQL; `--require-empty` refuses a
  non-empty target (and forbids `--truncate-user-tables`);
  `--expect-users N` asserts the exact profile count after transform
  and again inside the load transaction, whose integrity gate must
  pass before commit.
- Legacy push tokens: `transform.py` drops `notification_token`
  values before validation (stale tokens; devices re-register on
  sign-in), so a token collision can never exclude a matched profile.
  Dropped tokens are counted in the manifest's transform stats.
- `make_fixture.py`, `make_fixture_matched.py`: synthetic fixture
  generators (the 890-row edge-case fixture and the production-shape
  299-user / 294-matched fixture). All identifiers in both are
  invented.
- `tests/`: the pipeline test suite. The database end-to-end tests
  skip when no disposable PostgreSQL instance is reachable.

## What is deliberately NOT in Git

The real recovered dump, the production UID allowlist, UID
fingerprints, and all generated outputs (fixture dumps, run
manifests, rejects files) stay out of Git, always. Generated outputs
land in `fixture/`, `fixture-matched/`, and `runs/` inside this
directory and are gitignored. The production allowlist reaches the
box only by the transfer route in `../PRODUCTION_PREFLIGHT.md`.

## Commands

Rehearsal: `../REHEARSAL_RUNBOOK.md` (exact commands, approved and
executed 2026-11-23). Production: `../PRODUCTION_PREFLIGHT.md` gates
the step 5 load; no production transfer or write happens without
Frank's approval of that preflight.
