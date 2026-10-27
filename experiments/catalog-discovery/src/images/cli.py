"""CLI for the image-sourcing experiment.

Reads beverage records from a CSV, finds image candidates via the
configured sources (Stage 2: Open Food Facts only), evaluates product
identity and rights independently, and writes structured outputs.

Example:
    python -m src.images.cli --input pilot/curated_useful_additions.csv
    python -m src.images.cli --input pilot/curated_useful_additions.csv --limit 5

Never modifies discovery state or production data. Records image URLs
and metadata only; no image binaries are downloaded.
"""
from __future__ import annotations

import argparse
import csv
import logging
import sys
from collections import Counter
from pathlib import Path

from ..config import Config
from ..sources.base import CachedClient
from . import export as export_mod
from . import match as match_mod
from . import off_images
from . import review as review_mod
from . import rights as rights_mod
from .models import ImageCandidate

log = logging.getLogger(__name__)

# Maps known input CSV column names to beverage record fields.
COLUMN_ALIASES = {
    "candidate_id": "beverage_id",
    "product_name": "beverage_name",
}


def read_beverages(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    beverages = []
    for row in rows:
        bev = {}
        for k, v in row.items():
            bev[COLUMN_ALIASES.get(k, k)] = (v or "").strip()
        if not bev.get("beverage_id"):
            bev["beverage_id"] = bev.get("barcode") or bev.get("beverage_name")
        beverages.append(bev)
    return beverages


def process_beverage(beverage: dict, client: CachedClient,
                     refresh: bool = False) -> tuple[list[ImageCandidate], dict]:
    """Run one beverage through sources, matching, rights, and review."""
    stats = {"source_errors": 0, "no_candidate": 0}
    all_candidates: list[ImageCandidate] = []

    candidates, product, error = off_images.find_candidates(
        beverage, client, refresh=refresh)
    if error is not None:
        stats["source_errors"] += 1
        log.warning("Source failure for %s; not counted as zero coverage",
                    beverage.get("beverage_id"))
        # A source failure is not a fallback: we cannot say there is no image.
        return [], stats

    for cand in candidates:
        if product is not None:
            match_mod.apply_match(cand, beverage, product)
        rights_mod.classify_rights(cand)
        review_mod.decide(cand)
        all_candidates.append(cand)

    if not all_candidates:
        stats["no_candidate"] += 1
        all_candidates.append(review_mod.fallback_record(beverage))
    return all_candidates, stats


def run(cfg: Config, input_path: Path, output_dir: Path,
        limit: int | None = None, refresh: bool = False) -> dict:
    beverages = read_beverages(input_path)
    if limit is not None:
        beverages = beverages[:limit]
    client = CachedClient(cfg.cache_dir / "images", delay=cfg.off_delay,
                          timeout=cfg.request_timeout,
                          max_retries=cfg.max_retries)

    candidates: list[ImageCandidate] = []
    totals: Counter[str] = Counter()
    for bev in beverages:
        cands, stats = process_beverage(bev, client, refresh=refresh)
        candidates.extend(cands)
        totals["source_errors"] += stats["source_errors"]
        totals["no_candidate"] += stats["no_candidate"]
        for c in cands:
            totals[f"approval:{c.approval_status}"] += 1
            totals[f"match:{c.match_confidence}"] += 1
            totals[f"rights:{c.rights_status}"] += 1

    summary = {
        "input": str(input_path),
        "beverages": len(beverages),
        "candidates": len(candidates),
        "totals": dict(totals),
    }
    paths = export_mod.export_all(output_dir, candidates, summary)
    summary["outputs"] = paths
    return summary


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(description="BeerPassport image-sourcing experiment")
    p.add_argument("--input", type=Path, required=True,
                   help="CSV of beverage records (e.g. pilot/curated_useful_additions.csv)")
    p.add_argument("--output-dir", type=Path, default=None,
                   help="Output directory (default: <experiment>/output/images)")
    p.add_argument("--limit", type=int, default=None,
                   help="Process at most N beverages (for test runs)")
    p.add_argument("--refresh", action="store_true",
                   help="Ignore cached API responses and refetch")
    args = p.parse_args(argv)

    cfg = Config()
    output_dir = args.output_dir or (Path(__file__).resolve().parent.parent
                                     / "output" / "images")
    if not args.input.exists():
        print(f"Input not found: {args.input}")
        return 1
    summary = run(cfg, args.input, output_dir, limit=args.limit,
                  refresh=args.refresh)
    print(f"\nBeverages: {summary['beverages']}, "
          f"candidates: {summary['candidates']}")
    for k in sorted(summary["totals"]):
        print(f"  {k}: {summary['totals'][k]}")
    print("Outputs:")
    for name, path in summary["outputs"].items():
        print(f"  {name}: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
