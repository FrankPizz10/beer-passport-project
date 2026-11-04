# 003: User data continuity, not a restart

- **Date:** 2026-10-27
- **Status:** accepted

## Context

The app is still listed in the App Store with installs in the field, and its backend has been down long enough that every open shows an "unable to reach server" screen. The user data lives in two places: Firebase Authentication (accounts; each server profile row stores the Firebase uid) and the dormant MySQL on EFS (users, user_beers, user_badges, friends, and the collections/collection_beers definitions, which exist nowhere else; Frank's spreadsheets hold only the catalog).

Verified 2026-10-27 in the Firebase console (project beerpassport-b31d8, Blaze): 309 Auth accounts, all email/password, created 2023-09-11 to 2026-02-20. Firestore holds only a 4-document users collection (a side store). The app gates on server reachability before sign-up is reachable (Frank), so Auth accounts are expected to map one-to-one to server profile rows; the recovery step still diffs the UID sets to prove it.

## Options considered

- **Continuity:** recover the EFS database read-only (temporary EC2 in the VPC mounts EFS, matching MySQL, full dump), transform and load the user tables into Postgres with IDs preserved, keep the Firebase project as the identity provider.
- **Full restart to v2:** catalog only; every user starts empty; collection definitions must be recreated from scratch.

## Decision

Continuity. The EFS volume and the Firebase project are frozen (no deletion, teardown, or modification) until the migrated data is verified on the Lightsail box.

## Rationale

Asymmetric cost. Continuity costs one bounded recovery session plus a few more tables through the import path that already exists for the catalog. Restart permanently destroys the one asset that cannot be recreated (users' personal beer logs, badge progress, friend graph) and the collection definitions, and turns the relaunch moment for returning users into data loss.

## Consequences and affected repositories

- Catalog and user IDs are load-bearing: the import preserves source IDs as primary keys, verified in the Milestone 1 step 2 load proof.
- The recovery spike is Milestone 1 step 3; user tables load with the catalog at step 5.
- Agreed fallback trigger: if the EFS data directory is unrecoverable after a clean InnoDB recovery attempt, or the Firebase inventory had shown only test accounts, Jarvis presents the evidence and the plan switches to catalog-only restart. The catalog path is identical either way.
