# Image-Sourcing Pilot Report (2026-10-13)

First run of the image-sourcing experiment against the 17 curated
useful additions from the catalog-quality pilot.

## Method

```
python -m src.images.cli --input pilot/curated_useful_additions.csv
```

Barcode-first OFF product lookup (17 API calls, within rate limits, no
usage form per owner decision). Product identity and rights evaluated
independently. URLs and metadata only; no image binaries downloaded.

## Results

| Outcome | Count |
|---|---:|
| Beverages processed | 17 |
| Approved (barcode-exact + rights approved) | 12 |
| Fallback (no OFF image; beverage stays valid) | 5 |
| Needs review | 0 |
| Rejected | 0 |
| Source errors | 0 |

All 12 approvals rest on barcode-exact matches, the strongest identity
signal. Every approved row carries image URL, CC BY-SA license
statement, attribution text, contributor, and permission evidence.

The 5 fallbacks (Nordic Wolf, Stelz, Doort, Ravini, Vista Bay) are
smaller European brands with no OFF image. They are flagged for
category fallback artwork, not rejected as beverages.

## Outputs

- `output/images/image_candidates.csv` - all 17 records
- `output/images/image_candidates.json` - structured metadata
- `output/images/image_approved.csv` - 12 approved
- `output/images/image_review_queue.csv` - empty this run
- `output/images/image_run_summary.json` - counts

## Limitations

- n=17, all hard seltzers, all OFF-sourced. Not proof of broad coverage.
- Approval is experiment-level, not production clearance: attribution
  format, CC BY-SA version, and embedded trademark risk still need
  legal review before any production display.
- Front-image correctness was not visually verified; barcode-exact is
  strong evidence but not a visual check.
- Manufacturer path is schema-only; no automated manufacturer discovery
  (per owner decision: no manual lookups at 10k+ scale).

## Next steps

- Visual spot-check of approved images.
- Run against a representative sample of existing catalog beverages.
- Legal review of the open questions in docs/07 before production use.
