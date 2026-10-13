# Catalog-quality pilot: are discovered candidates good enough for image sourcing?

Date: 2026-10-13. Branch: `experiment/catalog-discovery-prototype` @ `0bb2f43`.
Artifacts: `pilot/PILOT_REPORT_2026-10-13.md` (this file),
`pilot/curated_useful_additions.csv`, `pilot/sample_manifest.json`.
Isolated working copy (not committed): `/tmp/pilot_work` (deleted after the pilot).

## Sample

Seeded stratified sample (seed `20261013`, method in `sample_manifest.json`):
targets were 20 `new_candidate` / 5 `needs_review` / 5 `existing`.
The pool (committed discovery state, 100 candidates) held only 1 `existing`
record, so the 4 unused slots were reallocated to `new_candidate`.

Inspected: 24 `new_candidate`, 5 `needs_review`, 1 `existing` (30 total).
Spread: 25 distinct producers, 10 categories, 9 countries/regions.

Pool: discovery_state.json on the branch (100 candidates: 57 new_candidate,
42 needs_review, 1 existing). Note: the owner separately validated a larger
local state (200 candidates); this pilot uses the committed state only.

## Key finding: the baseline already covers the big seltzer brands

The baseline's modern additions (beer IDs 5900+, 146 records) include full
flavor lineups for White Claw (21, Mark Anthony Brewing), Truly (25+,
Boston Beer Company), and High Noon (18, E. & J. Gallo Winery). The
discovery pipeline classified several of these as `new_candidate` because
the OFF brand name ("White Claw") does not match the baseline brewery
name ("Mark Anthony Brewing"), defeating producer agreement in fuzzy
matching. This is a systematic false-"new" pattern, not a data problem:
the products are genuinely already represented.

## Per-record assessments

Format: candidate ID [pipeline status] -- product / producer -- conclusion.
Rationale and evidence follow. Source URLs are the OFF product pages from
the source records; OFF HTML pages were not directly readable from this
environment (403), so page-level verification was done via a live-browser
read of the 10 most uncertain records (see Evidence notes).

### new_candidate (24)

1. `cand_db5e08458143` [new_candidate] -- "Hard Seltzer- Natural Lime" /
   White Claw (Suisse, 5391537510793, abv 4.5) -- **Already represented**.
   Baseline beer 5936 is "White Claw - Natural Lime" by Mark Anthony
   Brewing (abv 5). Same beverage; the OFF barcode is a regional packaging
   variant. The pipeline missed it because OFF brand "White Claw" does not
   match baseline brewery "Mark Anthony Brewing".
   https://world.openfoodfacts.org/product/5391537510793/natural-lime-hard-seltzer-white-claw

2. `cand_ccc58134e403` [new_candidate] -- "Wild Berry Hard Seltzer" / Truly
   (US, 0087692006770, abv 5.0) -- **Already represented**. Baseline beer
   5954 is "Truly - Wild Berry" by Boston Beer Company (abv 5). Same
   product; missed for the same brand-vs-brewery name reason (Truly vs
   Boston Beer Company).
   https://world.openfoodfacts.org/product/0087692006770/wild-berry-hard-seltzer-truly

3. `cand_c61a60f81a5a` [new_candidate] -- "Nordic Wolf Cherry And Cranberry
   Hard Seltzer" / Nordic wolf (UK, 7350071700563, abv missing) --
   **Useful addition**. Specific flavor, real UK seltzer brand, barcode
   present; no baseline record. Missing abv noted but not blocking for
   image search.
   https://world.openfoodfacts.org/product/7350071700563/nordic-wolf-cherry-and-cranberry-hard-seltzer

4. `cand_05f15b96c82c` [new_candidate] -- "Hard Seltzer" / Mikes Hard (UK,
   5014379010053, abv 5.0) -- **Useful addition**. Mike's Hard Seltzer is a
   real AB InBev UK product line (5% ABV, lemon/lime/black cherry/
   raspberry); the generic record name omits the flavor, but brand +
   barcode + UK market all check out and there is no baseline record.
   https://world.openfoodfacts.org/product/5014379010053/hard-seltzer-mikes-hard

