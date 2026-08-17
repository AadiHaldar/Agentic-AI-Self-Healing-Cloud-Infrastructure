# ==============================================================================
# Multi-Stage Dockerfile for Agentic AI Self-Healing & PR Review Platform
# Stage 1: Build React + Vite SPA Frontend
# Stage 2: Python FastAPI Backend + ML & Simulation Engine
# ==============================================================================

# --- Stage 1: Frontend Build ---
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Copy frontend package definitions
COPY dashboard/frontend-vite/package*.json ./
RUN npm ci

# Copy frontend source and build
COPY dashboard/frontend-vite/ ./
RUN npm run build

# --- Stage 2: Runtime Backend ---
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

# Install Python requirements
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
COPY infrastructure/ ./infrastructure/
COPY github-app-manifest.json .
COPY action.yml .

# Copy compiled Vite frontend from Stage 1 into backend static location
COPY --from=frontend-builder /app/frontend/dist ./dashboard/frontend-vite/dist

# Ensure data directory exists for SQLite persistence
RUN mkdir -p /app/data

# Expose HTTP port
EXPOSE 8000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/api/status || exit 1

# Start FastAPI application with uvicorn
CMD ["python", "-m", "uvicorn", "dashboard.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
