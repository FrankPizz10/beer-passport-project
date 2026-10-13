# Product Scope and Taxonomy

Defines what BeerPassport's catalog should contain as it expands beyond
the current beer-centric baseline. Intended scope: **packaged beverages
sold in cans or bottles**.

## In-scope categories

| Category | Examples | Notes |
|---|---|---|
| Beer | Lagers, IPAs, stouts, sours | Core of the existing baseline |
| Non-alcoholic beer | Heineken 0.0, Athletic Brewing | In scope; ABV ~0.0-0.5% |
| Cider and perry | Angry Orchard, Strongbow | Fermented apple/pear |
| Hard seltzer | White Claw, Truly, High Noon | Includes malt-, sugar-, and spirit-based |
| Flavored malt beverages | Mike's Hard Lemonade, Smirnoff Ice | |
| Spirit-based RTDs | Cutwater, Surfside, High Noon, Stateside | Canned cocktails; the baseline already contains these |
| Wine and wine-based drinks | Wine spritzers, canned wine, sangria RTDs | Packaged format only |
| Hard iced tea / lemonade | Twisted Tea | |

## Explicit boundaries

**Bottled spirits sold as liquor** (e.g. a 750ml bottle of vodka): OUT.
These are not single-serve packaged beverages and are not what
BeerPassport catalogs. A canned vodka soda from the same brand is IN;
the bottle on the shelf is OUT.

**Non-alcoholic cocktails / mocktails**: UNDECIDED (owner decision).
They fit the packaged format, but the product has not settled whether
the catalog covers non-alcoholic drinks beyond non-alcoholic beer.

**Kombucha**: UNDECIDED (owner decision). Fermented, sometimes lightly
alcoholic, packaged in cans/bottles. Fits the format; category fit is
unclear.

**Unclear or varying ABV**: when ABV is missing, the record stays
`needs_review` (existing pipeline behavior treats ABV 0.0 as unknown,
not as verified zero). Do not infer alcohol status from the name. When
ABV varies by region for the same barcode, keep the most documented
value and note the variance in review reasons.

## Three axes, not one label

Do not treat "alcoholic beverage" and "beer" as interchangeable. Every
candidate is described on three independent axes:

1. **Product type** (category/style): beer, cider, seltzer, RTD, wine...
2. **Alcohol status**: alcoholic / non-alcoholic / unknown (from ABV,
   never inferred from the name)
3. **Packaging format**: can / bottle / unknown (with size where known)

A record can be in-scope on format but out on type (bottled spirits), or
in-scope on type but unknown on alcohol status (missing ABV). Review
handling differs per axis; see the review outcomes in
`04-alias-and-review-procedure.md`.

## Suggested labels

Use the baseline's category/style vocabulary where it exists; propose
new labels only when the baseline has no fit, and record the proposal in
the review notes. Do not invent parallel taxonomies per source.

## Related

- Matcher behavior: `../src/match.py`
- Alias data: `../data/brand_aliases.json`
- Pilot evidence: `../pilot/PILOT_REPORT_2026-10-13.md`
