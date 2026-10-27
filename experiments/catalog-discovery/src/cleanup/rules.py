"""Cleanup rules for the old BeerPassport catalog (v1).

Implements docs/09-old-catalog-cleanup-strategy.md. Every rule is
provable from the data itself; nothing is changed on suspicion.
All functions are pure: they take row dicts and return new rows plus
a change log, so they can be unit tested without touching files.

Rules:
    R1  Drop breweries referenced by zero beers.
    R2  Clear provably garbage UPCs to the dataset's null value "0";
        flag other unexpected UPC formats without changing them.
    R3  Strip the "(discontinued)" marker from beer names and record
        it in a new "discontinued" column ("1" or "0") instead.
    R4  Report duplicate (name, brewery_id) groups; never merge.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# 2147483647 is INT_MAX, the classic sentinel left behind by imports
# that had no real barcode.
SENTINEL_UPCS = {"2147483647"}
# The shortest real barcode format relevant here is UPC-E (8 digits);
# UPC-A is 12 and EAN-13 is 13.
MIN_BARCODE_LEN = 8
# The baseline's own null convention for upc is "0" (or empty).
NULL_UPC = "0"

_DISCONTINUED_RE = re.compile(r"\(\s*discontinued\s*\)", re.IGNORECASE)


@dataclass
class Change:
    rule: str
    entity: str        # "beer" or "brewery"
    row_id: str
    field: str         # "" for whole-row changes
    before: str
    after: str
    action: str        # "drop_row" or "set_field"


@dataclass
class Flag:
    """A finding reported to a human; the data is never changed."""
    rule: str
    entity: str
    row_id: str
    detail: str


@dataclass
class CleanupResult:
    beers: list[dict]
    breweries: list[dict]
    changes: list[Change] = field(default_factory=list)
    flags: list[Flag] = field(default_factory=list)
    input_beer_count: int = 0
    input_brewery_count: int = 0

    @property
    def dropped_brewery_ids(self) -> list[str]:
        return [c.row_id for c in self.changes
                if c.rule == "R1" and c.action == "drop_row"]


def is_garbage_upc(value: str | None) -> bool:
    """True when a stored UPC is provably not a real barcode.

    Empty and "0" are the dataset's null convention and are not
    garbage. A value is garbage when it is a known sentinel or an
    all-digit string shorter than any real barcode format. Anything
    else, including non-numeric strings, is not this rule's business;
    see is_unexpected_upc.
    """
    v = (value or "").strip()
    if v in ("", NULL_UPC):
        return False
    if v in SENTINEL_UPCS:
        return True
    return v.isdigit() and len(v) < MIN_BARCODE_LEN


def is_unexpected_upc(value: str | None) -> bool:
    """True for a non-null UPC that is neither valid-looking nor
    covered by the garbage rule (for example, letters in the field).
    Such values are reported, never changed."""
    v = (value or "").strip()
    if v in ("", NULL_UPC) or is_garbage_upc(v):
        return False
    return not (v.isdigit() and len(v) >= MIN_BARCODE_LEN)


def has_discontinued_marker(name: str | None) -> bool:
    return bool(_DISCONTINUED_RE.search(name or ""))


def strip_discontinued_marker(name: str) -> str:
    """Remove the (discontinued) marker and normalize whitespace."""
    cleaned = _DISCONTINUED_RE.sub("", name or "")
    return " ".join(cleaned.split())


def apply_cleanup(beers: list[dict],
                  breweries: list[dict]) -> CleanupResult:
    """Apply rules R1-R4. The input rows are not mutated."""
    changes: list[Change] = []
    flags: list[Flag] = []

    # R1: drop breweries referenced by zero beers.
    referenced = {b.get("brewery_id", "") for b in beers}
    kept_breweries: list[dict] = []
    for brew in breweries:
        bid = brew.get("id", "")
        if bid in referenced:
            kept_breweries.append(dict(brew))
        else:
            changes.append(Change(
                rule="R1", entity="brewery", row_id=bid, field="",
                before=brew.get("name", ""), after="",
                action="drop_row"))

    # R2 and R3, per beer.
    cleaned_beers: list[dict] = []
    for beer in beers:
        row = dict(beer)
        beer_id = row.get("id", "")

        upc = row.get("upc", "")
        if is_garbage_upc(upc):
            changes.append(Change(
                rule="R2", entity="beer", row_id=beer_id, field="upc",
                before=upc, after=NULL_UPC, action="set_field"))
            row["upc"] = NULL_UPC
        elif is_unexpected_upc(upc):
            flags.append(Flag(
                rule="R2", entity="beer", row_id=beer_id,
                detail=f"unexpected UPC format left unchanged: {upc!r}"))

        name = row.get("name", "")
        if has_discontinued_marker(name):
            new_name = strip_discontinued_marker(name)
            changes.append(Change(
                rule="R3", entity="beer", row_id=beer_id, field="name",
                before=name, after=new_name, action="set_field"))
            row["name"] = new_name
            row["discontinued"] = "1"
        else:
            row["discontinued"] = "0"
        cleaned_beers.append(row)

    # R4: duplicate (normalized name, brewery_id) groups, report only.
    groups: dict[tuple[str, str], list[str]] = {}
    for beer in cleaned_beers:
        key = ((beer.get("name") or "").strip().lower(),
               beer.get("brewery_id", ""))
        groups.setdefault(key, []).append(beer.get("id", ""))
    for (norm_name, brewery_id), ids in sorted(groups.items()):
        if len(ids) > 1:
            flags.append(Flag(
                rule="R4", entity="beer", row_id=",".join(ids),
                detail=(f"duplicate group: name={norm_name!r} "
                        f"brewery_id={brewery_id} rows={ids}")))

    return CleanupResult(
        beers=cleaned_beers,
        breweries=kept_breweries,
        changes=changes,
        flags=flags,
        input_beer_count=len(beers),
        input_brewery_count=len(breweries),
    )


def reconcile(result: CleanupResult) -> list[str]:
    """Accounting check. Returns a list of problems; empty balances.

    Invariants: v1 never drops a beer, and every dropped brewery is
    accounted for in the change log exactly once and absent from the
    output.
    """
    problems: list[str] = []
    if len(result.beers) != result.input_beer_count:
        problems.append(
            f"beer count mismatch: in={result.input_beer_count} "
            f"out={len(result.beers)} (v1 never drops a beer)")
    dropped = result.dropped_brewery_ids
    if len(result.breweries) + len(dropped) != result.input_brewery_count:
        problems.append(
            f"brewery count mismatch: in={result.input_brewery_count} "
            f"out={len(result.breweries)} dropped={len(dropped)}")
    kept_ids = {b.get("id", "") for b in result.breweries}
    overlap = kept_ids.intersection(dropped)
    if overlap:
        problems.append(
            f"dropped breweries still present in output: {sorted(overlap)}")
    if len(set(dropped)) != len(dropped):
        problems.append("a brewery id appears more than once in the drop log")
    return problems
