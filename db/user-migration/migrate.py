"""MySQL user-tables dump -> PostgreSQL migration.

Consumes the user-tables mysqldump produced by the EFS recovery guide
(Phase H2) plus its SHA-256 (Phase H3), and loads users, collections,
user_beers, friends, collection_beers, user_badges, and notifications
into a PostgreSQL database that already has the Prisma schema applied
and the catalog loaded (user_beers and collection_beers reference beers).

Usage:
    python3 migrate.py --dump beerpassport-user-tables.sql \
        --sha256 beerpassport-user-tables.sql.sha256 \
        --database beerpassport_migtest --out runs/2026-11-21-fixture \
        [--truncate-user-tables]

Connection comes from PGHOST / PGPORT / PGUSER / PSQL_BIN environment
variables (defaults target the db-recovery workstream's local instance).
The load refuses to touch a target whose user tables are non-empty
unless --truncate-user-tables is passed. Rejected and deduplicated rows
are written to rejects.json / rejects.csv in the output directory and
summarized in manifest.json; nothing is silently dropped.
"""

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dump_parser import parse_dump
from transform import USER_TABLES, transform_all
from user_scope import apply_matched_scope, load_matched_uids

LOAD_ORDER = [
    "users",
    "collections",
    "user_beers",
    "friends",
    "collection_beers",
    "user_badges",
    "notifications",
]

COLUMNS = {
    "users": ["id", "uid", "notification_token", "age", "email", "user_name", "private", "created_at", "updated_at"],
    "collections": ["id", "name", "difficulty", "description", "created_at", "updated_at"],
    "user_beers": ["id", "user_id", "beer_id", "liked", "created_at", "updated_at"],
    "friends": ["id", "user_1", "user_2", "created_at", "updated_at"],
    "collection_beers": ["id", "collection_id", "beer_id", "created_at", "updated_at"],
    "user_badges": ["id", "user_id", "collection_id", "earned", "progress", "created_at", "updated_at"],
    "notifications": ["id", "user_id", "type", "message", "created_at", "updated_at", "viewed"],
}


def psql(database, args, input_text=None, capture=True):
    bin_path = os.environ.get("PSQL_BIN", "psql")
    cmd = [
        bin_path,
        "-h", os.environ.get("PGHOST", "127.0.0.1"),
        "-p", os.environ.get("PGPORT", "54329"),
        "-U", os.environ.get("PGUSER", "postgres"),
        "-d", database,
        "-v", "ON_ERROR_STOP=1",
    ] + args
    result = subprocess.run(cmd, input=input_text, capture_output=capture, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"psql failed: {result.stderr.strip()[:500]}")
    return result.stdout


def query_scalar(database, sql):
    out = psql(database, ["-tAc", sql])
    return out.strip()


