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
    source: str           # "openai" | "mock"
    mock_mode: bool
    ai_error: Optional[str] = None   # Non-null when real AI failed; explains why mock was used


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
    """Generate content ideas.

    Uses real OpenAI when USE_MOCK=false and OPENAI_API_KEY is set.
    If the real provider fails (quota exhausted, auth error, network error) the
    response includes ai_error explaining what failed so the frontend can show a
    clear message rather than silently presenting mock content as real AI output.
    """
    prompt = (
        f"Generate 3 distinct Instagram post ideas for a {req.niche} brand targeting "
        f"{req.target_audience}. Tone: {req.tone}. Goal: {req.goal}. "
        f"Make each idea genuinely different in angle, format, and hook. "
        f"Return a JSON object with key 'ideas', each idea having 'title' and 'caption'."
    )
    if req.extra_context:
        prompt += f" Additional context: {req.extra_context}"

    ai_error: Optional[str] = None

    try:
        provider = get_ai_provider()
        result = await provider.generate(
            prompt,
            niche=req.niche,
            audience=req.target_audience,
            tone=req.tone,
            platform=req.platform,
            goal=req.goal,
        )
    except RuntimeError as exc:
        err_msg = str(exc)
        # ai_not_configured: missing OPENAI_API_KEY outside of mock mode
        if "ai_not_configured" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "ai_not_configured",
                    "message": "OPENAI_API_KEY is not configured on this server. Add the key to the environment to enable AI generation.",
                },
            )
        # Distinguish between quota/billing errors and other failures
        if "rate limit" in err_msg.lower() or "429" in err_msg or "quota" in err_msg.lower() or "credits" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "code": "ai_quota_exceeded",
                    "message": f"OpenAI quota exhausted. Add credits at platform.openai.com to enable real AI generation.",
                },
            )
        if "authentication" in err_msg.lower() or "api key" in err_msg.lower() or "401" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "ai_auth_failed",
                    "message": f"OpenAI authentication failed. Verify OPENAI_API_KEY in environment.",
                },
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "ai_upstream_error", "message": err_msg},
        )

    return ContentGenerateResponse(
        ideas=result.get("ideas", []),
        source=result.get("source", "unknown"),
        mock_mode=settings.USE_MOCK,
        ai_error=ai_error,
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
