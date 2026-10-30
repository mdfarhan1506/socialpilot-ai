from .mock_ai_provider import MockAIProvider
from ..settings import settings


def get_ai_provider():
    """Return an AIProvider instance.

    When ``settings.USE_MOCK`` is True (or OPENAI_API_KEY is absent) the
    MockAIProvider is returned.  Otherwise the real OpenAI SDK provider is
    returned.  All responses from the mock are prefixed with ``[MOCK]`` so
    it is always clear which mode is active.
    """
    if settings.USE_MOCK or not settings.OPENAI_API_KEY:
        return MockAIProvider()
    from .openai_provider import OpenAIProvider
    return OpenAIProvider()
