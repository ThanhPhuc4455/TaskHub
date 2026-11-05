import pytest
from pydantic import ValidationError

from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate


def test_update_rejects_explicit_null() -> None:
    with pytest.raises(ValidationError):
        WorkspaceUpdate.model_validate({"name": None})


def test_update_allows_empty_body() -> None:
    update = WorkspaceUpdate.model_validate({})
    assert update.model_dump(exclude_unset=True) == {}


def test_update_accepts_valid_name() -> None:
    update = WorkspaceUpdate.model_validate({"name": "Team B"})
    assert update.model_dump(exclude_unset=True) == {"name": "Team B"}


def test_whitespace_only_name_rejected() -> None:
    with pytest.raises(ValidationError):
        WorkspaceCreate.model_validate({"name": "   "})


def test_name_is_stripped() -> None:
    assert WorkspaceCreate.model_validate({"name": "  Team A  "}).name == "Team A"
