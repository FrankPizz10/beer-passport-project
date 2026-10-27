"""Catalog import: cleaned baseline CSVs -> PostgreSQL load files.

Reads the catalog baseline committed in experiments/catalog-discovery/data/
(the cleaned catalog, promoted to baseline 2026-10-27) and produces, in an
output directory:

- categories.csv, styles.csv, breweries.csv, beers.csv in PostgreSQL COPY
  CSV format (NULL written as \\N), columns in schema order.
- load.psql: an idempotent psql script that truncates, copies in foreign
  key dependency order, resets the id sequences to MAX(id), and prints
  verification counts.
- import_manifest.json: source checksums, row counts, transform stats.

Validation runs before anything is written and fails the run on any
problem: unexpected row counts (the frozen import source v1 numbers),
duplicate ids, dangling foreign keys, malformed values. The escape hatch
--skip-count-check exists for future baseline revisions; the run then
still validates everything else and reports the counts it found.

Run from the db/ directory:
    python -m src.catalog_import [--data-dir PATH] [--out-dir PATH]
"""
from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import io
import json
import os
import re
import sys
from dataclasses import dataclass, field

EXPECTED_COUNTS = {
    "beers": 5894,
    "breweries": 1339,
    "categories": 14,
    "styles": 147,
}

NULL = r"\N"
# 2147483647 is INT_MAX, the classic sentinel left behind by imports that
# had no real barcode (same constant as the cleanup module).
SENTINEL_UPCS = {"2147483647"}
# The shortest real barcode format relevant here is UPC-E (8 digits).
MIN_BARCODE_LEN = 8
ISO_Z = re.compile(r"^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})(?:\.\d+)?Z$")


class ImportDataError(Exception):
    """Raised for any validation problem in the source data."""


def load_parts(data_dir: str, stem: str) -> tuple[list[str], list[dict[str, str]]]:
    """Assemble a part-file set (header in part 01) or a single CSV."""
    parts = sorted(glob.glob(os.path.join(data_dir, f"{stem}.part*.csv")))
    if not parts:
        single = os.path.join(data_dir, f"{stem}.csv")
        if not os.path.exists(single):
            raise ImportDataError(f"no source files for {stem} in {data_dir}")
        parts = [single]
    text = ""
    for path in parts:
        with open(path, newline="", encoding="utf-8") as fh:
            text += fh.read()
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        raise ImportDataError(f"{stem}: no rows")
    header, data = rows[0], rows[1:]
    out = []
    for i, row in enumerate(data):
        if len(row) != len(header):
            raise ImportDataError(
                f"{stem} data row {i}: {len(row)} fields, header has {len(header)}")
        out.append(dict(zip(header, row)))
    return header, out


def sha256_of(data_dir: str, stem: str) -> dict[str, str]:
    digests = {}
    for path in sorted(glob.glob(os.path.join(data_dir, f"{stem}*"))):
        if path.endswith(".csv"):
            with open(path, "rb") as fh:
                digests[os.path.basename(path)] = hashlib.sha256(fh.read()).hexdigest()
    return digests


# --- transforms: each returns the COPY-ready value (NULL sentinel for None) ---

def t_int_id(value: str) -> str:
    if not value.isdigit():
        raise ImportDataError(f"bad integer id: {value!r}")
    return value


def t_fk(value: str) -> str:
    """Foreign key: source null conventions ('' or '0') become real NULL."""
    return NULL if value in ("", "0") else t_int_id(value)


def t_float(value: str) -> str:
    if value == "":
        return NULL
    try:
        float(value)
    except ValueError as exc:
        raise ImportDataError(f"bad float: {value!r}") from exc
    return value


def t_upc(value: str) -> str:
    """Barcodes are strings now (audit F-2); the dataset null (0/'') -> NULL.

    Anything else must look like a real barcode: the cleanup owns data
    cleaning, but a known sentinel or an implausibly short value means the
    source was not cleaned, and the import fails loudly instead of
    loading garbage (same rule as the cleanup module).
    """
    if value in ("", "0"):
        return NULL
    if value in SENTINEL_UPCS or not value.isdigit() or len(value) < MIN_BARCODE_LEN:
        raise ImportDataError(f"suspect upc in source data: {value!r}")
    return value


