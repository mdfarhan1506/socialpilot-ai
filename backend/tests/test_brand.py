"""Full brand CRUD tests including auth and authorization checks."""
import unittest
from backend.tests.conftest import client, get_auth_headers, create_workspace

BRAND_DATA = {
    "niche": "Tech",
    "target_audience": "Developers",
    "tone": "Professional",
    "brand_voice": "Authoritative",
    "content_preferences": "Tutorials",
}


class TestBrandCRUD(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.headers = get_auth_headers("brand_user@test.com")
        cls.other_headers = get_auth_headers("brand_other@test.com")
        cls.workspace_id = create_workspace(cls.headers, "Brand WS")
        data = {**BRAND_DATA, "workspace_id": cls.workspace_id}
        resp = client.post("/brand/", json=data, headers=cls.headers)
        assert resp.status_code == 201, resp.text
        cls.brand_id = resp.json()["id"]

    def test_create_brand_returns_201(self):
        data = {**BRAND_DATA, "workspace_id": self.workspace_id}
        resp = client.post("/brand/", json=data, headers=self.headers)
        self.assertEqual(resp.status_code, 201)

    def test_get_brand_by_id(self):
        resp = client.get(f"/brand/{self.brand_id}", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["niche"], BRAND_DATA["niche"])

    def test_list_brands(self):
        resp = client.get(f"/brand/?workspace_id={self.workspace_id}", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        ids = [b["id"] for b in resp.json()]
        self.assertIn(self.brand_id, ids)

    def test_update_brand(self):
        resp = client.put(
            f"/brand/{self.brand_id}",
            json={"niche": "Updated Tech"},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["niche"], "Updated Tech")

    def test_delete_brand(self):
        data = {**BRAND_DATA, "workspace_id": self.workspace_id}
        create_resp = client.post("/brand/", json=data, headers=self.headers)
        self.assertEqual(create_resp.status_code, 201)
        del_id = create_resp.json()["id"]
        resp = client.delete(f"/brand/{del_id}", headers=self.headers)
        self.assertEqual(resp.status_code, 204)
        # Should now be 404
        get_resp = client.get(f"/brand/{del_id}", headers=self.headers)
        self.assertEqual(get_resp.status_code, 404)

    def test_get_nonexistent_brand(self):
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = client.get(f"/brand/{fake_id}", headers=self.headers)
        self.assertEqual(resp.status_code, 404)

    def test_brand_requires_auth(self):
        resp = client.get(f"/brand/{self.brand_id}")
        self.assertEqual(resp.status_code, 401)

    def test_brand_workspace_authorization(self):
        """Non-member user cannot create brand in another user's workspace."""
        data = {**BRAND_DATA, "workspace_id": self.workspace_id}
        resp = client.post("/brand/", json=data, headers=self.other_headers)
        self.assertIn(resp.status_code, [403, 404])


if __name__ == "__main__":
    unittest.main()
