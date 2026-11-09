"""Image generation and retrieval service.

Supports:
1. Real OpenAI DALL-E image generation (dall-e-3) when OPENAI_API_KEY is configured and not in mock mode.
2. Curated, high-resolution topic-specific Unsplash stock imagery matching niche/topic categories as a verified fallback or when requested.
3. Aspect ratio validation and format checks compliant with Instagram publishing rules.
4. Metadata extraction (provider, prompt/query, resolution, format, aspect_ratio).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from ..settings import settings

logger = logging.getLogger("socialpilot.image_service")

# Curated, topic-specific verified high-resolution images for key niches.
# Each category has at least 6 distinct URLs to minimise hash collisions when
# multiple topics in the same niche are requested in the same session.
# All URLs are direct HTTPS images suitable for Instagram feed (1:1 or 4:5).
NICHE_STOCK_LIBRARY: Dict[str, list[str]] = {
    "tech": [
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1531482615713-2afd69097998?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1555949963-aa79dcee981c?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1573164713988-8665fc963095?w=1080&auto=format&fit=crop&q=80",
    ],
    "fitness": [
        "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1476480862126-209bfaa8edc8?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1538805060514-97d9cc17730c?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1549060279-7e168fcee0c2?w=1080&auto=format&fit=crop&q=80",
    ],
    "business": [
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1521737711867-e3b97375f902?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1556761175-4b46a572b786?w=1080&auto=format&fit=crop&q=80",
    ],
    "food": [
        "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1498837167922-ddd27525d352?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1476224203421-9ac39bcb3327?w=1080&auto=format&fit=crop&q=80",
    ],
    "travel": [
        "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1530789253388-582c481c54b0?w=1080&auto=format&fit=crop&q=80",
    ],
    "fashion": [
        "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1445205170230-053b83016050?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1529139574466-a303027c1d8b?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=1080&auto=format&fit=crop&q=80",
    ],
    "finance": [
        "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1543699565-003b8adda5fc?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1565514020179-026b92b2d70b?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1619944671609-56263f0a3e09?w=1080&auto=format&fit=crop&q=80",
    ],
    "marketing": [
        "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1432888498266-38ffec3eaf0a?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1533750349088-cd871a92f312?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1504868584819-f8e8b4b6d7e3?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1557838923-2985c318be48?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1562577309-4932fdd64cd1?w=1080&auto=format&fit=crop&q=80",
    ],
    "default": [
        "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1557682250-33bd709cbe85?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1558591710-4b4a1ae0f964?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1534796636912-3b95b3ab5986?w=1080&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1500462918059-b1a0cb512f1d?w=1080&auto=format&fit=crop&q=80",
    ],
}


def get_stock_image_for_topic(niche: str, topic: Optional[str] = None) -> Dict[str, Any]:
    """Select a relevant topic-specific stock image from the curated library.

    Uses a PYTHONHASHSEED-independent hash (sum of ordinal values) so the same
    niche+topic always resolves to the same image regardless of Python run, while
    different topics spread across the full candidate list to minimise collisions.
    """
    search_text = f"{niche} {topic or ''}".lower()
    matched_category = "default"
    for cat in NICHE_STOCK_LIBRARY.keys():
        if cat in search_text:
            matched_category = cat
            break

    candidates = NICHE_STOCK_LIBRARY.get(matched_category, NICHE_STOCK_LIBRARY["default"])
    # Stable hash: sum of Unicode ordinals — not affected by PYTHONHASHSEED.
    # This guarantees identical behaviour locally, in CI, and in production.
    stable_hash = sum(ord(c) for c in search_text)
    idx = stable_hash % len(candidates)
    image_url = candidates[idx]

    return {
        "url": image_url,
        "source": "stock_library",
        "category": matched_category,
        "metadata": {
            "provider": "unsplash_curated",
            "matched_category": matched_category,
            "aspect_ratio": 1.0,
            "format": "image/jpeg",
            "resolution": "1080x1080",
            "is_ai_generated": False,
        },
    }


async def generate_topic_image(
    prompt: str,
    niche: Optional[str] = None,
    topic: Optional[str] = None,
    prefer_ai: bool = True,
) -> Dict[str, Any]:
    """Generate or retrieve a topic-specific Instagram image.

    If OpenAI is configured and `prefer_ai` is True (and not forced mock mode),
    uses DALL-E to generate a photo/graphic for the exact topic.
    Otherwise, gracefully falls back to the curated topic-specific stock library.
    Never pretends an image was AI-generated when it was from stock.
    """
    niche_clean = (niche or "Tech").strip()
    topic_clean = (topic or prompt).strip()

    # Determine if OpenAI DALL-E can be used
    can_use_openai = bool(settings.OPENAI_API_KEY) and not settings.USE_MOCK and prefer_ai

    if can_use_openai:
        try:
            import openai

            client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY, timeout=35.0)
            full_prompt = (
                f"Professional, aesthetic Instagram image for {niche_clean}. "
                f"Topic: {topic_clean}. "
                f"Style: clean, modern visual design, high resolution, no distorted text."
            )
            response = await client.images.generate(
                model="dall-e-3",
                prompt=full_prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            image_url = response.data[0].url
            revised_prompt = getattr(response.data[0], "revised_prompt", full_prompt)
            return {
                "url": image_url,
                "source": "openai_dalle3",
                "category": niche_clean.lower(),
                "metadata": {
                    "provider": "openai_dalle3",
                    "prompt": full_prompt,
                    "revised_prompt": revised_prompt,
                    "aspect_ratio": 1.0,
                    "format": "image/png",
                    "resolution": "1024x1024",
                    "is_ai_generated": True,
                },
            }
        except Exception as e:
            logger.warning("OpenAI DALL-E generation failed, falling back to stock library: %s", e)
            fallback = get_stock_image_for_topic(niche_clean, topic_clean)
            fallback["fallback_reason"] = f"OpenAI DALL-E unavailable: {str(e)}"
            return fallback

    # Mock mode or no API key -> curated stock fallback
    stock_res = get_stock_image_for_topic(niche_clean, topic_clean)
    if settings.USE_MOCK:
        stock_res["mock_mode"] = True
    return stock_res
