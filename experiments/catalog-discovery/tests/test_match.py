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
                      single_token_producer_threshold=85.0,
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


class TestSingleTokenGenericNameFuzzy(unittest.TestCase):
    def setUp(self):
        beers = [
            {"id": "34", "name": "Blonde", "upc": "", "abv": "7.5",
             "_brewery": "Brasserie La Choulette"},
            {"id": "825", "name": "Blonde", "upc": "", "abv": "6.0",
             "_brewery": "Brasserie De L'Abbaye Des Rocs"},
            {"id": "220", "name": "Ambree", "upc": "", "abv": "7.0",
             "_brewery": "Brasserie De L'Abbaye Des Rocs"},
        ]
        self.index = match_mod.build_baseline_index(beers, make_baseline(beers))

    def test_goudale_blonde_different_brewery_needs_review(self):
        # "la goudale blonde" / "Brasserie Goudale" should not auto-match
        # baseline "Blonde" / "Brasserie La Choulette" despite high fuzzy name score.
        status, bid, conf, reasons = match_mod.match_record(
            rec("la goudale blonde", "Brasserie Goudale"), self.index, CFG)
        self.assertEqual(status, "needs_review")
        self.assertNotEqual(status, "existing")
        self.assertTrue(any("weak producer agreement" in r for r in reasons))

    def test_mont_blanc_blonde_different_brewery_needs_review(self):
        # "La Blonde" / "Brasserie du Mont Blanc" should not auto-match
        # baseline "Blonde" / "Brasserie De L'Abbaye Des Rocs".
        status, bid, conf, reasons = match_mod.match_record(
            rec("La Blonde", "Brasserie du Mont Blanc"), self.index, CFG)
        self.assertEqual(status, "needs_review")
        self.assertNotEqual(status, "existing")
        self.assertTrue(any("weak producer agreement" in r for r in reasons))

    def test_goudale_ambree_different_brewery_needs_review(self):
        # "75CL BIERE LA GOUDALE AMBREE" / "Brasserie de Gayant" should not
        # auto-match baseline "Ambree" / "Brasserie De L'Abbaye Des Rocs".
        status, bid, conf, reasons = match_mod.match_record(
            rec("75CL BIERE LA GOUDALE AMBREE", "Brasserie de Gayant"), self.index, CFG)
        self.assertEqual(status, "needs_review")
        self.assertNotEqual(status, "existing")
        self.assertTrue(any("weak producer agreement" in r for r in reasons))

    def test_single_word_name_strong_producer_matches_existing(self):
        # Positive control: single-word name with strong producer agreement
        # ("Blonde de Choulette" vs baseline "Blonde" / "Brasserie La Choulette")
        # should still be classified as existing.
        status, bid, conf, reasons = match_mod.match_record(
            rec("Blonde de Choulette", "Brasserie La Choulette"), self.index, CFG)
        self.assertEqual(status, "existing")
        self.assertEqual(bid, "34")
        self.assertGreaterEqual(conf, CFG.fuzzy_threshold)


