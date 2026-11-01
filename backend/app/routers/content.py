"""Content generation and image rendering router.

POST /content/generate        – generate post ideas via AI (real or mock).
POST /content/generate-image – generate or retrieve topic-specific image with metadata.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Any, Dict

from .. import models, deps
from ..services.provider_factory import get_ai_provider
from ..services.image_service import generate_topic_image
from ..settings import settings

router = APIRouter()


class ContentGenerateRequest(BaseModel):
    niche: str
    target_audience: str
    tone: Optional[str] = "friendly"
    platform: Optional[str] = "instagram"
    goal: Optional[str] = "engage"
    extra_context: Optional[str] = None


class ContentGenerateResponse(BaseModel):
    ideas: list
    source: str  # "openai" | "mock"
    mock_mode: bool


class ImageGenerateRequest(BaseModel):
    prompt: str
    niche: Optional[str] = None
    topic: Optional[str] = None
    prefer_ai: Optional[bool] = True


class ImageGenerateResponse(BaseModel):
    url: str
    source: str  # "openai_dalle3" | "stock_library"
    category: str
    metadata: Dict[str, Any]
    mock_mode: Optional[bool] = False
    fallback_reason: Optional[str] = None


@router.post("/generate", response_model=ContentGenerateResponse)
async def generate_content(
    req: ContentGenerateRequest,
    current_user: models.User = Depends(deps.get_current_user),
):
    """Generate content ideas. Uses real OpenAI when USE_MOCK=false and key is set."""
    prompt = (
        f"Generate 3 Instagram post ideas for a {req.niche} brand targeting "
        f"{req.target_audience}. Tone: {req.tone}. Goal: {req.goal}. "
        f"Return a JSON object with key 'ideas', each idea having 'title' and 'caption'."
    )
    if req.extra_context:
        prompt += f" Additional context: {req.extra_context}"

    provider = get_ai_provider()
    try:
        result = await provider.generate(
            prompt,
            niche=req.niche,
            audience=req.target_audience,
            tone=req.tone,
            platform=req.platform,
            goal=req.goal,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )

    return ContentGenerateResponse(
        ideas=result.get("ideas", []),
        source=result.get("source", "unknown"),
        mock_mode=settings.USE_MOCK,
    )


@router.post("/generate-image", response_model=ImageGenerateResponse)
async def generate_image(
    req: ImageGenerateRequest,
    current_user: models.User = Depends(deps.get_current_user),
):
    """Generate topic-specific image using OpenAI DALL-E or curated stock library."""
    if not req.prompt and not req.niche and not req.topic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of prompt, niche, or topic must be provided",
        )

    result = await generate_topic_image(
        prompt=req.prompt,
        niche=req.niche,
        topic=req.topic,
        prefer_ai=bool(req.prefer_ai),
    )
    return ImageGenerateResponse(
        url=result["url"],
        source=result["source"],
        category=result.get("category", "default"),
        metadata=result.get("metadata", {}),
        mock_mode=result.get("mock_mode", False),
        fallback_reason=result.get("fallback_reason"),
    )
