import unittest
import unittest.mock
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

            self.assertEqual(version, 6)

            with sqlite3.connect(db_path) as conn:
                rows = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                tables = {name for (name,) in rows}

            self.assertTrue(
                {
                    "workflows",
                    "workflow_revisions",
                    "workflow_status",
                    "channel_configs",
                    "workflow_channels",
                    "workflow_source_configs",
                    "workflow_ai_configs",
                    "workflow_voice_criteria",
                }.issubset(tables)
            )

    def test_init_db_records_initial_migration(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "auripostao.db"
            init_db(str(db_path))

            with sqlite3.connect(db_path) as conn:
                version = conn.execute(
                    "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
                ).fetchone()[0]

            self.assertEqual(version, 6)

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
        self.client.put("/channels/dummy", json={"enabled": True})

    def tearDown(self) -> None:
        api_main.DB_PATH = self.original_db_path
        self.tmpdir.cleanup()

    def test_crud_workflow_lifecycle(self) -> None:
        create = self.client.post(
            "/workflows",
            json={"name": "WF demo", "description": "initial", "is_active": True, "channels": ["dummy"]},
        )
        self.assertEqual(create.status_code, 201)
        created = create.json()
        self.assertEqual(created["name"], "WF demo")
        self.assertTrue(created["is_active"])
        self.assertIn("dummy", created["channels"])
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
            json={"description": "missing name", "channels": ["dummy"]},
        )
        self.assertEqual(response.status_code, 422)
        body = response.json()
        self.assertEqual(body["code"], "validation_error")
        self.assertIn("name", body["message"])

    def test_duplicate_name_returns_structured_conflict(self) -> None:
        first = self.client.post(
            "/workflows",
            json={"name": "WF unique", "description": "first", "is_active": True, "channels": ["dummy"]},
        )
        self.assertEqual(first.status_code, 201)

        second = self.client.post(
            "/workflows",
            json={"name": "WF unique", "description": "duplicate", "is_active": True, "channels": ["dummy"]},
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

    def test_create_is_blocked_without_valid_channel(self) -> None:
        disable = self.client.put("/channels/dummy", json={"enabled": False})
        self.assertEqual(disable.status_code, 200)

        response = self.client.post(
            "/workflows",
            json={"name": "WF blocked", "description": "x", "is_active": True, "channels": ["dummy"]},
        )
        self.assertEqual(response.status_code, 403)
        body = response.json()
        self.assertEqual(body["code"], "no_valid_channel")

    def test_channels_status_and_dummy_toggle(self) -> None:
        disabled = self.client.put("/channels/dummy", json={"enabled": False})
        self.assertEqual(disabled.status_code, 200)
        self.assertFalse(disabled.json()["has_valid_channel"])

        status = self.client.get("/channels/status")
        self.assertEqual(status.status_code, 200)
        self.assertFalse(status.json()["has_valid_channel"])

        enabled = self.client.put("/channels/dummy", json={"enabled": True})
        self.assertEqual(enabled.status_code, 200)
        self.assertTrue(enabled.json()["has_valid_channel"])
        self.assertIn("dummy", enabled.json()["valid_channels"])


class ApiWorkflowChannelsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmpdir.name) / "auripostao.db")
        self.original_db_path = api_main.DB_PATH
        api_main.DB_PATH = self.db_path
        init_db(self.db_path)
        self.client = TestClient(app)
        self.client.put("/channels/dummy", json={"enabled": True})

    def tearDown(self) -> None:
        api_main.DB_PATH = self.original_db_path
        self.tmpdir.cleanup()

    def _create_workflow(self, name: str = "WF canaux") -> dict:
        resp = self.client.post(
            "/workflows",
            json={"name": name, "description": "", "is_active": True, "channels": ["dummy"]},
        )
        self.assertEqual(resp.status_code, 201)
        return resp.json()

    def test_create_workflow_returns_channels(self) -> None:
        created = self._create_workflow()
        self.assertIn("channels", created)
        self.assertEqual(created["channels"], ["dummy"])

    def test_list_includes_channels(self) -> None:
        self._create_workflow()
        resp = self.client.get("/workflows")
        self.assertEqual(resp.status_code, 200)
        item = resp.json()["items"][0]
        self.assertIn("dummy", item["channels"])

    def test_get_workflow_channels(self) -> None:
        created = self._create_workflow()
        wf_id = created["id"]
        resp = self.client.get(f"/workflows/{wf_id}/channels")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["channels"], ["dummy"])

    def test_set_workflow_channels(self) -> None:
        created = self._create_workflow()
        wf_id = created["id"]
        resp = self.client.put(f"/workflows/{wf_id}/channels", json={"channels": ["dummy"]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["channels"], ["dummy"])

    def test_get_channels_unknown_workflow_returns_404(self) -> None:
        resp = self.client.get("/workflows/99999/channels")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["code"], "workflow_not_found")

    def test_set_channels_unknown_workflow_returns_404(self) -> None:
        resp = self.client.put("/workflows/99999/channels", json={"channels": ["dummy"]})
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["code"], "workflow_not_found")

    def test_create_without_channels_returns_validation_error(self) -> None:
        resp = self.client.post(
            "/workflows",
            json={"name": "WF no canal", "description": "", "is_active": True, "channels": []},
        )
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()["code"], "validation_error")

    def test_set_channels_with_unknown_channel_returns_error(self) -> None:
        created = self._create_workflow()
        wf_id = created["id"]
        resp = self.client.put(
            f"/workflows/{wf_id}/channels", json={"channels": ["inexistant"]}
        )
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()["code"], "channel_not_found")


class ApiIngestionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmpdir.name) / "auripostao.db")
        self.original_db_path = api_main.DB_PATH
        api_main.DB_PATH = self.db_path
        init_db(self.db_path)
        self.client = TestClient(app)
        self.sources_dir = Path(self.tmpdir.name) / "sources"
        self.sources_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        api_main.DB_PATH = self.original_db_path
        self.tmpdir.cleanup()

    def test_multi_files_utf8_and_non_text_ignored(self) -> None:
        file_txt = self.sources_dir / "a.txt"
        file_md = self.sources_dir / "b.md"
        file_png = self.sources_dir / "c.png"
        file_latin1 = self.sources_dir / "latin1.txt"

        file_txt.write_text("hello utf8", encoding="utf-8")
        file_md.write_text("# titre", encoding="utf-8")
        file_png.write_bytes(b"\x89PNG")
        file_latin1.write_bytes("cafe\xe9".encode("latin-1"))

        resp = self.client.post(
            "/ingestion/preview",
            json={
                "file_paths": [
                    str(file_txt),
                    str(file_md),
                    str(file_png),
                    str(file_latin1),
                ],
                "recursive": False,
                "max_file_size_bytes": 1024,
            },
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()

        accepted_paths = {item["path"] for item in body["accepted_files"]}
        self.assertIn(str(file_txt), accepted_paths)
        self.assertIn(str(file_md), accepted_paths)
        self.assertIn(str(file_latin1), accepted_paths)
        self.assertEqual(body["summary"]["accepted"], 3)
        self.assertEqual(body["summary"]["total_size_bytes"], 22)

        latin = next(item for item in body["accepted_files"] if item["path"] == str(file_latin1))
        self.assertEqual(latin["encoding"], "latin-1")

        ignored = {(item["path"], item["reason"]) for item in body["ignored_files"]}
        self.assertIn((str(file_png), "non_text_extension"), ignored)

    def test_directory_recursive_and_size_limit(self) -> None:
        nested = self.sources_dir / "nested"
        nested.mkdir(parents=True, exist_ok=True)
        root_file = self.sources_dir / "root.txt"
        deep_file = nested / "deep.txt"
        too_large = self.sources_dir / "large.txt"

        root_file.write_text("root", encoding="utf-8")
        deep_file.write_text("deep", encoding="utf-8")
        too_large.write_text("x" * 64, encoding="utf-8")

        non_recursive = self.client.post(
            "/ingestion/preview",
            json={
                "directory_path": str(self.sources_dir),
                "recursive": False,
                "max_file_size_bytes": 8,
            },
        )
        self.assertEqual(non_recursive.status_code, 200)
        body_non_recursive = non_recursive.json()
        accepted_non_recursive = {item["path"] for item in body_non_recursive["accepted_files"]}
        self.assertIn(str(root_file), accepted_non_recursive)
        self.assertNotIn(str(deep_file), accepted_non_recursive)
        ignored_non_recursive = {
            (item["path"], item["reason"]) for item in body_non_recursive["ignored_files"]
        }
        self.assertIn((str(too_large), "file_too_large"), ignored_non_recursive)

        recursive = self.client.post(
            "/ingestion/preview",
            json={
                "directory_path": str(self.sources_dir),
                "recursive": True,
                "max_file_size_bytes": 1024,
            },
        )
        self.assertEqual(recursive.status_code, 200)
        body_recursive = recursive.json()
        accepted_recursive = {item["path"] for item in body_recursive["accepted_files"]}
        self.assertIn(str(root_file), accepted_recursive)
        self.assertIn(str(deep_file), accepted_recursive)
        self.assertEqual(body_recursive["summary"]["total_size_bytes"], 72)


class ApiWorkflowSourcesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmpdir.name) / "auripostao.db")
        self.original_db_path = api_main.DB_PATH
        api_main.DB_PATH = self.db_path
        init_db(self.db_path)
        self.client = TestClient(app)
        self.client.put("/channels/dummy", json={"enabled": True})
        created = self.client.post(
            "/workflows",
            json={"name": "WF sources", "description": "", "is_active": True, "channels": ["dummy"]},
        )
        self.assertEqual(created.status_code, 201)
        self.workflow_id = created.json()["id"]

        self.sources_dir = Path(self.tmpdir.name) / "sources"
        self.sources_dir.mkdir(parents=True, exist_ok=True)
        self.f1 = self.sources_dir / "a.txt"
        self.f2 = self.sources_dir / "b.md"
        self.f1.write_text("aaa", encoding="utf-8")
        self.f2.write_text("bbb", encoding="utf-8")

    def tearDown(self) -> None:
        api_main.DB_PATH = self.original_db_path
        self.tmpdir.cleanup()

    def test_get_sources_default_config(self) -> None:
        resp = self.client.get(f"/workflows/{self.workflow_id}/sources")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["file_paths"], [])
        self.assertIsNone(body["directory_path"])
        self.assertFalse(body["recursive"])
        self.assertEqual(body["max_file_size_bytes"], 1_000_000)

    def test_set_and_get_sources_for_workflow(self) -> None:
        put = self.client.put(
            f"/workflows/{self.workflow_id}/sources",
            json={
                "file_paths": [str(self.f1), str(self.f2), str(self.f1)],
                "directory_path": str(self.sources_dir),
                "recursive": True,
                "max_file_size_bytes": 2048,
            },
        )
        self.assertEqual(put.status_code, 200)
        body_put = put.json()
        self.assertEqual(len(body_put["file_paths"]), 2)
        self.assertEqual(body_put["directory_path"], str(self.sources_dir))
        self.assertTrue(body_put["recursive"])
        self.assertEqual(body_put["max_file_size_bytes"], 2048)

        get = self.client.get(f"/workflows/{self.workflow_id}/sources")
        self.assertEqual(get.status_code, 200)
        body_get = get.json()
        self.assertEqual(set(body_get["file_paths"]), {str(self.f1), str(self.f2)})

    def test_preview_uses_persisted_workflow_sources(self) -> None:
        self.client.put(
            f"/workflows/{self.workflow_id}/sources",
            json={
                "file_paths": [str(self.f1)],
                "directory_path": None,
                "recursive": False,
                "max_file_size_bytes": 1024,
            },
        )
        resp = self.client.post(f"/workflows/{self.workflow_id}/ingestion/preview")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["summary"]["accepted"], 1)
        self.assertEqual(body["accepted_files"][0]["path"], str(self.f1))

    def test_sources_deleted_with_workflow(self) -> None:
        self.client.put(
            f"/workflows/{self.workflow_id}/sources",
            json={
                "file_paths": [str(self.f1)],
                "directory_path": str(self.sources_dir),
                "recursive": True,
                "max_file_size_bytes": 1024,
            },
        )
        deleted = self.client.delete(f"/workflows/{self.workflow_id}")
        self.assertEqual(deleted.status_code, 200)

        get = self.client.get(f"/workflows/{self.workflow_id}/sources")
        self.assertEqual(get.status_code, 404)
        self.assertEqual(get.json()["code"], "workflow_not_found")


class ApiAIConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmpdir.name) / "auripostao.db")
        self.original_db_path = api_main.DB_PATH
        api_main.DB_PATH = self.db_path
        init_db(self.db_path)
        self.client = TestClient(app)
        self.client.put("/channels/dummy", json={"enabled": True})
        created = self.client.post(
            "/workflows",
            json={"name": "WF ai", "description": "", "is_active": True, "channels": ["dummy"]},
        )
        self.assertEqual(created.status_code, 201)
        self.workflow_id = created.json()["id"]

    def tearDown(self) -> None:
        api_main.DB_PATH = self.original_db_path
        self.tmpdir.cleanup()

    def test_ai_config_default_values(self) -> None:
        resp = self.client.get(f"/workflows/{self.workflow_id}/ai-config")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["provider"], "ollama")
        self.assertEqual(body["model"], "llama3.2")
        self.assertEqual(body["base_url"], "http://localhost:11434")
        self.assertEqual(body["timeout_seconds"], 30)

    def test_set_and_get_ai_config(self) -> None:
        put = self.client.put(
            f"/workflows/{self.workflow_id}/ai-config",
            json={"provider": "openai_compat", "base_url": "http://localhost:8080", "model": "mistral", "timeout_seconds": 60},
        )
        self.assertEqual(put.status_code, 200)
        body = put.json()
        self.assertEqual(body["provider"], "openai_compat")
        self.assertEqual(body["model"], "mistral")
        self.assertEqual(body["timeout_seconds"], 60)

        get = self.client.get(f"/workflows/{self.workflow_id}/ai-config")
        self.assertEqual(get.status_code, 200)
        self.assertEqual(get.json()["model"], "mistral")

    def test_ai_config_unknown_workflow_returns_404(self) -> None:
        resp = self.client.get("/workflows/99999/ai-config")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["code"], "workflow_not_found")

    def test_ai_config_invalid_provider_returns_422(self) -> None:
        resp = self.client.put(
            f"/workflows/{self.workflow_id}/ai-config",
            json={"provider": "unknown_provider", "base_url": "http://x", "model": "x", "timeout_seconds": 30},
        )
        self.assertEqual(resp.status_code, 422)


class ApiVoiceCriteriaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmpdir.name) / "auripostao.db")
        self.original_db_path = api_main.DB_PATH
        api_main.DB_PATH = self.db_path
        init_db(self.db_path)
        self.client = TestClient(app)
        self.client.put("/channels/dummy", json={"enabled": True})
        created = self.client.post(
            "/workflows",
            json={"name": "WF voice", "description": "", "is_active": True, "channels": ["dummy"]},
        )
        self.assertEqual(created.status_code, 201)
        self.workflow_id = created.json()["id"]

    def tearDown(self) -> None:
        api_main.DB_PATH = self.original_db_path
        self.tmpdir.cleanup()

    def test_voice_criteria_default_values(self) -> None:
        resp = self.client.get(f"/workflows/{self.workflow_id}/voice-criteria")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["preset"], "professional_concise")
        self.assertEqual(body["custom_instructions"], "")
        self.assertEqual(body["min_length"], 100)
        self.assertEqual(body["max_length"], 500)

    def test_set_all_standard_presets(self) -> None:
        for preset in ["professional_concise", "professional_detailed", "casual", "storytelling", "technical"]:
            resp = self.client.put(
                f"/workflows/{self.workflow_id}/voice-criteria",
                json={"preset": preset, "custom_instructions": "", "min_length": 50, "max_length": 300},
            )
            self.assertEqual(resp.status_code, 200, f"preset '{preset}' failed")
            self.assertEqual(resp.json()["preset"], preset)

    def test_custom_preset_stores_instructions(self) -> None:
        resp = self.client.put(
            f"/workflows/{self.workflow_id}/voice-criteria",
            json={"preset": "custom", "custom_instructions": "Write like Hemingway.", "min_length": 50, "max_length": 200},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["preset"], "custom")
        self.assertEqual(resp.json()["custom_instructions"], "Write like Hemingway.")

        get = self.client.get(f"/workflows/{self.workflow_id}/voice-criteria")
        self.assertEqual(get.json()["custom_instructions"], "Write like Hemingway.")

    def test_invalid_preset_returns_422(self) -> None:
        resp = self.client.put(
            f"/workflows/{self.workflow_id}/voice-criteria",
            json={"preset": "unknown_style", "custom_instructions": "", "min_length": 50, "max_length": 200},
        )
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()["code"], "invalid_preset")

    def test_min_max_length_constraint(self) -> None:
        resp = self.client.put(
            f"/workflows/{self.workflow_id}/voice-criteria",
            json={"preset": "casual", "custom_instructions": "", "min_length": 300, "max_length": 100},
        )
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()["code"], "invalid_length")

    def test_voice_criteria_unknown_workflow_returns_404(self) -> None:
        resp = self.client.get("/workflows/99999/voice-criteria")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["code"], "workflow_not_found")


class ApiGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmpdir.name) / "auripostao.db")
        self.original_db_path = api_main.DB_PATH
        api_main.DB_PATH = self.db_path
        init_db(self.db_path)
        self.client = TestClient(app)
        self.client.put("/channels/dummy", json={"enabled": True})
        created = self.client.post(
            "/workflows",
            json={"name": "WF gen", "description": "", "is_active": True, "channels": ["dummy"]},
        )
        self.assertEqual(created.status_code, 201)
        self.workflow_id = created.json()["id"]
        sources_dir = Path(self.tmpdir.name) / "sources"
        sources_dir.mkdir()
        f = sources_dir / "content.txt"
        f.write_text("This is the source content for testing.", encoding="utf-8")
        self.client.put(
            f"/workflows/{self.workflow_id}/sources",
            json={"file_paths": [str(f)], "directory_path": None, "recursive": False, "max_file_size_bytes": 1024},
        )

    def tearDown(self) -> None:
        api_main.DB_PATH = self.original_db_path
        self.tmpdir.cleanup()

    @unittest.mock.patch("core.api.main._call_ai_provider")
    def test_generate_success(self, mock_call: unittest.mock.MagicMock) -> None:
        mock_call.return_value = ('{"journal": "Private entry.", "post": "Public post."}', None, None)
        resp = self.client.post(f"/workflows/{self.workflow_id}/generate")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["journal"], "Private entry.")
        self.assertEqual(body["post"], "Public post.")
        self.assertIsNone(body["error_type"])
        self.assertEqual(body["provider"], "ollama")
        mock_call.assert_called_once()

    @unittest.mock.patch("core.api.main._call_ai_provider")
    def test_generate_transient_error_returned_in_body(self, mock_call: unittest.mock.MagicMock) -> None:
        mock_call.return_value = (None, "transient", "Connection refused")
        resp = self.client.post(f"/workflows/{self.workflow_id}/generate")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIsNone(body["journal"])
        self.assertIsNone(body["post"])
        self.assertEqual(body["error_type"], "transient")
        self.assertEqual(body["error_message"], "Connection refused")

    @unittest.mock.patch("core.api.main._call_ai_provider")
    def test_generate_permanent_error_returned_in_body(self, mock_call: unittest.mock.MagicMock) -> None:
        mock_call.return_value = (None, "permanent", "Authentication failed (HTTP 401)")
        resp = self.client.post(f"/workflows/{self.workflow_id}/generate")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["error_type"], "permanent")

    @unittest.mock.patch("core.api.main._call_ai_provider")
    def test_generate_uses_persisted_ai_config(self, mock_call: unittest.mock.MagicMock) -> None:
        mock_call.return_value = ('{"journal": "j", "post": "p"}', None, None)
        self.client.put(
            f"/workflows/{self.workflow_id}/ai-config",
            json={"provider": "openai_compat", "base_url": "http://localhost:8080", "model": "mistral", "timeout_seconds": 45},
        )
        resp = self.client.post(f"/workflows/{self.workflow_id}/generate")
        self.assertEqual(resp.status_code, 200)
        _, kwargs = mock_call.call_args
        self.assertEqual(kwargs["provider"], "openai_compat")
        self.assertEqual(kwargs["model"], "mistral")
        self.assertEqual(kwargs["timeout"], 45)

    @unittest.mock.patch("core.api.main._call_ai_provider")
    def test_generate_unknown_workflow_returns_404(self, mock_call: unittest.mock.MagicMock) -> None:
        resp = self.client.post("/workflows/99999/generate")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["code"], "workflow_not_found")
        mock_call.assert_not_called()

    @unittest.mock.patch("core.api.main._call_ai_provider")
    def test_generate_uses_persisted_voice_criteria_in_prompt(self, mock_call: unittest.mock.MagicMock) -> None:
        mock_call.return_value = ('{"journal": "j", "post": "p"}', None, None)
        self.client.put(
            f"/workflows/{self.workflow_id}/voice-criteria",
            json={"preset": "custom", "custom_instructions": "UNIQUE_MARKER_XYZ", "min_length": 50, "max_length": 200},
        )
        self.client.post(f"/workflows/{self.workflow_id}/generate")
        _, kwargs = mock_call.call_args
        self.assertIn("UNIQUE_MARKER_XYZ", kwargs["prompt"])


if __name__ == "__main__":
    unittest.main()