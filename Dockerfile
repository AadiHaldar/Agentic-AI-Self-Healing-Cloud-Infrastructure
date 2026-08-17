# ==============================================================================
# Multi-Stage Dockerfile for Agentic AI Self-Healing & PR Review Platform
#
# Build args:
#   SKIP_FRONTEND=true   — skip the Vite SPA build stage (for CI/CD when the
#                          frontend hasn't been built yet or is not in scope).
#                          Set to any non-empty value to skip.
#
# Example builds:
#   docker build .                                  # full build (Node + Python)
#   docker build --build-arg SKIP_FRONTEND=true .  # Python only (faster CI)
# ==============================================================================

# ── Stage 1: Frontend Build (skipped when SKIP_FRONTEND=true) ─────────────────
FROM node:20-alpine AS frontend-builder

ARG SKIP_FRONTEND=false
WORKDIR /app/frontend

# Only copy and build if the vite source exists.
# We use a shell conditional so a missing directory doesn't fail the build.
COPY dashboard/frontend-vite/package*.json ./

RUN if [ "$SKIP_FRONTEND" = "true" ]; then \
      echo "SKIP_FRONTEND=true — skipping npm install"; \
    else \
      npm ci --prefer-offline; \
    fi

COPY dashboard/frontend-vite/ ./

RUN if [ "$SKIP_FRONTEND" = "true" ]; then \
      mkdir -p /app/frontend/dist && echo '{}' > /app/frontend/dist/index.html; \
    else \
      npm run build; \
    fi

# ── Stage 2: Runtime Backend ──────────────────────────────────────────────────
FROM python:3.11-slim

# Prevent Python from writing .pyc and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install system dependencies (git, curl for kubectl/healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY agentic_engine/ ./agentic_engine/
COPY digital_twin/ ./digital_twin/
COPY detection/ ./detection/
COPY pr_review_agent/ ./pr_review_agent/
COPY dashboard/backend/ ./dashboard/backend/
COPY dashboard/frontend/ ./dashboard/frontend/
COPY datasets/ ./datasets/
COPY github-app-manifest.json .
COPY action.yml .

# Copy compiled Vite frontend from Stage 1 into backend static location
COPY --from=frontend-builder /app/frontend/dist ./dashboard/frontend-vite/dist

# Ensure data directory exists for SQLite persistence
# (In production, mount an Azure File Share or use PostgreSQL via DATABASE_URL)
RUN mkdir -p /app/data

# Non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && chown -R appuser:appuser /app
USER appuser

# Expose HTTP port
EXPOSE 8000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8000/api/status || exit 1

# Start FastAPI application with uvicorn
CMD ["python", "-m", "uvicorn", "dashboard.backend.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", "--log-level", "info"]
