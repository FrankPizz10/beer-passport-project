"""Generate a SYNTHETIC MySQL user-tables dump for pipeline testing.

This fixture is not real user data. It mimics the shape of the
beerpassport-user-tables.sql dump the EFS recovery guide (Phase H2)
will produce, using MySQL-era column sets (notably: users has no
created_at / updated_at, which the PostgreSQL port added as F-11).
Beer IDs reference real baseline catalog IDs so foreign keys can be
validated against the loaded catalog. Edge cases are deliberate and
enumerated in the header of the generated file and in the expected
outcomes asserted by tests/test_migration.py.

Usage: python3 make_fixture.py [output_dir]
Writes fixture_user_tables.sql and fixture_user_tables.sql.sha256.
"""

import hashlib
import os
import random
import sys

BEER_IDS = list(range(1, 61)) + list(range(2000, 2010)) + [3914, 3951, 4271]

MOJIBAKE_NAME = "MÃ¼nchen Fan"  # double-encoded "München Fan"
MOJIBAKE_COLLECTION = "BrÃ¤uhaus Classics"  # double-encoded "Bräuhaus Classics"
MOJIBAKE_MESSAGE = "Anna earned the BrÃ¤uhaus badge"  # double-encoded


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
    tuples = ",\n".join("(" + ",".join(esc(v) for v in row) + ")" for row in rows)
    return f"INSERT INTO `{table}` ({','.join('`' + c + '`' for c in cols)}) VALUES\n{tuples};\n"


