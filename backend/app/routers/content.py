"""Content generation router.

POST /content/generate  – generate post ideas via AI (real or mock).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from .. import models, deps
from ..services.provider_factory import get_ai_provider
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
