"""Tests for content generation endpoint."""
import unittest
from backend.tests.conftest import client, get_auth_headers


class TestContentGeneration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.headers = get_auth_headers("content_user@test.com")

    def test_generate_returns_ideas(self):
        resp = client.post(
            "/content/generate",
            json={"niche": "Fitness", "target_audience": "Athletes", "tone": "Motivational"},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertIn("ideas", data)
        self.assertIsInstance(data["ideas"], list)
        self.assertGreater(len(data["ideas"]), 0)

    def test_mock_mode_flag_present(self):
        resp = client.post(
            "/content/generate",
            json={"niche": "Food", "target_audience": "Foodies"},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # In test environment USE_MOCK=true so source should be "mock"
        self.assertEqual(data["source"], "mock")
        self.assertTrue(data["mock_mode"])

    def test_mock_ideas_are_labeled(self):
        resp = client.post(
            "/content/generate",
            json={"niche": "Travel", "target_audience": "Backpackers"},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200)
        ideas = resp.json()["ideas"]
        # Each idea caption should contain [MOCK] when in mock mode
        for idea in ideas:
            self.assertIn("[MOCK]", idea.get("caption", ""), f"Idea not labeled as mock: {idea}")

    def test_content_requires_auth(self):
        resp = client.post(
            "/content/generate",
            json={"niche": "Tech", "target_audience": "Devs"},
        )
        self.assertEqual(resp.status_code, 401)

    def test_missing_required_field(self):
        resp = client.post(
            "/content/generate",
            json={"niche": "Tech"},  # missing target_audience
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 422)


if __name__ == "__main__":
    unittest.main()
