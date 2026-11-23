"""Drift guard: the vendored scope stage must match the canonical copy.

db/src/user_scope.py is canonical (PR #12). The user-migration package
vendors a copy so it can run standalone on the box; if the two files
ever differ, this test fails and the copies must be reconciled before
either is used.
"""

import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PACKAGE_COPY = os.path.join(HERE, "..", "user_scope.py")
CANONICAL = os.path.join(HERE, "..", "..", "src", "user_scope.py")


class VendoredScopeTests(unittest.TestCase):
    def test_vendored_copy_matches_canonical(self):
        with open(PACKAGE_COPY, "rb") as f:
            vendored = f.read()
        with open(CANONICAL, "rb") as f:
            canonical = f.read()
        self.assertEqual(vendored, canonical)


if __name__ == "__main__":
    unittest.main()
