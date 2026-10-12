# Experiment data

Baseline snapshots for the catalog discovery experiment. These are **experimental
snapshots only**, exported 2026-10-12 from the "Beer Updates" Google Sheet
(spreadsheet provided by the project owner):

- `LiveBeers.csv` — 5,894 beverage rows
- `LiveBreweries.csv` — 1,431 producer rows
- `LiveCategories.csv` — 14 category rows
- `LiveStyles.csv` — 147 style rows

Exported via the Google Sheets API (UNFORMATTED_VALUE rendering) on 2026-10-12.
Raw contents are preserved as exported; do not clean or rewrite these files in
place. Normalization for matching happens in code (`src/normalize.py`).

No credentials, tokens, or secrets are stored here.

- `cache/` — cached API responses from Open Brewery DB and Open Food Facts,
  keyed by URL hash. Safe to delete; `--refresh` refetches.
- `state/` — `discovery_state.json`: seen source record ids and merged
  candidates for incremental runs. `--reset-state` rebuilds it (destructive).