5. `cand_7effe6325d7d` [new_candidate] -- "Hard Seltzer - Berry Blast" /
   Truly Unruly (US, 0087692019220, abv 8.0) -- **Already represented**.
   Baseline beer 5968 is "Truly Unruly - Berry Blast" by Boston Beer
   Company (abv 5; the OFF record says 8.0, likely the higher-ABV Unruly
   variant, but the baseline already covers this product line and flavor).
   https://world.openfoodfacts.org/product/0087692019220/hard-seltzer-berry-blast-truly

6. `cand_ec652f7497ee` [new_candidate] -- "Hard Seltzer Passionfruit" /
   Stelz (Netherlands, 8720865027319, abv 3.55) -- **Useful addition**.
   Specific flavor, real Dutch seltzer brand, barcode present; no baseline
   record. Category missing in the record but the product is
   well-identified.
   https://world.openfoodfacts.org/product/8720865027319/hard-seltzer-passionfruit-stelz

7. `cand_9ef2b31b3adc` [new_candidate] -- "Hard Seltzer raisin blanc
   pasteque" / Doort (France, 3760259622756, abv missing) -- **Useful
   addition**. Specific flavor (white grape / watermelon), barcode
   present; no baseline record. Missing abv noted.
   https://world.openfoodfacts.org/product/3760259622756/hard-seltzer-raisin-blanc-pasteque-doort

8. `cand_e0de7cb653bc` [new_candidate] -- "Vodka Seltzer Pineapple" / High
   Noon (US, 0085000029268, abv 4.5) -- **Already represented**. Baseline
   beer 6014 is "High Noon Vodka - Pineapple" by E. & J. Gallo Winery
   (abv 4.5). Same product; missed because OFF brand "High Noon" does not
   match baseline brewery "E. & J. Gallo Winery".
   https://world.openfoodfacts.org/product/0085000029268/vodka-seltzer-pineapple-high-noon

9. `cand_3a659884ffdb` [new_candidate] -- "Tangerine & Hops" / Snow Melt
   (France, 0897682002657, abv 5.0) -- **Useful addition**. Specific
   flavored seltzer; the baseline's only "Snow Melt" entry is "Snow Melt
   Nitrogen Pale" (a beer, different product). Barcode and abv present.
   https://world.openfoodfacts.org/product/0897682002657/tangerine-hops-snow-melt

10. `cand_980dc9fd423d` [new_candidate] -- "Quirk Spiked Sparkling Pear Yuzu
    Hard Seltzer" / Boulevard Beverage Co. (US, 0068274347283, abv
    missing) -- **Useful addition**. Quirk is Boulevard Brewing's seltzer
    line; specific flavor, barcode present; no baseline record. Missing
    abv noted.
    https://world.openfoodfacts.org/product/0068274347283/quirk-spiked-sparkling-pear-yuzu-hard-seltzer-boulevard-beverage-co

11. `cand_2ac65f4a0227` [new_candidate] -- "Clean & Press: Smashed Cactus &
    Lime" / BrewDog (France, 5056025439733, abv 5.0) -- **Useful
    addition**. BrewDog's Clean & Press seltzer line; specific flavor,
    barcode present. The baseline's BrewDog entries are beers only.
    (Producer attribution to the dataset's "Brewdog" AU record remains
    unresolved per the enrichment review; product identity is unaffected.)
    https://world.openfoodfacts.org/product/5056025439733/clean-press-smashed-cactus-lime-brewdog

12. `cand_5100011aa1a6` [new_candidate] -- "Hard Seltzer" / Aldi (France,
    4061461064051, abv 1.36) -- **Uncertain**. Generic name; abv 1.36% is
    unusually low for a hard seltzer and may be a data error; Aldi is a
    retailer (private label). Could not confirm the product identity from
    available evidence.
    https://world.openfoodfacts.org/product/4061461064051/hard-seltzer-aldi

