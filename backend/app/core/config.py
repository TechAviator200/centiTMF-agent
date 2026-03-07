import re
import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("centitmf.config")

# Local Docker defaults — only used when env vars are not set
_LOCAL_ASYNC_URL = "postgresql+asyncpg://centitmf:centitmf@postgres:5432/centitmf"
_LOCAL_SYNC_URL = "postgresql://centitmf:centitmf@postgres:5432/centitmf"


def _normalize_async_url(url: str) -> str:
    """
    Normalize a Postgres URL for use with SQLAlchemy's async engine (asyncpg).

    Handles common variants:
      postgres://...         -> postgresql+asyncpg://...
      postgresql://...       -> postgresql+asyncpg://...
      postgresql+asyncpg://  -> unchanged
    """
    url = url.strip()
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url


def _normalize_sync_url(url: str) -> str:
    """
    Normalize a Postgres URL for use with SQLAlchemy's sync engine (psycopg2).

    Handles common variants:
      postgres://...           -> postgresql://...
      postgresql+asyncpg://... -> postgresql://...
      postgresql://...         -> unchanged
    """
    url = url.strip()
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql+asyncpg://"):
        return "postgresql://" + url[len("postgresql+asyncpg://"):]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Database ──────────────────────────────────────────────────────────────
    # Async URL used by the FastAPI application.
    # In production (Supabase), set DATABASE_URL to the full connection string.
    # SQLAlchemy requires postgresql+asyncpg:// scheme; postgres:// and
    # postgresql:// are automatically normalised at runtime.
    DATABASE_URL: str = _LOCAL_ASYNC_URL

    # Sync URL used by the seed script.
    # If not set, it is derived from DATABASE_URL by stripping the asyncpg driver.
    SYNC_DATABASE_URL: str = ""

    # ── Object storage (S3-compatible) ────────────────────────────────────────
    # Local: MinIO via Docker.  Production: Cloudflare R2 (or any S3-compatible).
    S3_ENDPOINT_URL: str = "http://minio:9000"
    S3_ACCESS_KEY: str = "centitmf"
    S3_SECRET_KEY: str = "centitmf123"
    S3_BUCKET: str = "centitmf-docs"
    # AWS_REGION: use "auto" for Cloudflare R2, or a real AWS region for AWS S3.
    AWS_REGION: str = "auto"

    # ── AI (optional) ─────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""

    # ── Runtime ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def has_openai(self) -> bool:
        return bool(self.OPENAI_API_KEY and self.OPENAI_API_KEY.startswith("sk-"))

    @property
    def async_database_url(self) -> str:
        """DATABASE_URL normalized for SQLAlchemy async engine."""
        return _normalize_async_url(self.DATABASE_URL)

    @property
    def sync_database_url(self) -> str:
        """SYNC_DATABASE_URL (or DATABASE_URL) normalized for SQLAlchemy sync engine."""
        raw = self.SYNC_DATABASE_URL.strip() or self.DATABASE_URL.strip()
        return _normalize_sync_url(raw)


settings = Settings()
