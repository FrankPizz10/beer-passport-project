"""Open Brewery DB official dataset adapter (Source B, dataset path).

Uses a pinned snapshot of the official dataset repository instead of the
live API. The API adapter (``openbrewerydb.py``) is retained; select via
``--brewery-source {api,dataset}``.

Snapshot provenance is recorded in ``SNAPSHOT`` and in
``data/dataset/SNAPSHOT.md``. Do not commit the raw snapshot file itself
(2.2 MB CSV); it is gitignored. Reproduce with the documented download URL.

Reuse guidance (Open Brewery DB FAQ, checked 2026-10-12): the dataset may be
used for any project with credit to Open Brewery DB. The repository LICENSE
is MIT (covers the software); the FAQ's credit requirement governs dataset
reuse. What "credit" concretely requires (e.g. attribution text) is not
spelled out; treat it as an open question for production use.
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path

log = logging.getLogger(__name__)

SNAPSHOT = {
    "repo": "https://github.com/openbrewerydb/openbrewerydb",
    "commit": "4d33d43af09eac011415eba834cd97fc86b0c99a",
    "commit_short": "4d33d43af09e",
    "file": "breweries.csv",
    "download_url": (
        "https://raw.githubusercontent.com/openbrewerydb/openbrewerydb/"
        "4d33d43af09eac011415eba834cd97fc86b0c99a/breweries.csv"
    ),
    "retrieved": "2026-10-12",
    "rows": 11959,
    "attribution": "Producer data: Open Brewery DB (openbrewerydb.org)",
}

EXPECTED_COLUMNS = [
    "id", "name", "brewery_type", "address_1", "address_2", "address_3",
    "city", "state_province", "postal_code", "country", "phone",
    "website_url", "longitude", "latitude",
]


def load_snapshot(path: Path, limit: int | None = None) -> list[dict]:
    """Load the pinned CSV snapshot. Returns raw row dicts."""
    if not path.exists():
        raise FileNotFoundError(
            f"Brewery dataset snapshot not found: {path}. "
            f"Download it from {SNAPSHOT['download_url']}")
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in ("id", "name") if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Snapshot missing columns {missing}")
        rows = list(reader)
    if limit is not None:
        rows = rows[:limit]
    log.info("Loaded Open Brewery DB snapshot: %d rows from %s", len(rows), path)
    return rows


def to_producer_record(row: dict) -> dict:
    """Map a dataset CSV row to the internal producer representation."""
    rid = row.get("id") or ""
    return {
        "source_name": "openbrewerydb-dataset",
        "source_record_id": rid,
        "original_name": row.get("name") or "",
        "brewery_type": row.get("brewery_type") or "",
        "city": row.get("city") or "",
        "state": row.get("state_province") or "",
        "country": row.get("country") or "",
        "website": row.get("website_url") or "",
        "source_url": (
            f"https://github.com/openbrewerydb/openbrewerydb/blob/"
            f"{SNAPSHOT['commit']}/breweries.csv"
        ),
        "snapshot": SNAPSHOT["commit_short"],
    }
