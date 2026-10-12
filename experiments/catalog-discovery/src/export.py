"""Export candidates, source records, producers, review queue, and run summary."""
from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

CANDIDATE_COLUMNS = [
    "candidate_id", "name", "brand", "producer_name", "category", "style",
    "abv", "barcode", "country", "source_names", "source_record_ids",
    "source_urls", "existing_beerpassport_id", "match_status",
    "match_confidence", "missing_fields", "review_reasons",
    "first_discovered_at", "last_seen_at",
]

SOURCE_COLUMNS = [
    "source_name", "source_record_id", "original_name", "producer_name",
    "brand", "categories", "abv", "barcode", "country", "source_url",
    "retrieved_at",
]

PRODUCER_COLUMNS = [
    "producer_id", "original_name", "normalized_name", "brewery_type",
    "city", "state", "country", "website", "source_name",
    "source_record_id", "source_url", "matched_baseline_brewery_id",
    "match_status",
]


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            flat = {}
            for c in columns:
                v = row.get(c, "")
                if isinstance(v, (list, tuple)):
                    v = "; ".join(str(x) for x in v)
                flat[c] = v
            w.writerow(flat)
    log.info("Wrote %s (%d rows)", path, len(rows))


def export_all(output_dir: Path, candidates: list[dict],
               source_records: list[dict], producers: list[dict],
               summary: dict) -> dict[str, str]:
    """Write all output files. Returns {logical_name: path}."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {}

    paths["beverage_candidates"] = str(output_dir / "beverage_candidates.csv")
    _write_csv(output_dir / "beverage_candidates.csv", CANDIDATE_COLUMNS, candidates)

    paths["source_records"] = str(output_dir / "source_records.csv")
    _write_csv(output_dir / "source_records.csv", SOURCE_COLUMNS, source_records)

    paths["producer_candidates"] = str(output_dir / "producer_candidates.csv")
    _write_csv(output_dir / "producer_candidates.csv", PRODUCER_COLUMNS, producers)

    review = [c for c in candidates if c["match_status"] == "needs_review"]
    paths["review_queue"] = str(output_dir / "review_queue.csv")
    _write_csv(output_dir / "review_queue.csv",
                [c for c in CANDIDATE_COLUMNS if c != "missing_fields"],
                review)

    summary_path = output_dir / "run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False),
                            encoding="utf-8")
    paths["run_summary"] = str(summary_path)
    log.info("Wrote %s", summary_path)
    return paths
