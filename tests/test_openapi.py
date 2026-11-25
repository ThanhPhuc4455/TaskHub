from app.main import app


def test_openapi_documents_error_schema_for_every_endpoint() -> None:
    document = app.openapi()
    schemas = document["components"]["schemas"]
    assert "ErrorResponse" in schemas

    for path, path_item in document["paths"].items():
        for method, operation in path_item.items():
            if method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}:
                continue
            responses = operation["responses"]
            assert "500" in responses, f"{method.upper()} {path} is missing 500"
            for status_code, response in responses.items():
                if not str(status_code).startswith("4") and not str(status_code).startswith("5"):
                    continue
                schema = response.get("content", {}).get("application/json", {}).get("schema")
                assert schema is not None, f"{method.upper()} {path} {status_code} lacks schema"
                assert schema.get("$ref") == "#/components/schemas/ErrorResponse"
