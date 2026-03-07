"""
Embedding service.
Uses OpenAI text-embedding-3-small when OPENAI_API_KEY is present.
Falls back to deterministic hash-based 1536-dim embeddings.
"""
import hashlib
import math
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("centitmf.embeddings")

EMBEDDING_DIM = 1536


def _deterministic_embedding(text: str) -> list[float]:
    """Generate a stable 1536-dim unit vector from text using SHA-256 seeding."""
    seed = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    i = 0
    while len(values) < EMBEDDING_DIM:
        chunk = hashlib.sha256(seed + i.to_bytes(4, "big")).digest()
        for b in chunk:
            values.append((b / 127.5) - 1.0)
        i += 1
    values = values[:EMBEDDING_DIM]
    # Normalize to unit vector
    magnitude = math.sqrt(sum(v * v for v in values))
    if magnitude > 0:
        values = [v / magnitude for v in values]
    return values


async def embed_text(text: str) -> list[float]:
    """Return a 1536-dim embedding for the given text."""
    if settings.has_openai:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.embeddings.create(
                model="text-embedding-3-small",
                input=text[:8000],
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"OpenAI embedding failed, using deterministic fallback: {e}")

    return _deterministic_embedding(text)
