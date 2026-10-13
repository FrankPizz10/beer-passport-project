# Catalog Expansion Runbook

Safe, repeatable sequence for discovery runs. All commands use flags
that exist on this branch. Work in an isolated copy; never mutate the
committed discovery state or normal outputs during validation.

## 1. Prepare an isolated working copy

```bash
cp -r experiments/catalog-discovery /tmp/expand_run
cd /tmp/expand_run
# Use the branch's venv or create one:
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Verify the baseline loads before fetching anything:

```bash
python -m src.main --summary
```

## 2. Run bounded discovery

Start small. `--limit` caps records per source; `--search-terms`
overrides the default OFF queries.

```bash
# Smoke test: 100 records per source
python -m src.main --limit 100

# Wider net, still bounded
python -m src.main --limit 500 --search-terms beer cider "hard seltzer" "ready to drink"
```

Producer coverage: `--brewery-pages N` (API, 200/page) or
`--brewery-source dataset` for the pinned OBDB snapshot (see
`../data/dataset/SNAPSHOT.md`; download the CSV first, it is gitignored).

## 3. Review candidates

Candidates land in the isolated `data/state/discovery_state.json` with
statuses `existing`, `new_candidate`, or `needs_review`.

- `new_candidate` means **unmatched to the baseline**, not verified new.
- `needs_review` means ambiguous: conflicting ABV, weak producer
  agreement, single-token generic names, alias-supported but
  flavor-uncertain, or missing name/producer.
- Triage `needs_review` first; those are the highest-risk merges.

## 4. Evaluate a stratified sample

Draw a seeded, stratified sample before judging a run. The pilot used
seed `20261013`, targeting 20 new / 5 review / 5 existing (shortfalls
reallocated to new); see `../pilot/sample_manifest.json` for the method.
Classify each sampled record by hand against the source record and the
baseline: Useful addition / Already represented / Not a useful beverage
candidate / Uncertain. Unverifiable records are Uncertain, never guessed.

## 5. Track errors and uncertainty

Keep a per-run log noting:

- Counts by status (per-run, not cumulative).
- Counts by manual classification for the sample.
- Failure types separately: already-represented (which alias or name
  pattern?), unverifiable (thin record?), out-of-scope (which
  boundary?), merge-risk (what evidence was missing?).
- Do not collapse different failure types into one score.

## 6. Decide whether to broaden

Expansion gates (all must hold before the next batch widens scope):

1. Useful-addition rate among sampled `new_candidate` is acceptable for
   the cost of review (pilot: 67% before alias fix, 89% after; n=30,
   directional only).
2. No systematic false-`existing` merges in the sample.
3. `needs_review` volume is triageable (not growing faster than review
   capacity).
4. New aliases, if any, are evidence-backed and tested.

## Accumulated vs per-run counts

`--summary` prints the last run's accumulated state. Per-run counts come
from diffing state before/after a run, or from a fresh isolated copy.
When reporting, always label which one a number is.

## Never for routine validation

Do not use `--reset-state` to "re-check" a run. It destructively forgets
previously discovered candidates, so the next run counts everything as
new again and per-run comparisons become meaningless. Reset only when
the state schema itself changes, and say so in the commit message.

## Related

- Current flags: `../src/config.py`
- Matcher: `../src/match.py`
- Pilot method: `../pilot/sample_manifest.json`
