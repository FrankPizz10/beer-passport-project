# Catalog Refresh Measurement (2026-10-21)

Question: can the existing pipeline produce a noticeable catalog
improvement for a relaunch? Method: one bounded discovery run on an
isolated copy (fresh state), image measurement on the results, and a
manual classification of a seeded sample. Committed discovery state
and outputs were not touched.

## Run

```
python -m src.main --limit 2000 --brewery-source dataset \
  --search-terms beer cider "hard seltzer" "hard iced tea" \
  "malt beverage" "ready to drink"
```

OFF returned 1,480 records before three terms were truncated by
repeated 503s (beer p2, cider p6, malt beverage p3). The pool below is
therefore partial, not exhaustive.

| Outcome | Count |
|---|---:|
| Candidates | 1,479 |
| new_candidate | 728 |
| needs_review | 705 |
| existing | 46 |

All 1,479 candidates carry trustworthy barcodes. ABV completeness is
weak (12.8%), the known OFF gap.

needs_review composition: insufficient evidence 323, uncertain
category 88, possible-duplicate fuzzy matches ~150, alias
flavor-uncertain 17, remainder mixed.

## Image measurement

From the already-fetched OFF data (no extra API calls):

| Pool | With OFF front image |
|---|---:|
| new_candidate | 596/728 (82%) |
| needs_review | 621/705 (88%) |
| existing | 40/46 (87%) |

End-to-end validation of the image workflow on 40 new candidates:
40/40 approved (barcode-exact + rights approved), 0 errors.

## Sample classification (n=30, seed 20261021)

Classified by hand against scope (docs/01). Full table:
`refresh_sample30_classified.csv`.

| Class | Count |
|---|---:|
| Useful addition | 17 (57%) |
| Not a useful beverage candidate | 11 (37%) |
| Uncertain | 2 |

The 11 not-useful are overwhelmingly NON-beverages pulled in by the
cider/malt search terms: potato crisps x3, breakfast cereal, chutney,
vinegar gummies, cooking vinegar, a vinegar drink, a ready meal, a
malt health-drink powder, a smoothie. This is a relevance-filter gap,
fixable with negative category filters, not a matcher failure.

The 2 uncertain: a non-alcoholic apple cider (juice boundary) and a
bottled Scotch whisky (owner decision still open).

Also observed: pack-variant duplication inside the new pool (same
product, several barcodes: Old Mout x2, Vizzy x2). Promotion needs a
variant policy.

## Estimated yield

At the sampled 57% useful rate, the 728 new candidates imply roughly
400 genuinely new, in-scope products from this one partial run, about
340 of them with images. The needs_review pool holds more, unquantified.
That is a modern, recognizable, photo-bearing layer the 2010-era
baseline cannot get from backfill: the baseline has effectively no
usable barcodes (0/5,894 trustworthy; see the Oct 21 catalog test).

## Recommended path

1. Two or three more bounded runs with negative category filters added
   and the truncated terms retried, plus alias expansion where evidence
   supports it. Target 800-1,200 verified new products with images.
2. Promote per docs/05 (provenance, batch, rollback). Schema first:
   the app schema has no image fields (known 2.0 blocker).
3. Backend and domain restoration is separate work and needs owner
   AWS write access (the agent IAM is read-only).

## Limitations

n=30 sample, directional. 503 truncation means the pool understates
OFF coverage. Useful rate will move with the relevance fix. Image
approval remains experiment-level pending legal review (docs/07).
