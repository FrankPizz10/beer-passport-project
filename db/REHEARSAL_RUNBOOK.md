# Rehearsal Runbook: R2 and R3 Exact Commands (for CTO approval)

**Approval gate: do not run any command in this runbook until Frank
approves this runbook. Every command runs against a disposable copy of
the local PostgreSQL instance inside a fresh private directory created
by that run. The real data directory is never started, and no
production system, database, or account is touched.**

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

## Step 0: start the disposable instance (fresh private directory)

Each run allocates its own private directory with `mktemp -d` and
copies the instance into it. PostgreSQL is configured to listen only
on its Unix socket inside that directory: `listen_addresses` is empty,
so the server opens no TCP port at all.

```sh
REHEARSAL_DIR="$(mktemp -d /tmp/bp-rehearsal.XXXXXXXX)"
cp -a ~/workspace/workstreams/db-recovery/pgdata "$REHEARSAL_DIR/pgdata"
cp -a ~/workspace/workstreams/db-recovery/pginstall "$REHEARSAL_DIR/pginstall"
chown -R 1000:1000 "$REHEARSAL_DIR" && chmod 700 "$REHEARSAL_DIR/pgdata"
setpriv --reuid 1000 --regid 1000 --clear-groups \
  env LD_LIBRARY_PATH="$REHEARSAL_DIR/pginstall/lib" HOME="$REHEARSAL_DIR" \
  "$REHEARSAL_DIR/pginstall/bin/pg_ctl" -D "$REHEARSAL_DIR/pgdata" \
  -l "$REHEARSAL_DIR/server.log" \
  -o "-k $REHEARSAL_DIR -c listen_addresses=''" start
export PSQL_BIN="$REHEARSAL_DIR/pginstall/bin/psql" \
  PGHOST="$REHEARSAL_DIR" PGUSER=postgres \
  LD_LIBRARY_PATH="$REHEARSAL_DIR/pginstall/lib"
```

The copy carries the `beerpassport_migtest` database with the schema
applied and the catalog loaded (step 2 load proof), which is the
rehearsal target.

## Step 1: verify the server and target database (read-only, mandatory)

Run this before any `migrate.py` invocation. The `--truncate-user-tables`
runs in steps 2 and 3 are forbidden until both checks pass.

```sh
"$PSQL_BIN" -d beerpassport_migtest -tAc \
  "SELECT current_database(), current_setting('data_directory')"
"$PSQL_BIN" -d beerpassport_migtest -tAc "SELECT count(*) FROM beers"
```

Expected, exactly:

- First query returns `beerpassport_migtest` and
  `$REHEARSAL_DIR/pgdata`: the connected server is the disposable copy
  in this run's private directory, and the target database is the
  rehearsal database. If either value differs, STOP. In particular, if
  the data directory is the real workstream `pgdata`, the wrong server
  answered and no further command may run.
- Second query returns `5894`: the catalog is present in the target
  database.

## Step 2 (R2): existing fixture, scoped

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

## Step 3 (R3): production-shape fixture, scoped to 294

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

## Step 4: teardown (scoped to this run's directory)

Teardown stops this run's server and removes only the directory this
run created. The guard refuses to remove anything that is not a
`/tmp/bp-rehearsal.*` directory from step 0.

```sh
setpriv --reuid 1000 --regid 1000 --clear-groups \
  env LD_LIBRARY_PATH="$REHEARSAL_DIR/pginstall/lib" HOME="$REHEARSAL_DIR" \
  "$REHEARSAL_DIR/pginstall/bin/pg_ctl" -D "$REHEARSAL_DIR/pgdata" stop
case "$REHEARSAL_DIR" in
  /tmp/bp-rehearsal.*) rm -rf "$REHEARSAL_DIR" ;;
  *) echo "REFUSING to remove unexpected path: $REHEARSAL_DIR" ;;
esac
```

## Stop conditions

Stop and report, without improvising, if: the step 1 verification
shows any value other than the expected database, this run's data
directory, or 5,894 catalog rows; the checksum verification fails; any
assertion above fails; the scope stage raises (an allowlisted UID with
no recovered profile); any validation check is non-zero; or the
instance copy fails to start. The rehearsal report (R4) records the
manifests either way.

Out of scope for this approval: the production load (step 5), any
Lightsail action (Frank and Codex), any Firebase change, and any use
of real recovered data. The rehearsal uses synthetic fixtures only.
