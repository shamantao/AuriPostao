import unittest
import sqlite3
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

import core.api.main as api_main
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


class ApiWorkflowCrudTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmpdir.name) / "auripostao.db")
        self.original_db_path = api_main.DB_PATH
        api_main.DB_PATH = self.db_path
        init_db(self.db_path)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        api_main.DB_PATH = self.original_db_path
        self.tmpdir.cleanup()

    def test_crud_workflow_lifecycle(self) -> None:
        create = self.client.post(
            "/workflows",
            json={"name": "WF demo", "description": "initial", "is_active": True},
        )
        self.assertEqual(create.status_code, 201)
        created = create.json()
        self.assertEqual(created["name"], "WF demo")
        self.assertTrue(created["is_active"])
        workflow_id = created["id"]

        listing = self.client.get("/workflows")
        self.assertEqual(listing.status_code, 200)
        items = listing.json()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], workflow_id)

        update = self.client.put(
            f"/workflows/{workflow_id}",
            json={"name": "WF v2", "description": "updated", "is_active": False},
        )
        self.assertEqual(update.status_code, 200)
        updated = update.json()
        self.assertEqual(updated["name"], "WF v2")
        self.assertFalse(updated["is_active"])

        delete = self.client.delete(f"/workflows/{workflow_id}")
        self.assertEqual(delete.status_code, 200)
        self.assertTrue(delete.json()["deleted"])

    def test_create_requires_name_validation(self) -> None:
        response = self.client.post(
            "/workflows",
            json={"description": "missing required field"},
        )
        self.assertEqual(response.status_code, 422)
        body = response.json()
        self.assertEqual(body["code"], "validation_error")
        self.assertIn("name", body["message"])

    def test_duplicate_name_returns_structured_conflict(self) -> None:
        first = self.client.post(
            "/workflows",
            json={"name": "WF unique", "description": "first", "is_active": True},
        )
        self.assertEqual(first.status_code, 201)

        second = self.client.post(
            "/workflows",
            json={"name": "WF unique", "description": "duplicate", "is_active": True},
        )
        self.assertEqual(second.status_code, 409)
        body = second.json()
        self.assertEqual(body["code"], "workflow_name_conflict")
        self.assertIn("already exists", body["message"])

    def test_update_unknown_id_returns_structured_not_found(self) -> None:
        response = self.client.put(
            "/workflows/99999",
            json={"name": "unknown", "description": "x", "is_active": True},
        )
        self.assertEqual(response.status_code, 404)
        body = response.json()
        self.assertEqual(body["code"], "workflow_not_found")
        self.assertIn("not found", body["message"])


if __name__ == "__main__":
    unittest.main()