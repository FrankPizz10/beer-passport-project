# Production Preflight: Step 5 User-Data Load (294 Matched Profiles)

**Gate: no production transfer or write until Frank approves the
execution of this preflight. Every check in sections 1 to 4 is
read-only. Section 5 is the load itself and needs its own explicit
go-ahead after the checks pass.**

Scope: load the recovered MySQL user data for exactly the 294 matched
profiles (the Firebase and recovered MySQL intersection from the
completed UID reconciliation: 309 Firebase accounts, 299 recovered
users, 294 matched, 15 Firebase-only left as they are, 5 MySQL-only
preserved in the verified backup) into the Lightsail PostgreSQL,
where the frozen catalog baseline is already loaded and verified.
The pipeline is the packaged revision in `user-migration/`; the
rehearsal evidence is `REHEARSAL_REPORT_2026-11-23.md`.

## 0. The export (isolated recovery instance, read-only against MySQL)

The step 5 input is a dedicated seven-table export taken from the
isolated recovery instance, NOT the verified full archive. The full
archive stays untouched and remains the recovery source of truth;
the export is a derived file with its own checksum.

```sh
mysqldump --single-transaction --complete-insert \
  beersdb users collections user_beers friends collection_beers \
  user_badges notifications \
  > beerpassport-user-tables.sql
sha256sum beerpassport-user-tables.sql > beerpassport-user-tables.sql.sha256
```

- `--complete-insert` writes explicit column lists on every INSERT,
  which is the format the pipeline parser is rehearsed against.
- Exactly the seven user tables are exported. Catalog tables are
  never part of this file; the baseline is already loaded on the box.
- The export runs only on the isolated recovery instance (MySQL
  3306 is never published). The dump and its checksum move to the box
  by the same approved route as the allowlist (section 3), with
  permissions 600.

## 1. Target identity (read-only, on the box)

Run against the production database before anything is transferred:

```sql
SELECT current_database(), current_setting('data_directory');
SELECT (SELECT count(*) FROM beers) AS beers,
       (SELECT count(*) FROM breweries) AS breweries,
       (SELECT count(*) FROM users) AS users;
```

Expected: the production database on the Lightsail instance; beers
5,894 and breweries 1,339 (the frozen baseline); users 0 (no user
data loaded yet). Any other values: STOP.

## 2. Dump integrity (read-only, wherever the dump is staged)

- The user-tables dump's SHA-256 equals the checksum recorded when
  the section 0 export was taken. A mismatch is a hard stop; do not
  re-export silently.
- The dump parses (the pipeline verifies the checksum before parsing)
  and contains only the seven user tables: users, collections,
  user_beers, friends, collection_beers, user_badges, notifications.
- Parsed source counts are recorded before the load; the users count
  must be 299.

## 3. Allowlist integrity (the 294)

- The production allowlist file has exactly 294 lines, one UID per
  line, no duplicates, no blank lines.
- Transfer route: the allowlist moves from Frank's Mac to the box by
  a route Frank approves for this execution. Never email, never Git,
  never chat. File permissions 600 on the box; delete the staging
  copy after the load manifest is verified.
- The pipeline's scope stage hard-fails if any allowlisted UID has no
  recovered profile, so zero allowlisted-without-profile is enforced
  at load time; a failure there is a stop, not a retry with edits.

## 4. Pre-load safeguards

- Take a pg_dump of the seven (empty) user tables plus a full
  database snapshot or Lightsail snapshot before the load. The load
  itself commits only after its in-transaction integrity gate
  passes, so a failed load commits nothing; rolling back a committed
  load is a separate approved action against the user tables only.
  The catalog tables are never truncated by this procedure.
- Data handling note: the pipeline drops legacy push
  (notification) tokens before validation. The recovered tokens are
  stale and are not carried into production; devices re-register on
  sign-in. This also guarantees a shared or recycled token can never
  exclude a matched profile.
- Confirm the pinned pipeline revision on the box is the merged
  revision of the packaging PR (record the commit SHA in the run
  notes), and that `tests/` passes there in its non-database mode.
- Confirm the run environment: PSQL_BIN, PGHOST, PGPORT, PGUSER set
  for the box's PostgreSQL (the rehearsal's PGPORT lesson applies:
  set the port explicitly, never rely on a default).

## 5. Dry run, then the load (separately approved)

First the dry run, which parses, scopes, and transforms the real
export and reports aggregate counts and rejects in the manifest,
writing nothing to PostgreSQL:

```sh
python3 migrate.py \
  --dump <user-tables dump> \
  --sha256 <recorded checksum file> \
  --database <production database> \
  --out runs/production-step5-dryrun \
  --matched-uids <allowlist file> \
  --expect-users 294 \
  --dry-run
```

Expected dry-run outcome: users loaded exactly 294, excluded_unmatched
exactly 5, and every reject itemized. Any reject of a matched profile
is a stop: resolve it before the load, never by editing the export.

Then the load itself, with the same inputs:

```sh
python3 migrate.py \
  --dump <user-tables dump> \
  --sha256 <recorded checksum file> \
  --database <production database> \
  --out runs/production-step5 \
  --matched-uids <allowlist file> \
  --require-empty \
  --expect-users 294
```

The initial production load never truncates: `--require-empty`
refuses to run unless all seven target user tables are empty, and
the flag cannot be combined with `--truncate-user-tables`. Inside
the single load transaction, an integrity gate re-runs the nine
orphan and order checks plus the exact 294-user count; the
transaction commits only if every check passes, and a failure rolls
back completely.

## 6. Post-load verification (all must hold)

- Manifest accounting closes per table:
  source = loaded + rejected + deduped + excluded_unmatched.
- users: source 299, excluded_unmatched exactly 5 (the MySQL-only
  profiles), allowlist_size exactly 294.
- All nine validation checks zero (no orphaned user_beers, friends,
  collection_beers, user_badges, or notifications; no uniqueness
  violations).
- Every database count equals the manifest's loaded count.
- Spot checks: three known beers from the pilot contract (90 Minute
  IPA, Boston Lager, Sierra Nevada Pale Ale) resolve with their
  preserved IDs, and the discovery API health check passes against
  the loaded database.

Any failure: stop, keep the manifest and rejects files, and roll
back from the section 4 safeguard rather than patching data in
place.

## 7. Sign-off

- Preflight checks 1 to 4 recorded by: ______  Date: ______
- Frank's approval to execute section 5: ______  Date: ______
- Post-load verification recorded by: ______  Date: ______
