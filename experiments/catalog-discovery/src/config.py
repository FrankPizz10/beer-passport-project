"""CLI configuration for the catalog discovery prototype."""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
USER_AGENT = "BeerPassportCatalogExperiment/1.0 (research prototype; contact via repo)"


@dataclass
class Config:
    data_dir: Path = BASE_DIR / "data"
    output_dir: Path = BASE_DIR / "output"
    cache_dir: Path = BASE_DIR / "data" / "cache"
    state_dir: Path = BASE_DIR / "data" / "state"
    limit: int | None = None          # cap on source records per source (test runs)
    refresh: bool = False             # ignore cached API responses
    summary_only: bool = False        # print last run summary and exit
    reset_state: bool = False         # rebuild discovery state from scratch
    assume_yes: bool = False          # skip confirmation prompts
    search_terms: list[str] = field(
        default_factory=lambda: [
            "beer",
            "cider",
            "hard seltzer",
            "hard iced tea",
            "malt beverage",
        ]
    )
    brewery_pages: int = 2            # Open Brewery DB pages (200 records each)
    brewery_source: str = "api"       # "api" or "dataset"
    brewery_dataset: Path | None = None  # snapshot CSV for --brewery-source dataset
    fuzzy_threshold: float = 88.0     # rapidfuzz score to call a fuzzy match
    review_threshold: float = 70.0    # below this: new_candidate; between: needs_review
    single_token_producer_threshold: float = 85.0  # min producer score for single-token name fuzzy matches
    abv_conflict: float = 2.0         # ABV point difference that flags a conflict
    request_timeout: int = 25
    max_retries: int = 3
    # Open Food Facts documents 10 req/min/IP for search queries
    # (/cgi/search.pl); 6s keeps us under that limit.
    off_delay: float = 6.0
    obdb_delay: float = 1.0           # seconds between Open Brewery DB requests


def parse_args(argv: list[str] | None = None) -> Config:
    p = argparse.ArgumentParser(
        description="BeerPassport multi-source catalog discovery prototype"
    )
    p.add_argument("--limit", type=int, default=None,
                   help="Cap source records fetched per source (for test runs).")
    p.add_argument("--refresh", action="store_true",
                   help="Ignore cached API responses and refetch.")
    p.add_argument("--summary", action="store_true", dest="summary_only",
                   help="Print the last run summary and exit.")
    p.add_argument("--reset-state", action="store_true",
                   help="Rebuild local discovery state from scratch (destructive).")
    p.add_argument("--yes", action="store_true",
                   help="Answer yes to confirmation prompts (needed for --reset-state in scripts).")
    p.add_argument("--search-terms", nargs="+", default=None,
                   help="Override the Open Food Facts search terms.")
    p.add_argument("--brewery-pages", type=int, default=2,
                   help="Number of Open Brewery DB pages to fetch (200 records each).")
    p.add_argument("--brewery-source", choices=["api", "dataset"], default="api",
                   help="Open Brewery DB access path: live API or pinned dataset snapshot.")
    p.add_argument("--brewery-dataset", type=Path, default=None,
                   help="Path to the Open Brewery DB snapshot CSV (with --brewery-source dataset).")
    p.add_argument("--data-dir", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, default=None)
    args = p.parse_args(argv)

    cfg = Config()
    if args.limit is not None:
        cfg.limit = args.limit
    cfg.refresh = args.refresh
    cfg.summary_only = args.summary_only
    cfg.reset_state = args.reset_state
    cfg.assume_yes = args.yes
    if args.search_terms:
        cfg.search_terms = args.search_terms
    cfg.brewery_pages = args.brewery_pages
    cfg.brewery_source = args.brewery_source
    if args.data_dir:
        cfg.data_dir = args.data_dir
        cfg.cache_dir = args.data_dir / "cache"
        cfg.state_dir = args.data_dir / "state"
    cfg.brewery_dataset = (args.brewery_dataset
                           or cfg.data_dir / "dataset" / "openbrewerydb-breweries.csv")
    if args.output_dir:
        cfg.output_dir = args.output_dir
    return cfg
