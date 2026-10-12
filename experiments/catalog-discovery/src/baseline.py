"""Load the BeerPassport baseline CSV snapshots and resolve ID lookups."""
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

EXPECTED = {
    "LiveBeers.csv": ["id", "brewery_id", "name", "cat_id", "style_id",
                      "abv", "ibu", "srm", "upc", "descript", "last_mod"],
    "LiveBreweries.csv": ["id", "name", "address1", "address2", "city", "state",
                          "code", "country", "phone", "website", "descript",
                          "add_user"],
    "LiveCategories.csv": ["id", "cat_name", "last_mod"],
    "LiveStyles.csv": ["id", "cat_id", "style_name", "last_mod"],
}


@dataclass
class Baseline:
    beers: list[dict] = field(default_factory=list)
    breweries: dict[str, dict] = field(default_factory=dict)
    categories: dict[str, str] = field(default_factory=dict)
    styles: dict[str, str] = field(default_factory=dict)
    row_counts: dict[str, int] = field(default_factory=dict)


def _read_csv(path: Path, expected_headers: list[str]) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Baseline CSV not found: {path}")
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"Baseline CSV is empty: {path}")
    actual = list(rows[0].keys())
    missing = [h for h in expected_headers if h not in actual]
    if missing:
        raise ValueError(f"{path.name} missing expected headers {missing}; "
                         f"got {actual}")
    return rows


def load_baseline(data_dir: Path) -> Baseline:
    """Load the four baseline CSVs and build lookup dicts keyed by string id."""
    base = Baseline()
    for filename, headers in EXPECTED.items():
        rows = _read_csv(data_dir / filename, headers)
        base.row_counts[filename] = len(rows)
        log.info("Loaded %s: %d rows", filename, len(rows))
        if filename == "LiveBeers.csv":
            base.beers = rows
        elif filename == "LiveBreweries.csv":
            base.breweries = {r["id"]: r for r in rows if r.get("id")}
        elif filename == "LiveCategories.csv":
            base.categories = {r["id"]: r.get("cat_name", "") for r in rows
                               if r.get("id")}
        elif filename == "LiveStyles.csv":
            base.styles = {r["id"]: r.get("style_name", "") for r in rows
                           if r.get("id")}
    return base


def resolve_beer_labels(beer: dict, base: Baseline) -> dict:
    """Return brewery/category/style labels for a baseline beer row."""
    brewery = base.breweries.get(beer.get("brewery_id", ""), {})
    return {
        "brewery_name": brewery.get("name", ""),
        "category_name": base.categories.get(beer.get("cat_id", ""), ""),
        "style_name": base.styles.get(beer.get("style_id", ""), ""),
    }