def t_bool_flag(value: str) -> str:
    if value == "1":
        return "true"
    if value == "0":
        return "false"
    raise ImportDataError(f"bad boolean flag: {value!r}")


def t_timestamp(value: str) -> str:
    """ISO-8601 Zulu export values -> naive timestamp preserving wall time."""
    if value == "":
        return NULL
    match = ISO_Z.match(value)
    if not match:
        raise ImportDataError(f"unrecognized timestamp: {value!r}")
    return f"{match.group(1)} {match.group(2)}"


def t_text(value: str) -> str:
    return value


def t_nullable_text(value: str) -> str:
    return NULL if value == "" else value


def t_add_user(value: str) -> str:
    """breweries.add_user: 0 meant 'unknown' (audit F-9) and imports as NULL."""
    return NULL if value in ("", "0") else t_int_id(value)


@dataclass
class TableResult:
    name: str
    rows: list[list[str]] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)


def check_unique_ids(table: str, rows: list[dict[str, str]]) -> set[str]:
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ImportDataError(f"{table}: duplicate ids present")
    return set(ids)


def build_tables(data_dir: str) -> tuple[dict[str, TableResult], dict[str, str]]:
    _, categories = load_parts(data_dir, "LiveCategories")
    _, styles = load_parts(data_dir, "LiveStyles")
    _, breweries = load_parts(data_dir, "LiveBreweries")
    _, beers = load_parts(data_dir, "LiveBeers")

    cat_ids = check_unique_ids("categories", categories)
    style_ids = check_unique_ids("styles", styles)
    brewery_ids = check_unique_ids("breweries", breweries)
    check_unique_ids("beers", beers)

    for s in styles:
        if s["cat_id"] not in ("", "0") and s["cat_id"] not in cat_ids:
            raise ImportDataError(f"styles {s['id']}: dangling cat_id {s['cat_id']}")
    for b in beers:
        for col, ids in (("brewery_id", brewery_ids), ("cat_id", cat_ids),
                         ("style_id", style_ids)):
            if b[col] not in ("", "0") and b[col] not in ids:
                raise ImportDataError(f"beers {b['id']}: dangling {col} {b[col]}")
        for col in ("name", "descript"):
            if b[col] == NULL:
                raise ImportDataError(f"beers {b['id']}: field {col} equals the NULL marker")

    tables: dict[str, TableResult] = {}

    t = TableResult("categories")
    for r in categories:
        t.rows.append([t_int_id(r["id"]), t_text(r["cat_name"]),
                       t_timestamp(r["last_mod"])])
    tables["categories"] = t

    t = TableResult("styles")
    for r in styles:
        t.rows.append([t_int_id(r["id"]), t_fk(r["cat_id"]),
                       t_text(r["style_name"]), t_timestamp(r["last_mod"])])
    tables["styles"] = t

    t = TableResult("breweries")
    for r in breweries:
        t.rows.append([t_int_id(r["id"]), t_text(r["name"]), t_text(r["address1"]),
                       t_text(r["address2"]), t_text(r["city"]), t_text(r["state"]),
                       t_text(r["code"]), t_text(r["country"]), t_text(r["phone"]),
                       t_text(r["website"]), t_text(r["descript"]),
                       t_add_user(r["add_user"]), t_timestamp(r["last_mod"])])
    t.stats["add_user_nulled"] = sum(1 for row in t.rows if row[11] == NULL)
    tables["breweries"] = t

    t = TableResult("beers")
    for r in beers:
        t.rows.append([t_int_id(r["id"]), t_fk(r["brewery_id"]), t_text(r["name"]),
                       t_fk(r["cat_id"]), t_fk(r["style_id"]), t_float(r["abv"]),
                       t_float(r["ibu"]), t_float(r["srm"]), t_upc(r["upc"]),
                       t_nullable_text(r["descript"]), t_bool_flag(r["discontinued"]),
                       t_timestamp(r["last_mod"])])
    t.stats["ibu_nulled"] = sum(1 for row in t.rows if row[6] == NULL)
    t.stats["descript_nulled"] = sum(1 for row in t.rows if row[9] == NULL)
    t.stats["discontinued_true"] = sum(1 for row in t.rows if row[10] == "true")
    tables["beers"] = t

    counts = {name: len(t.rows) for name, t in (
        ("categories", tables["categories"]), ("styles", tables["styles"]),
        ("breweries", tables["breweries"]), ("beers", tables["beers"]))}
    return tables, counts


