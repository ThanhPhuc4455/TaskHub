import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.messages import SMTP_TLS_MUTUALLY_EXCLUSIVE_MESSAGE


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


def test_production_rejects_blocklisted_default_secret_key() -> None:
    with pytest.raises(ValidationError):
        Settings(
            database_url="sqlite+aiosqlite://",
            app_env="production",
            secret_key="replace-with-a-local-secret-32-chars",
        )


def test_production_accepts_strong_non_default_secret_key() -> None:
    settings = Settings(
        database_url="sqlite+aiosqlite://",
        app_env="production",
        secret_key="a" * 32,
    )
    assert settings.secret_key == "a" * 32


def test_production_rejects_debug_mode() -> None:
    with pytest.raises(ValidationError, match="debug mode cannot be enabled in production"):
        Settings(
            database_url="sqlite+aiosqlite://",
            app_env="production",
            secret_key="a" * 32,
            debug=True,
        )


def test_development_accepts_debug_mode() -> None:
    settings = Settings(
        database_url="sqlite+aiosqlite://",
        secret_key="test",
        debug=True,
    )
    assert settings.app_env == "development"
    assert settings.debug is True


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


def test_smtp_tls_and_start_tls_mutually_exclusive() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            database_url="sqlite+aiosqlite://",
            secret_key="test",
            smtp_use_tls=True,
            smtp_start_tls=True,
        )
    assert SMTP_TLS_MUTUALLY_EXCLUSIVE_MESSAGE in str(exc_info.value)


def test_settings_debug_validation_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TASKHUB_DEBUG", "true")
    settings = Settings(database_url="sqlite+aiosqlite://", secret_key="test")
    assert settings.debug is True


def test_fastapi_app_debug_matches_settings() -> None:
    from fastapi import FastAPI

    dev_settings = Settings(database_url="sqlite+aiosqlite://", secret_key="test", debug=True)
    custom_app = FastAPI(debug=dev_settings.debug)
    assert custom_app.debug is True
