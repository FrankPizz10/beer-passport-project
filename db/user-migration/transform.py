"""Transform parsed MySQL rows into PostgreSQL-ready rows.

Every input row ends up in exactly one of three places: the clean output,
the rejects list (cannot migrate cleanly; reported with a reason), or the
dedupes list (a valid row dropped because an equivalent row was kept;
reported with the kept row's id). Nothing is silently dropped.

Conventions:
- Source IDs are preserved as primary keys, unchanged.
- MySQL zero dates ('0000-00-00 00:00:00') become NULL; where the target
  column is NOT NULL (users.created_at / updated_at, added by the
  PostgreSQL port, audit F-11), the migration run timestamp is filled and
  counted.
- Mojibake (UTF-8 bytes mis-decoded as Latin-1 somewhere in the old
  stack's history) is repaired conservatively: a field is only rewritten
  when the Latin-1 to UTF-8 round trip succeeds and removes mojibake
  markers. Repairs are counted per table and field.
"""

import re

MOJIBAKE_MARKERS = ("Ã", "â€", "Â", "ðŸ")
ZERO_DATE = "0000-00-00 00:00:00"
_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(\.\d+)?$")

NOTIFICATION_TYPES = {"NEW_FRIEND", "BADGE_EARNED"}

USER_TABLES = [
    "users",
    "collections",
    "user_beers",
    "friends",
    "collection_beers",
    "user_badges",
    "notifications",
]


def repair_mojibake(value):
    """Return (possibly_repaired_value, repaired_bool)."""
    if not isinstance(value, str):
        return value, False
    if not any(marker in value for marker in MOJIBAKE_MARKERS):
        return value, False
    try:
        fixed = value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value, False
    if any(marker in fixed for marker in MOJIBAKE_MARKERS):
        return value, False
    return fixed, True


def _ts(value, *, nullable, run_ts, stats, field):
    """Normalize a timestamp value. Returns (value, ok)."""
    if value is None or value == ZERO_DATE or value == "":
        if nullable:
            return None, True
        stats["timestamps_filled"] = stats.get("timestamps_filled", 0) + 1
        return run_ts, True
    if isinstance(value, str) and _TS_RE.match(value):
        return value.replace("T", " "), True
    return None, False


def _bool(value):
    if value in (1, "1", True):
        return True
    if value in (0, "0", False, None):
        return False
    return bool(value)


class Reject:
    def __init__(self, table, source_id, category, reason, detail=""):
        self.table = table
        self.source_id = source_id
        self.category = category  # "reject" or "dedupe"
        self.reason = reason
        self.detail = detail

    def as_dict(self):
        return {
            "table": self.table,
            "source_id": self.source_id,
            "category": self.category,
            "reason": self.reason,
            "detail": self.detail,
        }


def _repair_fields(row, fields, stats, table):
    for field in fields:
        if field in row:
            fixed, repaired = repair_mojibake(row.get(field))
            if repaired:
                row[field] = fixed
                key = f"mojibake_repaired_{field}"
                stats[key] = stats.get(key, 0) + 1