def build_rows():
    rng = random.Random(20261121)
    rows = {}

    # ---- users: 120 regular + 6 edge rows ------------------------------
    users = []
    for i in range(1, 121):
        users.append(
            (
                i,
                f"synthetic{i:019d}",
                f"token-{i}" if i % 3 else None,
                rng.choice([21, 25, 30, 34, 41, 55]),
                f"user{i}@example.invalid",
                f"synthetic_user_{i}",
                1 if i % 7 == 0 else 0,
            )
        )
    users += [
        (121, "syntheticNullAge0000000000001"[:28], None, None, "nullage@example.invalid", "null_age_user", 0),  # reject: missing_age
        (122, "", None, 30, "emptyuid@example.invalid", "empty_uid_user", 0),  # reject: missing_uid
        (123, "syntheticDupEmail000000000001"[:28], None, 28, "user5@example.invalid", "dup_email_user", 0),  # reject: duplicate_email
        (124, "syntheticDupName0000000000001"[:28], None, 28, "dupname@example.invalid", "synthetic_user_7", 0),  # reject: duplicate_user_name
        (125, "syntheticMojibake000000000001"[:28], None, 33, "mojibake@example.invalid", MOJIBAKE_NAME, 0),  # loads, name repaired
        (126, "syntheticDupToken000000000001"[:28], "token-1", 29, "duptoken@example.invalid", "dup_token_user", 0),  # reject: duplicate_notification_token
    ]
    rows["users"] = users

    # ---- collections: 12 regular + 2 edge rows --------------------------
    collections = []
    for i in range(1, 13):
        collections.append(
            (
                i,
                f"Synthetic Collection {i}",
                rng.choice([1, 2, 3, 4, 5]),
                f"Synthetic badge set {i}",
                "2023-10-01 10:00:00",
                "2024-01-15 10:00:00",
            )
        )
    collections += [
        (13, "Synthetic Collection 3", 2, "Duplicate name row", "2023-10-02 10:00:00", "2024-01-16 10:00:00"),  # reject: duplicate_name
        (14, MOJIBAKE_COLLECTION, 3, "Mojibake name row", "2023-10-03 10:00:00", "2024-01-17 10:00:00"),  # loads, repaired
    ]
    rows["collections"] = collections

    # ---- collection_beers ------------------------------------------------
    cb = []
    cb_id = 1
    used = set()
    for coll in range(1, 13):
        for beer in rng.sample(BEER_IDS, 12):
            if (coll, beer) in used:
                continue
            used.add((coll, beer))
            cb.append((cb_id, coll, beer, "2023-10-05 09:00:00", "2023-10-05 09:00:00"))
            cb_id += 1
    # exact duplicates of the first two rows (dedupe)
    cb.append((cb_id, cb[0][1], cb[0][2], "2023-10-06 09:00:00", "2023-10-06 09:00:00"))
    cb_id += 1
    cb.append((cb_id, cb[1][1], cb[1][2], "2023-10-06 09:00:00", "2023-10-06 09:00:00"))
    cb_id += 1
    # orphans
    cb.append((cb_id, 999, BEER_IDS[0], "2023-10-07 09:00:00", "2023-10-07 09:00:00"))  # orphan collection
    cb_id += 1
    cb.append((cb_id, 1, 999999, "2023-10-07 09:00:00", "2023-10-07 09:00:00"))  # orphan beer
    cb_id += 1
    # beer in the duplicate-name collection 13 (orphan after that collection is rejected)
    cb.append((cb_id, 13, BEER_IDS[1], "2023-10-08 09:00:00", "2023-10-08 09:00:00"))
    cb_id += 1
    rows["collection_beers"] = cb

    # ---- user_beers -------------------------------------------------------
    ub = []
    ub_id = 1
    used = set()
    while len(ub) < 280:
        user = rng.randint(1, 120)
        beer = rng.choice(BEER_IDS)
        if (user, beer) in used:
            continue
        used.add((user, beer))
        ub.append(
            (
                ub_id,
                user,
                beer,
                1 if rng.random() < 0.4 else 0,
                "2024-02-01 12:00:00",
                "2024-03-01 12:00:00",
            )
        )
        ub_id += 1
    # duplicates of an early row: one newer (wins), one older (loses)
    first = ub[0]
    ub.append((ub_id, first[1], first[2], 1, "2024-02-02 12:00:00", "2024-06-01 12:00:00"))
    ub_id += 1
    ub.append((ub_id, first[1], first[2], 0, "2024-02-03 12:00:00", "2024-01-01 12:00:00"))
    ub_id += 1
    # null timestamps (nullable in PostgreSQL: loads)
    ub.append((ub_id, 3, BEER_IDS[5], 0, None, None))
    ub_id += 1
    # zero-date updated_at (becomes NULL: loads)
    ub.append((ub_id, 4, BEER_IDS[6], 1, "2024-02-10 12:00:00", "0000-00-00 00:00:00"))
    ub_id += 1
    # orphans
    ub.append((ub_id, 9999, BEER_IDS[0], 0, "2024-02-11 12:00:00", "2024-02-11 12:00:00"))  # orphan user
    ub_id += 1
    ub.append((ub_id, 5, 999999, 0, "2024-02-11 12:00:00", "2024-02-11 12:00:00"))  # orphan beer
    ub_id += 1
    # row for the rejected null-age user 121 (orphan after user rejection)
    ub.append((ub_id, 121, BEER_IDS[2], 0, "2024-02-12 12:00:00", "2024-02-12 12:00:00"))
    ub_id += 1
    rows["user_beers"] = ub

    # ---- friends ------------------------------------------------------------
    fr = []
    fr_id = 1
    pairs = set()
    while len(fr) < 100:
        a, b = rng.randint(1, 120), rng.randint(1, 120)
        if a == b or (min(a, b), max(a, b)) in pairs:
            continue
        pairs.add((min(a, b), max(a, b)))
        # store half the pairs in reversed order, as the old app could
        fr.append((fr_id, a, b, "2024-01-20 08:00:00", "2024-01-20 08:00:00") if fr_id % 2 else (fr_id, b, a, "2024-01-20 08:00:00", "2024-01-20 08:00:00"))
        fr_id += 1
    # both-orders duplicates of the first 8 pairs (dedupe after normalization)
    for row in list(fr[:8]):
        fr.append((fr_id, row[2], row[1], "2024-01-21 08:00:00", "2024-01-21 08:00:00"))
        fr_id += 1
    fr.append((fr_id, 42, 42, "2024-01-22 08:00:00", "2024-01-22 08:00:00"))  # reject: self pair
    fr_id += 1
    fr.append((fr_id, 7, 9999, "2024-01-22 08:00:00", "2024-01-22 08:00:00"))  # reject: orphan user
    fr_id += 1
    rows["friends"] = fr

    # ---- user_badges ---------------------------------------------------------
    bd = []
    bd_id = 1
    used = set()
    while len(bd) < 130:
        user = rng.randint(1, 120)
        coll = rng.randint(1, 12)
        if (user, coll) in used:
            continue
        used.add((user, coll))
        progress = round(rng.uniform(0, 1), 3)
        bd.append((bd_id, user, coll, 1 if progress >= 1 else 0, progress, "2024-03-05 07:00:00", "2024-04-05 07:00:00"))
        bd_id += 1
    # duplicate pair with higher progress (wins) and one with lower (loses)
    first = bd[0]
    bd.append((bd_id, first[1], first[2], 1, 1.0, "2024-03-06 07:00:00", "2024-05-05 07:00:00"))
    bd_id += 1
    bd.append((bd_id, first[1], first[2], 0, 0.1, "2024-03-07 07:00:00", "2024-04-06 07:00:00"))
    bd_id += 1
    # null progress (coerced to 0)
    bd.append((bd_id, 9, 2, 0, None, "2024-03-08 07:00:00", "2024-04-08 07:00:00"))
    bd_id += 1
    # orphans
    bd.append((bd_id, 9999, 1, 0, 0.5, "2024-03-09 07:00:00", "2024-04-09 07:00:00"))
    bd_id += 1
    bd.append((bd_id, 10, 999, 0, 0.5, "2024-03-09 07:00:00", "2024-04-09 07:00:00"))
    bd_id += 1
    rows["user_badges"] = bd

    # ---- notifications ---------------------------------------------------------
    nt = []
    for i in range(1, 66):
        user = rng.randint(1, 120)
        ntype = "NEW_FRIEND" if i % 3 else "BADGE_EARNED"
        nt.append((i, user, ntype, f"Synthetic notification {i} for user {user}", "2024-05-01 06:00:00", "2024-05-01 06:00:00", 1 if i % 4 == 0 else 0))
    nt_id = 66
    # duplicate (user_id, message) of row 1 (dedupe)
    nt.append((nt_id, nt[0][1], nt[0][2], nt[0][3], "2024-05-02 06:00:00", "2024-05-02 06:00:00", 0))
    nt_id += 1
    # unknown type (reject)
    nt.append((nt_id, 11, "PROMO_BLAST", "Synthetic promo notification", "2024-05-03 06:00:00", "2024-05-03 06:00:00", 0))
    nt_id += 1
    # orphan user (reject)
    nt.append((nt_id, 9999, "NEW_FRIEND", "Synthetic orphan notification", "2024-05-03 06:00:00", "2024-05-03 06:00:00", 0))
    nt_id += 1
    # mojibake message (loads, repaired)
    nt.append((nt_id, 12, "BADGE_EARNED", MOJIBAKE_MESSAGE, "2024-05-04 06:00:00", "2024-05-04 06:00:00", 0))
    nt_id += 1
    rows["notifications"] = nt

    return rows


