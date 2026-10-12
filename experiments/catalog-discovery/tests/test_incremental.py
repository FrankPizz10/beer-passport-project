"""Tests for incremental state and graceful source failure. No network access."""
import csv
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from src import state as state_mod
from src.sources.base import CachedClient, SourceError


def cand(cid, sources=("openfoodfacts",)):
    return {
        "candidate_id": cid,
        "name": "Test Beer",
        "source_names": list(sources),
        "source_record_ids": ["rec-1"],
        "source_urls": ["http://example.com/1"],
        "match_status": "new_candidate",
        "match_confidence": 0.0,
        "existing_beerpassport_id": "",
        "review_reasons": [],
        "missing_fields": [],
        "first_discovered_at": "",
        "last_seen_at": "",
    }


class TestStateMerging(unittest.TestCase):
    def test_repeat_run_does_not_inflate(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            state = state_mod.load_state(d)
            self.assertEqual(state_mod.merge_candidate(state, cand("c1")), "new")
            # Same candidate seen again: updated, not new.
            self.assertEqual(state_mod.merge_candidate(state, cand("c1")), "updated")
            self.assertEqual(len(state.candidates), 1)
            state_mod.save_state(d, state)
            reloaded = state_mod.load_state(d)
            self.assertEqual(len(reloaded.candidates), 1)
            self.assertTrue(reloaded.candidates["c1"]["first_discovered_at"])

    def test_second_source_updates_associations(self):
        state = state_mod.State()
        state_mod.merge_candidate(state, cand("c1", sources=("openfoodfacts",)))
        c2 = cand("c1", sources=("openfoodfacts", "manual"))
        c2["source_record_ids"] = ["rec-1", "rec-2"]
        c2["source_urls"] = ["http://example.com/1", "http://example.com/2"]
        self.assertEqual(state_mod.merge_candidate(state, c2), "updated")
        merged = state.candidates["c1"]
        self.assertEqual(len(state.candidates), 1)  # no duplicate created
        self.assertIn("manual", merged["source_names"])
        self.assertIn("rec-2", merged["source_record_ids"])


class TestCandidateIdentity(unittest.TestCase):
    def test_same_barcode_across_search_terms_merges(self):
        # The same Open Food Facts product surfacing under two search terms
        # carries the same barcode, so it must resolve to one candidate.
        from src.match import make_candidate_id
        id_a = make_candidate_id("openfoodfacts", "5056025440449",
                                 "Punk IPA", "Brewdog")
        id_b = make_candidate_id("openfoodfacts", "5056025440449",
                                 "PUNK IPA", "BREWDOG")
        self.assertEqual(id_a, id_b)
        state = state_mod.State()
        self.assertEqual(state_mod.merge_candidate(state, cand(id_a)), "new")
        self.assertEqual(state_mod.merge_candidate(state, cand(id_a)),
                         "updated")
        self.assertEqual(len(state.candidates), 1)

    def test_cross_source_merge_without_record_ids_is_unsupported(self):
        # Known limitation, documented in the README: when source record ids
        # are missing, the source name is part of the identity hash, so the
        # same product reported by two different sources does NOT merge.
        # (With the current sources this cannot happen: Open Brewery DB
        # yields producers only, never product candidates.)
        from src.match import make_candidate_id
        id_a = make_candidate_id("source_a", "", "Punk IPA", "Brewdog")
        id_b = make_candidate_id("source_b", "", "Punk IPA", "Brewdog")
        self.assertNotEqual(id_a, id_b)


class TestSourceFailure(unittest.TestCase):
    def test_client_raises_after_retries(self):
        import requests
        with tempfile.TemporaryDirectory() as tmp:
            client = CachedClient(Path(tmp), delay=0, timeout=1, max_retries=2)
            client.session.get = mock.Mock(
                side_effect=requests.ConnectionError("nope"))
            with self.assertRaises(SourceError):
                client.get_json("http://example.com/x")

    def test_one_source_failing_does_not_stop_run(self):
        # Build a minimal baseline in a temp dir and run with OBDB failing.
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "cache").mkdir()
            (d / "state").mkdir()
            out = d / "output"
            self._write_baseline(d)

            cfg = SimpleNamespace(
                data_dir=d, output_dir=out, cache_dir=d / "cache",
                state_dir=d / "state", limit=10, refresh=False,
                brewery_pages=1, fuzzy_threshold=88.0, review_threshold=70.0,
                abv_conflict=2.0, request_timeout=5, max_retries=1,
                off_delay=0, obdb_delay=0,
                search_terms=["beer"],
            )
            product = {
                "source_name": "openfoodfacts", "source_record_id": "111",
                "original_name": "Brand New IPA", "brand": "NewCo",
                "categories": "Beers", "abv": 6.0, "abv_unknown": False,
                "barcode": "1234567890128", "country": "US", "quantity": "",
                "source_url": "http://example.com/p/111",
                "retrieved_note": "", "review_reasons": [],
            }
            from src import main as main_mod
            with mock.patch("src.sources.openbrewerydb.fetch_breweries",
                            side_effect=SourceError("blocked")), \
                 mock.patch("src.sources.openfoodfacts.fetch_products",
                            return_value=([product], {"terms_ok": 1})):
                summary = main_mod.run(cfg)

            self.assertTrue(any("openbrewerydb" in e for e in summary["errors"]))
            self.assertEqual(summary["sources"]["openfoodfacts"]["raw_records"], 1)
            self.assertTrue((out / "beverage_candidates.csv").exists())
            self.assertTrue((out / "run_summary.json").exists())

    def _write_baseline(self, d: Path):
        specs = {
            "LiveBeers.csv": (["id", "brewery_id", "name", "cat_id",
                               "style_id", "abv", "ibu", "srm", "upc",
                               "descript", "last_mod"],
                              [["1", "1", "Old Ale", "1", "1", "5.0", "", "",
                                 "", "", ""]]),
            "LiveBreweries.csv": (["id", "name", "address1", "address2",
                                   "city", "state", "code", "country",
                                   "phone", "website", "descript", "add_user"],
                                  [["1", "Old Brewery", "", "", "", "", "",
                                    "", "", "", "", ""]]),
            "LiveCategories.csv": (["id", "cat_name", "last_mod"],
                                   [["1", "British Ale", ""]]),
            "LiveStyles.csv": (["id", "cat_id", "style_name", "last_mod"],
                               [["1", "1", "Old Ale Style", ""]]),
        }
        for name, (headers, rows) in specs.items():
            with open(d / name, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(headers)
                w.writerows(rows)


class TestChunkedBaseline(unittest.TestCase):
    def test_parts_reassemble_without_row_loss(self):
        # Large exports are committed as <stem>.partNN.csv chunks; the
        # loader must reassemble them exactly, with no dropped rows.
        from src.baseline import load_baseline
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            headers = ["id", "brewery_id", "name", "cat_id", "style_id",
                       "abv", "ibu", "srm", "upc", "descript", "last_mod"]
            rows = [[str(i), "1", f"Beer {i}", "1", "1", "5.0", "", "", "",
                     "", ""] for i in range(1, 251)]
            with open(d / "LiveBeers.part01.csv", "w", newline="",
                      encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(headers)
                w.writerows(rows[:100])
            with open(d / "LiveBeers.part02.csv", "w", newline="",
                      encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerows(rows[100:200])
            with open(d / "LiveBeers.part03.csv", "w", newline="",
                      encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerows(rows[200:])
            for name, h, r in [
                    ("LiveBreweries.csv",
                     ["id", "name", "address1", "address2", "city", "state",
                      "code", "country", "phone", "website", "descript",
                      "add_user"],
                     [["1", "Brew Co", "", "", "", "", "", "", "", "", "",
                       ""]]),
                    ("LiveCategories.csv", ["id", "cat_name", "last_mod"],
                     [["1", "British Ale", ""]]),
                    ("LiveStyles.csv",
                     ["id", "cat_id", "style_name", "last_mod"],
                     [["1", "1", "Style", ""]])]:
                with open(d / name, "w", newline="", encoding="utf-8") as f:
                    w = csv.writer(f)
                    w.writerow(h)
                    w.writerows(r)
            base = load_baseline(d)
            self.assertEqual(len(base.beers), 250)
            self.assertEqual(base.beers[0]["name"], "Beer 1")
            self.assertEqual(base.beers[99]["name"], "Beer 100")
            self.assertEqual(base.beers[100]["name"], "Beer 101")
            self.assertEqual(base.beers[249]["name"], "Beer 250")


if __name__ == "__main__":
    unittest.main()