def transform_all(parsed, *, valid_beer_ids, run_ts):
    """Transform all user tables.

    parsed: {table: [row, ...]} from dump_parser.parse_dump.
    valid_beer_ids: set of beer IDs present in the target catalog.
    run_ts: 'YYYY-MM-DD HH:MM:SS' string used to fill NOT NULL timestamps.

    Returns (clean, rejects, stats) where clean is {table: [row, ...]}
    with PostgreSQL column names and values, rejects is a list of Reject,
    and stats holds per-table counters.
    """
    clean = {t: [] for t in USER_TABLES}
    rejects = []
    stats = {t: {} for t in USER_TABLES}

    def reject(table, row, category, reason, detail=""):
        rejects.append(Reject(table, row.get("id"), category, reason, detail))

    # ---- users -------------------------------------------------------
    # Legacy push tokens are dropped before validation (set to None on
    # every output row, and counted in stats): the recovered tokens are
    # stale, devices re-register on sign-in, and a shared or recycled
    # token must never collide and exclude a matched profile.
    seen_uid, seen_email, seen_name = {}, {}, {}
    for row in sorted(parsed.get("users", []), key=lambda r: r["id"]):
        r = dict(row)
        _repair_fields(r, ["user_name"], stats["users"], "users")
        uid, email, name = r.get("uid"), r.get("email"), r.get("user_name")
        if uid is None or str(uid).strip() == "":
            reject("users", r, "reject", "missing_uid")
            continue
        if email is None or str(email).strip() == "":
            reject("users", r, "reject", "missing_email")
            continue
        if name is None or str(name).strip() == "":
            reject("users", r, "reject", "missing_user_name")
            continue
        if r.get("age") is None:
            reject("users", r, "reject", "missing_age", "age is NOT NULL in the PostgreSQL schema")
            continue
        dup = None
        if uid in seen_uid:
            dup = ("duplicate_uid", seen_uid[uid])
        elif email in seen_email:
            dup = ("duplicate_email", seen_email[email])
        elif name in seen_name:
            dup = ("duplicate_user_name", seen_name[name])
        if dup:
            reject("users", r, "reject", dup[0], f"conflicts with kept user id {dup[1]}")
            continue
        created, ok1 = _ts(r.get("created_at"), nullable=False, run_ts=run_ts, stats=stats["users"], field="created_at")
        updated, ok2 = _ts(r.get("updated_at"), nullable=False, run_ts=run_ts, stats=stats["users"], field="updated_at")
        if not (ok1 and ok2):
            reject("users", r, "reject", "unparseable_timestamp")
            continue
        seen_uid[uid] = r["id"]
        seen_email[email] = r["id"]
        seen_name[name] = r["id"]
        if r.get("notification_token"):
            stats["users"]["notification_tokens_dropped"] = (
                stats["users"].get("notification_tokens_dropped", 0) + 1
            )
        clean["users"].append(
            {
                "id": r["id"],
                "uid": uid,
                "notification_token": None,
                "age": int(r["age"]),
                "email": email,
                "user_name": name,
                "private": _bool(r.get("private")),
                "created_at": created,
                "updated_at": updated,
            }
        )
    valid_user_ids = {r["id"] for r in clean["users"]}

    # ---- collections ---------------------------------------------------
    seen_coll_name = {}
    for row in sorted(parsed.get("collections", []), key=lambda r: r["id"]):
        r = dict(row)
        _repair_fields(r, ["name", "description"], stats["collections"], "collections")
        name = r.get("name")
        if name is None or str(name).strip() == "":
            reject("collections", r, "reject", "missing_name")
            continue
        if name in seen_coll_name:
            reject("collections", r, "reject", "duplicate_name", f"conflicts with kept collection id {seen_coll_name[name]}")
            continue
        created, ok1 = _ts(r.get("created_at"), nullable=True, run_ts=run_ts, stats=stats["collections"], field="created_at")
        updated, ok2 = _ts(r.get("updated_at"), nullable=True, run_ts=run_ts, stats=stats["collections"], field="updated_at")
        if not (ok1 and ok2):
            reject("collections", r, "reject", "unparseable_timestamp")
            continue
        seen_coll_name[name] = r["id"]
        clean["collections"].append(
            {
                "id": r["id"],
                "name": name,
                "difficulty": int(r["difficulty"]) if r.get("difficulty") is not None else 0,
                "description": r.get("description") or "",
                "created_at": created,
                "updated_at": updated,
            }
        )
    valid_collection_ids = {r["id"] for r in clean["collections"]}

    # ---- friends -------------------------------------------------------
    # The PostgreSQL schema enforces user_1 < user_2 (audit F-1 CHECK).
    # Normalize order, collapse both-orders duplicates, reject self pairs
    # and pairs referencing users that did not migrate.
    seen_pairs = {}
    for row in sorted(parsed.get("friends", []), key=lambda r: r["id"]):
        r = dict(row)
        u1, u2 = r.get("user_1"), r.get("user_2")
        if u1 is None or u2 is None:
            reject("friends", r, "reject", "missing_user_reference")
            continue
        if u1 == u2:
            reject("friends", r, "reject", "self_friend_pair", f"user {u1}")
            continue
        lo, hi = min(u1, u2), max(u1, u2)
        if lo not in valid_user_ids or hi not in valid_user_ids:
            reject("friends", r, "reject", "orphan_user_reference", f"pair ({u1}, {u2})")
            continue
        if (lo, hi) in seen_pairs:
            reject("friends", r, "dedupe", "duplicate_pair_after_normalization", f"kept friend id {seen_pairs[(lo, hi)]}")
            continue
        created, ok1 = _ts(r.get("created_at"), nullable=False, run_ts=run_ts, stats=stats["friends"], field="created_at")
        updated, ok2 = _ts(r.get("updated_at"), nullable=False, run_ts=run_ts, stats=stats["friends"], field="updated_at")
        if not (ok1 and ok2):
            reject("friends", r, "reject", "unparseable_timestamp")
            continue
        seen_pairs[(lo, hi)] = r["id"]
        clean["friends"].append(
            {"id": r["id"], "user_1": lo, "user_2": hi, "created_at": created, "updated_at": updated}
        )

    # ---- user_beers ------------------------------------------------------
    best = {}
    for row in sorted(parsed.get("user_beers", []), key=lambda r: r["id"]):
        r = dict(row)
        if r.get("user_id") not in valid_user_ids:
            reject("user_beers", r, "reject", "orphan_user_reference", f"user_id {r.get('user_id')}")
            continue
        if r.get("beer_id") not in valid_beer_ids:
            reject("user_beers", r, "reject", "orphan_beer_reference", f"beer_id {r.get('beer_id')}")
            continue
        created, ok1 = _ts(r.get("created_at"), nullable=True, run_ts=run_ts, stats=stats["user_beers"], field="created_at")
        updated, ok2 = _ts(r.get("updated_at"), nullable=True, run_ts=run_ts, stats=stats["user_beers"], field="updated_at")
        if not (ok1 and ok2):
            reject("user_beers", r, "reject", "unparseable_timestamp")
            continue
        out = {
            "id": r["id"],
            "user_id": r["user_id"],
            "beer_id": r["beer_id"],
            "liked": _bool(r.get("liked")),
            "created_at": created,
            "updated_at": updated,
        }
        key = (out["user_id"], out["beer_id"])
        if key in best:
            kept = best[key]
            # Keep the most recently updated row; ties go to the higher id.
            if (out["updated_at"] or "", out["id"]) >= (kept["updated_at"] or "", kept["id"]):
                rejects.append(Reject("user_beers", kept["id"], "dedupe", "duplicate_user_beer", f"kept user_beer id {out['id']}"))
                best[key] = out
            else:
                rejects.append(Reject("user_beers", out["id"], "dedupe", "duplicate_user_beer", f"kept user_beer id {kept['id']}"))
            continue
        best[key] = out
    clean["user_beers"] = sorted(best.values(), key=lambda r: r["id"])

    # ---- collection_beers -------------------------------------------------
    seen_cb = {}
    for row in sorted(parsed.get("collection_beers", []), key=lambda r: r["id"]):
        r = dict(row)
        if r.get("collection_id") not in valid_collection_ids:
            reject("collection_beers", r, "reject", "orphan_collection_reference", f"collection_id {r.get('collection_id')}")
            continue
        if r.get("beer_id") not in valid_beer_ids:
            reject("collection_beers", r, "reject", "orphan_beer_reference", f"beer_id {r.get('beer_id')}")
            continue
        key = (r["collection_id"], r["beer_id"])
        if key in seen_cb:
            reject("collection_beers", r, "dedupe", "duplicate_collection_beer", f"kept collection_beer id {seen_cb[key]}")
            continue
        created, ok1 = _ts(r.get("created_at"), nullable=True, run_ts=run_ts, stats=stats["collection_beers"], field="created_at")
        updated, ok2 = _ts(r.get("updated_at"), nullable=True, run_ts=run_ts, stats=stats["collection_beers"], field="updated_at")
        if not (ok1 and ok2):
            reject("collection_beers", r, "reject", "unparseable_timestamp")
            continue
        seen_cb[key] = r["id"]
        clean["collection_beers"].append(
            {
                "id": r["id"],
                "collection_id": r["collection_id"],
                "beer_id": r["beer_id"],
                "created_at": created,
                "updated_at": updated,
            }
        )

    # ---- user_badges -------------------------------------------------------
    best_badge = {}
    for row in sorted(parsed.get("user_badges", []), key=lambda r: r["id"]):
        r = dict(row)
        if r.get("user_id") not in valid_user_ids:
            reject("user_badges", r, "reject", "orphan_user_reference", f"user_id {r.get('user_id')}")
            continue
        if r.get("collection_id") not in valid_collection_ids:
            reject("user_badges", r, "reject", "orphan_collection_reference", f"collection_id {r.get('collection_id')}")
            continue
        created, ok1 = _ts(r.get("created_at"), nullable=False, run_ts=run_ts, stats=stats["user_badges"], field="created_at")
        updated, ok2 = _ts(r.get("updated_at"), nullable=False, run_ts=run_ts, stats=stats["user_badges"], field="updated_at")
        if not (ok1 and ok2):
            reject("user_badges", r, "reject", "unparseable_timestamp")
            continue
        progress = r.get("progress")
        if progress is None:
            stats["user_badges"]["progress_nulled_to_zero"] = stats["user_badges"].get("progress_nulled_to_zero", 0) + 1
            progress = 0.0
        out = {
            "id": r["id"],
            "user_id": r["user_id"],
            "collection_id": r["collection_id"],
            "earned": _bool(r.get("earned")),
            "progress": float(progress),
            "created_at": created,
            "updated_at": updated,
        }
        key = (out["user_id"], out["collection_id"])
        if key in best_badge:
            kept = best_badge[key]
            # Keep the row showing the most progress; earned beats not.
            score = (out["earned"], out["progress"], out["id"])
            kept_score = (kept["earned"], kept["progress"], kept["id"])
            if score >= kept_score:
                rejects.append(Reject("user_badges", kept["id"], "dedupe", "duplicate_user_badge", f"kept user_badge id {out['id']}"))
                best_badge[key] = out
            else:
                rejects.append(Reject("user_badges", out["id"], "dedupe", "duplicate_user_badge", f"kept user_badge id {kept['id']}"))
            continue
        best_badge[key] = out
    clean["user_badges"] = sorted(best_badge.values(), key=lambda r: r["id"])

    # ---- notifications -------------------------------------------------------
    seen_notif = {}
    for row in sorted(parsed.get("notifications", []), key=lambda r: r["id"]):
        r = dict(row)
        _repair_fields(r, ["message"], stats["notifications"], "notifications")
        if r.get("user_id") not in valid_user_ids:
            reject("notifications", r, "reject", "orphan_user_reference", f"user_id {r.get('user_id')}")
            continue
        if r.get("type") not in NOTIFICATION_TYPES:
            reject("notifications", r, "reject", "unknown_notification_type", f"type {r.get('type')!r}")
            continue
        key = (r["user_id"], r.get("message"))
        if key in seen_notif:
            reject("notifications", r, "dedupe", "duplicate_user_message", f"kept notification id {seen_notif[key]}")
            continue
        created, ok1 = _ts(r.get("created_at"), nullable=False, run_ts=run_ts, stats=stats["notifications"], field="created_at")
        updated, ok2 = _ts(r.get("updated_at"), nullable=False, run_ts=run_ts, stats=stats["notifications"], field="updated_at")
        if not (ok1 and ok2):
            reject("notifications", r, "reject", "unparseable_timestamp")
            continue
        seen_notif[key] = r["id"]
        clean["notifications"].append(
            {
                "id": r["id"],
                "user_id": r["user_id"],
                "type": r["type"],
                "message": r.get("message") or "",
                "created_at": created,
                "updated_at": updated,
                "viewed": _bool(r.get("viewed")),
            }
        )

    return clean, rejects, stats
