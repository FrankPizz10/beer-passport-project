# Catalog Selection Strategy: US-First, Evidence-Based

Status: PROPOSED, companion to decision
[005: Catalog selection is US-first, evidence-based](../../decisions/005-catalog-selection-us-first.md).
The counts in this document are a proposal baseline taken from the
2026-11-23 American-first reassessment dry run. Nothing in this
document imports anything; every import remains a separate dry-run
manifest and a separate CTO approval.

## Purpose and audience

BeerPassport is a beverage discovery catalog for adults 21 and over,
primarily young men and secondarily young women. The catalog succeeds
when a user can actually find and drink what it shows them, so
selection is governed by where a beverage is produced and where it is
sold, not by where a data source happened to harvest it. The
discovery expansion is dominated by a 2025 Dutch and European craft
import in Wikidata, which is a poor default order for a US audience.

Audience fit is judged only on market availability and product
relevance evidence: production country, sales-country data, federal
label approval, and retailer or distributor presence. No product is
excluded, demoted, or promoted through assumptions about gender.
Category and style relevance follow the approved scope in decision
004 (all canned beverages, not only beer).

## Inputs

- **Baseline (untouched):** 5,894 beers and 1,339 breweries, the
  frozen catalog. Nothing in this strategy changes it.
- **Batch 2 (separate path):** 702 measured records (190 Open Food
  Facts + 512 CraftCans) under decision 004, with 687 importable
  records, 170 importable verified images, and 15 records held for a
  missing brewery. Batch 2 follows its own already-approved path
  (`BATCH_2_DRY_RUN_MANIFEST.md` in this directory; record file
  `batch-702.json`, SHA-256
  `a2ad122a0ce50b6f445537a05615d8379fb4a870706b313f28e1bc59d2f84913`,
  held locally in the `catalog-expansion-poc` workstream). It is not
  part of the candidate pool below and is never double-counted: the
  11 expansion records that matched batch 2 were excluded from the
  candidates for exactly that reason.
