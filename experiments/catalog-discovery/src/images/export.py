"""Export image candidates, review queue, and run summary."""
from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

from .models import ApprovalStatus, ImageCandidate

log = logging.getLogger(__name__)

CANDIDATE_COLUMNS = [
    "beverage_id", "barcode", "beverage_name", "brand", "producer",
    "flavor_variant", "packaging", "source_type", "source_record_url",
    "image_url", "license_name", "license_version", "license_url",
    "attribution_text", "contributor", "permission_basis",
    "permission_evidence", "retrieved_at", "match_evidence",
    "match_confidence", "rights_status", "rights_notes",
    "approval_status", "reviewer_notes", "rejection_reason",
]


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            flat = {}
            for c in columns:
                v = row.get(c, "")
                if isinstance(v, (list, tuple)):
                    v = "; ".join(str(x) for x in v)
                flat[c] = v
            w.writerow(flat)
    log.info("Wrote %s (%d rows)", path, len(rows))


def export_all(output_dir: Path, candidates: list[ImageCandidate],
               summary: dict) -> dict[str, str]:
    """Write candidate report, JSON metadata, review queue, and summary."""
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = [c.to_dict() for c in candidates]
    paths = {}

    paths["image_candidates"] = str(output_dir / "image_candidates.csv")
    _write_csv(output_dir / "image_candidates.csv", CANDIDATE_COLUMNS, rows)

    meta_path = output_dir / "image_candidates.json"
    meta_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False),
                         encoding="utf-8")
    paths["image_candidates_json"] = str(meta_path)

    review = [c.to_dict() for c in candidates
              if c.approval_status == ApprovalStatus.NEEDS_REVIEW.value]
    paths["review_queue"] = str(output_dir / "image_review_queue.csv")
    _write_csv(output_dir / "image_review_queue.csv", CANDIDATE_COLUMNS, review)

    approved = [c.to_dict() for c in candidates
                if c.approval_status == ApprovalStatus.APPROVED.value]
    paths["approved"] = str(output_dir / "image_approved.csv")
    _write_csv(output_dir / "image_approved.csv", CANDIDATE_COLUMNS, approved)

    summary_path = output_dir / "image_run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False),
                            encoding="utf-8")
    paths["run_summary"] = str(summary_path)
    return paths
