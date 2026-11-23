"""Generate a PRODUCTION-SHAPE synthetic user-tables dump for the
Milestone 1 step 5 rehearsal (R3).

Shape mirrors the verified reconciliation exactly: 299 users, of whom
294 are matched (their UIDs are in the allowlist) and 5 are MySQL-only
(excluded by the scope stage). Every row is otherwise valid, so the
expected rehearsal outcome is deterministic: zero rejects, zero dedupes,
and per-table excluded counts driven only by scoping. All identifiers
are synthetic. Beer IDs reference real baseline catalog IDs.

Usage: python3 make_fixture_matched.py [output_dir]
Writes matched_user_tables.sql, matched_user_tables.sql.sha256,
matched_allowlist.txt (the 294 matched UIDs), and
matched_expected.json (the expected scope accounting).
"""

import hashlib
import json
import os
import sys

BEER_IDS = list(range(1, 61)) + [3914, 3951, 4271]
TS = "2026-01-15 12:00:00"

MATCHED = 294
TOTAL_USERS = 299


def esc(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return repr(value)
    text = str(value).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{text}'"


def insert(table, cols, rows):
    tuples = ",\n".join(
        "(" + ",".join(esc(v) for v in row) + ")" for row in rows)
    return (f"INSERT INTO `{table}` "
            f"({','.join('`' + c + '`' for c in cols)}) VALUES\n{tuples};\n")


def uid_for(i):
    return f"matched{i:022d}" if i <= MATCHED else f"mysqlonly{i:018d}"


def build():
    users, user_beers, user_badges, notifications, friends = [], [], [], [], []
    ub_id = ubg_id = n_id = f_id = 0
    for i in range(1, TOTAL_USERS + 1):
        users.append((i, uid_for(i), f"token-{i}", 20 + (i % 40),
                      f"user{i}@example.invalid", f"matched_user_{i}",
                      1 if i % 7 == 0 else 0))
        beers = 3 if i <= MATCHED else 2
        for k in range(beers):
            ub_id += 1
            user_beers.append((ub_id, i, BEER_IDS[(i + k) % len(BEER_IDS)],
                               1 if k == 0 else 0, TS, TS))
        badges = 2 if i <= MATCHED else 1
        for k in range(badges):
            ubg_id += 1
            user_badges.append((ubg_id, i, 1 + ((i + k) % 6), 1, 100, TS, TS))
        n_id += 1
        notifications.append((n_id, i, "NEW_FRIEND",
                              f"User {i} has a new friend", TS, TS, 0))
    for i in range(1, MATCHED, 2):  # (1,2), (3,4), ..., (293,294)
        f_id += 1
        friends.append((f_id, i, i + 1, TS, TS))
    f_id += 1
    friends.append((f_id, 1, 295, TS, TS))       # one endpoint MySQL-only
    f_id += 1
    friends.append((f_id, 295, 296, TS, TS))     # both endpoints MySQL-only

    collections = [(i, f"Synthetic Collection {i}", 1 + (i % 5),
                    f"Synthetic badge set {i}", TS, TS) for i in range(1, 7)]
    collection_beers = []
    cb_id = 0
    for c in range(1, 7):
        for k in range(5):
            cb_id += 1
            collection_beers.append(
                (cb_id, c, BEER_IDS[(c * 7 + k) % len(BEER_IDS)], TS, TS))

    rows = {
        "users": users, "collections": collections,
        "user_beers": user_beers, "friends": friends,
        "collection_beers": collection_beers, "user_badges": user_badges,
        "notifications": notifications,
    }
    cols = {
        "users": ["id", "uid", "notification_token", "age", "email",
                  "user_name", "private"],
        "collections": ["id", "name", "difficulty", "description",
                        "created_at", "updated_at"],
        "user_beers": ["id", "user_id", "beer_id", "liked",
                       "created_at", "updated_at"],
        "friends": ["id", "user_1", "user_2", "created_at", "updated_at"],
        "collection_beers": ["id", "collection_id", "beer_id",
                             "created_at", "updated_at"],
        "user_badges": ["id", "user_id", "collection_id", "earned",
                        "progress", "created_at", "updated_at"],
        "notifications": ["id", "user_id", "type", "message",
                          "created_at", "updated_at", "viewed"],
    }
    expected = {
        "users": {"source": 299, "kept": 294, "excluded_unmatched": 5},
        "user_beers": {"source": 892, "kept": 882, "excluded_unmatched": 10},
        "user_badges": {"source": 593, "kept": 588, "excluded_unmatched": 5},
        "notifications": {"source": 299, "kept": 294, "excluded_unmatched": 5},
        "friends": {"source": 149, "kept": 147, "excluded_unmatched": 2},
        "collections": {"source": 6, "kept": 6, "excluded_unmatched": 0},
        "collection_beers": {"source": 30, "kept": 30, "excluded_unmatched": 0},
        "allowlist_size": 294,
    }
    return rows, cols, expected


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "fixture-matched"
    os.makedirs(out_dir, exist_ok=True)
    rows, cols, expected = build()
    header = ("-- SYNTHETIC production-shape fixture for the step 5 "
              "rehearsal. Not real user data.\n"
              "-- 299 users (294 matched, 5 MySQL-only), all rows valid; "
              "expected outcome is scope exclusions only.\n")
    sql = header + "\n".join(
        insert(t, cols[t], rows[t]) for t in
        ["users", "collections", "user_beers", "friends",
         "collection_beers", "user_badges", "notifications"])
    dump_path = os.path.join(out_dir, "matched_user_tables.sql")
    with open(dump_path, "w", encoding="utf-8") as f:
        f.write(sql)
    digest = hashlib.sha256(sql.encode("utf-8")).hexdigest()
    with open(dump_path + ".sha256", "w", encoding="utf-8") as f:
        f.write(f"{digest}  matched_user_tables.sql\n")
    with open(os.path.join(out_dir, "matched_allowlist.txt"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(uid_for(i) for i in range(1, MATCHED + 1)) + "\n")
    with open(os.path.join(out_dir, "matched_expected.json"), "w",
              encoding="utf-8") as f:
        json.dump(expected, f, indent=2)
    print(f"wrote {dump_path} (sha256 {digest[:12]}...), allowlist "
          f"({MATCHED} uids), expected accounting")


if __name__ == "__main__":
    main()
