"""Synthetic-fixture tests for src.user_scope (no database required).

All UIDs and rows below are invented. The production-shape test mirrors
the real reconciliation counts (299 recovered users, 294 matched,
5 MySQL-only, 15 Firebase-only) with synthetic identifiers only.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.user_scope import apply_matched_scope, load_matched_uids


def small_fixture():
    parsed = {
        "users": [
            {"id": 1, "uid": "uid-a"},
            {"id": 2, "uid": "uid-b"},
            {"id": 3, "uid": "uid-c"},
            {"id": 4, "uid": "uid-d"},
            {"id": 5, "uid": "uid-e"},   # MySQL-only in this fixture
            {"id": 6, "uid": "uid-f"},   # MySQL-only in this fixture
        ],
        "user_beers": [
            {"id": 11, "user_id": 1, "beer_id": 100},
            {"id": 12, "user_id": 5, "beer_id": 100},
            {"id": 13, "user_id": 999, "beer_id": 100},  # unknown user
        ],
        "user_badges": [
            {"id": 21, "user_id": 2, "collection_id": 7},
            {"id": 22, "user_id": 6, "collection_id": 7},
        ],
        "notifications": [
            {"id": 31, "user_id": 3},
            {"id": 32, "user_id": 5},
        ],
        "friends": [
            {"id": 41, "user_1": 1, "user_2": 2},   # both matched
            {"id": 42, "user_1": 2, "user_2": 1},   # reversed, both matched
            {"id": 43, "user_1": 1, "user_2": 5},   # one endpoint out
            {"id": 44, "user_1": 5, "user_2": 6},   # both out
        ],
        "collections": [{"id": 7, "name": "Synthetic Collection"}],
        "collection_beers": [{"id": 51, "collection_id": 7, "beer_id": 100}],
    }
    matched = {"uid-a", "uid-b", "uid-c", "uid-d", "uid-ghost"}
    return parsed, matched


class MatchedScopeTests(unittest.TestCase):
    def test_users_scoped_by_uid(self):
        parsed, matched = small_fixture()
        scoped, acc = apply_matched_scope(parsed, matched)
        self.assertEqual([r["id"] for r in scoped["users"]], [1, 2, 3, 4])
        self.assertEqual(acc["users"],
                         {"source": 6, "kept": 4, "excluded_unmatched": 2})

    def test_dependents_follow_their_user(self):
        parsed, matched = small_fixture()
        scoped, acc = apply_matched_scope(parsed, matched)
        self.assertEqual([r["id"] for r in scoped["user_beers"]], [11, 13])
        self.assertEqual([r["id"] for r in scoped["user_badges"]], [21])
        self.assertEqual([r["id"] for r in scoped["notifications"]], [31])
        self.assertEqual(acc["user_badges"]["excluded_unmatched"], 1)
        self.assertEqual(acc["notifications"]["excluded_unmatched"], 1)

    def test_unknown_user_reference_is_kept_for_transform(self):
        # user_id 999 is not in the users table at all: a data error for
        # the transform stage's orphan checks, not a scope exclusion.
        parsed, matched = small_fixture()
        scoped, _ = apply_matched_scope(parsed, matched)
        self.assertIn(13, [r["id"] for r in scoped["user_beers"]])

    def test_friend_pair_needs_both_endpoints(self):
        parsed, matched = small_fixture()
        scoped, acc = apply_matched_scope(parsed, matched)
        self.assertEqual([r["id"] for r in scoped["friends"]], [41, 42])
        self.assertEqual(acc["friends"]["excluded_unmatched"], 2)

    def test_collections_are_unscoped(self):
        parsed, matched = small_fixture()
        scoped, acc = apply_matched_scope(parsed, matched)
        self.assertEqual(scoped["collections"], parsed["collections"])
        self.assertEqual(scoped["collection_beers"],
                         parsed["collection_beers"])
        self.assertEqual(acc["collections"]["excluded_unmatched"], 0)

    def test_accounting_invariant_every_table(self):
        parsed, matched = small_fixture()
        _, acc = apply_matched_scope(parsed, matched)
        for table, counts in acc.items():
            if isinstance(counts, dict):
                self.assertEqual(
                    counts["source"],
                    counts["kept"] + counts["excluded_unmatched"],
                    table)

    def test_matched_without_profile_count(self):
        # "uid-ghost" is matched (a Firebase account) with no user row:
        # the Firebase-only analog.
        parsed, matched = small_fixture()
        _, acc = apply_matched_scope(parsed, matched)
        self.assertEqual(acc["matched_uids_without_profile"], 1)

    def test_empty_allowlist_excludes_all_known_users(self):
        parsed, _ = small_fixture()
        scoped, acc = apply_matched_scope(parsed, set())
        self.assertEqual(scoped["users"], [])
        self.assertEqual([r["id"] for r in scoped["user_beers"]], [13])
        self.assertEqual(scoped["friends"], [])
        self.assertEqual(acc["matched_uids_without_profile"], 0)

    def test_production_shape_counts(self):
        users = [{"id": i, "uid": f"synthetic-uid-{i}"}
                 for i in range(1, 300)]            # 299 recovered users
        matched = {f"synthetic-uid-{i}" for i in range(1, 295)}  # 294
        matched |= {f"firebase-only-{i}" for i in range(15)}     # 15
        parsed = {"users": users,
                  "friends": [{"id": 1, "user_1": 1, "user_2": 299},
                              {"id": 2, "user_1": 1, "user_2": 2}]}
        scoped, acc = apply_matched_scope(parsed, matched)
        self.assertEqual(acc["users"]["kept"], 294)
        self.assertEqual(acc["users"]["excluded_unmatched"], 5)
        self.assertEqual(acc["matched_uids_without_profile"], 15)
        self.assertEqual([r["id"] for r in scoped["friends"]], [2])


class LoadMatchedUidsTests(unittest.TestCase):
    def test_parsing_blanks_comments_duplicates_whitespace(self):
        with tempfile.NamedTemporaryFile(
                "w", suffix=".txt", delete=False) as fh:
            fh.write("uid-a\n\n# comment\n  uid-b  \nuid-a\nuid-c\n")
            path = fh.name
        try:
            self.assertEqual(load_matched_uids(path),
                             {"uid-a", "uid-b", "uid-c"})
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
