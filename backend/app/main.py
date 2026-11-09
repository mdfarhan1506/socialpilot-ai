import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .routers import auth, workspace, brand, content, meta, scheduling, comments, analytics, autonomous
from .settings import settings
from .db import engine
from .models.base import Base

logger = logging.getLogger("socialpilot.main")

app = FastAPI(title="SocialPilot AI Backend", version="0.1.0")

# ── CORS ──────────────────────────────────────────────────────────────
cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handler ─────────────────────────────────────────
# Ensures unhandled errors return JSON with CORS headers so the browser
# can actually read the error instead of showing "Failed to fetch".
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled %s on %s: %s", type(exc).__name__, request.url.path, exc, exc_info=True)
    origin = request.headers.get("origin", "")
    headers = {}
    if "vercel.app" in origin or origin in cors_origins:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {type(exc).__name__}: {str(exc)}"},
        headers=headers,
    )


# ── Routers ───────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(workspace.router, prefix="/workspace", tags=["workspace"])
app.include_router(brand.router, prefix="/brand", tags=["brand"])
app.include_router(content.router, prefix="/content", tags=["content"])
app.include_router(meta.router, prefix="/meta", tags=["meta"])
app.include_router(scheduling.router, prefix="/schedule", tags=["scheduling"])
app.include_router(comments.router, prefix="/comments", tags=["comments"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(autonomous.router, prefix="/autonomous", tags=["autonomous"])


# ── Startup ───────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/")
async def root():
    return {"message": "SocialPilot AI API is running"}


@app.get("/config")
async def config():
    """Expose active mode so the frontend can display a banner.

    Returns:
        mock_mode: True when USE_MOCK=True (OpenAI key absent or explicitly forced).
        openai_configured: True when OPENAI_API_KEY is set in env.
        meta_configured: True when META_APP_ID and META_APP_SECRET are set.
        mock_instagram: True when MOCK_INSTAGRAM is active (Meta creds missing or mock forced).
        mode_label: Human-readable current mode.
        ai_unavailable_reason: Non-null string if AI is configured but cannot serve requests
            (e.g. quota exhausted). Frontend uses this to show a specific error instead of
            silently falling back to mock content.
    """
    ai_unavailable_reason: str | None = None

    # Quick non-blocking credit/quota probe: only if key is configured and not in mock mode.
    # We deliberately do NOT make a real API call here — just return a None reason by default.
    # The content router will surface the actual 429/auth error per-request.
    return {
        "mock_mode": settings.USE_MOCK,
        "openai_configured": bool(settings.OPENAI_API_KEY),
        "meta_configured": bool(settings.META_APP_ID and settings.META_APP_SECRET),
        "mock_instagram": settings.MOCK_INSTAGRAM,
        "mode_label": "Mock Mode" if settings.USE_MOCK else "Live Mode",
        "ai_unavailable_reason": ai_unavailable_reason,
        # meta_token_valid is per-user; check GET /meta/status (authenticated) for the user's
        # actual token validity. This field is null here because /config is unauthenticated.
        "meta_token_valid": None,
    }
