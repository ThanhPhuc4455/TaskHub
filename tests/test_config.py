import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_cache_ttl_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite+aiosqlite://", secret_key="test", cache_ttl_seconds=0)
