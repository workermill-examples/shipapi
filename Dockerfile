# Multi-stage Dockerfile for ShipAPI
# Stage 1: Frontend build using Node.js
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package*.json ./

# Install frontend dependencies
RUN npm ci

# Copy frontend source code
COPY frontend/ ./

# Build frontend application
RUN npm run build

# Stage 2: Python dependencies with uv
FROM python:3.13-slim AS python-builder

# Install uv for fast Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy Python project files including README.md (required by hatchling)
COPY pyproject.toml uv.lock README.md ./

# Copy source code
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY seed/ ./seed/

# Install Python dependencies into virtual environment
RUN uv sync --frozen --no-dev

# Stage 3: Final runtime image
FROM python:3.13-alpine

# Install runtime dependencies for PostgreSQL client and create user in single layer
RUN apk add --no-cache libpq \
    && addgroup -S shipapi \
    && adduser -S -G shipapi -s /bin/false shipapi

WORKDIR /app

# Copy Python virtual environment from builder stage
COPY --from=python-builder --chown=shipapi:shipapi /app/.venv /app/.venv

# Copy application code from builder stage (minimal files only)
COPY --from=python-builder --chown=shipapi:shipapi /app/src /app/src
COPY --from=python-builder --chown=shipapi:shipapi /app/alembic /app/alembic
COPY --from=python-builder --chown=shipapi:shipapi /app/alembic.ini /app/alembic.ini
COPY --from=python-builder --chown=shipapi:shipapi /app/seed /app/seed

# Copy frontend build output only (not entire dist folder)
COPY --from=frontend-builder --chown=shipapi:shipapi /app/frontend/dist /app/frontend/dist

# Set PATH to include virtual environment binaries (required for Railway preDeployCommand)
ENV PATH="/app/.venv/bin:$PATH"

# Switch to non-root user
USER shipapi

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"

# Start the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]