class TestBrandAliasMatching(unittest.TestCase):
    """Brand alias as producer evidence (pilot: White Claw/Truly/High Noon).

    No network access; aliases are passed directly, not read from disk.
    """
    ALIASES = [
        {"brand": "White Claw", "producer": "Mark Anthony Brewing"},
        {"brand": "Truly", "producer": "Boston Beer Company"},
        {"brand": "High Noon", "producer": "E. & J. Gallo Winery"},
    ]

    def setUp(self):
        beers = [
            {"id": "5936", "name": "White Claw - Natural Lime", "upc": "",
             "abv": "5", "_brewery": "Mark Anthony Brewing"},
            {"id": "5941", "name": "White Claw - Lemon", "upc": "",
             "abv": "5", "_brewery": "Mark Anthony Brewing"},
            {"id": "5954", "name": "Truly - Wild Berry", "upc": "",
             "abv": "5", "_brewery": "Boston Beer Company"},
            {"id": "5968", "name": "Truly Unruly - Berry Blast", "upc": "",
             "abv": "5", "_brewery": "Boston Beer Company"},
            {"id": "6014", "name": "High Noon Vodka - Pineapple", "upc": "",
             "abv": "4.5", "_brewery": "E. & J. Gallo Winery"},
        ]
        self.index = match_mod.build_baseline_index(
            beers, make_baseline(beers), aliases=self.ALIASES)

    def test_white_claw_natural_lime_is_existing(self):
        status, bid, conf, _ = match_mod.match_record(
            rec("Hard Seltzer- Natural Lime", "White Claw"), self.index, CFG)
        self.assertEqual(status, "existing")
        self.assertEqual(bid, "5936")

    def test_white_claw_lemon_is_existing(self):
        status, bid, conf, _ = match_mod.match_record(
            rec("Hard Seltzer Lemon", "White Claw"), self.index, CFG)
        self.assertEqual(status, "existing")
        self.assertEqual(bid, "5941")

    def test_truly_wild_berry_is_existing(self):
        status, bid, conf, _ = match_mod.match_record(
            rec("Wild Berry Hard Seltzer", "Truly"), self.index, CFG)
        self.assertEqual(status, "existing")
        self.assertEqual(bid, "5954")

    def test_truly_unruly_berry_blast_is_existing(self):
        status, bid, conf, _ = match_mod.match_record(
            rec("Truly Unruly Berry Blast", "Truly"), self.index, CFG)
        self.assertEqual(status, "existing")
        self.assertEqual(bid, "5968")

    def test_high_noon_pineapple_is_existing(self):
        status, bid, conf, _ = match_mod.match_record(
            rec("High Noon Pineapple", "High Noon"), self.index, CFG)
        self.assertEqual(status, "existing")
        self.assertEqual(bid, "6014")

    def test_alias_does_not_merge_different_flavors(self):
        # Same brand/producer, different flavor: must NOT auto-merge.
        status, bid, conf, reasons = match_mod.match_record(
            rec("Hard Seltzer Mango", "White Claw"), self.index, CFG)
        self.assertNotEqual(status, "existing")
        self.assertIn(status, ("new_candidate", "needs_review"))

    def test_alias_does_not_merge_natural_lime_into_lime(self):
        # "Natural Lime" vs "Lime" are distinct flavors; the flavor
        # signature gate must keep them apart even with alias agreement.
        status, bid, conf, reasons = match_mod.match_record(
            rec("Hard Seltzer Natural Lime", "White Claw"), self.index, CFG)
        # Must match Natural Lime (5936), never Lime (5941).
        self.assertEqual(status, "existing")
        self.assertEqual(bid, "5936")

    def test_flavor_mismatch_with_alias_goes_to_review(self):
        # Producer matched via alias but flavor identity uncertain:
        # needs_review, not existing.
        beers = [
            {"id": "5901", "name": "White Claw - Lime", "upc": "",
             "abv": "5", "_brewery": "Mark Anthony Brewing"},
        ]
        index = match_mod.build_baseline_index(
            beers, make_baseline(beers), aliases=self.ALIASES)
        status, bid, conf, reasons = match_mod.match_record(
            rec("Hard Seltzer Natural Lime", "White Claw"), index, CFG)
        self.assertEqual(status, "needs_review")
        self.assertTrue(any("flavor identity uncertain" in r for r in reasons))

    def test_unsupported_brand_gets_no_alias_boost(self):
        # A brand with no alias must not benefit from alias scoring.
        status, _, _, _ = match_mod.match_record(
            rec("Hard Seltzer Natural Lime", "Vizzy"), self.index, CFG)
        self.assertNotEqual(status, "existing")

    def test_ambiguous_alias_is_ignored(self):
        # Entries marked ambiguous are documented but never used.
        aliases = self.ALIASES + [
            {"brand": "Mystery", "producer": "Mark Anthony Brewing",
             "ambiguous": True},
        ]
        loaded = [a for a in aliases if not a.get("ambiguous")]
        self.assertNotIn("Mystery", [a["brand"] for a in loaded])
        score, via_alias = match_mod.producer_agreement_score(
            "Mystery", "Mark Anthony Brewing", loaded)
        self.assertFalse(via_alias)
        self.assertLess(score, 100.0)

    def test_multi_brand_string_resolves_alias(self):
        # OFF brand fields can list several brands comma-separated.
        # The alias must resolve from the raw string (normalization
        # strips the commas).
        brand = "Hard Seltzer Beverage Company LLC, Truly, Truly Unruly"
        status, bid, conf, _ = match_mod.match_record(
            {"original_name": "Hard Seltzer - Berry Blast",
             "producer_name": brand, "brand": brand,
             "barcode": "", "abv": 5.0, "review_reasons": []},
            self.index, CFG)
        self.assertEqual(status, "existing")
        self.assertEqual(bid, "5968")

    def test_empty_flavor_signature_goes_to_review(self):
        # A generic alias-branded candidate ("Hard Seltzer" / White Claw)
        # has an empty flavor signature. Even against a generic baseline
        # product for the aliased producer, empty == empty must NOT count
        # as product identity: route to needs_review, never existing.
        beers = [
            {"id": "6000", "name": "White Claw", "upc": "",
             "abv": "5", "_brewery": "Mark Anthony Brewing"},
        ]
        index = match_mod.build_baseline_index(
            beers, make_baseline(beers), aliases=self.ALIASES)
        self.assertEqual(
            match_mod.flavor_signature("Hard Seltzer", "White Claw"),
            frozenset())
        status, bid, conf, reasons = match_mod.match_record(
            rec("Hard Seltzer", "White Claw"), index, CFG)
        self.assertEqual(status, "needs_review")
        self.assertNotEqual(status, "existing")
        self.assertTrue(any("flavor identity uncertain" in r for r in reasons))

    def test_flavor_identity_confirmed_requires_nonempty(self):
        self.assertFalse(match_mod.flavor_identity_confirmed(
            "Hard Seltzer", "White Claw", "White Claw"))
        self.assertTrue(match_mod.flavor_identity_confirmed(
            "Hard Seltzer Natural Lime", "White Claw",
            "White Claw - Natural Lime"))
        self.assertFalse(match_mod.flavor_identity_confirmed(
            "Hard Seltzer Natural Lime", "White Claw", "White Claw - Lime"))

    def test_abv_conflict_with_alias_goes_to_review(self):
        # Alias + flavor match, but ABV conflicts: needs_review, not existing.
        brand = "Hard Seltzer Beverage Company LLC, Truly, Truly Unruly"
        status, bid, conf, reasons = match_mod.match_record(
            {"original_name": "Hard Seltzer - Berry Blast",
             "producer_name": brand, "brand": brand,
             "barcode": "", "abv": 8.0, "review_reasons": []},
            self.index, CFG)
        self.assertEqual(status, "needs_review")
        self.assertTrue(any("ABV" in r for r in reasons))


