import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_cache_ttl_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite+aiosqlite://", secret_key="test", cache_ttl_seconds=0)


def test_invalid_app_env_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite+aiosqlite://", secret_key="test", app_env="staging")


def test_production_requires_strong_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite+aiosqlite://", app_env="production", secret_key="short")

    with pytest.raises(ValidationError):
        monkeypatch.delenv("SECRET_KEY", raising=False)
        Settings(database_url="sqlite+aiosqlite://", app_env="production", _env_file=None)


def test_development_settings_are_valid() -> None:
    settings = Settings(database_url="sqlite+aiosqlite://", secret_key="test")
    assert settings.app_env == "development"
    assert settings.debug is False
