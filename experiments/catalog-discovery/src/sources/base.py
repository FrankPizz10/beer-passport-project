"""Cached, rate-limited HTTP client shared by the source adapters.

- Responses are cached on disk under the cache dir, keyed by a hash of the URL.
- Transient failures are retried with backoff.
- A per-source delay keeps request rates polite.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path

import requests

from ..config import USER_AGENT

log = logging.getLogger(__name__)


class SourceError(Exception):
    """Raised when a source cannot be reached after retries."""


class CachedClient:
    def __init__(self, cache_dir: Path, delay: float = 1.0,
                 timeout: int = 25, max_retries: int = 3,
                 user_agent: str = USER_AGENT):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.delay = delay
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent,
                                     "Accept": "application/json"})
        self._last_request = 0.0

    def _cache_path(self, url: str) -> Path:
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{key}.json"

    def get_json(self, url: str, refresh: bool = False) -> tuple[object, bool]:
        """Fetch JSON from url. Returns (payload, from_cache)."""
        path = self._cache_path(url)
        if path.exists() and not refresh:
            try:
                return json.loads(path.read_text(encoding="utf-8")), True
            except (json.JSONDecodeError, OSError) as e:
                log.warning("Ignoring corrupt cache entry for %s: %s", url, e)

        wait = self.delay - (time.time() - self._last_request)
        if wait > 0:
            time.sleep(wait)

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                self._last_request = time.time()
                resp = self.session.get(url, timeout=self.timeout)
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", "10"))
                    log.warning("Rate limited (429) on %s; sleeping %ds",
                                url, retry_after)
                    time.sleep(retry_after)
                    continue
                resp.raise_for_status()
                payload = resp.json()
                path.write_text(json.dumps(payload), encoding="utf-8")
                return payload, False
            except (requests.RequestException, json.JSONDecodeError) as e:
                last_error = e
                log.warning("Attempt %d/%d failed for %s: %s",
                            attempt, self.max_retries, url, e)
                time.sleep(2 ** attempt)
        raise SourceError(f"Failed to fetch {url}: {last_error}")
