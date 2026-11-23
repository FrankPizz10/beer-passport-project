"""Tests for the stdin \\copy load path, the in-transaction locked
empty-table gate, and private run outputs.

The load streams row data through psql's stdin (\\copy ... FROM STDIN)
instead of referencing host-side files, so it works when psql runs in a
container. The empty-table check runs inside the load transaction,
after LOCK TABLE ... ACCESS EXCLUSIVE on all seven user tables, so no
other writer can change the tables between the check and the load.

Unit tests cover the generated script's structure and the COPY
escaping. The live tests run the real psql subprocess path against the
local db-recovery PostgreSQL instance (same gating as
test_migration.py), in throwaway databases the tests create and drop,
including rollback on a non-empty table and data containing
backslashes, newlines, tabs, and the two characters backslash-dot.

Run: python3 -m unittest discover -s tests -v
"""

import hashlib
import os
import stat
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
MIGRATION_DIR = os.path.dirname(HERE)
sys.path.insert(0, MIGRATION_DIR)

import migrate

WS = "/home/hatch/workspace/workstreams/db-recovery"
PSQL = os.path.join(WS, "pginstall/bin/psql")
SCHEMA_SQL = (
    "/home/hatch/workspace/workstreams/pilot-impl/repo/prisma/migrations/"
    "20261027000001_init/migration.sql"
)
TS = "2024-01-01 00:00:00"


def empty_clean():
    return {table: [] for table in migrate.LOAD_ORDER}


def nasty_clean():
    clean = empty_clean()
    clean["users"] = [
        {"id": 1, "uid": "uid-backslash", "notification_token": None, "age": 30,
         "email": "back\\slash@example.com", "user_name": "Back\\Slash",
         "private": False, "created_at": TS, "updated_at": TS},
        {"id": 2, "uid": "uid-newline", "notification_token": None, "age": 41,
         "email": "nl@example.com", "user_name": "Line1\nLine2",
         "private": True, "created_at": TS, "updated_at": TS},
        {"id": 3, "uid": "uid-dot", "notification_token": None, "age": 25,
         "email": "dot@example.com", "user_name": "\\.",
         "private": False, "created_at": TS, "updated_at": TS},
    ]
    clean["collections"] = [
        {"id": 1, "name": "Starters", "difficulty": 1, "description": "Starter pack",
         "created_at": TS, "updated_at": TS},
    ]
    clean["user_beers"] = [
        {"id": 1, "user_id": 1, "beer_id": 101, "liked": True,
         "created_at": TS, "updated_at": TS},
    ]
    clean["friends"] = [
        {"id": 1, "user_1": 1, "user_2": 2, "created_at": TS, "updated_at": TS},
    ]
    clean["collection_beers"] = [
        {"id": 1, "collection_id": 1, "beer_id": 101,
         "created_at": TS, "updated_at": TS},
    ]
    clean["user_badges"] = [
        {"id": 1, "user_id": 1, "collection_id": 1, "earned": True,
         "progress": 100, "created_at": TS, "updated_at": TS},
    ]
    clean["notifications"] = [
        {"id": 1, "user_id": 1, "type": "NEW_FRIEND",
         "message": "first line\nsecond \\. line\twith tab and back\\slash",
         "created_at": TS, "updated_at": TS, "viewed": False},
    ]
    return clean


class TestCopyEscape(unittest.TestCase):
    def test_backslash_dot_is_escaped(self):
        self.assertEqual(migrate._copy_escape("\\."), "\\\\.")

    def test_backslash_doubled(self):
        self.assertEqual(migrate._copy_escape("a\\b"), "a\\\\b")

    def test_newline_and_tab_escaped(self):
        self.assertEqual(migrate._copy_escape("a\nb\tc\rd"), "a\\nb\\tc\\rd")

    def test_null_and_bool(self):
        self.assertEqual(migrate._copy_escape(None), "\\N")
        self.assertEqual(migrate._copy_escape(True), "t")
        self.assertEqual(migrate._copy_escape(False), "f")


class TestBuildLoadScript(unittest.TestCase):
    def test_structure_require_empty(self):
        script = migrate.build_load_script(
            nasty_clean(), truncate=False, require_empty=True, expect_users=3
        )
        lines = script.split("\n")
        self.assertEqual(lines[0], "BEGIN;")
        self.assertTrue(lines[1].startswith("LOCK TABLE"))
        self.assertIn("ACCESS EXCLUSIVE", lines[1])
        for table in migrate.LOAD_ORDER:
            self.assertIn(table, lines[1])
        lock_at = script.index("LOCK TABLE")
        gate_at = script.index("production load requires empty target user tables")
        copy_at = script.index("\\copy users")
        self.assertLess(lock_at, gate_at)
        self.assertLess(gate_at, copy_at)
        self.assertEqual(script.count("FROM STDIN"), 7)
        self.assertEqual(sum(1 for line in lines if line == "\\."), 7)
        self.assertNotIn(".copy", script)
        self.assertNotIn("FROM '", script)
        self.assertIn("expected exactly 3 users", script)
        self.assertEqual(lines[-1], "COMMIT;")

    def test_truncate_variant_has_no_empty_gate(self):
        script = migrate.build_load_script(
            nasty_clean(), truncate=True, require_empty=False
        )
        self.assertIn("TRUNCATE", script)
        self.assertNotIn("requires empty target user tables", script)
        self.assertNotIn("are not empty", script)

    def test_plain_variant_guards_nonempty(self):
        script = migrate.build_load_script(
            nasty_clean(), truncate=False, require_empty=False
        )
        self.assertIn("target user tables are not empty", script)
        self.assertIn("LOCK TABLE", script)


