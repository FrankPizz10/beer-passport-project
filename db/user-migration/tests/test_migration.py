"""Tests for the MySQL -> PostgreSQL user-data migration pipeline.

Unit tests for the dump parser and transforms, plus one end-to-end test
that runs the synthetic fixture through migrate.py into the local
beerpassport_migtest database. The end-to-end test is skipped when the
local db-recovery Postgres instance is not reachable.

Run: python3 -m unittest discover -s tests -v
"""

import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
MIGRATION_DIR = os.path.dirname(HERE)
sys.path.insert(0, MIGRATION_DIR)

from dump_parser import parse_dump
from transform import repair_mojibake, transform_all

RUN_TS = "2026-11-21 22:35:00"
BEER_IDS = {1, 2, 3, 2008}


def reasons(rejects, table):
    return sorted(r.reason for r in rejects if r.table == table)


class TestDumpParser(unittest.TestCase):
    def test_basic_insert(self):
        sql = "INSERT INTO `users` (`id`,`user_name`) VALUES (1,'anna'),(2,'bob');"
        rows = parse_dump(sql)["users"]
        self.assertEqual(rows, [{"id": 1, "user_name": "anna"}, {"id": 2, "user_name": "bob"}])

    def test_escapes_null_and_numbers(self):
        sql = r"INSERT INTO `t` (`a`,`b`,`c`,`d`) VALUES ('it\'s \\ fine\n',NULL,42,3.5);"
        row = parse_dump(sql)["t"][0]
        self.assertEqual(row["a"], "it's \\ fine\n")
        self.assertIsNone(row["b"])
        self.assertEqual(row["c"], 42)
        self.assertEqual(row["d"], 3.5)

    def test_doubled_quote_and_hex(self):
        sql = "INSERT INTO `t` (`a`,`b`) VALUES ('o''brien',0x41);"
        row = parse_dump(sql)["t"][0]
        self.assertEqual(row["a"], "o'brien")
        self.assertEqual(row["b"], "A")

    def test_column_count_mismatch_raises(self):
        sql = "INSERT INTO `t` (`a`,`b`) VALUES (1);"
        with self.assertRaises(ValueError):
            parse_dump(sql)

    def test_multiple_statements_and_tables(self):
        sql = (
            "INSERT INTO `a` (`id`) VALUES (1);\n"
            "INSERT INTO `b` (`id`) VALUES (2),(3);\n"
        )
        parsed = parse_dump(sql)
        self.assertEqual(len(parsed["a"]), 1)
        self.assertEqual(len(parsed["b"]), 2)


class TestMojibake(unittest.TestCase):
    def test_repairs_double_encoded(self):
        fixed, repaired = repair_mojibake("MÃ¼nchen Fan")
        self.assertTrue(repaired)
        self.assertEqual(fixed, "München Fan")

    def test_leaves_clean_text_alone(self):
        fixed, repaired = repair_mojibake("Plain Lager Fan")
        self.assertFalse(repaired)
        self.assertEqual(fixed, "Plain Lager Fan")

    def test_leaves_correct_utf8_alone(self):
        fixed, repaired = repair_mojibake("München Fan")
        self.assertFalse(repaired)
        self.assertEqual(fixed, "München Fan")


def base_parsed():
    return {
        "users": [
            {"id": 1, "uid": "uid1", "notification_token": None, "age": 30, "email": "a@x.invalid", "user_name": "anna", "private": 0},
            {"id": 2, "uid": "uid2", "notification_token": None, "age": 31, "email": "b@x.invalid", "user_name": "bob", "private": 1},
        ],
        "collections": [
            {"id": 1, "name": "Set One", "difficulty": 2, "description": "d", "created_at": "2023-01-01 00:00:00", "updated_at": "2023-01-02 00:00:00"},
        ],
        "friends": [],
        "user_beers": [],
        "collection_beers": [],
        "user_badges": [],
        "notifications": [],
    }