COLUMNS = {
    "users": ["id", "uid", "notification_token", "age", "email", "user_name", "private"],
    "collections": ["id", "name", "difficulty", "description", "created_at", "updated_at"],
    "collection_beers": ["id", "collection_id", "beer_id", "created_at", "updated_at"],
    "user_beers": ["id", "user_id", "beer_id", "liked", "created_at", "updated_at"],
    "friends": ["id", "user_1", "user_2", "created_at", "updated_at"],
    "user_badges": ["id", "user_id", "collection_id", "earned", "progress", "created_at", "updated_at"],
    "notifications": ["id", "user_id", "type", "message", "created_at", "updated_at", "viewed"],
}

ORDER = ["users", "collections", "collection_beers", "user_beers", "friends", "user_badges", "notifications"]


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixture")
    os.makedirs(out_dir, exist_ok=True)
    rows = build_rows()
    header = (
        "-- SYNTHETIC FIXTURE. NOT REAL USER DATA.\n"
        "-- Mimics the mysqldump user-tables file from the EFS recovery guide, Phase H2.\n"
        "-- Generated by make_fixture.py (seeded, deterministic).\n"
        "-- MySQL dump 10.13  Distrib 8.0.36, for Linux (x86_64)\n"
        "--\n"
        "-- Host: localhost    Database: beerpassport_synthetic\n"
        "-- ------------------------------------------------------\n"
        "-- Server version\t8.0.36\n\n"
        "/*!40101 SET NAMES utf8mb4 */;\n\n"
    )
    body = "".join(insert(t, COLUMNS[t], rows[t]) + "\n" for t in ORDER)
    path = os.path.join(out_dir, "fixture_user_tables.sql")
    with open(path, "w", encoding="utf-8") as f:
        f.write(header + body)
    digest = hashlib.sha256(open(path, "rb").read()).hexdigest()
    with open(path + ".sha256", "w") as f:
        f.write(f"{digest}  fixture_user_tables.sql\n")
    counts = {t: len(rows[t]) for t in ORDER}
    print("fixture rows:", counts, "total:", sum(counts.values()))
    print("sha256:", digest)
    print("wrote:", path)


if __name__ == "__main__":
    main()
