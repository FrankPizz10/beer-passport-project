"""Tests for the catalog import transforms and validation."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from catalog_import import (  # noqa: E402
    ImportDataError,
    build_tables,
    t_add_user,
    t_bool_flag,
    t_fk,
    t_float,
    t_timestamp,
    t_upc,
    write_outputs,
)


class TransformTests(unittest.TestCase):
    def test_fk_null_conventions(self):
        self.assertEqual(t_fk(""), r"\N")
        self.assertEqual(t_fk("0"), r"\N")
        self.assertEqual(t_fk("812"), "812")

    def test_fk_rejects_garbage(self):
        with self.assertRaises(ImportDataError):
            t_fk("abc")

    def test_float(self):
        self.assertEqual(t_float(""), r"\N")
        self.assertEqual(t_float("4.5"), "4.5")
        with self.assertRaises(ImportDataError):
            t_float("high")

    def test_upc(self):
        self.assertEqual(t_upc(""), r"\N")
        self.assertEqual(t_upc("0"), r"\N")
        self.assertEqual(t_upc("0085415002331"), "0085415002331")

    def test_upc_rejects_sentinels_and_garbage(self):
        with self.assertRaises(ImportDataError):
            t_upc("2147483647")
        with self.assertRaises(ImportDataError):
            t_upc("7")

    def test_bool_flag(self):
        self.assertEqual(t_bool_flag("1"), "true")
        self.assertEqual(t_bool_flag("0"), "false")
        with self.assertRaises(ImportDataError):
            t_bool_flag("yes")

    def test_timestamp(self):
        self.assertEqual(t_timestamp("2010-07-22T20:00:00.000Z"),
                         "2010-07-22 20:00:00")
        self.assertEqual(t_timestamp(""), r"\N")
        with self.assertRaises(ImportDataError):
            t_timestamp("July 22, 2010")

    def test_add_user(self):
        self.assertEqual(t_add_user("0"), r"\N")
        self.assertEqual(t_add_user("42"), "42")


FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


class BuildTablesTests(unittest.TestCase):
    def test_fixture_builds(self):
        tables, counts = build_tables(FIXTURE_DIR)
        self.assertEqual(counts, {"beers": 2, "breweries": 1,
                                  "categories": 1, "styles": 1})
        beer_rows = tables["beers"].rows
        self.assertEqual(beer_rows[0][8], "0085415002331")  # leading zeros kept
        self.assertEqual(beer_rows[0][10], "true")      # discontinued flag
        self.assertEqual(beer_rows[1][9], r"\N")        # empty descript nulled
        self.assertEqual(tables["breweries"].rows[0][11], r"\N")  # add_user 0

    def test_load_script_has_guard_and_sequence_resets(self):
        import tempfile
        tables, _ = build_tables(FIXTURE_DIR)
        with tempfile.TemporaryDirectory() as out:
            write_outputs(tables, out)
            with open(os.path.join(out, "load.psql")) as fh:
                script = fh.read()
        self.assertIn("initial load only", script)
        self.assertIn("setval('beers_id_seq'", script)
        self.assertIn("\\copy beers", script)


if __name__ == "__main__":
    unittest.main()
