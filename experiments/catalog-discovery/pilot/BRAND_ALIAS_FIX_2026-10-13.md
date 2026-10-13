# Brand-to-producer alias fix (2026-10-13)

Follow-up to `PILOT_REPORT_2026-10-13.md`, which found that 5 of 24
sampled `new_candidate` records were already in the baseline under a
different brewery name. This note documents the fix, the evidence, and
the measured before/after on the same 30-candidate pilot sample.

The original pilot report and sample artifacts are preserved intact;
before-fix values are quoted below.

## Problem

Open Food Facts records carry the consumer brand ("White Claw") while
the BeerPassport baseline stores the producing company ("Mark Anthony
Brewing"). The matcher's producer comparison saw no agreement, so
genuine duplicates scored 49-77 (below the 88 fuzzy threshold) and were
classified `new_candidate`.

## Implementation

**`data/brand_aliases.json`** (new): three evidence-backed brand ->
producer relationships. Each entry carries evidence URLs and a note.
Entries marked `ambiguous: true` are loaded for documentation but never
used for matching.

| Brand | Producer | Evidence |
|---|---|---|
| White Claw | Mark Anthony Brewing | https://en.wikipedia.org/wiki/White_Claw_Hard_Seltzer |
| Truly | Boston Beer Company | https://en.wikipedia.org/wiki/Truly_(brand) |
| High Noon | E. & J. Gallo Winery | https://en.wikipedia.org/wiki/High_Noon_(seltzer) |

**`src/match.py`** (modified):

- `load_brand_aliases()`: loads non-ambiguous aliases; missing file is
  not an error.
- `resolve_producer_alias()`: maps a brand to its producer from the raw
  (pre-normalization) string, so multi-brand OFF values like "Hard
  Seltzer Beverage Company LLC, Truly, Truly Unruly" resolve.
- `producer_agreement_score()`: alias-resolved producer equality scores
  100; otherwise the direct fuzzy score. An alias is producer evidence,
  not proof of product identity.
- `flavor_signature()`: flavor-identifying tokens (name minus brand
  minus category/base descriptors like "hard", "seltzer", "vodka").
- `fuzzy_score()`: the record's brand is included in its name for
  comparison, because OFF product names often omit the brand the
  baseline embeds ("Hard Seltzer Natural Lime" + brand "White Claw" vs
  baseline "White Claw - Natural Lime").
- `match_record()`: when the producer match came from an alias, the
  record only becomes `existing` if the flavor signatures also match;
  otherwise it goes to `needs_review` ("producer matched via brand
  alias but flavor identity uncertain"). The single-token safeguard and
  ABV-conflict check are unchanged.

**`src/main.py`** (modified): loads aliases from the data dir and passes
them to `build_baseline_index`.

## Tests

61 tests pass (45 prior + 16 new). New coverage:

- The 5 pilot duplicates (White Claw Natural Lime/Lemon, Truly Wild
  Berry, Truly Unruly Berry Blast, High Noon Pineapple) classify as
  `existing` with the correct baseline IDs.
- Negative controls: same-brand different-flavor (White Claw Mango vs
  Natural Lime) does not auto-merge; "Natural Lime" never merges into a
  "Lime" baseline (flavor-signature gate); unsupported brands get no
  boost; ambiguous aliases are ignored.
- Multi-brand OFF strings resolve; ABV conflicts still route to
  `needs_review` even with alias + flavor agreement.
- Prior Blonde/Ambrée regressions and the strong-producer positive
  control still pass.

## Reassessment of the 30-candidate pilot sample

Re-ran the new matcher on the 30 sampled records (isolated copy of the
baseline + aliases; committed discovery state and pilot artifacts
untouched).

Known duplicates:

| Candidate | Before | After | Baseline |
|---|---|---|---|
| White Claw Natural Lime (`cand_db5e08458143`) | new_candidate | existing | 5936 |
| Truly Wild Berry (`cand_ccc58134e403`) | new_candidate | existing | 5954 |
| Truly Unruly Berry Blast (`cand_7effe6325d7d`) | new_candidate | needs_review | 5968 (ABV 8.0 vs 5.0 conflict) |
| High Noon Pineapple (`cand_e0de7cb653bc`) | new_candidate | existing | 6014 |
| White Claw Lemon (`cand_dc5a292cafc1`) | new_candidate | existing | 5941 |

The Truly Unruly record is correctly held in review: the alias and
flavor match, but the source ABV (8.0) conflicts with the baseline (5.0),
and Truly Unruly is genuinely a higher-ABV line. The conflict checker
worked as designed.

Pipeline status counts, before -> after:

| Status | Before | After |
|---|---|---|
| new_candidate | 24 | 18 |
| needs_review | 5 | 6 |
| existing | 1 | 6 |

Other changes: White Claw Raspberry (`needs_review` -> `existing`,
baseline 5937, correct); generic Truly record (`new_candidate` ->
`needs_review`, no flavor to confirm identity, correctly flagged).

Useful-addition rate among sampled `new_candidate` records (manual
pilot classifications): 16/24 (67%) before -> 16/18 (89%) after. The 6
records that left the `new_candidate` pool were 5 Already-represented
and 1 Uncertain; all 16 Useful additions remain `new_candidate`.

## Limits

- Directional (n=30), not statistically conclusive. No claim is made
  about the raw candidate pool.
- Only three aliases are evidence-backed so far; other brand/producer
  mismatches in the full pool are unaddressed.
- No image-sourcing work was done.