class TestTransforms(unittest.TestCase):
    def run_transform(self, parsed):
        return transform_all(parsed, valid_beer_ids=BEER_IDS, run_ts=RUN_TS)

    def test_users_fill_missing_timestamps(self):
        clean, rejects, stats = self.run_transform(base_parsed())
        self.assertEqual(len(clean["users"]), 2)
        self.assertEqual(clean["users"][0]["created_at"], RUN_TS)
        self.assertEqual(stats["users"]["timestamps_filled"], 4)
        self.assertFalse(clean["users"][0]["private"])
        self.assertTrue(clean["users"][1]["private"])

    def test_users_shared_push_token_never_excludes(self):
        parsed = base_parsed()
        parsed["users"][0]["notification_token"] = "shared-token"
        parsed["users"][1]["notification_token"] = "shared-token"
        clean, rejects, stats = self.run_transform(parsed)
        self.assertEqual(len(clean["users"]), 2)
        self.assertEqual(reasons(rejects, "users"), [])
        self.assertEqual([u["notification_token"] for u in clean["users"]], [None, None])
        self.assertEqual(stats["users"]["notification_tokens_dropped"], 2)

    def test_users_reject_missing_age_and_duplicate_email(self):
        parsed = base_parsed()
        parsed["users"].append({"id": 3, "uid": "uid3", "notification_token": None, "age": None, "email": "c@x.invalid", "user_name": "cid", "private": 0})
        parsed["users"].append({"id": 4, "uid": "uid4", "notification_token": None, "age": 22, "email": "a@x.invalid", "user_name": "dan", "private": 0})
        clean, rejects, _ = self.run_transform(parsed)
        self.assertEqual(len(clean["users"]), 2)
        self.assertEqual(reasons(rejects, "users"), ["duplicate_email", "missing_age"])

    def test_friends_normalize_dedupe_and_reject(self):
        parsed = base_parsed()
        parsed["friends"] = [
            {"id": 1, "user_1": 2, "user_2": 1, "created_at": "2024-01-01 00:00:00", "updated_at": "2024-01-01 00:00:00"},
            {"id": 2, "user_1": 1, "user_2": 2, "created_at": "2024-01-02 00:00:00", "updated_at": "2024-01-02 00:00:00"},
            {"id": 3, "user_1": 1, "user_2": 1, "created_at": "2024-01-03 00:00:00", "updated_at": "2024-01-03 00:00:00"},
            {"id": 4, "user_1": 1, "user_2": 99, "created_at": "2024-01-04 00:00:00", "updated_at": "2024-01-04 00:00:00"},
        ]
        clean, rejects, _ = self.run_transform(parsed)
        self.assertEqual(len(clean["friends"]), 1)
        self.assertEqual((clean["friends"][0]["user_1"], clean["friends"][0]["user_2"]), (1, 2))
        self.assertEqual(
            reasons(rejects, "friends"),
            ["duplicate_pair_after_normalization", "orphan_user_reference", "self_friend_pair"],
        )

    def test_user_beers_dedupe_keeps_latest_and_orphans_reject(self):
        parsed = base_parsed()
        parsed["user_beers"] = [
            {"id": 1, "user_id": 1, "beer_id": 2008, "liked": 0, "created_at": "2024-02-01 00:00:00", "updated_at": "2024-03-01 00:00:00"},
            {"id": 2, "user_id": 1, "beer_id": 2008, "liked": 1, "created_at": "2024-02-01 00:00:00", "updated_at": "2024-06-01 00:00:00"},
            {"id": 3, "user_id": 1, "beer_id": 999999, "liked": 0, "created_at": None, "updated_at": None},
            {"id": 4, "user_id": 1, "beer_id": 2, "liked": 0, "created_at": "2024-02-01 00:00:00", "updated_at": "0000-00-00 00:00:00"},
        ]
        clean, rejects, _ = self.run_transform(parsed)
        self.assertEqual(len(clean["user_beers"]), 2)
        kept = [r for r in clean["user_beers"] if r["beer_id"] == 2008][0]
        self.assertEqual(kept["id"], 2)
        self.assertTrue(kept["liked"])
        zero = [r for r in clean["user_beers"] if r["beer_id"] == 2][0]
        self.assertIsNone(zero["updated_at"])
        self.assertEqual(reasons(rejects, "user_beers"), ["duplicate_user_beer", "orphan_beer_reference"])

    def test_notifications_unknown_type_rejects(self):
        parsed = base_parsed()
        parsed["notifications"] = [
            {"id": 1, "user_id": 1, "type": "PROMO", "message": "x", "created_at": "2024-05-01 00:00:00", "updated_at": "2024-05-01 00:00:00", "viewed": 0},
        ]
        clean, rejects, _ = self.run_transform(parsed)
        self.assertEqual(clean["notifications"], [])
        self.assertEqual(reasons(rejects, "notifications"), ["unknown_notification_type"])

    def test_every_row_accounted_for(self):
        parsed = base_parsed()
        parsed["friends"] = [
            {"id": 1, "user_1": 1, "user_2": 2, "created_at": "2024-01-01 00:00:00", "updated_at": "2024-01-01 00:00:00"},
            {"id": 2, "user_1": 2, "user_2": 1, "created_at": "2024-01-01 00:00:00", "updated_at": "2024-01-01 00:00:00"},
        ]
        clean, rejects, _ = self.run_transform(parsed)
        total_in = sum(len(v) for v in parsed.values())
        total_out = sum(len(v) for v in clean.values()) + len(rejects)
        self.assertEqual(total_in, total_out)


