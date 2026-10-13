"""Tests for the image-sourcing module. All sources are mocked; no live API."""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

from src.images import export as export_mod
from src.images import manufacturer, match as match_mod, off_images
from src.images import review as review_mod
from src.images import rights as rights_mod
from src.images.models import (ApprovalStatus, ImageCandidate,
                               MatchConfidence, RightsStatus)
from src.sources.base import SourceError


def make_product(**overrides):
    p = {
        "code": "5449000294708",
        "product_name": "Topo Chico Hard Seltzer",
        "brands": "Topo Chico",
        "url": "https://world.openfoodfacts.org/product/5449000294708",
        "image_front_url": "https://images.openfoodfacts.org/front.jpg",
        "image_url": "https://images.openfoodfacts.org/front.jpg",
        "images": {"1": {"uploader": "kiliweb"}},
    }
    p.update(overrides)
    return p


def make_beverage(**overrides):
    b = {
        "beverage_id": "cand_test",
        "beverage_name": "Topo Chico Hard Seltzer",
        "brand": "Topo Chico",
        "producer": "Topo Chico",
        "barcode": "5449000294708",
    }
    b.update(overrides)
    return b


def mock_client(product=None, fail=False):
    client = MagicMock()
    if fail:
        client.get_json.side_effect = SourceError("boom")
    elif product is None:
        client.get_json.return_value = ({"status": 0}, False)
    else:
        client.get_json.return_value = (
            {"status": 1, "product": product}, False)
    return client


class TestOffImages(unittest.TestCase):
    def test_to_candidate_extracts_metadata(self):
        cand = off_images.to_candidate(make_beverage(), make_product())
        self.assertIsNotNone(cand)
        self.assertEqual(cand.source_type, "openfoodfacts")
        self.assertEqual(cand.image_url,
                         "https://images.openfoodfacts.org/front.jpg")
        self.assertEqual(cand.contributor, "kiliweb")
        self.assertIn("Attribution-ShareAlike", cand.license_name)
        self.assertTrue(cand.permission_evidence.startswith("https://"))
        self.assertTrue(cand.retrieved_at)

    def test_to_candidate_none_without_image(self):
        p = make_product(image_front_url="", image_url="")
        self.assertIsNone(off_images.to_candidate(make_beverage(), p))

    def test_find_candidates_product_found(self):
        cands, product, err = off_images.find_candidates(
            make_beverage(), mock_client(make_product()))
        self.assertIsNone(err)
        self.assertIsNotNone(product)
        self.assertEqual(len(cands), 1)

    def test_find_candidates_product_missing(self):
        cands, product, err = off_images.find_candidates(
            make_beverage(), mock_client(None))
        self.assertIsNone(err)
        self.assertIsNone(product)
        self.assertEqual(cands, [])

    def test_find_candidates_source_failure_not_zero_coverage(self):
        cands, product, err = off_images.find_candidates(
            make_beverage(), mock_client(fail=True))
        self.assertIsNotNone(err)
        self.assertEqual(cands, [])

    def test_find_candidates_no_barcode(self):
        cands, product, err = off_images.find_candidates(
            make_beverage(barcode=""), mock_client(make_product()))
        self.assertIsNone(err)
        self.assertEqual(cands, [])


class TestMatch(unittest.TestCase):
    def test_barcode_exact(self):
        conf, ev = match_mod.evaluate_off_match(
            make_beverage(), make_product())
        self.assertEqual(conf, MatchConfidence.BARCODE_EXACT.value)
        self.assertTrue(any("barcode exact" in e for e in ev))

    def test_barcode_mismatch(self):
        conf, _ = match_mod.evaluate_off_match(
            make_beverage(barcode="12345678"), make_product())
        self.assertEqual(conf, MatchConfidence.MISMATCH.value)

    def test_name_brand_fuzzy_without_barcode(self):
        bev = make_beverage(barcode="")
        prod = make_product(code="")
        conf, _ = match_mod.evaluate_off_match(bev, prod)
        self.assertEqual(conf, MatchConfidence.NAME_BRAND_FLAVOR.value)

    def test_brand_only(self):
        bev = make_beverage(beverage_name="Topo Chico Margarita",
                            barcode="")
        prod = make_product(code="", product_name="Topo Chico Ranch Water")
        conf, ev = match_mod.evaluate_off_match(bev, prod)
        self.assertEqual(conf, MatchConfidence.BRAND_ONLY.value)
        self.assertTrue(any("flavor" in e for e in ev))

    def test_mismatch(self):
        bev = make_beverage(beverage_name="White Claw Mango", brand="White Claw",
                            barcode="")
        prod = make_product(code="", product_name="Topo Chico Hard Seltzer",
                            brands="Topo Chico")
        conf, _ = match_mod.evaluate_off_match(bev, prod)
        self.assertEqual(conf, MatchConfidence.MISMATCH.value)

    def test_missing_name_ambiguous(self):
        conf, _ = match_mod.evaluate_off_match(
            make_beverage(beverage_name="", barcode=""), make_product(code=""))
        self.assertEqual(conf, MatchConfidence.AMBIGUOUS.value)


