import unittest
import sqlite3
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from core.api.main import app, init_db


class ApiSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health_returns_expected_shape(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["service"], "auripostao-api")
        self.assertIn("version", body)
        self.assertIn("time_utc", body)

    def test_bootstrap_returns_db_path_and_mode(self) -> None:
        response = self.client.get("/bootstrap")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("db_path", body)
        self.assertIn("mode", body)


class ApiDatabaseTests(unittest.TestCase):
    def test_init_db_creates_expected_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "auripostao.db"
            version = init_db(str(db_path))

            self.assertEqual(version, 1)

            with sqlite3.connect(db_path) as conn:
                rows = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                tables = {name for (name,) in rows}

            self.assertTrue({"workflows", "workflow_revisions", "workflow_status"}.issubset(tables))

    def test_init_db_records_initial_migration(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "auripostao.db"
            init_db(str(db_path))

            with sqlite3.connect(db_path) as conn:
                version = conn.execute(
                    "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
                ).fetchone()[0]

            self.assertEqual(version, 1)

    def test_workflows_enforces_unique_name_per_local_user(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "auripostao.db"
            init_db(str(db_path))

            now = "2026-03-19T00:00:00+00:00"
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO workflows(local_user, name, description, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    ("local", "workflow-A", "", 1, now, now),
                )
                with self.assertRaises(sqlite3.IntegrityError):
                    conn.execute(
                        """
                        INSERT INTO workflows(local_user, name, description, is_active, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        ("local", "workflow-A", "duplicate", 1, now, now),
                    )


if __name__ == "__main__":
    unittest.main()