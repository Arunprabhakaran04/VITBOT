# Backend Dockerfile (no Redis/Celery). Env baked at build-time via ARG -> ENV.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps required by scientific libs (faiss, torch wheels) and psycopg2-binary
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libstdc++6 \
    libgomp1 \
    curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for better caching
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

# Copy only backend source
COPY backend /app/backend

# No runtime secrets baked into the image. Provide all configuration at runtime
# via docker run -e ... or docker-compose environment/env_file.

# Expose FastAPI port
EXPOSE 8000

# Default command: read HOST/PORT/WORKERS from env at runtime
# Using shell form to allow ${VAR:-default} expansion without baking values
CMD ["sh", "-lc", "uvicorn backend.main:app --host ${HOST:-0.0.0.0} --port ${PORT:-8000} --workers ${WORKERS:-1}"]