class TestAliasHelpers(unittest.TestCase):
    def test_resolve_alias_case_insensitive(self):
        aliases = [{"brand": "White Claw", "producer": "Mark Anthony Brewing"}]
        self.assertEqual(
            match_mod.resolve_producer_alias("white claw", aliases),
            "Mark Anthony Brewing")
        self.assertIsNone(
            match_mod.resolve_producer_alias("Unknown Brand", aliases))

    def test_flavor_signature_strips_brand_and_descriptors(self):
        sig = match_mod.flavor_signature("Hard Seltzer- Natural Lime",
                                         "White Claw")
        self.assertEqual(sig, frozenset({"natural", "lime"}))
        # Baseline side: brand removed from the beer name too.
        sig2 = match_mod.flavor_signature("White Claw - Natural Lime",
                                          "White Claw")
        self.assertEqual(sig, sig2)

    def test_load_brand_aliases_missing_file(self):
        self.assertEqual(match_mod.load_brand_aliases("/nonexistent"), [])

    def test_load_brand_aliases_skips_ambiguous(self):
        import json, tempfile, os
        with tempfile.TemporaryDirectory() as d:
            payload = {"aliases": [
                {"brand": "A", "producer": "P1"},
                {"brand": "B", "producer": "P2", "ambiguous": True},
                {"brand": "", "producer": "P3"},
            ]}
            with open(os.path.join(d, "brand_aliases.json"), "w") as f:
                json.dump(payload, f)
            loaded = match_mod.load_brand_aliases(d)
            self.assertEqual([a["brand"] for a in loaded], ["A"])


if __name__ == "__main__":
    unittest.main()
