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

    def test_no_double_mock_prefix_in_captions(self):
        """Mock captions must not contain '[MOCK] [MOCK]' (double-prefix bug)."""
        resp = client.post(
            "/content/generate",
            json={"niche": "Fashion", "target_audience": "Style enthusiasts"},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200)
        for idea in resp.json()["ideas"]:
            caption = idea.get("caption", "")
            self.assertNotIn("[MOCK] [MOCK]", caption, f"Double [MOCK] prefix found: {caption}")

    def test_key_missing_returns_503_in_live_mode(self):
        """When USE_MOCK=False and OPENAI_API_KEY is absent, endpoint must return 503."""
        import backend.app.services.provider_factory as pf_module
        import backend.app.settings as settings_module

        orig_use_mock = settings_module.settings.USE_MOCK
        orig_key = settings_module.settings.OPENAI_API_KEY
        pf_module.settings.USE_MOCK = False
        settings_module.settings.USE_MOCK = False
        pf_module.settings.OPENAI_API_KEY = ""
        settings_module.settings.OPENAI_API_KEY = ""
        try:
            resp = client.post(
                "/content/generate",
                json={"niche": "Tech", "target_audience": "Devs"},
                headers=self.headers,
            )
            self.assertEqual(
                resp.status_code, 503,
                f"Expected 503 when OPENAI_API_KEY missing in live mode, got {resp.status_code}: {resp.text}"
            )
            detail = resp.json().get("detail", {})
            self.assertEqual(detail.get("code"), "ai_not_configured")
        finally:
            pf_module.settings.USE_MOCK = orig_use_mock
            settings_module.settings.USE_MOCK = orig_use_mock
            pf_module.settings.OPENAI_API_KEY = orig_key
            settings_module.settings.OPENAI_API_KEY = orig_key

    def test_no_mock_text_in_live_mode(self):
        """When USE_MOCK=False and no OPENAI_API_KEY, response must not contain mock ideas silently."""
        import backend.app.services.provider_factory as pf_module
        import backend.app.settings as settings_module

        orig_use_mock = settings_module.settings.USE_MOCK
        orig_key = settings_module.settings.OPENAI_API_KEY
        pf_module.settings.USE_MOCK = False
        settings_module.settings.USE_MOCK = False
        pf_module.settings.OPENAI_API_KEY = ""
        settings_module.settings.OPENAI_API_KEY = ""
        try:
            resp = client.post(
                "/content/generate",
                json={"niche": "Tech", "target_audience": "Devs"},
                headers=self.headers,
            )
            # Must NOT return 200 with mock content silently
            self.assertNotEqual(resp.status_code, 200,
                "In live mode without OPENAI_API_KEY, 200 must not be returned with silent mock content")
        finally:
            pf_module.settings.USE_MOCK = orig_use_mock
            settings_module.settings.USE_MOCK = orig_use_mock
            pf_module.settings.OPENAI_API_KEY = orig_key
            settings_module.settings.OPENAI_API_KEY = orig_key


if __name__ == "__main__":
    unittest.main()
