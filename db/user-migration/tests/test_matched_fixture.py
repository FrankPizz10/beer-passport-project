"""Pure-Python integration test for the matched-profile rehearsal path.

Generates the production-shape fixture, parses it, applies the scope
stage, and runs the real transform stage in memory. No database is
touched: the database load itself is rehearsal step R3, gated on
Frank's approval of the exact commands.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
MIGRATION_DIR = os.path.dirname(HERE)
sys.path.insert(0, MIGRATION_DIR)

from dump_parser import parse_dump          # noqa: E402
from transform import transform_all         # noqa: E402
from user_scope import apply_matched_scope, load_matched_uids  # noqa: E402
import make_fixture_matched                 # noqa: E402


class MatchedFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="matched-fixture-")
        subprocess.run(
            [sys.executable,
             os.path.join(MIGRATION_DIR, "make_fixture_matched.py"), cls.tmp],
            check=True, capture_output=True)
        with open(os.path.join(cls.tmp, "matched_user_tables.sql"),
                  encoding="utf-8") as f:
            cls.parsed = parse_dump(f.read())
        with open(os.path.join(cls.tmp, "matched_expected.json"),
                  encoding="utf-8") as f:
            cls.expected = json.load(f)
        cls.matched = load_matched_uids(
            os.path.join(cls.tmp, "matched_allowlist.txt"))

    def test_allowlist_is_exactly_the_matched_set(self):
        self.assertEqual(len(self.matched), 294)

    def test_scope_accounting_matches_expected(self):
        _, accounting = apply_matched_scope(self.parsed, self.matched)
        for table, exp in self.expected.items():
            if isinstance(exp, dict):
                self.assertEqual(accounting[table], exp, table)
        self.assertEqual(accounting["allowlist_size"], 294)

    def test_transform_of_scoped_rows_is_clean(self):
        scoped, _ = apply_matched_scope(self.parsed, self.matched)
        beer_ids = set(make_fixture_matched.BEER_IDS)
        clean, rejects, _ = transform_all(
            scoped, valid_beer_ids=beer_ids, run_ts="2026-11-22 00:00:00")
        self.assertEqual(rejects, [])
        for table, exp in self.expected.items():
            if isinstance(exp, dict):
                self.assertEqual(len(clean[table]), exp["kept"], table)

    def test_unscoped_transform_would_load_all_users(self):
        # Control: without the scope stage the same fixture transforms
        # all 299 users, proving the exclusions come from scoping.
        beer_ids = set(make_fixture_matched.BEER_IDS)
        clean, rejects, _ = transform_all(
            self.parsed, valid_beer_ids=beer_ids,
            run_ts="2026-11-22 00:00:00")
        self.assertEqual(rejects, [])
        self.assertEqual(len(clean["users"]), 299)


if __name__ == "__main__":
    unittest.main()
