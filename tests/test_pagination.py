from app.schemas.page import PageResponse


def test_page_response_from_result_preserves_page_metadata() -> None:
    response = PageResponse[str].from_result(["first"], total=3, page=2, limit=1)

    assert response.model_dump() == {
        "items": ["first"],
        "total": 3,
        "page": 2,
        "limit": 1,
    }
