import random
from typing import List, Dict
from .ai_provider import AIProvider


class MockAIProvider(AIProvider):
    """Generate deterministic yet varied mock content.

    All returned strings are prefixed with ``[MOCK]`` so it is clear they are not
    produced by a real AI model.
    """

    def _random_phrase(self, niche: str) -> str:
        adjectives = ["Amazing", "Creative", "Innovative", "Fun", "Exciting"]
        verbs = ["Explore", "Discover", "Learn", "Enjoy", "Master"]
        return f"{random.choice(adjectives)} {niche} {random.choice(verbs)}"

    async def generate(self, prompt: str, **kwargs) -> Dict:  # type: ignore[override]
        # Expected kwargs: niche, audience, platform, tone, goal
        niche = kwargs.get("niche", "topic")
        audience = kwargs.get("audience", "people")
        platform = kwargs.get("platform", "instagram")
        tone = kwargs.get("tone", "friendly")
        goal = kwargs.get("goal", "engage")

        ideas: List[Dict[str, str]] = []
        for i in range(3):
            title = f"[MOCK] {self._random_phrase(niche)} #{i+1}"
            # caption must NOT re-wrap title (which already has [MOCK]); doing so
            # creates the double "[MOCK] [MOCK]" that was visible in the dashboard.
            caption = (
                f"[MOCK] A {tone} post for {audience} on {platform} "
                f"to {goal}. ({niche} – idea {i+1})"
            )
            ideas.append({"title": title, "caption": caption})
        return {"ideas": ideas, "source": "mock"}