COLUMNS = {
    "categories": "id, cat_name, last_mod",
    "styles": "id, cat_id, style_name, last_mod",
    "breweries": ("id, name, address1, address2, city, state, code, country, "
                  "phone, website, descript, add_user, last_mod"),
    "beers": ("id, brewery_id, name, cat_id, style_id, abv, ibu, srm, upc, "
              "descript, discontinued, last_mod"),
}
LOAD_ORDER = ["categories", "styles", "breweries", "beers"]


def write_outputs(tables: dict[str, TableResult], out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    for name in LOAD_ORDER:
        path = os.path.join(out_dir, f"{name}.csv")
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerows(tables[name].rows)
    lines = [
        "\\set ON_ERROR_STOP on",
        "-- Initial-load guard: this script wipes the catalog tables. If any",
        "-- user or enrichment data exists, that data must be loaded after,",
        "-- never before, a catalog (re)load. Refuse to run in that state.",
        "DO $$ BEGIN",
        "  IF EXISTS (SELECT 1 FROM users) OR EXISTS (SELECT 1 FROM user_beers)",
        "     OR EXISTS (SELECT 1 FROM user_badges)",
        "     OR EXISTS (SELECT 1 FROM collection_beers)",
        "     OR EXISTS (SELECT 1 FROM beverage_images) THEN",
        "    RAISE EXCEPTION 'user/enrichment data present: load.psql is for initial load only';",
        "  END IF;",
        "END $$;",
        "BEGIN;",
        ("TRUNCATE collection_beers, user_beers, user_badges, beverage_images, "
         "beers, breweries, styles, categories RESTART IDENTITY;"),
    ]
    for name in LOAD_ORDER:
        lines.append(
            f"\\copy {name} ({COLUMNS[name]}) FROM '{name}.csv' "
            f"WITH (FORMAT csv, NULL '\\N')")
    for name in LOAD_ORDER:
        lines.append(
            f"SELECT setval('{name}_id_seq', (SELECT MAX(id) FROM {name}));")
    lines.append("COMMIT;")
    for name in LOAD_ORDER:
        lines.append(f"SELECT '{name}' AS table_name, COUNT(*) AS rows FROM {name};")
    with open(os.path.join(out_dir, "load.psql"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    here = os.path.dirname(os.path.abspath(__file__))
    parser.add_argument("--data-dir", default=os.path.normpath(
        os.path.join(here, "..", "..", "experiments", "catalog-discovery", "data")))
    parser.add_argument("--out-dir", default=os.path.normpath(
        os.path.join(here, "..", "output")))
    parser.add_argument("--skip-count-check", action="store_true",
                        help="do not enforce the frozen v1 row counts")
    args = parser.parse_args(argv)

    try:
        tables, counts = build_tables(args.data_dir)
    except ImportDataError as exc:
        print(f"IMPORT ABORTED: {exc}", file=sys.stderr)
        return 1

    if not args.skip_count_check and counts != EXPECTED_COUNTS:
        print(f"IMPORT ABORTED: row counts {counts} != frozen v1 "
              f"{EXPECTED_COUNTS}", file=sys.stderr)
        return 1

    write_outputs(tables, args.out_dir)
    manifest = {
        "counts": counts,
        "expected_counts": EXPECTED_COUNTS,
        "count_check": "skipped" if args.skip_count_check else "passed",
        "stats": {name: t.stats for name, t in tables.items() if t.stats},
        "source_sha256": {
            stem: sha256_of(args.data_dir, stem)
            for stem in ("LiveBeers", "LiveBreweries", "LiveCategories", "LiveStyles")
        },
    }
    with open(os.path.join(args.out_dir, "import_manifest.json"), "w",
              encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"counts: {counts}")
    print(f"wrote load files to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