13. `cand_0fe5e034ec1c` [new_candidate] -- "Hard seltzer lemon & lime" /
    Olvi (Finland, 6419800082675, abv 4.5) -- **Useful addition**. Olvi is
    a major Finnish brewery; specific flavor, barcode present; no baseline
    record.
    https://world.openfoodfacts.org/product/6419800082675/hard-seltzer-lemon-lime-olvi

14. `cand_130bf641c872` [new_candidate] -- "Hard seltzer" / Vizzy (US,
    barcode "03454714", abv missing) -- **Uncertain**. The barcode is 8
    digits (not a valid EAN/UPC), the name is generic with no flavor, and
    abv/category are missing. Cannot identify the specific product; the
    record is not usable as an image-search input as-is.
    https://world.openfoodfacts.org/product/03454714/hard-seltzer-vizzy

15. `cand_61113bcd9f04` [new_candidate] -- "Corona Hard Seltzer" / Corona
    (US, 0033544000670, abv missing) -- **Useful addition**. Real product
    (Constellation); barcode present; no baseline seltzer record (baseline
    "Corona" hits are Coronado Brewing beers). Flavor unspecified in the
    name, but the barcode identifies the package.
    https://world.openfoodfacts.org/product/0033544000670/corona-hard-seltzer

16. `cand_c3f4560f37d9` [new_candidate] -- "Hard Seltzer Natural Lime" /
    Ravini (Germany, 4061458219808, abv missing) -- **Useful addition**.
    "Ravini Hard Seltzer Natural Lime" is a real product (Peter Mertes KG,
    Germany); barcode present; no baseline record. Missing abv noted.
    https://world.openfoodfacts.org/product/4061458219808/hard-seltzer-natural-lime-ravini

17. `cand_8c34e3441093` [new_candidate] -- "Hard Seltzer" / Vista Bay (US,
    4061463667649, category/abv missing) -- **Useful addition**. Vista Bay
    is Aldi USA's real hard-seltzer brand (lime, black cherry, ruby
    grapefruit, etc.); the OFF product page confirms a real beverage
    product and the barcode identifies the package. Flavor unspecified in
    the record.
    https://world.openfoodfacts.org/product/4061463667649/hard-seltzer-vista-bay

18. `cand_e91fbbe786d9` [new_candidate] -- "Hard seltzer mixed berries" /
    Kopparberg (Sweden, 7393714646002, abv 5.0) -- **Useful addition**.
    Kopparberg (known Swedish cider maker) seltzer; specific flavor,
    barcode present; no baseline record.
    https://world.openfoodfacts.org/product/7393714646002/hard-seltzer-mixed-berries-kopparberg

19. `cand_a9dbe661955c` [new_candidate] -- "Topo Chico Hard Seltzer" / Topo
    Chico (Espana, 5449000294708, abv 4.7) -- **Useful addition**. Real
    product (Coca-Cola); barcode present; no baseline record. Flavor
    unspecified in the name, but the barcode identifies the package.
    https://world.openfoodfacts.org/product/5449000294708/topo-chico-hard-seltzer

20. `cand_03874efd1a56` [new_candidate] -- "Willie's Superbrew Hard Seltzer
    Sparkling Mango and Passionfruit" / Willie's (US, 0860438001686, abv
    4.5) -- **Useful addition**. Specific flavor, real brand, barcode
    present; no baseline record.
    https://world.openfoodfacts.org/product/0860438001686/willie-s-superbrew-hard-seltzer-sparkling-mango-and-passionfruit

21. `cand_a9f52e224116` [new_candidate] -- "Pineapple Vodka Shelter" / Nutrl
    (US, 0018200263866, abv missing) -- **Useful addition**. NUTRL Pineapple
    Vodka Seltzer is a real product (Anheuser-Busch InBev, 4.5% ABV); the
    record name looks like an OFF parsing artifact ("Vodka Shelter" for
    "Vodka Seltzer"), but brand + barcode check out and there is no
    baseline record. Spirits-based, but the baseline already covers
    vodka-seltzer lines (High Noon, Cutwater, Stateside), so in-scope by
    the baseline's own precedent.
    https://world.openfoodfacts.org/product/0018200263866/pineapple-vodka-shelter-nutrl

