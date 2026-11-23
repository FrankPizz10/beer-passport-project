# Session Handoff: Milestone 1 Step 3, EFS MySQL Recovery (2026-11-22)

## Objective worked on

Execute Milestone 1 step 3 of the approved deployment proposal: recover the dormant MySQL data directory from the frozen EFS volume in isolation, and prove the recovered data is intact with an isolated test restore before any production load is considered.

## Changes actually made

- The MySQL data directory was copied off the original volume in isolation (the original data was not modified) and opened with a matching MySQL server version against the copy only.
- An isolated test restore was performed and fully verified (results below).
- This hub documentation was updated to record the outcome: `CURRENT_STATE.md` (this PR) and this handoff. No recovered records, dumps, infrastructure identifiers, or local paths were committed anywhere.

## Repositories, branches, and commits involved

- `beer-passport-project` (this hub): docs-only PR recording the step 3 result (branch and commit per the PR).
- No code repositories changed. The recovery ran against isolated infrastructure and a local copy; nothing was deployed and no production data was touched.

## Tests and results

Isolated test restore verification (one-off verification, run locally during the recovery session, not a CI suite):

- Tables restored: 14 of 14.
- Row counts: exact match against the recovered source for every table; 10,016 rows total.
- CHECK TABLE: passed for all 14 tables.
- Foreign-key integrity: all 13 foreign-key checks found zero orphaned rows.
- Result: PASS. The recovered dataset is internally consistent and complete as far as these checks establish.

Firebase Auth UID reconciliation (completed 2026-11-22, after the restore): performed by SHA-256 fingerprint comparison of the two UID sets; no raw UIDs were recorded in chat, logs, or git.

- Firebase Auth accounts: 309.
- Recovered MySQL users: 299 (uid required and unique in the recovered schema).
- Matched profiles: 294.
- Firebase-only accounts: 15 (no recovered profile; the accounts are left exactly as they are).
- MySQL-only profiles: 5 (no Firebase account; CTO decision: they stay in the verified backup and are excluded from the step 5 load scope).

The accounting closes exactly (294 + 15 = 309; 294 + 5 = 299).

## Decisions made

- None new. The result is consistent with TD-11 (user data continuity, decisions/003): the recovered data is intact, so the fallback trigger in decisions/003 was not met and no fallback path is being taken.

## Outstanding issues and risks

- Milestone 1 step 4 (Lightsail box setup, done together with Frank) has not been provisioned; the setup package is prepared and provisioning awaits Frank's go-ahead.
- The production database load has not been approved or performed; it remains a separate gated step under the approved deployment proposal. Its scope is set: the catalog plus the 294 matched profiles, source IDs preserved.
- The recovered MySQL system ran with credentials that were exposed in the 2026-11-21 incident (closed); recovered data must be loaded with fresh credentials, and legacy passwords must never be reused.

## Next recommended action

Proceed to Milestone 1 step 4 (box setup together) once Frank authorizes provisioning, and prepare the step 5 load and validation plan scoped to the 294 matched profiles for Frank's approval.
