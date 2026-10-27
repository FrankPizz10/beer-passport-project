# Session handoff: Milestone 1, step 1 (cleanup apply mode)

Date: 2026-10-27. Branch: `m1-step1-cleanup-apply`. Plan reference: "BeerPassport Relaunch: Deployment Proposal" (Google Doc, Drive BeerPassport folder), Milestone 1 step 1.

## What ran

`python -m src.cleanup.cli --mode apply` against the committed baseline in `data/`. Exit clean; the run enforces row reconciliation and would have failed otherwise.

- Input: 5,894 beers, 1,431 breweries
- Output: 5,894 beers, 1,339 breweries
- R1 breweries dropped (zero beers): 92
- R2 UPCs cleared to 0: 6. Flagged, unchanged: 0
- R3 discontinued markers normalized: 27
- R4 duplicate groups flagged: 0

The full change log is `cleanup/CLEANUP_REPORT.md` (mode: apply), updated by this PR.

R4 note: the rule keys on (normalized name, brewery_id) over the cleaned output and found no exact groups. The doc 08 audit counted 1 group under its own looser grouping. R4 is report-only and never merges, so this has no effect on the import source; pinning down the pair is optional during step 2.

## Frozen import source v1

The cleaned CSVs stay local per the repo git hygiene rules (generated output is not committed). They live at `experiments/catalog-discovery/cleanup/` in the working copy. SHA-256 checksums, so any later copy (including the one loaded onto the Lightsail box) can be verified identical:

| File | SHA-256 |
| --- | --- |
| CleanedBeers.part01.csv | f41528576e9602fb886cf1479a63ce91a2f09dbd636360cdbcceed287b769de3 |
| CleanedBeers.part02.csv | 1160ae2ab9e3454921412c8b8f22f778ead55b0bd6e10a80d628485b36b2c603 |
| CleanedBeers.part03.csv | 63ae4248985ae67fa3832462c9e1019dac0fd6f4625f7cc96877fded489f5562 |
| CleanedBeers.part04.csv | 4b99b8898d05689343d03546a217b52997577fc2853a836594caf47490d5208f |
| CleanedBeers.part05.csv | 7f44286eb4a7a6f945c714dfd1216534e3b1ebdf01f3af862337f27d04b1e765 |
| CleanedBeers.part06.csv | 071e7fec57c4bad7420c6957aa43b76d0b0e8cb03355b6a262f9c6c757908069 |
| CleanedBeers.part07.csv | 19b892ba839578563efeacaa81d4dc45f80579b1327c68274bbe76478d16bb93 |
| CleanedBeers.part08.csv | db6a946a329048b986e5ea734e5b7d958f01f92ed6dfe2aa82a5b2f6a44de933 |
| CleanedBeers.part09.csv | 307a9d92bf6c357a2f3a883810029f228987cca55442075c2a4b96701a449ae4 |
| CleanedBeers.part10.csv | 98aaea4de455954c22b2f0ebfe944b2576f0086b6a22d00454e1975089feadc8 |
| CleanedBeers.part11.csv | 7c413484ba0d4d77db13fe4f60d864cabbc84dc763e66ce80390bb3f884f634c |
| CleanedBeers.part12.csv | 4f5477c28bd16f7ca6007a523d2f32785c04b8570b35b5c162e9d8247d2c99ee |
| CleanedBreweries.part01.csv | 309d0645837c7c872a7e9655dd295f7acc287058275dfef7789e7eacecfe740b |
| CleanedBreweries.part02.csv | 9112d0f5d4599b1b931fd1e56a43a84cb95a17c51a9f3d4f9869601af6e139e2 |
| CleanedBreweries.part03.csv | 63846fde383cbaac8f7bf0625283ce81ef47ff23e30f17d049dbc238384ebfbe |
| CleanedBreweries.part04.csv | bb3fd49553391bbd2186858f18ff9b19551a57e0303ad424fb71754fe7c43a02 |

## Tests

No code changed in this step, so no new tests. Full suite re-run locally with the project venv: 101 tests, OK (the same suite the CI workflow runs; GitHub Actions still goes live only when the workflow file is pasted, a trailing item).

## Next step

Milestone 1, step 2: Postgres schema and import script (provider switch, upc as string, image fields, scripted import with tests), on its own branch when started.
