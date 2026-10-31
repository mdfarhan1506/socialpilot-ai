from fastapi import FastAPI
from .routers import auth, workspace, brand, content, meta, scheduling, comments, analytics, autonomous
from .settings import settings
from .db import engine
from .models.base import Base

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SocialPilot AI Backend", version="0.1.0")

# Allow configured origins and all Vercel preview/production deployments
cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(workspace.router, prefix="/workspace", tags=["workspace"])
app.include_router(brand.router, prefix="/brand", tags=["brand"])
app.include_router(content.router, prefix="/content", tags=["content"])
app.include_router(meta.router, prefix="/meta", tags=["meta"])
app.include_router(scheduling.router, prefix="/schedule", tags=["scheduling"])
app.include_router(comments.router, prefix="/comments", tags=["comments"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(autonomous.router, prefix="/autonomous", tags=["autonomous"])


@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/")
async def root():
    return {"message": "SocialPilot AI API is running"}


@app.get("/config")
async def config():
    """Expose active mode so the frontend can display a banner."""
    return {
        "mock_mode": settings.USE_MOCK,
        "openai_configured": bool(settings.OPENAI_API_KEY),
        "meta_configured": bool(settings.META_APP_ID and settings.META_APP_SECRET),
        "mode_label": "Mock Mode" if settings.USE_MOCK else "Live Mode",
    }
