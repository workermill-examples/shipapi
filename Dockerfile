# =============================================================================
# Build stage — install dependencies with uv
# =============================================================================
FROM python:3.13-slim AS builder

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Compile bytecode and use copy link mode for efficient Docker layers
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# Install project dependencies first (before copying app code)
# This layer is cached as long as pyproject.toml / uv.lock don't change
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy application source
COPY src/ ./src/

# Stub alembic/ and seed/ directories — populated by later cards.
# These stubs ensure the runtime COPY commands succeed immediately.
RUN mkdir -p alembic seed

# Install the project itself into the venv
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev

# =============================================================================
# Runtime stage — minimal image with non-root user
# =============================================================================
FROM python:3.13-slim

WORKDIR /app

# Copy virtual environment from builder (no uv needed at runtime)
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --from=builder /app/src ./src
COPY --from=builder /app/alembic ./alembic
COPY --from=builder /app/seed ./seed

# Create non-root user
RUN groupadd -g 1001 appuser \
    && useradd -u 1001 -g 1001 -m -s /bin/sh appuser

# Add venv binaries to PATH
ENV PATH="/app/.venv/bin:$PATH"

USER appuser

EXPOSE 8000

# Use sh -c so Railway's $PORT variable expands at container start time
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
