import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_cache_ttl_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite+aiosqlite://", secret_key="test", cache_ttl_seconds=0)


def test_invalid_app_env_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite+aiosqlite://", secret_key="test", app_env="staging")


def test_invalid_log_level_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite+aiosqlite://", secret_key="test", log_level="TRACE")


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


def test_enabled_smtp_requires_host_and_from_address() -> None:
    with pytest.raises(ValidationError):
        Settings(
            database_url="sqlite+aiosqlite://",
            secret_key="test",
            smtp_enabled=True,
            smtp_from_address="taskhub@example.local",
        )


def test_smtp_timeout_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite+aiosqlite://", secret_key="test", smtp_timeout_seconds=0)


def test_smtp_port_must_be_valid() -> None:
    for port in (0, 65536):
        with pytest.raises(ValidationError):
            Settings(database_url="sqlite+aiosqlite://", secret_key="test", smtp_port=port)


def test_disabled_smtp_does_not_require_configuration() -> None:
    settings = Settings(database_url="sqlite+aiosqlite://", secret_key="test")
    assert settings.smtp_enabled is False
