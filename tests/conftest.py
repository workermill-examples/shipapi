import os

import pytest

# Set required env vars before any src module is imported by test collection.
# Tests that need to test missing-field behavior should use monkeypatch to
# override these after the module is already loaded.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/testdb")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> None:
    """Reset the in-memory rate limit storage before every test.

    The module-level ``limiter`` is shared across tests (it's imported once at
    collection time).  Without this fixture, rate limit counters accumulate
    across tests and later tests may hit limits that were exhausted by earlier
    tests — especially important for endpoints with low limits (e.g. 5/minute
    for /auth/register).
    """
    from src.middleware.rate_limit import limiter

    limiter._storage.reset()
