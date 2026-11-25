from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import (
    REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS,
    REDIS_SOCKET_TIMEOUT_SECONDS,
    SECRET_KEY_BLOCKLIST,
    SECRET_KEY_MIN_LENGTH,
    SMTP_PORT_DEFAULT,
    SMTP_PORT_MAX,
    SMTP_PORT_MIN,
    SMTP_TIMEOUT_SECONDS,
)
from app.core.messages import (
    PRODUCTION_DEBUG_FORBIDDEN_MESSAGE,
    PRODUCTION_SECRET_KEY_MESSAGE,
    SMTP_CONFIGURATION_REQUIRED_MESSAGE,
)


class Settings(BaseSettings):
    app_name: str = "TaskHub"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    app_env: Literal["development", "test", "production"] = "development"
    debug: bool = Field(default=False, validation_alias=AliasChoices("TASKHUB_DEBUG", "debug"))
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    database_url: str
    db_echo: bool = False
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    redis_url: str = "redis://127.0.0.1:6379/0"
    cache_ttl_seconds: int = Field(default=120, gt=0)
    redis_socket_connect_timeout: float = REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS
    redis_socket_timeout: float = REDIS_SOCKET_TIMEOUT_SECONDS
    smtp_host: str | None = None
    smtp_port: int = Field(default=SMTP_PORT_DEFAULT, ge=SMTP_PORT_MIN, le=SMTP_PORT_MAX)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_use_tls: bool = False
    smtp_start_tls: bool = False
    smtp_timeout_seconds: float = Field(default=SMTP_TIMEOUT_SECONDS, gt=0)
    smtp_from_address: str | None = None
    smtp_enabled: bool = False

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.app_env == "production":
            if (
                len(self.secret_key) < SECRET_KEY_MIN_LENGTH
                or self.secret_key in SECRET_KEY_BLOCKLIST
            ):
                raise ValueError(PRODUCTION_SECRET_KEY_MESSAGE)
            if self.debug:
                raise ValueError(PRODUCTION_DEBUG_FORBIDDEN_MESSAGE)
        return self

    @model_validator(mode="after")
    def validate_smtp_configuration(self) -> "Settings":
        if self.smtp_enabled and (not self.smtp_host or not self.smtp_from_address):
            raise ValueError(SMTP_CONFIGURATION_REQUIRED_MESSAGE)
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )


settings = Settings()