22. `cand_12c26f728267` [new_candidate] -- "Hard Seltzer" / "fefe" (France,
    3770018391021, abv 5.0) -- **Useful addition**. The OFF product page
    ("Hard Seltzer - fefe - 33cl") confirms a real 33cl beverage product;
    barcode and abv present; no baseline record. The producer string is
    unusual but the product page is genuine.
    https://world.openfoodfacts.org/product/3770018391021/hard-seltzer-fefe

23. `cand_0106c4a2ff1b` [new_candidate] -- "Hard Seltzer" / Truly (US,
    0087692010104, category/abv missing) -- **Uncertain**. The Truly brand
    is fully covered in the baseline (25+ flavors), but this record names
    no flavor, so the specific product cannot be identified or checked
    against the baseline.
    https://world.openfoodfacts.org/product/0087692010104/hard-seltzer-truly

24. `cand_dc5a292cafc1` [new_candidate] -- "Lemon Hard Seltzer" / White Claw
    (US, 0635985800088, abv missing) -- **Already represented**. Baseline
    beer 5941 is "White Claw - Lemon" by Mark Anthony Brewing. Same
    product; missed for the brand-vs-brewery name reason.
    https://world.openfoodfacts.org/product/0635985800088/lemon-hard-seltzer-white-claw

### needs_review (5)

25. `cand_0f5fd2255605` [needs_review] -- "Premium hard seltzer", no
    producer/brand (US, 0858674005889, abv missing) -- **Uncertain**. The
    pipeline's fuzzy match to baseline beer 1862 "Premium" by Hansa
    Bryggeri (score 85.0) is not credible: generic name, no producer, and
    Hansa's "Premium" is almost certainly a lager, not a seltzer. The
    product identity cannot be verified from available evidence.
    Correctly held in review.
    https://world.openfoodfacts.org/product/0858674005889/premium-hard-seltzer

26. `cand_6b15f0c30f0d` [needs_review] -- "Hard Seltzer Raspberry" / White
    Claw (US, 0635985260356, abv missing) -- **Already represented**.
    Baseline beer 5937 is "White Claw - Raspberry" by Mark Anthony
    Brewing. Same product. The pipeline's fuzzy match to baseline beer
    2910 "Raspberry" by Shipwrecked Brew Pub (score 80.0) was a false
    positive on the shared word "Raspberry"; correctly held in review
    rather than auto-merged.
    https://world.openfoodfacts.org/product/0635985260356/hard-seltzer-raspberry-white-claw

27. `cand_9d32a525dfcc` [needs_review] -- "Hard Seltzer: Oasis Cherry" /
    Topo Chico (US, 0810078781370, abv 3.7) -- **Useful addition**. The OFF
    product page ("Hard Seltzer: Oasis Cherry - Topo Chico") confirms a
    real beverage product; barcode present; no Topo Chico in the baseline.
    The pipeline's fuzzy match to baseline beer 5848 "Oasis" by Tallgrass
    Brewing Co. (score 80.0) was a false positive on the shared word
    "Oasis"; correctly held in review rather than auto-merged.
    https://world.openfoodfacts.org/product/0810078781370/hard-seltzer-oasis-cherry-topo-chico