- **Discovery expansion (this strategy's subject):** 22,219 unique
  new records (Wikidata 15,825 + Open Food Facts full pull 6,394),
  cross-deduped against each other and against batch 2 with the POC
  dedupe ladder. Record-level accounting (verified 2026-11-23 against
  the staged files; this corrects an earlier headline figure of
  21,438, which silently excluded every cross-match-flagged record):
  22,219 minus 87 cross-source merges (76 Wikidata into Open Food
  Facts primaries, 9 Wikidata into batch 2, 2 Open Food Facts into
  CraftCans) leaves **22,132 candidate records**, staged in five
  mutually exclusive classes (tier table below). Ambiguous pairs are
  relationships between records, not records, and are counted
  separately (693 pairs, plus 1 held match link). Source report and
  staged files are local, not in GitHub:
  `~/workspace/workstreams/catalog-expansion-2/reassessment/REASSESSMENT_MANIFEST.md`,
  `candidates-us.json` (SHA-256
  `3fac5162193fb4d79280570c1a992f08ae72e5220980cb8708269c906499f6ed`),
  and `candidates-review.json` (SHA-256
  `30d040590a4e8b6317d29efa1ab1d2caa473098bb55a45a2baba6c8711522870`).

## Selection principles, in priority order

1. **US-produced beverages first.** A record with evidence of United
   States production outranks everything else in the expansion.
2. **Imports with evidence of US market presence.** A foreign-produced
   record is selected when there is evidence it is sold or consumed
   in the United States.
3. **The approved broader canned-beverage scope.** Within the tiers
   above, all canned beverages are in scope per decision 004, not
   only beer. Scope never substitutes for the tier evidence: a canned
   beverage with no US evidence sits in the review bucket like any
   other record.
4. **Image readiness and metadata completeness order a tier; they do
   not filter it.** Verified images first, then gate-passed images,
   then brewery, style, and ABV completeness. A record with no image
   or a thin description is sequenced later in its tier, never
   silently excluded.

## Evidence standards

Every selected record keeps its provenance (source, source record
id, source URL, retrieved date, tier) and its full `origin_evidence`
list, with each signal named and its raw value recorded.

**US production evidence:**

- Country-of-origin data naming the United States establishes US
  production. In the current pool this is the Wikidata P495
  (country of origin) assertion, recorded on each record inside the
  fused signal `wikidata_country_p495_else_p17`; the audit in this
  document separates the two properties (see "Wikidata origin
  evidence: P495 vs P17").
- **P17 alone does NOT establish US production.** P17 names the
  country associated with the item, often the brewery's or brand's
  country rather than the production site. It may corroborate an
  independent production signal, but a record whose only US signal
  is P17 is held (reason `origin_p17_only`) until corroborated by
  P495 from any source, manufacturer or origins data, or a TTB COLA
  record. The audit found zero Tier 1 records resting on P17.
- The producing brewery located in the United States, when the
  location is a structured country-level datum (the brewery's own
  country property or a verified address country). A place-name
  string alone is not sufficient (see the does-not-count list).
- Open Food Facts `origins_tags` or `origins` naming the United
  States, or `manufacturing_places` naming the United States, a US
  state, or a USA suffix, recorded verbatim; a bare state or place
  name that is internationally ambiguous does not suffice alone.
- For a record merged across sources, the alternate source's country
  counts as production evidence unless the primary source's origins
  explicitly contradict it; a contradiction holds the record with
  the conflict recorded (reason `origin_conflict`).

**Conflicting or ambiguous evidence is held, never resolved by
assumption:** P495 and P17 disagreeing, multiple P495 countries, a
later signal contradicting an earlier one, or an ambiguous place
name each move the record to the review classes with the reason
recorded (`origin_conflict`, `origin_ambiguous`, `origin_p17_only`).
In the current pool these classes are empty inside Tier 1 (verified
by the audit); the one P17-only-US record that reached the pool is
already in the review file.

**US market evidence (no US production evidence required):**

- Sales-country data listing the United States. In the current pool
  this is Open Food Facts `countries_tags` including
  `en:united-states` (signal `off_countries_tags_sales_country`).
- US federal label approval (TTB COLA). Not yet harvested; named
  below as a future enrichment signal, because a COLA approval is
  direct evidence a product is labeled for US sale.
- US retailer or distributor listings. Also a future signal, from
  the source discovery work.

**What does NOT count as evidence:**

- A barcode GS1 prefix. It records where the barcode was registered,
  not where the product is made or sold.
- Open Food Facts `emb_codes` as harvested: only 33 of 6,394 records
  carry one and all are EU-style packer codes, so no US signal can
  be read from them.
- The language of a product name, or a brewery name that sounds
  American.
- P17 by itself (see the production evidence rules above).
- An ambiguous place name: a location string that fits more than
  one country (Georgia, Cork, Cambridge, Richmond, and similar)
  without a structured country datum behind it.
- Assumed popularity, fame, or audience fit without availability
  evidence.

## Tier table (proposal baseline, from the reassessment)

Candidate RECORDS, in five mutually exclusive classes:

| Class | Definition | Records | Wikidata | Open Food Facts |
|---|---|---|---|---|
| Tier 1 | US-produced | 6,607 | 6,585 | 22 |
| Tier 2 | Clearly US-market | 210 | 0 | 210 |
| Review: uncertain | Origin or market evidence insufficient | 14,621 | 8,500 | 6,121 |
| Review: pair-flagged | Member of an ambiguous cross-source pair, held unmerged | 693 | 654 | 39 |
| Review: held match | Matched a held Open Food Facts record | 1 | 1 | 0 |
| **Total staged records** | | **22,132** | **15,740** | **6,392** |

US-selected total (tiers 1 + 2): **6,817**. Review classes total
15,315 records (14,621 + 693 + 1), staged in `candidates-review.json`,
each record with a `review_reason`. Per-source closure: Wikidata
6,585 + 8,500 + 654 + 1 = 15,740 staged records, plus 85 merged away
(76 into Open Food Facts primaries, 9 into batch 2) reconciles
exactly to the 15,825 harvested; Open Food Facts 22 + 210 + 6,121 +
39 = 6,392 staged records, plus 2 merged into CraftCans reconciles
exactly to 6,394. Batch 2's 702 records are staged separately; the
grand total of staged candidate records across all batches is
22,834.

RELATIONSHIPS, counted separately from records: 693 ambiguous pairs
(39 Open Food Facts vs CraftCans, 126 Wikidata vs batch 2, 528
Wikidata vs Open Food Facts; fuzzy scores 48.8 to 95.9), 1 held match
link (Wikidata vs Open Food Facts), and 87 merge links whose merged
records survive only as alternate-source provenance on the primary.

Image readiness inside the selected tiers (statuses inherited from
the source batches and preserved verbatim; unverified images were
never promoted, including across merges):

| Bucket | Verified | Gate-passed, unverified | Failed | None |
|---|---|---|---|---|
| Tier 1: US-produced (6,607) | 7 | 16 | 1 | 6,583 |
| Tier 2: US-market (210) | 64 | 122 | 6 | 18 |
| US total (6,817) | 71 | 138 | 7 | 6,601 |

Flagged merge stat from the reassessment: in 8 of the 76
cross-source merges, the Wikidata twin carried a verified image but
the Open Food Facts primary did not. The primary's lesser status was
kept in every case, and those 8 images count as verified nowhere in
these outputs.

Known limits on the baseline counts, from the reassessment: Open
Food Facts origin fields are sparse (`origins_tags` populated for
775 of 6,394 records, `manufacturing_places` for 355), so the Tier 1
Open Food Facts count of 22 is a floor, not a census. The 693
ambiguous pairs are inflated by dense same-brewery name families and
are likely mostly distinct products, but they stay unmerged pending
review. US state-name matching in `manufacturing_places` is a text
signal recorded verbatim (a value such as "Georgia" is ambiguous
between the US state and the country).

## Wikidata origin evidence: P495 vs P17 (verified 2026-11-23)

The reassessment's evidence string fuses the two Wikidata country
properties (`wikidata_country_p495_else_p17`), so the split was
recovered by joining all 6,585 Tier 1 Wikidata records, by QID,
against the harvest's raw SPARQL pull, which stored P495 (country of
origin) and P17 (country) separately per item.

| Evidence behind the US-produced classification | Records |
|---|---|
| P495 = "United States", sole P495 value | 6,585 |
| P495 absent, P17 = "United States" (fallback) | 0 |
| P495 multiple values including the US | 0 |
| P495 non-US (conflict with the classification) | 0 |
| No country in the raw pull | 0 |

The P17 fallback contributes nothing to Tier 1: in the entire raw
pull only 4 QIDs carry P17 = US with no P495, and none is in Tier 1
(1 sits in the review file; 3 never reached the pool). The Open Food
Facts Tier 1 records (22) rest on their own signals, chiefly
`off_manufacturing_places` (13 records) and `off_origins_tags` /
`off_origins` (8 each; signals overlap per record).

Why a Dutch/European-dominated harvest yields 6,585 US-produced
records: the harvest's European weight is real but it sits in the
uncertain class (8,500 Wikidata records, dominated by the 2025
Dutch/European craft import whose items carry language-neutral
labels and no US origin evidence). Tier 1 membership required an
explicit P495 = United States assertion, and Wikidata's beer-item
coverage itself skews toward recent US craft releases. Origin was
never inferred from product names, label language, or brewery place
names.

Auditable sample (fixed-seed random draw, seed 20261123, from the
6,585; every row is checkable at wikidata.org by QID):

| Beer | Brewery | QID | P495 |
|---|---|---|---|
| Oil of Aphrodite | Jackie O's Pub & Brewery | Q141727503 | United States |
| Handsome Maniac | Sand City Brewing Co. | Q140250822 | United States |
| Orloj | Xul Beer Company | Q140313835 | United States |
| Snap, Crackle, Pop | Mikerphone Brewing | Q140224763 | United States |
| Double Dope | 3 Sons Brewing Co. | Q140167549 | United States |
| Hydra \| Chonk | Mortalis Brewing Company | Q140172166 | United States |
| Formless Shadows | Pure Project Brewing | Q140250507 | United States |
| Cosmic Background | Spyglass Brewing Company | Q140130267 | United States |
| Cookie Jar Superstar | Kane Brewing Company | Q140250020 | United States |
| Caliban | Modern Times Beer | Q140204803 | United States |
| Fruitlands (Strawberry Limeade) | Modern Times Beer | Q140204966 | United States |
| Liquid Truth Serum | Dogfish Head Craft Brewery | Q141460283 | United States |
| Forestry | Outer Range Brewing Co. | Q140172436 | United States |
| Cooper Project No. 3 | Goose Island Brewery | Q139913423 | United States |
| A.D.I.D.A.S. | Xul Beer Company | Q140313829 | United States |

Confidence limits, stated plainly: the split above is exact for the
harvest's own raw data, but P495 is a community-edited Wikidata
assertion, not a registry record; the pull is a 2026-11-23 snapshot
and Wikidata changes; and a P495 can reflect brand origin for
contract-brewed or licensed products rather than the liquid's
production site. Standing rules that follow:

- Any record whose evidence later conflicts (a second P495 country
  appears, a P17 contradicts the P495, or a TTB COLA record shows
  foreign production) is held with reason origin_conflict until a
  human resolves it.
- Future harvests must store P495 and P17 as separate signals. A
  classification resting on P17 alone reaches Tier 1 only with a
  corroborating signal; otherwise it is held.
- Ambiguous place names are never evidence: brewery location and
  name language were excluded from classification for this reason.
  The sample shows why in both directions: "Orloj" is a Czech-named
  beer from Xul Beer Company of Knoxville, Tennessee, and is Tier 1
  on its P495 alone; a US-sounding name with no country evidence
  stays uncertain.

## Sequencing proposal

1. **Batch 2 first**, on its existing approval path: 687 importable
   records and 170 verified images; the 15 held records join once
   their breweries resolve. Its manifest already records the
   prerequisite that the catalog loader must carry provenance fields
   before a real import.
2. **Tier 1 (US-produced, 6,607).** Order inside the tier: verified
   images first (7 records), then gate-passed images (16), then by
   metadata completeness (brewery, then style, then ABV present).
   Harvest-reported completeness for the Wikidata majority is
   brewery 95.0%, style 80.9%, ABV 90.6%, so most of the tier is
   import-shaped once a dry-run manifest confirms it.
3. **Tier 2 (US-market, 210).** The most image-ready slice of the
   pool (64 verified, 122 gate-passed): order verified images first,
   then gate-passed, then completeness.
4. **Review bucket (15,315) last, and only after review.** Two cheap
   evidence upgrades come first, both already identified in source
   discovery (`~/workspace/workstreams/catalog-expansion-2/SOURCE_DISCOVERY.md`):
   a TTB COLA registry sweep (free, CC0, and a label approval is
   direct US market evidence) and an Open Food Facts sales-country
   enrichment pass over the uncertain records. The 693 ambiguous
   pairs need human review before any merge. Records promoted out of
   the review bucket enter through a new dry-run manifest, never by
   editing these counts.

Each stage is its own dry-run manifest and its own approval. A stage
may be split further (for example Tier 1 by image readiness) without
changing this strategy, as long as the manifest accounts for every
record it draws from the pool.

Image decisions precede manifests: under the discovery hub flow
(issues/001-catalog-discovery-hub.md), a candidate's image is
previewed and approved in the hub, bound to the exact image by
content hash, before the candidate may enter an import manifest;
the approved decision then carries through the import into the
published catalog. Image readiness in the ordering above therefore
means decision-ready (verified images first), not merely present.

## Governance

- The counts above are a proposal baseline. They change only
  through a new dry-run manifest that reconciles against them.
- Nothing imports without Frank's approval. Accepting this strategy
  (decision 005) approves the selection rule, not any import.
- The image quality gate from decision 004 binds every selection
  that carries an image: an image counts as ready only when it is
  verified to show the correct product at usable quality. Inherited
  image statuses are preserved as recorded and never promoted.
- Provenance is recorded for every record regardless of tier, and
  the hard lines from decision 004 are unchanged: no bypassing
  authentication, paywalls, or technical access controls.

## Verification note

The record-level reconciliation and the P495/P17 audit in this
document were performed by Jarvis against the local staged files on
2026-11-23 (file names and SHA-256 values are stated where the
counts are introduced; the audit method is the QID join against the
harvest's raw SPARQL pull, sample seed 20261123). **Codex has not
independently accessed the source files**; its review covers these
documents, not the underlying data. Any reviewer with access to the
`catalog-expansion-2` workstream can reproduce both checks from the
stated methods.

## Acceptance checks

- [ ] Re-running the QID join (Tier 1 Wikidata records against the
      raw pull) reproduces the audit split exactly: P495 = US sole
      value 6,585; P17-only 0; multi-country P495 0; conflicts 0.
- [ ] The five staging classes sum to 22,132 and the per-source
      closures hold (Wikidata 15,740 + 85 merged = 15,825; Open Food
      Facts 6,392 + 2 merged = 6,394).
- [ ] Classifier cases, applied to fixture records: P495 = US ->
      Tier 1. P17 = US with no P495 and no other production signal
      -> held (`origin_p17_only`). P495 = Canada with P17 = US ->
      held (`origin_conflict`). P495 = {US, Canada} -> held
      (`origin_conflict`). A place-name string with no structured
      country datum -> held (`origin_ambiguous`). Open Food Facts
      `manufacturing_places` = "Georgia" alone -> held pending
      corroboration.
- [ ] No record in Tier 1 or Tier 2 lacks an `origin_evidence` list
      naming the signal that placed it there.
