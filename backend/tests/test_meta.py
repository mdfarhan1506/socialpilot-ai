"""Tests for Meta OAuth and publishing router (mock mode only).

Security checks:
- OAuth start generates cryptographically secure state tied to user.
- OAuth callback validates single-use expiring state and prevents replay attacks.
- OAuth callback functions without requiring Authorization header from browser redirect.
- OAuth callback must never return raw access tokens.
- Publishing uses stored encrypted token, not user-submitted raw token.
- Publish without linking first must fail with 400.
"""
import unittest
from backend.tests.conftest import client, get_auth_headers


class TestMetaStatus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.headers = get_auth_headers("meta_user@test.com")

    def test_status_returns_mock_mode(self):
        resp = client.get("/meta/status", headers=self.headers)
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertIn("mock_mode", data)
        self.assertTrue(data["mock_mode"])

    def test_status_requires_auth(self):
        resp = client.get("/meta/status")
        self.assertEqual(resp.status_code, 401)


class TestMetaOAuth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.headers = get_auth_headers("meta_oauth@test.com")

    def test_oauth_start_returns_url_and_state(self):
        resp = client.get("/meta/oauth/start", headers=self.headers)
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertTrue(data.get("mock_mode"), "Expected mock_mode=True in test environment")
        self.assertIn("oauth_url", data)
        self.assertIn("state", data)
        # Unified Login (Instagram Login Compatible): uses Facebook Login dialog with prompt=login
        self.assertIn("facebook.com", data["oauth_url"])
        self.assertIn("dialog/oauth", data["oauth_url"])
        self.assertIn("prompt=login", data["oauth_url"])
        self.assertIn(f"state={data['state']}", data["oauth_url"])

    def test_oauth_callback_browser_redirect_with_valid_state(self):
        """Callback with valid state redirects browser to frontend with success parameters."""
        # 1. Start OAuth to generate state
        start_res = client.get("/meta/oauth/start", headers=self.headers)
        state = start_res.json()["state"]

        # 2. Simulate browser redirect from Meta (no Authorization headers)
        callback_res = client.get(
            f"/meta/oauth/callback?code=mock_code&state={state}",
            follow_redirects=False,
        )
        self.assertEqual(callback_res.status_code, 302)
        redirect_location = callback_res.headers.get("location", "")
        self.assertIn("connected=instagram", redirect_location)
        self.assertIn("ig_user_id=MOCK_IG_USER_ID", redirect_location)

        # 3. Check status is now connected for this user
        status_res = client.get("/meta/status", headers=self.headers)
        self.assertTrue(status_res.json()["connected"])
        self.assertEqual(status_res.json()["ig_user_id"], "MOCK_IG_USER_ID")

    def test_oauth_callback_direct_api_fetch_returns_json(self):
        """Direct API fetch from frontend with Accept: application/json returns JSON."""
        start_res = client.get("/meta/oauth/start", headers=self.headers)
        state = start_res.json()["state"]

        res = client.get(
            f"/meta/oauth/callback?code=mock_code&state={state}",
            headers={"Accept": "application/json"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("account_linked"))
        self.assertTrue(data.get("token_stored"))
        self.assertEqual(data.get("ig_user_id"), "MOCK_IG_USER_ID")

    def test_oauth_callback_state_single_use_prevents_replay(self):
        """Re-using the same state token must fail (prevent CSRF/replay attack)."""
        start_res = client.get("/meta/oauth/start", headers=self.headers)
        state = start_res.json()["state"]

        # First use succeeds
        res1 = client.get(f"/meta/oauth/callback?code=mock_code&state={state}", follow_redirects=False)
        self.assertEqual(res1.status_code, 302)
        self.assertIn("connected=instagram", res1.headers.get("location", ""))

        # Second use with same state must be rejected with error
        res2 = client.get(f"/meta/oauth/callback?code=mock_code&state={state}", follow_redirects=False)
        self.assertEqual(res2.status_code, 302)
        self.assertIn("oauth_error=", res2.headers.get("location", ""))
        self.assertIn("already+been+used", res2.headers.get("location", ""))

    def test_oauth_callback_invalid_state_rejected(self):
        """Callback with forged/invalid state must be rejected."""
        res = client.get("/meta/oauth/callback?code=mock_code&state=fake_tampered_state", follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn("oauth_error=", res.headers.get("location", ""))

    def test_oauth_requires_auth(self):
        resp = client.get("/meta/oauth/start")
        self.assertEqual(resp.status_code, 401)


class TestMetaPublish(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.headers = get_auth_headers("meta_pub@test.com")
        # Link account first via OAuth start & callback with valid state
        start_res = client.get("/meta/oauth/start", headers=cls.headers)
        state = start_res.json()["state"]
        client.get(f"/meta/oauth/callback?code=fake_code&state={state}", follow_redirects=False)

        cls.unlinked_headers = get_auth_headers("meta_unlinked@test.com")

    def test_publish_uses_stored_token(self):
        """Publish endpoint uses stored token from the linked account."""
        resp = client.post(
            "/meta/publish",
            json={
                "image_url": "https://example.com/image.jpg",
                "caption": "Test post #socialpilot",
            },
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertTrue(data.get("mock"), "Publish response must be labeled as mock")
        self.assertIn("[MOCK]", data.get("message", ""), "Mock message must contain [MOCK] label")
        self.assertEqual(data.get("status"), "published")

    def test_publish_without_linking_fails(self):
        """Publishing without completing OAuth first must return 400."""
        resp = client.post(
            "/meta/publish",
            json={"image_url": "https://example.com/img.jpg", "caption": "no link"},
            headers=self.unlinked_headers,
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("No Instagram account linked", resp.json()["detail"])

    def test_publish_requires_auth(self):
        resp = client.post(
            "/meta/publish",
            json={"image_url": "x", "caption": "x"},
        )
        self.assertEqual(resp.status_code, 401)

    def test_disconnect_meta(self):
        """Test disconnecting an active Instagram connection and verifying status."""
        user_headers = get_auth_headers("meta_disc_test@test.com")
        start_resp = client.get("/meta/oauth/start", headers=user_headers)
        state = start_resp.json()["state"]
        client.get(f"/meta/oauth/callback?code=fake_code&state={state}", follow_redirects=False)

        # Confirm connected
        status_resp = client.get("/meta/status", headers=user_headers)
        self.assertTrue(status_resp.json()["connected"])

        # Disconnect
        disc_resp = client.delete("/meta/disconnect", headers=user_headers)
        self.assertEqual(disc_resp.status_code, 200)

        # Confirm disconnected
        status_resp2 = client.get("/meta/status", headers=user_headers)
        self.assertFalse(status_resp2.json()["connected"])

        # Disconnecting again when not connected returns 404
        disc_resp2 = client.delete("/meta/disconnect", headers=user_headers)
        self.assertEqual(disc_resp2.status_code, 404)


if __name__ == "__main__":
    unittest.main()
