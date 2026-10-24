"""Open Food Facts adapter (Source C: packaged-product database).

Docs: https://openfoodfacts.github.io/openfoodfacts-server/api/

Uses the documented search endpoint with configurable search terms.
No images are downloaded, stored, or processed (explicitly out of scope).

Licensing: the Open Food Facts database is ODbL-licensed. This experiment
evaluates discovery potential only; incorporating records into production
requires a licensing review (see README).
"""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlencode

from ..config import Config
from ..normalize import (classify_relevance, is_relevant_beverage,
                         normalize_barcode, parse_abv)
from .base import CachedClient, SourceError

log = logging.getLogger(__name__)

SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
PAGE_SIZE = 100  # products per search page
MAX_PAGES_PER_TERM = 10  # safety bound; --limit usually binds first


def fetch_products(cfg: Config, client: CachedClient) -> tuple[list[dict], dict]:
    """Search packaged beverages across the configured search terms."""
    records: list[dict] = []
    stats: dict[str, Any] = {"terms_attempted": 0, "terms_ok": 0, "errors": [],
             "raw_hits": 0, "rejected": 0}
    terms = cfg.search_terms

    for term in terms:
        if cfg.limit is not None and len(records) >= cfg.limit:
            break
        stats["terms_attempted"] += 1
        pages = MAX_PAGES_PER_TERM
        try:
            for page in range(1, pages + 1):
                if cfg.limit is not None and len(records) >= cfg.limit:
                    break
                params = {
                    "search_terms": term,
                    "search_simple": 1,
                    "action": "process",
                    "json": 1,
                    "page_size": PAGE_SIZE,
                    "page": page,
                }
                url = f"{SEARCH_URL}?{urlencode(params)}"
                payload, _ = client.get_json(url, refresh=cfg.refresh)
                products = payload.get("products", []) if isinstance(payload, dict) else []
                stats["raw_hits"] += len(products)
                if not products:
                    break
                for p in products:
                    rec = to_product_record(p, terms)
                    if rec is None:
                        stats["rejected"] += 1
                        continue
                    records.append(rec)
                    if cfg.limit is not None and len(records) >= cfg.limit:
                        break
                page_count = payload.get("page_count", page) if isinstance(payload, dict) else page
                if page >= page_count:
                    break
            stats["terms_ok"] += 1
            log.info("Open Food Facts term %r: %d records so far",
                     term, len(records))
        except SourceError as e:
            stats["errors"].append(f"{term}: {e}")
            log.error("Open Food Facts term %r failed: %s", term, e)
            continue
    return records, stats


def to_product_record(product: dict, terms: list[str]) -> dict | None:
    """Map an OFF product to our internal record; None when irrelevant."""
    name = product.get("product_name") or ""
    brands = product.get("brands") or ""
    categories = product.get("categories") or ""
    relevant, reason = is_relevant_beverage(name, categories, brands, terms)
    if not relevant:
        return None

    nutriments = product.get("nutriments") or {}
    abv = parse_abv(nutriments.get("alcohol_value"))
    code = str(product.get("code") or product.get("_id") or "")
    relevance, relevance_reason = classify_relevance(name, categories, brands,
                                                     terms)
    review_reasons = []
    if relevance_reason:
        review_reasons.append(relevance_reason)

    return {
        "source_name": "openfoodfacts",
        "source_record_id": code,
        "original_name": name,
        "brand": brands,
        "categories": categories,
        "abv": abv,
        "abv_unknown": abv is None,
        "barcode": normalize_barcode(code),
        "country": product.get("countries") or "",
        "quantity": product.get("quantity") or "",
        "source_url": product.get("url") or "",
        "retrieved_note": "Open Food Facts (ODbL); discovery evaluation only",
        "relevance": relevance,
        "review_reasons": review_reasons,
    }
