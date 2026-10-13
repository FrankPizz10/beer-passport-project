"""Open Brewery DB adapter (Source B: producer directory).

Docs: https://www.openbrewerydb.org/documentation

Brewery records are used to discover producers and enrich producer matching.
Breweries are NEVER counted as beverage discoveries; producer candidates are
reported separately.
"""
from __future__ import annotations

import logging
from urllib.parse import urlencode

from ..config import Config
from .base import CachedClient, SourceError

log = logging.getLogger(__name__)

API_ROOT = "https://api.openbrewerydb.org/v1/breweries"
PER_PAGE = 200  # documented maximum


def fetch_breweries(cfg: Config, client: CachedClient) -> tuple[list[dict], dict]:
    """Fetch a bounded number of brewery pages. Returns (records, stats)."""
    records: list[dict] = []
    stats = {"pages_attempted": 0, "pages_ok": 0, "errors": []}
    pages = cfg.brewery_pages
    if cfg.limit is not None:
        # --limit caps total brewery records for test runs
        pages = max(1, min(pages, (cfg.limit + PER_PAGE - 1) // PER_PAGE))

    for page in range(1, pages + 1):
        stats["pages_attempted"] += 1
        url = f"{API_ROOT}?{urlencode({'page': page, 'per_page': PER_PAGE})}"
        try:
            payload, _ = client.get_json(url, refresh=cfg.refresh)
            if not isinstance(payload, list):
                raise SourceError(f"Unexpected payload for {url}")
            records.extend(payload)
            stats["pages_ok"] += 1
            log.info("Open Brewery DB page %d: %d records", page, len(payload))
            if cfg.limit is not None and len(records) >= cfg.limit:
                records = records[:cfg.limit]
                break
            if len(payload) < PER_PAGE:
                break  # last page
        except SourceError as e:
            stats["errors"].append(str(e))
            log.error("Open Brewery DB page %d failed: %s", page, e)
            break
    return records, stats


def to_producer_record(raw: dict) -> dict:
    """Map an Open Brewery DB record to our internal producer representation."""
    return {
        "source_name": "openbrewerydb",
        "source_record_id": str(raw.get("id", "")),
        "original_name": raw.get("name") or "",
        "brewery_type": raw.get("brewery_type") or "",
        "city": raw.get("city") or "",
        "state": raw.get("state_province") or "",
        "country": raw.get("country") or "",
        "website": raw.get("website_url") or "",
        "source_url": f"{API_ROOT}/{raw.get('id', '')}",
    }
