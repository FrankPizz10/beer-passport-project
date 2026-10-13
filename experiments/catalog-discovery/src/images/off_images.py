"""Open Food Facts image source adapter.

Barcode-first product lookup: GET /api/v2/product/<barcode>.json.
Falls back to nothing (no fuzzy product search here; identity is
evaluated separately in match.py). Records image URLs and metadata
only; never downloads image binaries.

Rate limits: product reads are documented at 15 req/min/IP. The shared
CachedClient enforces a polite delay and caches responses on disk.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import quote

from ..normalize import normalize_barcode
from ..sources.base import CachedClient, SourceError
from .models import ImageCandidate

log = logging.getLogger(__name__)

PRODUCT_URL = "https://world.openfoodfacts.org/api/v2/product/{}.json"
LICENSE_NAME = "Creative Commons Attribution-ShareAlike"
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/3.0/legalcode.en"
# License version is the project-wide statement; per-image version is not
# exposed by the API. Recorded as stated, not asserted per image.
LICENSE_VERSION = "unspecified (project-wide CC BY-SA statement)"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fetch_product(client: CachedClient, barcode: str,
                  refresh: bool = False) -> dict | None:
    """Return the OFF product dict for a barcode, or None.

    Returns None when the product does not exist (source returned
    nothing). Raises SourceError when the source fails to respond;
    callers must not interpret that as zero coverage.
    """
    code = normalize_barcode(barcode)
    if not code:
        return None
    url = PRODUCT_URL.format(quote(code, safe=""))
    payload, _ = client.get_json(url, refresh=refresh)
    if not isinstance(payload, dict):
        return None
    if payload.get("status") == 0:
        return None
    product = payload.get("product")
    return product if isinstance(product, dict) else None


def extract_front_image(product: dict) -> dict:
    """Pick the front image and its metadata from a product dict."""
    image_url = product.get("image_front_url") or product.get("image_url") or ""
    contributor = ""
    images = product.get("images") or {}
    # Prefer the uploader of a raw front upload when present.
    for key, val in images.items():
        if isinstance(val, dict) and key.startswith("front") is False and \
                str(key).isdigit() and val.get("uploader"):
            contributor = val.get("uploader") or contributor
    return {"image_url": image_url, "contributor": contributor}


def to_candidate(beverage: dict, product: dict) -> ImageCandidate | None:
    """Build an ImageCandidate from a beverage record and OFF product.

    Returns None when the product carries no usable front image.
    """
    img = extract_front_image(product)
    if not img["image_url"]:
        return None
    code = str(product.get("code") or "")
    return ImageCandidate(
        beverage_id=beverage.get("beverage_id", ""),
        barcode=normalize_barcode(beverage.get("barcode", "")),
        beverage_name=beverage.get("beverage_name", ""),
        brand=beverage.get("brand", ""),
        producer=beverage.get("producer", ""),
        flavor_variant=beverage.get("flavor_variant", ""),
        packaging=beverage.get("packaging", ""),
        source_type="openfoodfacts",
        source_record_url=(
            product.get("url")
            or f"https://world.openfoodfacts.org/product/{code}"
        ),
        image_url=img["image_url"],
        license_name=LICENSE_NAME,
        license_version=LICENSE_VERSION,
        license_url=LICENSE_URL,
        attribution_text=(
            f"Image via Open Food Facts ({LICENSE_NAME}); "
            f"contributor: {img['contributor'] or 'unknown'}"
        ),
        contributor=img["contributor"],
        permission_basis="CC BY-SA (OFF project-wide image statement)",
        permission_evidence=(
            "https://openfoodfacts.github.io/documentation/docs/"
            "Product-Opener/api/tutorials/license-be-on-the-legal-side/"
        ),
        retrieved_at=utcnow(),
    )


def find_candidates(beverage: dict, client: CachedClient,
                    refresh: bool = False
                    ) -> tuple[list[ImageCandidate], dict | None, str | None]:
    """Find OFF image candidates for one beverage.

    Returns (candidates, product, error). An empty candidate list with
    error=None means the source returned nothing. error set means the
    source failed and must not be read as zero coverage.
    """
    barcode = normalize_barcode(beverage.get("barcode", ""))
    if not barcode:
        return [], None, None
    try:
        product = fetch_product(client, barcode, refresh=refresh)
    except SourceError as e:
        log.warning("OFF lookup failed for %s: %s", barcode, e)
        return [], None, str(e)
    if product is None:
        return [], None, None
    cand = to_candidate(beverage, product)
    return ([cand] if cand else []), product, None
