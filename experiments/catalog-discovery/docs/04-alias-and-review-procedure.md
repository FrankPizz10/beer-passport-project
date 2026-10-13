# Alias and Review Procedure

How brand-to-producer aliases are added, substantiated, tested, and
maintained. Aliases live in `../data/brand_aliases.json`.

## Principle

An alias is **producer evidence, not proof of product identity**. It lets
"White Claw" count as "Mark Anthony Brewing" for producer agreement.
A record still becomes `existing` only with product-level identity
(non-empty, equal flavor signatures). Alias-supported but
flavor-uncertain pairs go to `needs_review`. An alias never auto-merges
two different products from the same company.

## Adding an alias

1. **Evidence first.** Find at least one credible primary or
   strong-secondary source stating the brand is produced by the company
   (brand owner site, company press release, Wikipedia with citations).
   Record the URL and access date.
2. **Check for ambiguity.** Does the brand map to different producers by
   region or over time? (Example pattern: a brand brewed under license by
   different companies in different markets.) If yes, either mark the
   entry `"ambiguous": true` (documented, never used for matching) or
   leave it out entirely. Never encode a guess.
3. **Add the entry**: `brand`, `producer`, `evidence` (URLs),
   `note` (one or two sentences), `ambiguous` (false unless step 2 says
   otherwise).
4. **Test it**: add positive cases (brand record -> correct baseline ID
   as `existing`) and negative controls (same-brand different-flavor
   stays out of `existing`; unsupported brands get no boost) to
   `../tests/test_match.py`. Run the full suite.
5. **Reassess**: re-run the change against a fixed sample (the pilot's
   30-candidate manifest) on an isolated copy and report before/after.

## Regional and licensed relationships

When a brand's producer varies (licensed brewing, regional splits),
do not pick one producer. Options in order of preference:

1. Omit the alias; let those records stay `needs_review`.
2. Add it as `"ambiguous": true` with a note explaining the variance,
   so the next reviewer sees the research instead of redoing it.

## Manual-review outcomes

| Outcome | Meaning | Evidence needed |
|---|---|---|
| Useful addition | Real product, in scope, not in baseline | Source record + barcode/page; no baseline match |
| Already represented | Same beverage is in the baseline | Baseline ID + flavor/brand correspondence |
| Not a useful beverage candidate | Real product but out of scope, or not a beverage | Scope boundary it violates |
| Uncertain | Cannot verify from available evidence | Note what is missing; never guess |

Unverifiable records stay Uncertain. A thin record with an alias is
still Uncertain if the product identity cannot be established.

## Maintenance

- Re-verify aliases when the underlying relationship could change
  (brand sales, licensed-brewing shifts). Note the re-check date in the
  entry's note.
- Keep the file small and reviewable. Prefer a handful of
  evidence-backed aliases over broad coverage.
- The matcher loads the file at startup (`load_brand_aliases` in
  `../src/match.py`); a missing file disables alias behavior without
  erroring.

## Related

- Current aliases: `../data/brand_aliases.json`
- Matcher: `../src/match.py` (`resolve_producer_alias`,
  `flavor_identity_confirmed`)
- Pilot evidence: `../pilot/PILOT_REPORT_2026-10-13.md`,
  `../pilot/BRAND_ALIAS_FIX_2026-10-13.md`
