"""Orchestration for the catalog discovery prototype.

Run order:
  1. Load baseline CSVs and build the match index.
  2. Load persisted discovery state.
  3. Fetch each source (graceful partial failure: one source failing does not
     stop the others).
  4. Normalize records, match against the baseline, merge into state.
  5. Export candidates, source records, producers, review queue, run summary.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from rapidfuzz import fuzz

from . import baseline as baseline_mod
from . import export as export_mod
from . import match as match_mod
from . import state as state_mod
from .config import Config, parse_args
from .match import Candidate, make_candidate_id, missing_fields_for
from .normalize import normalize_barcode, normalize_name, parse_abv
from .sources import openbrewerydb as obdb
from .sources import openfoodfacts as off
from .sources import brewery_dataset
from .sources.base import CachedClient, SourceError

log = logging.getLogger("catalog_discovery")

# Distinct beverage categories for the summary (normalized).
CATEGORY_HINTS = ["beer", "cider", "seltzer", "hard iced tea", "malt beverage"]


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        datefmt="%H:%M:%S")


def confirm(prompt: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    answer = input(f"{prompt} [y/N] ").strip().lower()
    return answer in ("y", "yes")


def run(cfg: Config) -> dict:
    cfg.cache_dir.mkdir(parents=True, exist_ok=True)
    cfg.state_dir.mkdir(parents=True, exist_ok=True)

    base = baseline_mod.load_baseline(cfg.data_dir)
    index = match_mod.build_baseline_index(base.beers, base)
    state = state_mod.load_state(cfg.state_dir)

    summary: dict = {
        "baseline_files": {k: v for k, v in base.row_counts.items()},
        "sources": {},
        "errors": [],
        "warnings": [],
    }

    # ---- Source B: Open Brewery DB (producers) ----
    producers: list[dict] = []
    obdb_stats: dict = {}
    try:
        if cfg.brewery_source == "dataset":
            raw_breweries = brewery_dataset.load_snapshot(
                cfg.brewery_dataset, limit=cfg.limit)
            obdb_stats = {"source": "dataset",
                          "snapshot": brewery_dataset.SNAPSHOT["commit_short"],
                          "snapshot_rows": brewery_dataset.SNAPSHOT["rows"]}
            producers = [match_producer(brewery_dataset.to_producer_record(r), base)
                         for r in raw_breweries]
        else:
            client = CachedClient(cfg.cache_dir / "openbrewerydb",
                                  delay=cfg.obdb_delay,
                                  timeout=cfg.request_timeout,
                                  max_retries=cfg.max_retries)
            raw_breweries, obdb_stats = obdb.fetch_breweries(cfg, client)
            producers = [match_producer(obdb.to_producer_record(r), base)
                         for r in raw_breweries]
    except (SourceError, FileNotFoundError, ValueError) as e:
        summary["errors"].append(f"openbrewerydb: {e}")
        log.error("Open Brewery DB unavailable: %s", e)
    summary["sources"]["openbrewerydb"] = {
        "raw_records": len(producers),
        "producer_candidates": len(producers),
        **obdb_stats,
    }

    # ---- Source C: Open Food Facts (packaged products) ----
    products: list[dict] = []
    off_stats: dict = {}
    try:
        client = CachedClient(cfg.cache_dir / "openfoodfacts",
                              delay=cfg.off_delay,
                              timeout=cfg.request_timeout,
                              max_retries=cfg.max_retries)
        products, off_stats = off.fetch_products(cfg, client)
    except SourceError as e:
        summary["errors"].append(f"openfoodfacts: {e}")
        log.error("Open Food Facts unavailable: %s", e)
    summary["sources"]["openfoodfacts"] = {
        "raw_records": len(products),
        **off_stats,
    }

    # ---- Normalize + match product records ----
    source_records: list[dict] = []
    new_this_run = 0
    updated_this_run = 0
    repeated_this_run = 0
    # Snapshot of previously seen record ids. A record counts as repeated
    # when its id was seen in a previous run OR earlier in this run.
    seen_at_start = {src: set(ids)
                     for src, ids in state.seen_source_ids.items()}
    seen_this_run: dict[str, set[str]] = {}
    now = state_mod.utcnow()
    for rec in products:
        rec["producer_name"] = rec.get("brand") or ""
        rec["retrieved_at"] = now
        source_records.append(rec)
        src, sid = rec["source_name"], rec["source_record_id"]
        if (sid in seen_at_start.get(src, set())
                or sid in seen_this_run.setdefault(src, set())):
            repeated_this_run += 1
        seen_this_run[src].add(sid)

        status, baseline_id, confidence, reasons = match_mod.match_record(
            rec, index, cfg)
        cand = Candidate(
            candidate_id=make_candidate_id(rec["source_name"],
                                           rec["source_record_id"],
                                           rec["original_name"],
                                           rec["producer_name"]),
            name=rec["original_name"],
            normalized_name=normalize_name(rec["original_name"]),
            brand=rec.get("brand", ""),
            producer_name=rec["producer_name"],
            normalized_producer=normalize_name(rec["producer_name"]),
            category=rec.get("categories", ""),
            abv=rec.get("abv"),
            barcode=rec.get("barcode", ""),
            country=rec.get("country", ""),
            source_names=[rec["source_name"]],
            source_record_ids=[rec["source_record_id"]],
            source_urls=[rec["source_url"]],
            existing_beerpassport_id=baseline_id,
            match_status=status,
            match_confidence=round(confidence, 1),
            relevance=rec.get("relevance", "unclassified"),
            missing_fields=missing_fields_for(rec),
            review_reasons=reasons,
        )
        outcome = state_mod.merge_candidate(state, cand.__dict__)
        if outcome == "new":
            new_this_run += 1
        else:
            updated_this_run += 1

        seen = state.seen_source_ids.setdefault(rec["source_name"], [])
        if rec["source_record_id"] not in seen:
            seen.append(rec["source_record_id"])

    state_mod.save_state(cfg.state_dir, state)

    candidates = list(state.candidates.values())
    counts = {"existing": 0, "new_candidate": 0, "needs_review": 0}
    by_source: dict[str, int] = {}
    relevance_counts: dict[str, int] = {}
    for c in candidates:
        counts[c["match_status"]] = counts.get(c["match_status"], 0) + 1
        rel = c.get("relevance", "unclassified")
        relevance_counts[rel] = relevance_counts.get(rel, 0) + 1
        for s in c["source_names"]:
            by_source[s] = by_source.get(s, 0) + 1

    summary.update({
        "run_at": state.last_run,
        "unique_source_records_processed": len(source_records),
        "match_counts": counts,
        "relevance_counts": relevance_counts,
        "candidates_by_source": by_source,
        "incremental": {
            "new_candidates_this_run": new_this_run,
            "updated_candidates_this_run": updated_this_run,
            "repeated_source_records_this_run": repeated_this_run,
            "total_candidates": len(candidates),
        },
        "field_completeness": field_completeness(candidates),
        "producer_candidates": len(producers),
        "notes": [
            "Absence from the baseline does not prove a product is genuinely "
            "new; unmatched records are candidates, not verified products.",
            "Open Brewery DB records are producers only and are never counted "
            "as beverage discoveries.",
            "Open Food Facts data is ODbL-licensed; discovery evaluation only, "
            "not permission to incorporate into production.",
        ],
    })

    export_mod.export_all(cfg.output_dir, candidates, source_records,
                          producers, summary)
    return summary


def match_producer(rec: dict, base: baseline_mod.Baseline) -> dict:
    """Match an Open Brewery DB producer against baseline breweries."""
    nn = normalize_name(rec["original_name"])
    best_id, best_score = "", 0.0
    for bid, brow in base.breweries.items():
        score = fuzz.token_set_ratio(nn, normalize_name(brow.get("name", "")))
        if score > best_score:
            best_id, best_score = bid, score
    status = ("existing" if best_score >= 90
              else "needs_review" if best_score >= 70 else "new_candidate")
    return {
        "producer_id": f"prod_{rec['source_record_id'] or nn[:16]}",
        "original_name": rec["original_name"],
        "normalized_name": nn,
        "brewery_type": rec["brewery_type"],
        "city": rec["city"],
        "state": rec["state"],
        "country": rec["country"],
        "website": rec["website"],
        "source_name": rec["source_name"],
        "source_record_id": rec["source_record_id"],
        "source_url": rec["source_url"],
        "matched_baseline_brewery_id": best_id if status == "existing" else "",
        "match_status": status,
    }


def field_completeness(candidates: list[dict]) -> dict:
    fields = ["name", "producer", "category", "abv", "trustworthy_barcode"]
    total = max(len(candidates), 1)
    out = {}
    for f in fields:
        present = sum(1 for c in candidates if f not in c["missing_fields"])
        out[f] = round(present / total, 3)
    return out


def print_summary(summary: dict) -> None:
    print("\n=== Catalog discovery run summary ===")
    print(f"Run at: {summary.get('run_at')}")
    print(f"Baseline: {summary.get('baseline_files')}")
    for name, stats in summary.get("sources", {}).items():
        print(f"Source {name}: {stats.get('raw_records', 0)} raw records; "
              f"errors: {stats.get('errors', [])}")
    print(f"Match counts (accumulated): {summary.get('match_counts')}")
    print(f"Relevance (accumulated): {summary.get('relevance_counts')}")
    print(f"This run: {summary.get('incremental')}")
    print(f"Field completeness: {summary.get('field_completeness')}")
    if summary.get("errors"):
        print(f"Errors: {summary['errors']}")


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    cfg = parse_args(argv)

    if cfg.summary_only:
        path = cfg.output_dir / "run_summary.json"
        if not path.exists():
            print("No run summary found; run the discovery first.")
            return 1
        print_summary(json.loads(path.read_text(encoding="utf-8")))
        return 0

    if cfg.reset_state:
        if not confirm(
                "Reset local discovery state? Previously discovered "
                "candidates will be forgotten and the next run will count "
                "everything as new.", cfg.assume_yes):
            print("Aborted.")
            return 1
        state_mod.reset_state(cfg.state_dir)

    try:
        summary = run(cfg)
    except (FileNotFoundError, ValueError) as e:
        log.error("Startup failure: %s", e)
        return 1
    print_summary(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
