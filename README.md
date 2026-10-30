# SocialPilot AI

A full‑stack, AI‑powered Instagram automation platform.

## Overview
- **Frontend**: Next.js (App Router) with TypeScript, Tailwind CSS, shadcn/ui.
- **Backend**: FastAPI (Python 3.12) with SQLAlchemy, Alembic, Celery, Redis.
- **Database**: PostgreSQL.
- **Message Queue**: Redis + Celery.
- **Storage**: S3‑compatible (MinIO for dev).
- **AI**: OpenAI‑compatible provider abstraction.

## Quick Start (Development)
```bash
# Clone repository (already present)
cd socialpilot-ai
docker compose up --build
```

The API will be available at `http://localhost:8000`, and the UI at `http://localhost:3000`.

## Docs
See the `docs/` folder for architecture, setup, and deployment guides.
