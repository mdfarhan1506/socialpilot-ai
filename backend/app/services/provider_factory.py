from .mock_ai_provider import MockAIProvider
from ..settings import settings


def get_ai_provider():
    """Return an AIProvider instance.

    Routing rules (in order):
    1. USE_MOCK=True  → MockAIProvider (explicit test/dev mode).
    2. OPENAI_API_KEY set → OpenAIProvider (real API; caller handles RuntimeError).
    3. OPENAI_API_KEY missing and USE_MOCK=False → raise RuntimeError with code
       "ai_not_configured" so callers surface HTTP 503 instead of silently
       returning mock content.
    """
    if settings.USE_MOCK:
        return MockAIProvider()
    if not settings.OPENAI_API_KEY:
        raise RuntimeError(
            "ai_not_configured: OPENAI_API_KEY is not set. "
            "Add the key to your environment to enable AI content generation."
        )
    from .openai_provider import OpenAIProvider
    return OpenAIProvider()
