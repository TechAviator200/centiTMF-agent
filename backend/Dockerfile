FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        fastapi \
        "uvicorn[standard]" \
        "sqlalchemy[asyncio]" \
        asyncpg \
        psycopg2-binary \
        pgvector \
        "pydantic>=2.8.2" \
        "pydantic-settings>=2.3.4" \
        boto3 \
        pypdf \
        openai \
        python-multipart \
        alembic

# Copy application code
COPY . .

# Make scripts executable
RUN chmod +x scripts/seed.py 2>/dev/null || true

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
