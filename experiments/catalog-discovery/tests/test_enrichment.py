"""Tests for the producer-enrichment analysis (src/enrichment.py).

Covers the high-priority corrections:
- An exact dataset match is reported separately from whether it adds
  information beyond the baseline (the BrewDog case: baseline already
  scores 100, so the result is unresolved, not an improvement).
- Fuzzy buckets are provisional score buckets; exact matches are
  reported separately.
"""
import unittest
from types import SimpleNamespace

from src import enrichment as enrich_mod
from src.normalize import normalize_name


def _baseline(names):
    """Minimal baseline stand-in: {brewery_id: {'name': ...}}."""
    base = SimpleNamespace(breweries={str(i): {"name": n}
                                      for i, n in enumerate(names)})
    return base


def _row(name, **kw):
    r = {"id": f"ds-{name}", "name": name, "brewery_type": "micro",
         "city": "Town", "country": "US"}
    r.update(kw)
    return r


class TestCompareProducers(unittest.TestCase):
    def test_exact_matches_reported_separately_from_fuzzy(self):
        base = _baseline(["BrewDog Ltd", "Old Brewery"])
        rows = [_row("Brewdog"), _row("Old Brewery"),
                _row("1 of Us Brewing Company")]
        out = enrich_mod.compare_producers(base, rows)
        c = out["counts"]
        # Exact normalized-name matches are their own finding.
        self.assertEqual(c["exact_name_matches_unique"], 1)
        self.assertIn("old brewery", out["exact_name_matches"])
        # "Brewdog" is NOT an exact match for "BrewDog Ltd" even though
        # token_set_ratio scores it 100; it lands in a fuzzy bucket.
        self.assertNotIn("brewdog", out["exact_name_matches"])
        self.assertEqual(c["fuzzy_ge_90_provisional"], 2)  # brewdog, old brewery
        self.assertEqual(c["total"], 3)

    def test_buckets_are_provisional_not_verified(self):
        # The key names themselves must not read as verified findings.
        base = _baseline(["(512) Brewing Company"])
        rows = [_row("1 of Us Brewing Company")]
        out = enrich_mod.compare_producers(base, rows)
        c = out["counts"]
        self.assertEqual(c["exact_name_matches_unique"], 0)
        # Known token-subset false positive: must not be called "clear".
        self.assertNotIn("clear", " ".join(c.keys()))
        self.assertNotIn("likely_new", " ".join(c.keys()))
        self.assertGreaterEqual(c["fuzzy_70_90_provisional"], 1)


class TestAssessOffEnrichment(unittest.TestCase):
    def _candidates(self, prods):
        return [{"candidate_id": f"cand_{i}", "name": f"Beer {i}",
                 "producer_name": p,
                 "normalized_producer": normalize_name(p)}
                for i, p in enumerate(prods)]

    def test_brewdog_is_unresolved_not_improved(self):
        # The BrewDog case from the review: baseline contains "BrewDog Ltd"
        # (fuzzy score 100), so an exact dataset match for "brewdog" does
        # not prove incremental attribution.
        base = _baseline(["BrewDog Ltd"])
        rows = [_row("Brewdog", city="Coburg", country="Australia")]
        cands = self._candidates(["BrewDog"])
        out = enrich_mod.assess_off_enrichment(cands, base, rows)
        e = out["counts"]
        self.assertEqual(e["improved"], 0)
        self.assertEqual(e["unresolved"], 1)
        entry = out["unresolved"][0]
        self.assertTrue(entry["exact_dataset_match"])
        self.assertEqual(entry["baseline_score"], 100.0)

    def test_genuine_new_attribution_counts_as_improved(self):
        base = _baseline(["Old Brewery"])
        rows = [_row("Brand New Brewing Co")]
        cands = self._candidates(["Brand New Brewing Co"])
        out = enrich_mod.assess_off_enrichment(cands, base, rows)
        e = out["counts"]
        self.assertEqual(e["improved"], 1)
        self.assertEqual(e["unresolved"], 0)

    def test_no_producer_and_unchanged(self):
        base = _baseline(["Old Brewery"])
        rows = [_row("Brewdog")]
        cands = self._candidates(["Old Brewery", ""])
        cands[1]["normalized_producer"] = ""
        out = enrich_mod.assess_off_enrichment(cands, base, rows)
        e = out["counts"]
        self.assertEqual(e["unchanged"], 1)
        self.assertEqual(e["no_producer"], 1)
        self.assertEqual(e["improved"], 0)


if __name__ == "__main__":
    unittest.main()