def verify_checksum(dump_path, sha_path):
    digest = hashlib.sha256()
    with open(dump_path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if sha_path:
        expected = None
        with open(sha_path) as f:
            for line in f:
                parts = line.split()
                if parts and os.path.basename(dump_path) in line:
                    expected = parts[0].strip().lower()
                    break
                if parts and len(parts[0]) == 64 and expected is None:
                    expected = parts[0].strip().lower()
        if expected is None:
            raise RuntimeError(f"no checksum entry for {dump_path} in {sha_path}")
        if expected != actual:
            raise RuntimeError(f"SHA-256 mismatch: expected {expected}, got {actual}")
    return actual


def _copy_escape(value):
    if value is None:
        return "\\N"
    if isinstance(value, bool):
        return "t" if value else "f"
    if isinstance(value, (int, float)):
        return repr(value)
    text = str(value)
    return (
        text.replace("\\", "\\\\")
        .replace("\t", "\\t")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def write_copy_files(clean, out_dir):
    paths = {}
    for table in LOAD_ORDER:
        path = os.path.join(out_dir, f"{table}.copy")
        with open(path, "w", encoding="utf-8") as f:
            for row in clean[table]:
                f.write("\t".join(_copy_escape(row[col]) for col in COLUMNS[table]) + "\n")
        paths[table] = path
    return paths


def load(database, clean, out_dir, truncate):
    counts = {t: int(query_scalar(database, f"SELECT count(*) FROM {t}")) for t in USER_TABLES}
    nonempty = {t: c for t, c in counts.items() if c > 0}
    if nonempty and not truncate:
        raise RuntimeError(f"target user tables are not empty: {nonempty}; pass --truncate-user-tables to reload")
    paths = write_copy_files(clean, out_dir)
    script = ["BEGIN;"]
    if nonempty:
        script.append(
            "TRUNCATE users, collections, user_beers, friends, collection_beers, user_badges, notifications RESTART IDENTITY CASCADE;"
        )
    for table in LOAD_ORDER:
        cols = ", ".join(COLUMNS[table])
        script.append(f"\\copy {table} ({cols}) FROM '{paths[table]}'")
    for table in LOAD_ORDER:
        script.append(
            f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE((SELECT max(id) FROM {table}), 1), true);"
        )
    script.append("COMMIT;")
    psql(database, ["-q"], input_text="\n".join(script))


def validate(database):
    checks = {}
    for table in USER_TABLES:
        checks[f"count_{table}"] = int(query_scalar(database, f"SELECT count(*) FROM {table}"))
    orphan_queries = {
        "user_beers_orphan_users": "SELECT count(*) FROM user_beers ub LEFT JOIN users u ON ub.user_id = u.id WHERE u.id IS NULL",
        "user_beers_orphan_beers": "SELECT count(*) FROM user_beers ub LEFT JOIN beers b ON ub.beer_id = b.id WHERE b.id IS NULL",
        "friends_orphan_users": "SELECT count(*) FROM friends f WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = f.user_1) OR NOT EXISTS (SELECT 1 FROM users u WHERE u.id = f.user_2)",
        "friends_order_violations": "SELECT count(*) FROM friends WHERE user_1 >= user_2",
        "collection_beers_orphan_collections": "SELECT count(*) FROM collection_beers cb LEFT JOIN collections c ON cb.collection_id = c.id WHERE c.id IS NULL",
        "collection_beers_orphan_beers": "SELECT count(*) FROM collection_beers cb LEFT JOIN beers b ON cb.beer_id = b.id WHERE b.id IS NULL",
        "user_badges_orphan_users": "SELECT count(*) FROM user_badges ub LEFT JOIN users u ON ub.user_id = u.id WHERE u.id IS NULL",
        "user_badges_orphan_collections": "SELECT count(*) FROM user_badges ub LEFT JOIN collections c ON ub.collection_id = c.id WHERE c.id IS NULL",
        "notifications_orphan_users": "SELECT count(*) FROM notifications n LEFT JOIN users u ON n.user_id = u.id WHERE u.id IS NULL",
    }
    for name, sql in orphan_queries.items():
        checks[name] = int(query_scalar(database, sql))
    checks["all_orphan_checks_zero"] = all(v == 0 for k, v in checks.items() if "orphan" in k or "violations" in k)
    return checks


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dump", required=True)
    ap.add_argument("--sha256", default=None)
    ap.add_argument("--database", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--truncate-user-tables", action="store_true")
    ap.add_argument("--matched-uids", default=None, help="path to a matched-UID allowlist file; when given, the import is scoped to matched profiles (step 5 rehearsal)")
    ap.add_argument("--run-ts", default=None, help="fill timestamp for NOT NULL columns, default: now (UTC)")
    args = ap.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    run_ts = args.run_ts or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    digest = verify_checksum(args.dump, args.sha256)
    with open(args.dump, encoding="utf-8", errors="replace") as f:
        parsed = parse_dump(f.read())
    source_counts = {t: len(parsed.get(t, [])) for t in USER_TABLES}

    beer_ids = {
        int(x)
        for x in query_scalar(args.database, "SELECT string_agg(id::text, ',') FROM beers").split(",")
        if x
    }
    if not beer_ids:
        raise RuntimeError("target database has no beers loaded; load the catalog first")

    scope_accounting = None
    if args.matched_uids:
        matched_uids = load_matched_uids(args.matched_uids)
        parsed, scope_accounting = apply_matched_scope(parsed, matched_uids)

    clean, rejects, stats = transform_all(parsed, valid_beer_ids=beer_ids, run_ts=run_ts)
    load(args.database, clean, args.out, args.truncate_user_tables)
    checks = validate(args.database)

    reject_dicts = [r.as_dict() for r in rejects]
    with open(os.path.join(args.out, "rejects.json"), "w", encoding="utf-8") as f:
        json.dump(reject_dicts, f, indent=2, ensure_ascii=False)
    with open(os.path.join(args.out, "rejects.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["table", "source_id", "category", "reason", "detail"])
        writer.writeheader()
        writer.writerows(reject_dicts)

    per_table = {}
    for table in USER_TABLES:
        table_rejects = [r for r in rejects if r.table == table]
        per_table[table] = {
            "source_rows": source_counts[table],
            "loaded": len(clean[table]),
            "rejected": sum(1 for r in table_rejects if r.category == "reject"),
            "deduped": sum(1 for r in table_rejects if r.category == "dedupe"),
            "db_count_after_load": checks[f"count_{table}"],
            "transform_stats": stats[table],
            "excluded_unmatched": (scope_accounting[table]["excluded_unmatched"] if scope_accounting else 0),
        }
    manifest = {
        "run_ts": run_ts,
        "dump_file": os.path.basename(args.dump),
        "dump_sha256": digest,
        "checksum_verified": bool(args.sha256),
        "target_database": args.database,
        "per_table": per_table,
        "scope": ({"allowlist_size": scope_accounting["allowlist_size"]} if scope_accounting else None),
        "validation": checks,
        "total_source_rows": sum(source_counts.values()),
        "total_loaded": sum(len(clean[t]) for t in USER_TABLES),
        "total_rejected": sum(1 for r in rejects if r.category == "reject"),
        "total_deduped": sum(1 for r in rejects if r.category == "dedupe"),
    }
    with open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(json.dumps({k: manifest[k] for k in ("total_source_rows", "total_loaded", "total_rejected", "total_deduped")}, indent=2))
    print(f"manifest: {os.path.join(args.out, 'manifest.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
