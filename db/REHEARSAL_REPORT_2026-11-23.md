# Migration Rehearsal Report: R2 and R3 (2026-11-23)

Rehearsal of the Milestone 1 step 5 user-data import, executed under
the runbook in `REHEARSAL_RUNBOOK.md` as approved in PR #14 at commit
2ddad98. Synthetic fixtures only. The run used a disposable copy of
the local PostgreSQL instance in a fresh `mktemp -d` directory,
listening only on its Unix socket; the real data directory was never
started, and teardown removed only that run's directory.

## Preflight (runbook step 1): PASS

- Connected database: `beerpassport_migtest`
- Server data directory: the run's own copy
  (`/tmp/bp-rehearsal.<random>/pgdata`), not the real workstream
  `pgdata`
- Catalog rows in `beers`: 5,894

## Incident during the run (no data written)

The first R2 attempt failed immediately: the pipeline reads its port
from the PGPORT environment variable and defaults to the workstream
instance's 54329, while the rehearsal server, started without an
explicit port, created its socket with the 5432 suffix. The failure
occurred at the pipeline's read-only catalog query, before any load or
truncate, so nothing was written. The runbook's environment block now
sets PGPORT=5432 explicitly (PR #14 updated), and the rerun passed.

## R2: existing 890-row fixture, scoped to a 100-UID synthetic allowlist

Manifest assertions all PASS: allowlist size 100; users source 126,
loaded 100, excluded_unmatched 26 (every deliberate edge-case user
fell outside the allowlist, so their would-be rejects never reached
the transform stage); the accounting invariant
source = loaded + rejected + deduped + excluded_unmatched held for
every table; every database count equaled the loaded count; all
validation checks zero.

| Table | Source | Loaded | Rejected | Deduped | Excluded |
|---|---:|---:|---:|---:|---:|
| users | 126 | 100 | 0 | 0 | 26 |
| collections | 14 | 13 | 1 | 0 | 0 |
| user_beers | 287 | 225 | 2 | 2 | 58 |
| friends | 110 | 76 | 2 | 6 | 26 |
| collection_beers | 149 | 144 | 3 | 2 | 0 |
| user_badges | 135 | 112 | 2 | 2 | 19 |
| notifications | 69 | 56 | 2 | 1 | 10 |

The remaining rejects and dedupes are the fixture's deliberate
in-scope edge cases among dependents of kept users (for example rows
referencing a rejected collection), which is the designed behavior.

## R3: production-shape fixture, scoped to the 294 matched profiles

Exact expected results, all PASS: rejected 0 and deduped 0 in every
table, allowlist size 294, every database count equal to the loaded
count, all nine validation checks zero.

| Table | Source | Loaded | Excluded |
|---|---:|---:|---:|
| users | 299 | 294 | 5 |
| user_beers | 892 | 882 | 10 |
| user_badges | 593 | 588 | 5 |
| notifications | 299 | 294 | 5 |
| friends | 149 | 147 | 2 |
| collections | 6 | 6 | 0 |
| collection_beers | 30 | 30 | 0 |

## Evidence

Run manifests stay in the local workstream per git hygiene
(`db-recovery/migration/runs/`), recorded here by SHA-256:

- R2 manifest: `ccd8335e0baa27e80d7f97f891eff0e291968cb80c7edbf95b4e7f1754433a6a`
- R3 manifest: `acd9e1d69fba3cc972badc4e604ebd381485174a3d3fa647279cefce5b55afce`
- R3 fixture dump: `314d57e4f3d8b55231334b9dc9fce2870ac2ae10a3d9bcf8542cbf2997d0646f`

## Conclusion

The pipeline and the matched-profile scope stage are verified end to
end against the production shape: the 294 matched profiles and their
dependent records load cleanly, the 5 unmatched profiles and their
dependents are excluded by scope (never rejected), and referential
integrity holds with zero orphans. This completes rehearsal step R4.
The step 5 production load remains separately gated: it needs the
box (step 4, Frank and Codex), the real dumps, the production
allowlist transfer route, and Frank's explicit approval.
