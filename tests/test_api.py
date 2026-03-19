import unittest

from fastapi.testclient import TestClient

from core.api.main import app


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


if __name__ == "__main__":
    unittest.main()