"""Tests for the old-catalog cleanup rules (docs/09).

Synthetic rows only; no baseline data and no files are touched.
"""
from __future__ import annotations

import unittest

from src.cleanup import rules


def make_beer(**overrides):
    b = {
        "id": "1", "brewery_id": "10", "name": "Test Ale",
        "cat_id": "1", "style_id": "1", "abv": "5.0", "ibu": "0",
        "srm": "0", "upc": "0", "descript": "", "last_mod": "2010-01-01",
    }
    b.update(overrides)
    return b


def make_brewery(**overrides):
    b = {
        "id": "10", "name": "Test Brewing", "address1": "", "address2": "",
        "city": "", "state": "", "code": "", "country": "", "phone": "",
        "website": "", "descript": "", "add_user": "0",
        "last_mod": "2010-01-01",
    }
    b.update(overrides)
    return b


class TestGarbageUpc(unittest.TestCase):
    def test_sentinel_is_garbage(self):
        self.assertTrue(rules.is_garbage_upc("2147483647"))

    def test_short_digit_string_is_garbage(self):
        self.assertTrue(rules.is_garbage_upc("7"))
        self.assertTrue(rules.is_garbage_upc("1234567"))

    def test_null_conventions_are_not_garbage(self):
        self.assertFalse(rules.is_garbage_upc("0"))
        self.assertFalse(rules.is_garbage_upc(""))
        self.assertFalse(rules.is_garbage_upc(None))

    def test_real_barcodes_are_not_garbage(self):
        self.assertFalse(rules.is_garbage_upc("12345678"))      # UPC-E
        self.assertFalse(rules.is_garbage_upc("012345678905"))  # UPC-A
        self.assertFalse(rules.is_garbage_upc("5901234123457"))  # EAN-13

    def test_non_numeric_is_unexpected_not_garbage(self):
        self.assertFalse(rules.is_garbage_upc("ABC123"))
        self.assertTrue(rules.is_unexpected_upc("ABC123"))
        self.assertFalse(rules.is_unexpected_upc("012345678905"))
        self.assertFalse(rules.is_unexpected_upc("7"))


class TestR1EmptyBreweries(unittest.TestCase):
    def test_unreferenced_brewery_dropped_and_logged(self):
        beers = [make_beer(brewery_id="10")]
        breweries = [make_brewery(id="10"),
                     make_brewery(id="11", name="Empty Brewing")]
        result = rules.apply_cleanup(beers, breweries)
        self.assertEqual([b["id"] for b in result.breweries], ["10"])
        drops = [c for c in result.changes if c.rule == "R1"]
        self.assertEqual(len(drops), 1)
        self.assertEqual(drops[0].row_id, "11")
        self.assertEqual(drops[0].action, "drop_row")


class TestR2UpcCleanup(unittest.TestCase):
    def test_sentinel_cleared_to_null(self):
        beers = [make_beer(upc="2147483647")]
        result = rules.apply_cleanup(beers, [make_brewery()])
        self.assertEqual(result.beers[0]["upc"], "0")
        clears = [c for c in result.changes if c.rule == "R2"]
        self.assertEqual(len(clears), 1)
        self.assertEqual(clears[0].before, "2147483647")
        self.assertEqual(clears[0].after, "0")

    def test_valid_upc_untouched(self):
        beers = [make_beer(upc="012345678905")]
        result = rules.apply_cleanup(beers, [make_brewery()])
        self.assertEqual(result.beers[0]["upc"], "012345678905")
        self.assertEqual([c for c in result.changes if c.rule == "R2"], [])

    def test_unexpected_upc_flagged_not_changed(self):
        beers = [make_beer(upc="ABC123")]
        result = rules.apply_cleanup(beers, [make_brewery()])
        self.assertEqual(result.beers[0]["upc"], "ABC123")
        flags = [f for f in result.flags if f.rule == "R2"]
        self.assertEqual(len(flags), 1)


class TestR3Discontinued(unittest.TestCase):
    def test_marker_stripped_and_flagged(self):
        beers = [make_beer(name="Old Ale (discontinued)")]
        result = rules.apply_cleanup(beers, [make_brewery()])
        self.assertEqual(result.beers[0]["name"], "Old Ale")
        self.assertEqual(result.beers[0]["discontinued"], "1")
        marks = [c for c in result.changes if c.rule == "R3"]
        self.assertEqual(len(marks), 1)

    def test_marker_case_insensitive(self):
        beers = [make_beer(name="Old Ale (Discontinued)")]
        result = rules.apply_cleanup(beers, [make_brewery()])
        self.assertEqual(result.beers[0]["name"], "Old Ale")
        self.assertEqual(result.beers[0]["discontinued"], "1")

    def test_no_marker_gets_zero_and_no_change(self):
        beers = [make_beer(name="Fresh Ale")]
        result = rules.apply_cleanup(beers, [make_brewery()])
        self.assertEqual(result.beers[0]["discontinued"], "0")
        self.assertEqual([c for c in result.changes if c.rule == "R3"], [])


class TestR4Duplicates(unittest.TestCase):
    def test_duplicate_group_flagged_rows_kept(self):
        beers = [make_beer(id="1", name="Same Ale"),
                 make_beer(id="2", name="Same Ale")]
        breweries = [make_brewery(id="10")]
        result = rules.apply_cleanup(beers, breweries)
        self.assertEqual(len(result.beers), 2)
        flags = [f for f in result.flags if f.rule == "R4"]
        self.assertEqual(len(flags), 1)
        self.assertIn("1", flags[0].row_id)
        self.assertIn("2", flags[0].row_id)


class TestReconcileAndPurity(unittest.TestCase):
    def test_mixed_fixture_balances(self):
        beers = [make_beer(id="1", brewery_id="10", upc="2147483647"),
                 make_beer(id="2", brewery_id="10",
                           name="Gone (discontinued)")]
        breweries = [make_brewery(id="10"),
                     make_brewery(id="11", name="Empty Brewing")]
        result = rules.apply_cleanup(beers, breweries)
        self.assertEqual(rules.reconcile(result), [])
        self.assertEqual(result.input_beer_count, 2)
        self.assertEqual(result.input_brewery_count, 2)
        self.assertEqual(len(result.beers), 2)
        self.assertEqual(len(result.breweries), 1)

    def test_inputs_not_mutated(self):
        beer = make_beer(upc="7", name="Old (discontinued)")
        brewery = make_brewery(id="11")
        rules.apply_cleanup([beer], [brewery])
        self.assertEqual(beer["upc"], "7")
        self.assertEqual(beer["name"], "Old (discontinued)")
        self.assertNotIn("discontinued", beer)


if __name__ == "__main__":
    unittest.main()
