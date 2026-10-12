"""Persistent discovery state for repeatable incremental runs.

State tracks, per source, the record ids already processed, plus the merged
candidate list. Reprocessing unchanged data is idempotent: previously
discovered candidates keep their first_discovered_at and are NOT counted as
new again. A record seen in a second source updates source associations
instead of creating a duplicate candidate.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class State:
    seen_source_ids: dict[str, list[str]] = field(default_factory=dict)
    candidates: dict[str, dict] = field(default_factory=dict)  # id -> record
    producers: dict[str, dict] = field(default_factory=dict)   # id -> record
    last_run: str = ""


def load_state(state_dir: Path) -> State:
    path = state_dir / "discovery_state.json"
    if not path.exists():
        return State()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return State(
            seen_source_ids=data.get("seen_source_ids", {}),
            candidates=data.get("candidates", {}),
            producers=data.get("producers", {}),
            last_run=data.get("last_run", ""),
        )
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Could not load state (%s); starting fresh", e)
        return State()


def save_state(state_dir: Path, state: State) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    state.last_run = utcnow()
    path = state_dir / "discovery_state.json"
    path.write_text(json.dumps(asdict(state), indent=2, ensure_ascii=False),
                    encoding="utf-8")


def reset_state(state_dir: Path) -> None:
    path = state_dir / "discovery_state.json"
    if path.exists():
        path.unlink()
    log.info("Discovery state reset (previous candidates are forgotten)")


def merge_candidate(state: State, cand: dict) -> str:
    """Merge a candidate into state. Returns 'new' or 'updated'.

    Identity: same candidate_id -> update source associations and last_seen_at.
    A second source reporting the same candidate updates associations rather
    than creating a duplicate.
    """
    cid = cand["candidate_id"]
    now = utcnow()
    existing = state.candidates.get(cid)
    if existing is None:
        cand["first_discovered_at"] = now
        cand["last_seen_at"] = now
        state.candidates[cid] = cand
        return "new"
    # Merge source associations.
    for key in ("source_names", "source_record_ids", "source_urls"):
        merged = list(existing.get(key, []))
        for v in cand.get(key, []):
            if v not in merged:
                merged.append(v)
        existing[key] = merged
    existing["last_seen_at"] = now
    # A later match verdict wins, but keep the earliest discovery timestamp.
    existing["match_status"] = cand["match_status"]
    existing["match_confidence"] = cand["match_confidence"]
    existing["existing_beerpassport_id"] = cand["existing_beerpassport_id"]
    for r in cand.get("review_reasons", []):
        if r not in existing["review_reasons"]:
            existing["review_reasons"].append(r)
    return "updated"
