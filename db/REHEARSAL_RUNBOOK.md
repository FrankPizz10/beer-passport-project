# Rehearsal Runbook: R2 and R3 Exact Commands (for CTO approval)

**Approval gate: do not run any command in this runbook until Frank
approves this runbook. Every command runs against a disposable copy of
the local PostgreSQL instance. The real data directory is never
started, and no production system, database, or account is touched.**

This runbook executes steps R2 and R3 of `MIGRATION_REHEARSAL_PLAN.md`
(the plan and the scope stage are PR #12). Preparation already done
locally, with no database touched:

- The pipeline CLI (`migrate.py` in the local db-recovery workstream)
  accepts `--matched-uids <file>` and applies the scope stage between
  parsing and transform; the manifest records `excluded_unmatched` per
  table and the allowlist size.
- A production-shape fixture generator (`make_fixture_matched.py`)
  produces a 299-user synthetic dump, the 294-UID synthetic allowlist,
  and the expected accounting.
- A synthetic allowlist for R2 (the first 100 regular fixture UIDs) is
  prepared at `fixture/fixture_allowlist.txt` in the workstream.
- Pure-Python verification, run 2026-11-22: the pipeline suite passes
  22 tests (4 database end-to-end tests skip while the instance is
  stopped; those are exactly what R2 and R3 execute). The new matched
  fixture tests prove, in memory, that scoping the production-shape
  fixture yields the expected accounting and a clean transform (zero
  rejects), and that the same fixture unscoped transforms all 299
  users.

## Step 0: start the disposable instance (copy only)

```sh
rm -rf /tmp/pgtest && mkdir -p /tmp/pgtest
cp -a ~/workspace/workstreams/db-recovery/pgdata /tmp/pgtest/pgdata
cp -a ~/workspace/workstreams/db-recovery/pginstall /tmp/pgtest/pginstall
chown -R 1000:1000 /tmp/pgtest && chmod 700 /tmp/pgtest/pgdata
setpriv --reuid 1000 --regid 1000 --clear-groups \
  env LD_LIBRARY_PATH=/tmp/pgtest/pginstall/lib HOME=/tmp/pgtest \
  /tmp/pgtest/pginstall/bin/pg_ctl -D /tmp/pgtest/pgdata \
  -l /tmp/pgtest/server.log -o '-p 54329 -k /tmp/pgtest' start
export PSQL_BIN=/tmp/pgtest/pginstall/bin/psql \
  PGHOST=/tmp/pgtest PGPORT=54329 PGUSER=postgres \
  LD_LIBRARY_PATH=/tmp/pgtest/pginstall/lib
```

The copy carries the `beerpassport_migtest` database with the schema
applied and the catalog loaded (step 2 load proof), which is the
rehearsal target.

## Step 1 (R2): existing fixture, scoped

```sh
cd ~/workspace/workstreams/db-recovery/migration
python3 migrate.py \
  --dump fixture/fixture_user_tables.sql \
  --sha256 fixture/fixture_user_tables.sql.sha256 \
  --database beerpassport_migtest \
  --out runs/r2-scoped \
  --truncate-user-tables \
  --matched-uids fixture/fixture_allowlist.txt
```

Assertions on `runs/r2-scoped/manifest.json`:

- `scope.allowlist_size` is 100.
- users: source 126, `excluded_unmatched` 26 (users 101 to 126 fall
  outside the allowlist, including every deliberate edge-case user, so
  their would-be rejects never reach the transform stage).
- Per table: source = loaded + rejected + deduped + excluded_unmatched.
- `validation.all_orphan_checks_zero` is true and every database count
  equals the manifest's loaded count.

## Step 2 (R3): production-shape fixture, scoped to 294

```sh
cd ~/workspace/workstreams/db-recovery/migration
python3 make_fixture_matched.py fixture-matched
python3 migrate.py \
  --dump fixture-matched/matched_user_tables.sql \
  --sha256 fixture-matched/matched_user_tables.sql.sha256 \
  --database beerpassport_migtest \
  --out runs/r3-matched \
  --truncate-user-tables \
  --matched-uids fixture-matched/matched_allowlist.txt
```

Expected result, exact (the fixture is valid by construction, so the
only outcomes are loads and scope exclusions):

| Table | Source | Loaded | Excluded |
|---|---:|---:|---:|
| users | 299 | 294 | 5 |
| user_beers | 892 | 882 | 10 |
| user_badges | 593 | 588 | 5 |
| notifications | 299 | 294 | 5 |
| friends | 149 | 147 | 2 |
| collections | 6 | 6 | 0 |
| collection_beers | 30 | 30 | 0 |

Plus: rejected 0 and deduped 0 in every table,
`scope.allowlist_size` 294, all nine validation checks zero, and every
database count equal to the loaded count.

## Step 3: teardown

```sh
setpriv --reuid 1000 --regid 1000 --clear-groups \
  env LD_LIBRARY_PATH=/tmp/pgtest/pginstall/lib HOME=/tmp/pgtest \
  /tmp/pgtest/pginstall/bin/pg_ctl -D /tmp/pgtest/pgdata stop
rm -rf /tmp/pgtest
```

## Stop conditions

Stop and report, without improvising, if: the checksum verification
fails; any assertion above fails; the scope stage raises (an
allowlisted UID with no recovered profile); any validation check is
non-zero; or the instance copy fails to start. The rehearsal report
(R4) records the manifests either way.

Out of scope for this approval: the production load (step 5), any
Lightsail action (Frank and Codex), any Firebase change, and any use
of real recovered data. The rehearsal uses synthetic fixtures only.
