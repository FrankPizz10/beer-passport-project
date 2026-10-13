# Image-Source Readiness Checklist

Metadata and checks an eventual image pilot must capture per product.
**Do not fetch images or begin that pilot here.** This checklist defines
readiness so a future run is auditable.

## Per-product capture

- [ ] **Product identity confidence**: the review outcome (Useful
      addition) and the evidence behind it (source record, baseline
      comparison, reviewer, date).
- [ ] **Barcode/name linkage**: the exact barcode and product name the
      image is claimed to depict; how the linkage was established
      (barcode search, brand+flavor search).
- [ ] **Image relevance**: does the image show the front of the actual
      package (not a generic brand shot, not a different flavor)?
- [ ] **Image source URL**: the page the image came from, not just the
      image file URL.
- [ ] **Retrieval date**: when the image was fetched.
- [ ] **Reuse terms/license**: the license or terms stated by the image
      source (e.g. CC BY-SA for OFF product images, with the caveat that
      label artwork may carry third-party copyright). Unclear terms =
      do not use.
- [ ] **Attribution**: the credit line the license requires, stored with
      the image record.

## Pilot discipline

- Start from the curated set only (`../pilot/curated_useful_additions.csv`,
  17 records), not the raw `new_candidate` pool.
- Record failures by type: no image found, wrong flavor shown,
  unclear license, low quality. Do not collapse into one score.
- Keep image binaries and license metadata together; one without the
  other is not a usable asset.
- Re-verify licensing before any production display; pilot collection
  is not production clearance.

## Related

- Curated set: `../pilot/curated_useful_additions.csv`
- OFF image licensing notes: `03-source-and-data-governance.md`
- Pilot limitations: `../pilot/PILOT_REPORT_2026-10-13.md` (seltzer-heavy
  n=30, directional only)
