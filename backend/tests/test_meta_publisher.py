"""Unit tests for meta_publisher.publish_image safety checks.

These tests run synchronously (no pytest-asyncio needed) by using asyncio.run().
They monkeypatch the `settings` object inside the meta_publisher module directly
so the guard checks see the patched values.
"""
import asyncio
import pytest
from backend.app.services import meta_publisher


def test_publish_image_mock_mode(monkeypatch):
    """Mock mode must return mock=True and a message without '[MOCK]'."""
    monkeypatch.setattr(meta_publisher.settings, "USE_MOCK", True)

    result = asyncio.run(meta_publisher.publish_image(
        ig_user_id="dummy",
        access_token="dummy",
        image_url="https://example.com/image.jpg",
        caption="any caption",
    ))

    assert result["mock"] is True, "Response must be labeled mock=True in mock mode"
    assert "[MOCK]" not in result["message"], (
        "Mock message must NOT contain the literal '[MOCK]' marker"
    )
    assert result["creation_id"] == "MOCK_CREATION_ID"
    assert result["status"] == "published"


def test_publish_image_missing_credentials(monkeypatch):
    """Real mode without Meta credentials must raise RuntimeError immediately."""
    monkeypatch.setattr(meta_publisher.settings, "USE_MOCK", False)
    monkeypatch.setattr(meta_publisher.settings, "META_APP_ID", "")
    monkeypatch.setattr(meta_publisher.settings, "META_APP_SECRET", "")

    with pytest.raises(RuntimeError) as exc:
        asyncio.run(meta_publisher.publish_image(
            ig_user_id="dummy",
            access_token="dummy",
            image_url="https://example.com/image.jpg",
            caption="valid caption",
        ))

    assert "Meta publishing is unavailable" in str(exc.value)


def test_publish_image_caption_contains_mock(monkeypatch):
    """Real mode must refuse to publish captions that contain '[MOCK]'."""
    monkeypatch.setattr(meta_publisher.settings, "USE_MOCK", False)
    monkeypatch.setattr(meta_publisher.settings, "META_APP_ID", "test_id")
    monkeypatch.setattr(meta_publisher.settings, "META_APP_SECRET", "test_secret")

    with pytest.raises(RuntimeError) as exc:
        asyncio.run(meta_publisher.publish_image(
            ig_user_id="dummy",
            access_token="dummy",
            image_url="https://example.com/image.jpg",
            caption="[MOCK] should not be published",
        ))

    assert "Caption contains mock placeholder" in str(exc.value)