WS = "/home/hatch/workspace/workstreams/db-recovery"
PSQL = os.path.join(WS, "pginstall/bin/psql")


def pg_reachable():
    if not os.path.exists(PSQL):
        return False
    env = dict(os.environ, LD_LIBRARY_PATH=os.path.join(WS, "pginstall/lib"))
    result = subprocess.run(
        [PSQL, "-h", "127.0.0.1", "-p", "54329", "-U", "postgres", "-d", "beerpassport_migtest", "-tAc", "SELECT 1"],
        capture_output=True, text=True, env=env,
    )
    return result.returncode == 0 and result.stdout.strip() == "1"


@unittest.skipUnless(pg_reachable(), "local db-recovery Postgres instance not reachable")
class TestEndToEndFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out_dir = os.path.join(MIGRATION_DIR, "runs", "test-e2e")
        env = dict(
            os.environ,
            PSQL_BIN=PSQL,
            PGHOST="127.0.0.1",
            PGPORT="54329",
            PGUSER="postgres",
            LD_LIBRARY_PATH=os.path.join(WS, "pginstall/lib"),
        )
        subprocess.run(
            [sys.executable, os.path.join(MIGRATION_DIR, "make_fixture.py"), os.path.join(MIGRATION_DIR, "fixture")],
            check=True, capture_output=True, text=True,
        )
        result = subprocess.run(
            [
                sys.executable, os.path.join(MIGRATION_DIR, "migrate.py"),
                "--dump", os.path.join(MIGRATION_DIR, "fixture/fixture_user_tables.sql"),
                "--sha256", os.path.join(MIGRATION_DIR, "fixture/fixture_user_tables.sql.sha256"),
                "--database", "beerpassport_migtest",
                "--out", cls.out_dir,
                "--truncate-user-tables",
                "--run-ts", RUN_TS,
            ],
            capture_output=True, text=True, env=env,
        )
        if result.returncode != 0:
            raise AssertionError(f"migrate.py failed: {result.stdout} {result.stderr}")
        with open(os.path.join(cls.out_dir, "manifest.json")) as f:
            cls.manifest = json.load(f)

    def test_totals(self):
        m = self.manifest
        self.assertEqual(m["total_source_rows"], 890)
        self.assertEqual(m["total_loaded"], 858)
        self.assertEqual(m["total_rejected"], 17)
        self.assertEqual(m["total_deduped"], 15)
        self.assertTrue(m["checksum_verified"])

    def test_per_table_loaded(self):
        expected = {
            "users": 122,
            "collections": 13,
            "user_beers": 282,
            "friends": 100,
            "collection_beers": 144,
            "user_badges": 131,
            "notifications": 66,
        }
        for table, count in expected.items():
            self.assertEqual(self.manifest["per_table"][table]["loaded"], count, table)
            self.assertEqual(self.manifest["per_table"][table]["db_count_after_load"], count, table)

    def test_validation_all_zero(self):
        self.assertTrue(self.manifest["validation"]["all_orphan_checks_zero"])

    def _run_migrate(self, extra_args, out_name):
        env = dict(os.environ, PSQL_BIN=PSQL, PGHOST="127.0.0.1", PGPORT="54329", PGUSER="postgres",
                   LD_LIBRARY_PATH=os.path.join(WS, "pginstall/lib"))
        result = subprocess.run(
            [
                sys.executable, os.path.join(MIGRATION_DIR, "migrate.py"),
                "--dump", os.path.join(MIGRATION_DIR, "fixture/fixture_user_tables.sql"),
                "--sha256", os.path.join(MIGRATION_DIR, "fixture/fixture_user_tables.sql.sha256"),
                "--database", "beerpassport_migtest",
                "--out", os.path.join(MIGRATION_DIR, "runs", out_name),
                "--run-ts", RUN_TS,
            ] + extra_args,
            capture_output=True, text=True, env=env,
        )
        return result, env

    def test_dry_run_reports_without_writing(self):
        result, env = self._run_migrate(["--dry-run"], "test-dry-run")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("DRY RUN", result.stdout)
        with open(os.path.join(MIGRATION_DIR, "runs", "test-dry-run", "manifest.json")) as f:
            m = json.load(f)
        self.assertTrue(m["dry_run"])
        self.assertIsNone(m["validation"])
        self.assertEqual(m["total_loaded"], 858)
        self.assertEqual(m["total_rejected"], 17)
        out = subprocess.run(
            [PSQL, "-h", "127.0.0.1", "-p", "54329", "-U", "postgres", "-d", "beerpassport_migtest", "-tAc",
             "SELECT count(*) FROM users"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(out.stdout.strip(), "122")

    def test_expect_users_mismatch_aborts_before_writing(self):
        result, _ = self._run_migrate(["--expect-users", "999"], "test-expect-users")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected exactly 999 users after transform", result.stderr + result.stdout)

    def test_require_empty_refuses_nonempty_target(self):
        result, _ = self._run_migrate(["--require-empty"], "test-require-empty")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires empty target user tables", result.stderr + result.stdout)

    def test_checksum_mismatch_aborts(self):
        env = dict(os.environ, PSQL_BIN=PSQL, PGHOST="127.0.0.1", PGPORT="54329", PGUSER="postgres",
                   LD_LIBRARY_PATH=os.path.join(WS, "pginstall/lib"))
        bad_sha = os.path.join(MIGRATION_DIR, "runs", "test-bad-sha-input.sha256")
        with open(bad_sha, "w") as f:
            f.write("0" * 64 + "  fixture_user_tables.sql\n")
        result = subprocess.run(
            [
                sys.executable, os.path.join(MIGRATION_DIR, "migrate.py"),
                "--dump", os.path.join(MIGRATION_DIR, "fixture/fixture_user_tables.sql"),
                "--sha256", bad_sha,
                "--database", "beerpassport_migtest",
                "--out", os.path.join(MIGRATION_DIR, "runs", "test-bad-sha"),
            ],
            capture_output=True, text=True, env=env,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SHA-256 mismatch", result.stderr + result.stdout)


if __name__ == "__main__":
    unittest.main()
