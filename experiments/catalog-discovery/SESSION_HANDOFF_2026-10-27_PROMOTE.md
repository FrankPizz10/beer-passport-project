# Session handoff: cleaned catalog promoted to baseline

Date: 2026-10-27. Branch: `data/promote-cleaned-catalog`. Directed by Frank: review the apply-mode output, and if good, override the CSVs saved in git. Frank holds backups in Drive; the pre-cleanup baseline also remains in git history on main up to this PR's parent.

## What this PR does

`data/LiveBeers.part01-12.csv` and `data/LiveBreweries.part01-04.csv` are replaced with the verified apply-mode output (`CleanedBeers` / `CleanedBreweries` from the Milestone 1 step 1 run). From this merge on, the repo baseline IS the cleaned catalog: 5,894 beers, 1,339 breweries, with the `discontinued` column on beers. Step 2's import reads from `data/` as before.

The generated files under `cleanup/` stay local and gitignored, unchanged. `cleanup/CLEANUP_REPORT.md` remains the record of the run against the old baseline.

## Review performed before promoting (all checks passed)

- Counts: beers 5,894 in and out; breweries 1,431 to 1,339.
- Beer ID set identical to the old baseline, all unique; exactly 92 brewery IDs dropped, none of them referenced by any beer; zero kept brewery rows modified in any field; zero cleaned beers with a dangling brewery_id.
- Beer changes confined to exactly two columns: `name` (27 rows, the "(discontinued)" strips; the flag lives in the new `discontinued` column, 27 rows = 1) and `upc` (6 rows, exactly the garbage values 2147483647 x4 and 7 x2, now 0; every cleaned upc is 0 or empty, matching the finding that the old catalog never had real barcodes).
- Format: strict UTF-8, no NUL bytes, every row's column count matches its header, every part ends with a newline.
- Idempotence: the cleanup run in report mode against the promoted data reports zero changes under every rule (R1 0, R2 0, R3 0, R4 0), input equals output.

## Next step

Milestone 1, step 2: Postgres schema and import script, importing from this baseline.
