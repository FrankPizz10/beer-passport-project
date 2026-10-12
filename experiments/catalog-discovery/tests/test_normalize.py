"""Tests for normalization helpers. No network access."""
import unittest

from src.normalize import (barcode_is_trustworthy, is_relevant_beverage,
                           normalize_barcode, normalize_name, parse_abv)


class TestNormalizeName(unittest.TestCase):
    def test_punctuation_and_case(self):
        self.assertEqual(normalize_name("Hocus-Pocus! (IPA)"), "hocus pocus ipa")

    def test_accents(self):
        self.assertEqual(normalize_name("Grimbergen Blondé"), "grimbergen blonde")

    def test_whitespace(self):
        self.assertEqual(normalize_name("  Double   IPA\n"), "double ipa")

    def test_unicode(self):
        self.assertEqual(normalize_name("Sørland's \"Bière\""), "sorland s biere")

    def test_empty(self):
        self.assertEqual(normalize_name(None), "")
        self.assertEqual(normalize_name(""), "")


class TestBarcode(unittest.TestCase):
    def test_leading_zeros_preserved(self):
        self.assertEqual(normalize_barcode("0071234567890"), "0071234567890")
        self.assertEqual(normalize_barcode(12345), "12345")

    def test_strips_non_digits(self):
        self.assertEqual(normalize_barcode(" 505-60254 40449 "), "5056025440449")

    def test_missing(self):
        self.assertEqual(normalize_barcode(None), "")
        self.assertEqual(normalize_barcode("n/a"), "")

    def test_trustworthy(self):
        self.assertTrue(barcode_is_trustworthy("5056025440449"))   # 13-digit
        self.assertTrue(barcode_is_trustworthy("0071234567890"))   # leading zeros
        self.assertFalse(barcode_is_trustworthy("12345"))          # too short
        self.assertFalse(barcode_is_trustworthy("0000000000000"))  # all zeros
        self.assertFalse(barcode_is_trustworthy("12345678"))       # placeholder
        self.assertFalse(barcode_is_trustworthy(""))


class TestAbv(unittest.TestCase):
    def test_zero_means_unknown(self):
        # ABV = 0.0 may mean unknown, not verified zero alcohol.
        self.assertIsNone(parse_abv(0.0))
        self.assertIsNone(parse_abv("0"))
        self.assertIsNone(parse_abv("0.0%"))

    def test_valid(self):
        self.assertEqual(parse_abv("4.5"), 4.5)
        self.assertEqual(parse_abv("6.7%"), 6.7)

    def test_missing_and_implausible(self):
        self.assertIsNone(parse_abv(None))
        self.assertIsNone(parse_abv(""))
        self.assertIsNone(parse_abv("abc"))
        self.assertIsNone(parse_abv(99.9))  # implausible


class TestRelevance(unittest.TestCase):
    def test_beer_term(self):
        ok, _ = is_relevant_beverage("Punk IPA", "Beers", "Brewdog", ["beer"])
        self.assertTrue(ok)

    def test_empty_rejected(self):
        ok, reason = is_relevant_beverage("", "", "", ["beer"])
        self.assertFalse(ok)
        self.assertTrue(reason)


if __name__ == "__main__":
    unittest.main()
