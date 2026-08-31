# ── Stage 1: dependency builder ─────────────────────────────────────────────
FROM python:3.10-slim-bookworm AS builder

WORKDIR /app

# Install build dependencies for psycopg2-binary and other native packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: runtime image ───────────────────────────────────────────────────
FROM python:3.10-slim-bookworm AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

EXPOSE 8000

# Use gunicorn with uvicorn workers for production
# Workers can be tuned via GUNICORN_WORKERS env var (default: 2)
CMD gunicorn app.main:app \
    --bind 0.0.0.0:8000 \
    --workers ${GUNICORN_WORKERS:-2} \
    --worker-class uvicorn.workers.UvicornWorker \
    --access-logfile - \
    --error-logfile - \
    --log-level info