class TestRights(unittest.TestCase):
    def test_off_approved_with_documented_basis(self):
        cand = off_images.to_candidate(make_beverage(), make_product())
        rights_mod.classify_rights(cand)
        self.assertEqual(cand.rights_status, RightsStatus.APPROVED.value)
        self.assertTrue(any("artwork" in n or "label" in n
                            for n in cand.rights_notes))

    def test_off_review_without_basis(self):
        cand = ImageCandidate(source_type="openfoodfacts", image_url="http://x/y.jpg",
                              permission_basis="")
        rights_mod.classify_rights(cand)
        self.assertEqual(cand.rights_status, RightsStatus.RIGHTS_REVIEW.value)

    def test_manufacturer_needs_permission(self):
        bev, img = make_beverage(), {"image_url": "http://brand/x.jpg",
                                     "source_page_url": "http://brand/p"}
        cand = manufacturer.build_candidate(bev, img)
        self.assertEqual(cand.rights_status, RightsStatus.RIGHTS_REVIEW.value)

    def test_manufacturer_approved_with_permission(self):
        img = {"image_url": "http://brand/x.jpg",
               "source_page_url": "http://brand/p",
               "permission_basis": "written grant",
               "permission_evidence": "http://brand/license",
               "permission_scope": "commercial app use and hosting"}
        cand = manufacturer.build_candidate(make_beverage(), img)
        self.assertEqual(cand.rights_status, RightsStatus.APPROVED.value)


class TestReview(unittest.TestCase):
    def _cand(self, match, rights):
        return ImageCandidate(match_confidence=match, rights_status=rights)

    def test_approved(self):
        c = review_mod.decide(self._cand(MatchConfidence.BARCODE_EXACT.value,
                                         RightsStatus.APPROVED.value))
        self.assertEqual(c.approval_status, ApprovalStatus.APPROVED.value)

    def test_rejected_on_mismatch(self):
        c = review_mod.decide(self._cand(MatchConfidence.MISMATCH.value,
                                         RightsStatus.APPROVED.value))
        self.assertEqual(c.approval_status, ApprovalStatus.REJECTED.value)
        self.assertIn("mismatch", c.rejection_reason)

    def test_rejected_on_rights(self):
        c = review_mod.decide(self._cand(MatchConfidence.BARCODE_EXACT.value,
                                         RightsStatus.REJECTED.value))
        self.assertEqual(c.approval_status, ApprovalStatus.REJECTED.value)

    def test_needs_review_brand_only(self):
        c = review_mod.decide(self._cand(MatchConfidence.BRAND_ONLY.value,
                                         RightsStatus.APPROVED.value))
        self.assertEqual(c.approval_status, ApprovalStatus.NEEDS_REVIEW.value)

    def test_needs_review_rights(self):
        c = review_mod.decide(self._cand(MatchConfidence.BARCODE_EXACT.value,
                                          RightsStatus.RIGHTS_REVIEW.value))
        self.assertEqual(c.approval_status, ApprovalStatus.NEEDS_REVIEW.value)

    def test_fallback_record(self):
        c = review_mod.fallback_record(make_beverage())
        self.assertEqual(c.approval_status, ApprovalStatus.FALLBACK.value)
        self.assertEqual(c.match_confidence,
                         MatchConfidence.NO_CANDIDATE.value)


class TestExport(unittest.TestCase):
    def test_export_writes_files(self):
        cands = [review_mod.fallback_record(make_beverage())]
        with TemporaryDirectory() as tmp:
            paths = export_mod.export_all(Path(tmp), cands, {"n": 1})
            for key in ("image_candidates", "image_candidates_json",
                        "review_queue", "approved", "run_summary"):
                self.assertTrue(Path(paths[key]).exists(), key)
            rows = json.loads(Path(paths["image_candidates_json"]).read_text())
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["approval_status"], "fallback")


if __name__ == "__main__":
    unittest.main()
