import pytest
from pydantic import ValidationError

from src.config import Settings


def test_settings_requires_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("JWT_SECRET_KEY", "supersecret")
    s = Settings(_env_file=None)
    assert s.database_url == "postgresql+asyncpg://u:p@localhost/db"
    assert s.jwt_secret_key == "supersecret"
    assert s.app_name == "ShipAPI"
    assert s.version == "1.0.0"
    assert s.debug is False
    assert s.access_token_expire_minutes == 30
    assert s.refresh_token_expire_days == 7


def test_settings_defaults(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("JWT_SECRET_KEY", "supersecret")
    s = Settings(_env_file=None)
    assert s.database_url_direct is None
    assert s.jwt_algorithm == "HS256"
