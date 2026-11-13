from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import (
    REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS,
    REDIS_SOCKET_TIMEOUT_SECONDS,
)


class Settings(BaseSettings):
    app_name: str = "TaskHub"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"

    database_url: str
    db_echo: bool = False
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    redis_url: str = "redis://127.0.0.1:6379/0"
    cache_ttl_seconds: int = 120
    redis_socket_connect_timeout: float = REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS
    redis_socket_timeout: float = REDIS_SOCKET_TIMEOUT_SECONDS

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
