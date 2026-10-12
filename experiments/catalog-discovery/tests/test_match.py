"""Tests for the three-stage matcher. No network access."""
import unittest
from types import SimpleNamespace

from src import match as match_mod
from src.normalize import normalize_barcode


def make_baseline(beers):
    """Build a fake baseline object with the fields build_baseline_index needs."""
    base = SimpleNamespace(beers=beers, breweries={}, categories={}, styles={})

    def resolve(beer, _base):
        return {"brewery_name": beer.get("_brewery", ""),
                "category_name": "", "style_name": ""}
    import src.baseline as baseline_mod
    baseline_mod.resolve_beer_labels = resolve
    return base


CFG = SimpleNamespace(fuzzy_threshold=88.0, review_threshold=70.0,
                      abv_conflict=2.0)


def rec(name, producer="", barcode="", abv=None):
    return {"original_name": name, "producer_name": producer,
            "brand": producer, "barcode": normalize_barcode(barcode),
            "abv": abv, "review_reasons": []}


class TestBarcodeStage(unittest.TestCase):
    def setUp(self):
        beers = [{"id": "1", "name": "Punk IPA", "upc": "5056025440449",
                  "abv": "5.4", "_brewery": "Brewdog"}]
        self.index = match_mod.build_baseline_index(beers, make_baseline(beers))

    def test_barcode_match(self):
        status, bid, conf, _ = match_mod.match_record(
            rec("Something Else", "Other", "5056025440449"), self.index, CFG)
        self.assertEqual(status, "existing")
        self.assertEqual(bid, "1")

    def test_suspicious_barcode_flagged(self):
        status, _, _, reasons = match_mod.match_record(
            rec("Totally New Beer", "New Brewery", "12345"), self.index, CFG)
        self.assertIn("suspicious barcode", " ".join(reasons))


class TestExactStage(unittest.TestCase):
    def setUp(self):
        beers = [{"id": "7", "name": "Hocus Pocus", "upc": "",
                  "abv": "4.5", "_brewery": "Magic Hat"}]
        self.index = match_mod.build_baseline_index(beers, make_baseline(beers))

    def test_exact_name_producer(self):
        status, bid, _, _ = match_mod.match_record(
            rec("hocus! pocus", "MAGIC HAT"), self.index, CFG)
        self.assertEqual(status, "existing")
        self.assertEqual(bid, "7")

    def test_name_alone_does_not_match(self):
        # Same name, different producer must not auto-merge.
        status, _, _, _ = match_mod.match_record(
            rec("Hocus Pocus", "Different Brewery"), self.index, CFG)
        self.assertIn(status, ("new_candidate", "needs_review"))

    def test_abv_conflict_goes_to_review(self):
        status, bid, _, reasons = match_mod.match_record(
            rec("Hocus Pocus", "Magic Hat", abv=9.9), self.index, CFG)
        self.assertEqual(status, "needs_review")
        self.assertTrue(any("ABV" in r for r in reasons))


class TestFuzzyStage(unittest.TestCase):
    def setUp(self):
        beers = [{"id": "3", "name": "Grimbergen Blonde", "upc": "",
                  "abv": "6.7", "_brewery": "Grimbergen"}]
        self.index = match_mod.build_baseline_index(beers, make_baseline(beers))

    def test_close_variant_is_existing(self):
        status, _, conf, _ = match_mod.match_record(
            rec("Grimbergen Blond", "Grimbergen"), self.index, CFG)
        self.assertEqual(status, "existing")
        self.assertGreaterEqual(conf, CFG.fuzzy_threshold)

    def test_unrelated_is_new(self):
        status, _, _, _ = match_mod.match_record(
            rec("Quantum Hazy DIPA", "Faraway Brewing Co"), self.index, CFG)
        self.assertEqual(status, "new_candidate")

    def test_missing_producer_needs_review(self):
        status, _, _, reasons = match_mod.match_record(
            rec("Mystery Brew", ""), self.index, CFG)
        self.assertEqual(status, "needs_review")
        self.assertTrue(any("insufficient evidence" in r for r in reasons))


if __name__ == "__main__":
    unittest.main()
