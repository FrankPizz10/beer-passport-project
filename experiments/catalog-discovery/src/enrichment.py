"""Producer-enrichment analysis: Open Brewery DB dataset vs baseline breweries.

Compares the pinned OBDB dataset snapshot against the 1,431-row baseline
brewery snapshot, then assesses whether the larger producer universe improves
producer attribution for Open Food Facts beverage candidates.

Breweries are NEVER counted as beverage discoveries; this only measures
producer coverage.

Usage:
    python -m src.enrichment [--dataset PATH] [--limit N] [--sample N]

Writes output/producer_enrichment.json with the full counts.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from rapidfuzz import fuzz, process

from . import baseline as baseline_mod
from . import state as state_mod
from .config import parse_args
from .normalize import normalize_name
from .sources import brewery_dataset

log = logging.getLogger("enrichment")

CLEAR = 90.0
AMBIGUOUS = 70.0


def best_baseline_match(name: str, baseline_names: dict[str, str]):
    """Return (brewery_id, score) of the best baseline match for a name."""
    nn = normalize_name(name)
    if not nn:
        return "", 0.0
    if nn in baseline_names:
        return baseline_names[nn], 100.0
    hit = process.extractOne(nn, baseline_names.keys(),
                             scorer=fuzz.token_set_ratio,
                             score_cutoff=AMBIGUOUS)
    if hit is None:
        return "", 0.0
    return baseline_names[hit[0]], hit[1]


def compare_producers(base: baseline_mod.Baseline,
                      dataset_rows: list[dict]) -> dict:
    """Classify each dataset producer vs the baseline breweries."""
    baseline_names = {normalize_name(b["name"]): bid
                      for bid, b in base.breweries.items()
                      if normalize_name(b["name"])}
    clear, ambiguous, likely_new = [], [], []
    exact_overlap = 0
    for row in dataset_rows:
        name = row.get("name") or ""
        nn = normalize_name(name)
        if nn in baseline_names:
            exact_overlap += 1
        bid, score = best_baseline_match(name, baseline_names)
        entry = {"dataset_id": row.get("id"), "name": name,
                 "brewery_type": row.get("brewery_type"),
                 "city": row.get("city"), "country": row.get("country"),
                 "baseline_id": bid, "score": round(score, 1)}
        if score >= CLEAR:
            clear.append(entry)
        elif score >= AMBIGUOUS:
            ambiguous.append(entry)
        else:
            likely_new.append(entry)
    return {"clear_matches": clear, "ambiguous": ambiguous,
            "likely_new": likely_new,
            "counts": {"exact_overlap": exact_overlap,
                       "clear": len(clear), "ambiguous": len(ambiguous),
                       "likely_new": len(likely_new),
                       "total": len(dataset_rows)}}


def assess_off_enrichment(candidates: list[dict],
                          base: baseline_mod.Baseline,
                          dataset_rows: list[dict]) -> dict:
    """Does the dataset improve producer attribution for OFF candidates?

    For each candidate producer, compare the best baseline-only score with
    the best score across baseline + dataset producers.
    """
    baseline_names = {normalize_name(b["name"]): bid
                      for bid, b in base.breweries.items()
                      if normalize_name(b["name"])}
    dataset_names = [normalize_name(r.get("name") or "") for r in dataset_rows]
    dataset_exact = {n for n in dataset_names if n}

    improved, unchanged, no_producer = [], [], []
    for c in candidates:
        prod = c.get("normalized_producer", "")
        if not prod:
            no_producer.append(c["candidate_id"])
            continue
        _, base_score = best_baseline_match(prod, baseline_names)
        ds_hit = process.extractOne(prod, dataset_names,
                                    scorer=fuzz.token_set_ratio,
                                    score_cutoff=0)
        ds_score = ds_hit[1] if ds_hit else 0.0
        entry = {"candidate_id": c["candidate_id"], "name": c["name"],
                 "producer": c.get("producer_name", ""),
                 "baseline_score": round(base_score, 1),
                 "dataset_score": round(ds_score, 1),
                 "dataset_match": ds_hit[0] if ds_hit else "",
                 "exact_dataset_match": prod in dataset_exact}
        # Improved means EXACT dataset attribution where the baseline has
        # nothing: fuzzy "improvements" were manually inspected and found
        # to be token-subset false positives (e.g. "High Noon" matching
        # "Grinder's High Noon Brewery"), so they do not count.
        if prod not in baseline_names and prod in dataset_exact:
            improved.append(entry)
        else:
            unchanged.append(entry)
    return {"improved": improved, "unchanged": unchanged,
            "no_producer": no_producer,
            "counts": {"improved": len(improved),
                       "unchanged": len(unchanged),
                       "no_producer": len(no_producer),
                       "total": len(candidates)}}


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s",
                        datefmt="%H:%M:%S")
    cfg = parse_args(argv)
    dataset_path = cfg.brewery_dataset or (cfg.data_dir / "dataset" /
                                           "openbrewerydb-breweries.csv")
    base = baseline_mod.load_baseline(cfg.data_dir)
    rows = brewery_dataset.load_snapshot(dataset_path, limit=cfg.limit)
    state = state_mod.load_state(cfg.state_dir)
    candidates = list(state.candidates.values())

    log.info("Comparing %d dataset producers against %d baseline breweries...",
             len(rows), len(base.breweries))
    comparison = compare_producers(base, rows)
    log.info("Assessing producer attribution for %d OFF candidates...",
             len(candidates))
    enrichment = assess_off_enrichment(candidates, base, rows)

    report = {
        "dataset_snapshot": brewery_dataset.SNAPSHOT,
        "baseline_breweries": len(base.breweries),
        "producer_comparison": comparison["counts"],
        "off_enrichment": enrichment["counts"],
        "improved_candidates": enrichment["improved"],
        "ambiguous_sample": comparison["ambiguous"][:25],
        "likely_new_sample": comparison["likely_new"][:25],
        "clear_sample": comparison["clear_matches"][:25],
    }
    out = cfg.output_dir / "producer_enrichment.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                   encoding="utf-8")

    c = comparison["counts"]
    e = enrichment["counts"]
    print("\n=== Producer enrichment (OBDB dataset vs baseline) ===")
    print(f"Dataset snapshot: {brewery_dataset.SNAPSHOT['commit_short']} "
          f"({c['total']} producers) vs {len(base.breweries)} baseline breweries")
    print(f"Clear matches (>=90): {c['clear']}")
    print(f"Ambiguous (70-90): {c['ambiguous']}")
    print(f"Likely new producers (<70): {c['likely_new']}")
    print(f"\nOFF candidates assessed: {e['total']}")
    print(f"Producer newly attributable via dataset: {e['improved']}")
    print(f"Unchanged: {e['unchanged']}, no producer listed: {e['no_producer']}")
    print(f"\nFull report: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
