from typing import Literal

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import (
    REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS,
    REDIS_SOCKET_TIMEOUT_SECONDS,
)


class Settings(BaseSettings):
    app_name: str = "TaskHub"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    app_env: Literal["development", "test", "production"] = "development"
    debug: bool = Field(default=False, validation_alias=AliasChoices("TASKHUB_DEBUG"))
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

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.app_env == "production" and (
            len(self.secret_key) < 32
            or self.secret_key in {"change-me", "changeme", "secret", "your-secret-key"}
        ):
            raise ValueError("production SECRET_KEY must be at least 32 characters and non-default")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
