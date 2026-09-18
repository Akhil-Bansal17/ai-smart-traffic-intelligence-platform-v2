# ==============================================================================
# AI Smart Traffic Intelligence Platform — Backend Container
# ==============================================================================
# Multi-stage / lightweight Python container running FastAPI with OpenCV headless.
# Non-root user execution, explicit health check, and volume mounts for persistence.
# ==============================================================================

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PYTHONPATH=/app/backend

WORKDIR /app

# Install runtime system dependencies for OpenCV, PostgreSQL, and health probing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a dedicated non-root user
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -s /bin/bash -m appuser

# Install Python dependencies first for optimal Docker layer caching
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy application source and model assets
COPY backend /app/backend
COPY data_science /app/data_science

# Create storage directories and set permissions
RUN mkdir -p /app/uploads /app/reports && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "backend"]
