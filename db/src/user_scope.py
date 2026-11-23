"""Matched-profile scoping for the BeerPassport user-data migration.

Milestone 1 step 5 loads only the profiles that matched a Firebase Auth
account in the UID reconciliation (294 of 299 recovered users). The five
MySQL-only profiles stay in the verified backup; Firebase accounts are
never modified by the migration.

The production allowlist is exactly the 294 matched UIDs: the
intersection of the Firebase Auth UID set and the recovered users' UID
set. Every allowlisted UID must have a recovered profile; an allowlisted
UID with no recovered profile is a hard error, not a metric. The 15
Firebase-only accounts (in Firebase, with no recovered profile) are a
separate reconciliation metric recorded with the reconciliation results;
they are not part of the allowlist and never enter this stage.

This module is the scope stage that sits between the migration pipeline's
dump parser and its transform stage (the pipeline itself is unchanged):

    parsed = parse_dump(sql_text)                 # {table: [row, ...]}
    scoped, accounting = apply_matched_scope(parsed, matched_uids)
    clean, rejects, stats = transform_all(scoped, ...)

Rules
- users: kept iff the row's uid is in the matched set.
- user_beers, user_badges, notifications: excluded iff their user_id
  belongs to a known excluded user. Rows referencing a user_id that does
  not appear in the users table at all are KEPT: they are data errors for
  the transform stage's orphan checks, not scope exclusions, and must not
  be silently removed here.
- friends: excluded iff either endpoint belongs to a known excluded user
  (a pair survives only when both profiles migrate).
- collections, collection_beers: unscoped. They are shared badge
  definitions, not per-user data, and user_badges references them.
- Any other table in the parsed dump passes through untouched.

Accounting: per table, source == kept + excluded_unmatched, asserted.
Nothing is written anywhere by this module.
"""

USER_ID_TABLES = ("user_beers", "user_badges", "notifications")
UNSCOPED_TABLES = ("collections", "collection_beers")


def load_matched_uids(path):
    """Read a matched-UID allowlist: one UID per line.

    Blank lines and lines starting with # are ignored; surrounding
    whitespace is stripped; duplicates collapse into the returned set.
    The file is produced locally by the UID reconciliation and is never
    committed to git.
    """
    uids = set()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            value = line.strip()
            if value and not value.startswith("#"):
                uids.add(value)
    return uids


def apply_matched_scope(parsed, matched_uids):
    """Filter parsed dump rows to the matched profiles.

    parsed: {table: [row, ...]} with MySQL column names, as produced by
    the pipeline's dump parser (users rows carry "id" and "uid";
    dependent rows carry "user_id"; friends rows carry "user_1"/"user_2").
    matched_uids: set of UID strings from the reconciliation.

    Returns (scoped, accounting): scoped has the same shape as parsed;
    accounting maps each table to {"source", "kept", "excluded_unmatched"}
    and carries the top-level "allowlist_size".

    Raises ValueError if any allowlisted UID has no recovered profile:
    the production allowlist is exactly the matched set, so that count
    is required to be zero. The error reports the count only, never the
    UIDs themselves.
    """
    users = parsed.get("users", [])
    present_uids = {r.get("uid") for r in users}
    without_profile = set(matched_uids) - present_uids
    if without_profile:
        raise ValueError(
            f"allowlist contains {len(without_profile)} UID(s) with no "
            "recovered profile; the production allowlist is exactly the "
            "matched set (Firebase-only accounts are a separate "
            "reconciliation metric and must not be allowlisted)")
    kept_user_ids = {r["id"] for r in users if r.get("uid") in matched_uids}
    excluded_user_ids = {r["id"] for r in users
                         if r.get("uid") not in matched_uids}

    scoped = {}
    accounting = {}
    for table, rows in parsed.items():
        if table == "users":
            kept = [r for r in rows if r["id"] in kept_user_ids]
        elif table in USER_ID_TABLES:
            kept = [r for r in rows
                    if r.get("user_id") not in excluded_user_ids]
        elif table == "friends":
            kept = [r for r in rows
                    if r.get("user_1") not in excluded_user_ids
                    and r.get("user_2") not in excluded_user_ids]
        else:  # UNSCOPED_TABLES and anything else pass through untouched
            kept = list(rows)
        excluded = len(rows) - len(kept)
        assert len(rows) == len(kept) + excluded
        scoped[table] = kept
        accounting[table] = {
            "source": len(rows),
            "kept": len(kept),
            "excluded_unmatched": excluded,
        }
    accounting["allowlist_size"] = len(matched_uids)
    return scoped, accounting