28. `cand_aaa363925d59` [needs_review] -- "NATURAL LIME" / "WHITE CLAW HARD
    SELTZER" (UK, 5391537510007, abv missing) -- **Already represented**.
    Baseline beer 5936 is "White Claw - Natural Lime" by Mark Anthony
    Brewing (Mark Anthony Brewing is White Claw's producer). Same
    product; correctly held in review given the producer-name mismatch.
    https://world.openfoodfacts.org/product/5391537510007/natural-lime-white-claw-hard-seltzer

29. `cand_6f278d7d4f71` [needs_review] -- "Truly Hard Seltzer Grapefruit",
    no producer/brand (US, 0087692004363, abv missing) -- **Already
    represented**. Baseline beer 5959 is "Truly - Grapefruit" by Boston
    Beer Company (Truly's producer). Same product; correctly held in
    review given the missing producer in the OFF record.
    https://world.openfoodfacts.org/product/0087692004363/truly-hard-seltzer-grapefruit

### existing (1)

30. `cand_cd89790f781e` [existing] -- "Happy Dad Fruit Punch Hard Seltzer"
    / Happy Dad (US, 0850046522024, abv 5.0) -- **Already represented**.
    Baseline beer 6051 is "Happy Dad - Fruit Punch" by Happy Dad (abv 5).
    Exact name+producer match at confidence 100; correct.
    https://world.openfoodfacts.org/product/0850046522024/happy-dad-fruit-punch-hard-seltzer

## Evidence notes

- OFF product HTML pages returned 403 to direct fetches from this
  environment; the 10 most uncertain records were verified through a
  live-browser read (results incorporated above). Records not
  page-verified were assessed from the OFF API source records
  (name/brand/categories/barcode/country/abv) plus direct baseline
  comparison.
- No images were fetched or evaluated, per the pilot scope.
- "Already represented" judgments for White Claw / Truly / High Noon
  flavors rest on exact flavor-name matches against baseline beers
  5933-6028 (Mark Anthony Brewing, Boston Beer Company, E. & J. Gallo
  Winery). The pipeline missed these because OFF brand names do not
  match baseline brewery names, defeating producer agreement in fuzzy
  matching.

## Summary

| Pipeline status | Inspected | Useful addition | Already represented | Not useful | Uncertain |
|---|---|---|---|---|---|
| new_candidate | 24 | 16 | 5 | 0 | 3 |
| needs_review | 5 | 1 | 3 | 0 | 1 |
| existing | 1 | 0 | 1 | 0 | 0 |
| **Total** | **30** | **17** | **9** | **0** | **4** |

Useful-addition rate among sampled `new_candidate` records: **16/24 (67%)**.
Five of the 24 (21%) were already in the baseline under a different
brewery name (the brand-vs-brewery mismatch); three (13%) could not be
verified.

Curated set (`curated_useful_additions.csv`): 17 records across 6
categories, 16 producers, 8 countries/regions (US, UK, France,
Netherlands, Germany, Finland, Sweden, Spain).

## Recommendation

**Proceed to image-sourcing pilot, using the curated set only.**

The 17 curated records are verified real products with barcodes and no
baseline presence: enough variety (16 producers, 8 regions) for image
testing. Do not feed the raw `new_candidate` pool to image sourcing yet:
21% of sampled new candidates were already represented (the systematic
brand-vs-brewery mismatch: White Claw/Mark Anthony Brewing, Truly/Boston
Beer Company, High Noon/E. & J. Gallo Winery), and 13% were unverifiable
thin records. The fix needed before broader ingestion is brand-alias
handling in producer matching (e.g. mapping consumer brands to their
producing brewery), not more data collection.

This is a directional pilot (n=30), not a statistically conclusive
accuracy estimate; no confidence intervals are claimed.

## Limitations and open questions

- The sample is seltzer-heavy because the discovery run's OFF results
  were; beer/cider coverage is untested here.
- Page-level verification was limited to the 10 most uncertain records
  (live-browser read; direct fetches returned 403 from this environment).
- "Already represented" judgments rest on flavor-name matches against the
  baseline's modern seltzer additions (IDs 5933-6028); package-variant
  differences (e.g. regional barcodes for the same flavor) were treated
  as non-meaningful duplicates.
- Whether spirits-based seltzers belong in BeerPassport's catalog is a
  product decision; the baseline already includes them (High Noon,
  Cutwater, Stateside), so they were treated as in-scope here.
- The owner's separate validation of a larger local state (200
  candidates) is not covered by this pilot, which used the committed
  100-candidate state.
