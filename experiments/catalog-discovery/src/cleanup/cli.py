"""CLI for the old-catalog cleanup.

Implements docs/09-old-catalog-cleanup-strategy.md.

Examples (from experiments/catalog-discovery/):
    python -m src.cleanup.cli --mode report
    python -m src.cleanup.cli --mode apply

Report mode writes only cleanup/CLEANUP_REPORT.md and prints a
summary; it writes no CSVs. Apply mode additionally writes the
cleaned CSVs as numbered parts (header row in part 01 only, the
repo convention, so src/baseline.py's loader can read them back).
Neither mode ever modifies the baseline inputs.
"""
from __future__ import annotations

import argparse
import csv
import io
import logging
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .. import baseline as baseline_mod
from . import rules

log = logging.getLogger(__name__)

# Repo convention: split CSV output into parts of about 90 KB so no
# single pushed file approaches the push payload ceiling.
PART_LIMIT_BYTES = 90_000

BEER_FIELDS = ["id", "brewery_id", "name", "cat_id", "style_id",
               "abv", "ibu", "srm", "upc", "descript", "last_mod",
               "discontinued"]
BREWERY_FIELDS = ["id", "name", "address1", "address2", "city",
                  "state", "code", "country", "phone", "website",
                  "descript", "add_user", "last_mod"]


def _header_line(fieldnames: list[str]) -> str:
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerow(fieldnames)
    return buf.getvalue()


def _row_line(row: dict, fieldnames: list[str]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames,
                            extrasaction="ignore", lineterminator="\n")
    writer.writerow({k: row.get(k, "") for k in fieldnames})
    return buf.getvalue()


def write_parts(rows: list[dict], fieldnames: list[str], stem: str,
                out_dir: Path) -> list[Path]:
    """Write rows as <stem>.partNN.csv; header only in part 01."""
    out_dir.mkdir(parents=True, exist_ok=True)
    parts: list[Path] = []
    current: list[str] = [_header_line(fieldnames)]
    size = len(current[0].encode("utf-8"))
    part_no = 0

    def flush() -> None:
        nonlocal current, size, part_no
        part_no += 1
        path = out_dir / f"{stem}.part{part_no:02d}.csv"
        path.write_text("".join(current), encoding="utf-8")
        parts.append(path)
        current = []
        size = 0

    for row in rows:
        line = _row_line(row, fieldnames)
        line_size = len(line.encode("utf-8"))
        if current and size + line_size > PART_LIMIT_BYTES:
            flush()
        current.append(line)
        size += line_size
    if current:
        flush()
    return parts


def _cell(value: str) -> str:
    """Make a value safe for a Markdown table cell."""
    text = " ".join((value or "").split())
    text = text.replace("|", "/")
    return text[:80]


def build_report(result: rules.CleanupResult, mode: str,
                 problems: list[str], generated: str) -> str:
    change_counts = Counter(c.rule for c in result.changes)
    flag_counts = Counter(f.rule for f in result.flags)
    lines = [
        "# Old-Catalog Cleanup Report",
        "",
        f"Generated: {generated} (mode: {mode})",
        "",
        f"Input: {result.input_beer_count} beers, "
        f"{result.input_brewery_count} breweries",
        f"Output: {len(result.beers)} beers, "
        f"{len(result.breweries)} breweries",
        "",
        "## Rule counts",
        "",
        f"- R1 breweries dropped (zero beers): {change_counts.get('R1', 0)}",
        f"- R2 UPCs cleared to 0: {change_counts.get('R2', 0)}",
        f"- R2 UPCs flagged, unchanged: {flag_counts.get('R2', 0)}",
        f"- R3 discontinued markers normalized: {change_counts.get('R3', 0)}",
        f"- R4 duplicate groups flagged: {flag_counts.get('R4', 0)}",
        "",
        "## Changes",
        "",
        "| Rule | Entity | ID | Field | Before | After |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for c in result.changes:
        lines.append(
            f"| {c.rule} | {c.entity} | {c.row_id} | {c.field or '(row)'} "
            f"| {_cell(c.before)} | {_cell(c.after)} |")
    lines += ["", "## Report-only flags", ""]
    if result.flags:
        for f in result.flags:
            lines.append(f"- {f.rule} {f.entity} {f.row_id}: {f.detail}")
    else:
        lines.append("- None.")
    lines += ["", "## Reconciliation", ""]
    if problems:
        lines.append("FAILED:")
        for p in problems:
            lines.append(f"- {p}")
    else:
        lines.append("PASS: input rows = output rows + logged drops; "
                     "every change is listed above.")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Old-catalog cleanup v1 (docs/09).")
    parser.add_argument("--data-dir", type=Path, default=Path("data"),
                        help="Directory holding the baseline CSV parts.")
    parser.add_argument("--out-dir", type=Path, default=Path("cleanup"),
                        help="Where the report (and cleaned CSVs) go.")
    parser.add_argument("--mode", choices=["report", "apply"],
                        default="report",
                        help="report writes no CSVs; apply writes them.")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(message)s")

    base = baseline_mod.load_baseline(args.data_dir)
    result = rules.apply_cleanup(base.beers,
                                 list(base.breweries.values()))
    problems = rules.reconcile(result)

    change_counts = Counter(c.rule for c in result.changes)
    print(f"Input:  {result.input_beer_count} beers, "
          f"{result.input_brewery_count} breweries")
    print(f"Output: {len(result.beers)} beers, "
          f"{len(result.breweries)} breweries")
    print(f"R1 drops: {change_counts.get('R1', 0)}  "
          f"R2 clears: {change_counts.get('R2', 0)}  "
          f"R3 flags: {change_counts.get('R3', 0)}  "
          f"flags: {len(result.flags)}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    report = build_report(result, args.mode, problems, generated)
    report_path = args.out_dir / "CLEANUP_REPORT.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"Report: {report_path}")

    if problems:
        for p in problems:
            print(f"RECONCILIATION FAILED: {p}", file=sys.stderr)
        return 1

    if args.mode == "apply":
        beer_parts = write_parts(result.beers, BEER_FIELDS,
                                 "CleanedBeers", args.out_dir)
        brewery_parts = write_parts(result.breweries, BREWERY_FIELDS,
                                    "CleanedBreweries", args.out_dir)
        print(f"Wrote {len(beer_parts)} beer parts and "
              f"{len(brewery_parts)} brewery parts to {args.out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
