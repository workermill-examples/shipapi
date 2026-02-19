import os

# Set required env vars before any src module is imported by test collection.
# Tests that need to test missing-field behavior should use monkeypatch to
# override these after the module is already loaded.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/testdb")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
