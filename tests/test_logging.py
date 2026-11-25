import io
import logging

from app.core.logging import PRODUCTION_FORMAT, RequestContextFilter, RequestContextFormatter
from app.core.middleware import request_id_context


def test_production_format_contains_request_id_and_redacts_sensitive_values() -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(RequestContextFilter())
    handler.setFormatter(RequestContextFormatter(PRODUCTION_FORMAT))
    logger = logging.getLogger("test.production.logging")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    token = request_id_context.set("prod-request-7")
    try:
        logger.info("Authorization: Bearer secret password=hidden email=user@example.com")
    finally:
        request_id_context.reset(token)
        logger.removeHandler(handler)
        handler.close()

    output = stream.getvalue()
    assert "request_id=prod-request-7" in output
    assert "secret" not in output
    assert "hidden" not in output
    assert "user@example.com" not in output


def test_formatter_redacts_quoted_dict_json_and_token_values() -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(RequestContextFilter())
    handler.setFormatter(RequestContextFormatter("%(message)s"))
    logger = logging.getLogger("test.redaction.shapes")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        logger.info(
            'password=plain "password": "json-secret" '
            "'authorization': 'Bearer dict-secret' "
            "access_token=access-secret refresh_token=refresh-secret"
        )
    finally:
        logger.removeHandler(handler)
        logger.propagate = True
        handler.close()

    output = stream.getvalue()
    for secret in ("plain", "json-secret", "dict-secret", "access-secret", "refresh-secret"):
        assert secret not in output
    assert output.count("[REDACTED]") >= 5


def test_formatter_redacts_custom_authorization_scheme_and_multiword_quoted_secrets() -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(RequestContextFilter())
    handler.setFormatter(RequestContextFormatter("%(message)s"))
    logger = logging.getLogger("test.redaction.schemes")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        logger.info('Authorization: Basic dXNlcjpwYXNz {"password": "my secret pw"}')
    finally:
        logger.removeHandler(handler)
        logger.propagate = True
        handler.close()

    output = stream.getvalue()
    assert "dXNlcjpwYXNz" not in output
    assert "secret pw" not in output
    assert "Basic [REDACTED]" in output
    assert '{"password": "[REDACTED]"}' in output


def test_mismatched_format_arguments_do_not_raise() -> None:
    logger = logging.getLogger("test.mismatched.logging")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(RequestContextFilter())
    handler.setFormatter(RequestContextFormatter("%(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    logger.setLevel(logging.WARNING)
    try:
        logger.warning("a %s %s", 1)
        assert "a %s %s" in stream.getvalue()
    finally:
        logger.removeHandler(handler)
        logger.propagate = True
        handler.close()


def test_uvicorn_loggers_configured_with_console_handler_and_filter() -> None:
    from app.core.config import Settings
    from app.core.logging import configure_logging

    settings = Settings(app_env="development")
    configure_logging(settings)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        assert any(
            isinstance(f, RequestContextFilter) for h in logger.handlers for f in h.filters
        ), f"{name} logger should have RequestContextFilter"
        assert any(isinstance(h.formatter, RequestContextFormatter) for h in logger.handlers), (
            f"{name} logger should have RequestContextFormatter"
        )


def test_configure_logging_selects_expected_formatter_for_environment() -> None:
    from app.core.config import Settings
    from app.core.logging import DEVELOPMENT_FORMAT, PRODUCTION_FORMAT, configure_logging

    token = request_id_context.set("test-req")
    try:
        dev_settings = Settings(app_env="development")
        configure_logging(dev_settings)
        dev_handler = logging.getLogger().handlers[0]
        assert getattr(dev_handler.formatter, "_fmt", None) == DEVELOPMENT_FORMAT

        record = logging.LogRecord(
            "test.dev",
            logging.INFO,
            "test.py",
            1,
            "test message",
            (),
            None,
        )
        dev_handler.filter(record)
        formatted_dev = dev_handler.format(record)
        assert "request_id=test-req test.dev: test message" in formatted_dev
        assert "level=INFO" not in formatted_dev

        prod_settings = Settings(app_env="production", secret_key="a" * 32)
        configure_logging(prod_settings)
        prod_handler = logging.getLogger().handlers[0]
        assert getattr(prod_handler.formatter, "_fmt", None) == PRODUCTION_FORMAT

        prod_handler.filter(record)
        formatted_prod = prod_handler.format(record)
        expected_prod_msg = "level=INFO request_id=test-req logger=test.dev message=test message"
        assert expected_prod_msg in formatted_prod
        assert "test.dev: test message" not in formatted_prod
    finally:
        request_id_context.reset(token)
