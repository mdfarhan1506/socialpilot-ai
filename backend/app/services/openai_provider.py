"""OpenAI AI provider using the official openai Python SDK.

Reads OPENAI_API_KEY and OPENAI_MODEL from settings.
Raises RuntimeError (callers translate to HTTP 502) on API errors.
"""
from __future__ import annotations

from typing import Any, Dict

from .ai_provider import AIProvider
from ..settings import settings


class OpenAIProvider(AIProvider):
    """Concrete AI provider using OpenAI chat completions."""

    def __init__(self) -> None:
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        import openai  # lazy import – mock path never requires the package
        self._client = openai.AsyncOpenAI(api_key=api_key, timeout=20.0)
        self.model = settings.OPENAI_MODEL or "gpt-4o-mini"

    async def generate(self, prompt: str, **kwargs: Any) -> Dict:  # type: ignore[override]
        import openai
        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
        except openai.AuthenticationError as exc:
            raise RuntimeError(f"OpenAI authentication failed: {exc}") from exc
        except openai.RateLimitError as exc:
            raise RuntimeError(f"OpenAI rate limit exceeded: {exc}") from exc
        except openai.APIConnectionError as exc:
            raise RuntimeError(f"OpenAI connection error: {exc}") from exc
        except openai.OpenAIError as exc:
            raise RuntimeError(f"OpenAI API error: {exc}") from exc

        content: str = response.choices[0].message.content or ""

        import json
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return {"ideas": parsed, "source": "openai"}
            if isinstance(parsed, dict) and "ideas" in parsed:
                parsed["source"] = "openai"
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

        return {
            "ideas": [{"title": "Generated content", "caption": content}],
            "source": "openai",
        }