class TestPrivateOutputs(unittest.TestCase):
    def test_dir_created_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "run-out")
            migrate.ensure_private_dir(target)
            self.assertEqual(stat.S_IMODE(os.stat(target).st_mode), 0o700)

    def test_existing_dir_tightened(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.chmod(tmp, 0o755)
            migrate.ensure_private_dir(tmp)
            self.assertEqual(stat.S_IMODE(os.stat(tmp).st_mode), 0o700)

    def test_file_written_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "manifest.json")
            migrate.write_private_file(path, "{}")
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
            migrate.write_private_file(path, "{\"a\": 1}")
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)


def pg_reachable():
    if not (os.path.exists(PSQL) and os.path.exists(SCHEMA_SQL)):
        return False
    env = dict(os.environ, LD_LIBRARY_PATH=os.path.join(WS, "pginstall/lib"))
    result = subprocess.run(
        [PSQL, "-h", "127.0.0.1", "-p", "54329", "-U", "postgres",
         "-d", "beerpassport_migtest", "-tAc", "SELECT 1"],
        capture_output=True, text=True, env=env,
    )
    return result.returncode == 0 and result.stdout.strip() == "1"


@unittest.skipUnless(pg_reachable(), "local db-recovery Postgres instance not reachable")
class TestStdinCopyLive(unittest.TestCase):
    DB = "beerpassport_stdin_test"
    DB2 = "beerpassport_stdin_test2"

    @classmethod
    def setUpClass(cls):
        cls._saved_env = {
            k: os.environ.get(k)
            for k in ("PSQL_BIN", "PGHOST", "PGPORT", "PGUSER", "LD_LIBRARY_PATH")
        }
        os.environ.update(
            PSQL_BIN=PSQL, PGHOST="127.0.0.1", PGPORT="54329",
            PGUSER="postgres",
            LD_LIBRARY_PATH=os.path.join(WS, "pginstall/lib"),
        )
        for db in (cls.DB, cls.DB2):
            migrate.psql("postgres", ["-q", "-c", f"DROP DATABASE IF EXISTS {db}"])
            migrate.psql("postgres", ["-q", "-c", f"CREATE DATABASE {db}"])
            migrate.psql(db, ["-q", "-f", SCHEMA_SQL])
            migrate.psql(db, ["-q", "-c",
                              "INSERT INTO beers (id, name) VALUES (101, 'Test Ale'), (102, 'Test Lager')"])

    @classmethod
    def tearDownClass(cls):
        for db in (cls.DB, cls.DB2):
            migrate.psql("postgres", ["-q", "-c", f"DROP DATABASE IF EXISTS {db}"])
        for key, value in cls._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_stdin_load_roundtrips_hostile_data(self):
        migrate.load(self.DB, nasty_clean(), truncate=False,
                     require_empty=True, expect_users=3)
        def md5_of(sql):
            return migrate.query_scalar(self.DB, sql)
        self.assertEqual(
            md5_of("SELECT md5(user_name) FROM users WHERE id = 1"),
            hashlib.md5("Back\\Slash".encode()).hexdigest())
        self.assertEqual(
            md5_of("SELECT md5(user_name) FROM users WHERE id = 2"),
            hashlib.md5("Line1\nLine2".encode()).hexdigest())
        self.assertEqual(
            md5_of("SELECT md5(user_name) FROM users WHERE id = 3"),
            hashlib.md5("\\.".encode()).hexdigest())
        self.assertEqual(
            md5_of("SELECT md5(message) FROM notifications WHERE id = 1"),
            hashlib.md5("first line\nsecond \\. line\twith tab and back\\slash".encode()).hexdigest())
        for table, expected in (("users", 3), ("collections", 1), ("user_beers", 1),
                                ("friends", 1), ("collection_beers", 1),
                                ("user_badges", 1), ("notifications", 1)):
            self.assertEqual(
                migrate.query_scalar(self.DB, f"SELECT count(*) FROM {table}"),
                str(expected), table)
        self.assertTrue(migrate.validate(self.DB)["all_orphan_checks_zero"])

    def test_nonempty_target_rolls_back(self):
        migrate.psql(self.DB2, ["-q", "-c",
                                "INSERT INTO users (id, uid, notification_token, age, email, user_name, private, created_at, updated_at) "
                                "VALUES (999, 'pre-existing', NULL, 50, 'pre@example.com', 'Pre Existing', false, "
                                "'2024-01-01 00:00:00', '2024-01-01 00:00:00')"])
        with self.assertRaises(RuntimeError) as ctx:
            migrate.load(self.DB2, nasty_clean(), truncate=False,
                         require_empty=True, expect_users=3)
        self.assertIn("requires empty target user tables", str(ctx.exception))
        self.assertEqual(
            migrate.query_scalar(self.DB2, "SELECT count(*) FROM users"), "1")
        self.assertEqual(
            migrate.query_scalar(self.DB2, "SELECT user_name FROM users WHERE id = 999"),
            "Pre Existing")
        for table in ("collections", "user_beers", "friends", "collection_beers",
                      "user_badges", "notifications"):
            self.assertEqual(
                migrate.query_scalar(self.DB2, f"SELECT count(*) FROM {table}"),
                "0", table)


if __name__ == "__main__":
    unittest.main()
