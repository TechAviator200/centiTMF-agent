from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.logging import setup_logging, logger
from app.db.models import Base
from app.db.session import async_engine
from app.api.routers import studies, documents, compute, simulate, audit


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("centiTMF backend starting up...")

    from app.core.config import settings
    import os
    port = os.environ.get("PORT", "8000")
    logger.info("Binding on port %s", port)
    logger.info(
        "DB driver: %s",
        settings.async_database_url.split("://")[0] if "://" in settings.async_database_url else "unknown",
    )
    logger.info("S3 endpoint: %s | bucket: %s", settings.S3_ENDPOINT_URL or "AWS default", settings.S3_BUCKET)
    logger.info("OpenAI: %s", "configured" if settings.has_openai else "not configured (using deterministic fallback)")

    # Create all tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready.")

    yield

    logger.info("centiTMF backend shutting down.")
    await async_engine.dispose()


app = FastAPI(
    title="centiTMF API",
    description="Inspection Readiness AI Agent for Clinical Trial Master Files",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(studies.router)
app.include_router(documents.router)
app.include_router(compute.router)
app.include_router(simulate.router)
app.include_router(audit.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "centiTMF", "version": "1.0.0"}


@app.get("/")
async def root():
    return {
        "service": "centiTMF",
        "description": "Inspection Readiness AI Agent for Clinical Trial Master Files",
        "docs": "/docs",
        "health": "/health",
    }
