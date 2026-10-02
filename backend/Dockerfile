FROM python:3.11-slim

# Install git for transcript cloning and curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first (layer cache optimization)
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

# Copy source
COPY . .

# Create data directory
RUN mkdir -p /data/transcripts

# Expose port
EXPOSE 8000

# Startup: run migrations then start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --log-level info"]
