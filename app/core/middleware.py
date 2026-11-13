import json
import logging
import re
import time
import uuid
from contextvars import ContextVar
from typing import Any, cast

from app.core.constants import (
    INTERNAL_SERVER_ERROR_CODE,
    INTERNAL_SERVER_ERROR_MESSAGE,
    REQUEST_ID_ALLOWED_PATTERN,
    REQUEST_ID_HEADER,
    REQUEST_ID_MAX_LENGTH,
)

logger = logging.getLogger(__name__)
request_id_context: ContextVar[str] = ContextVar("request_id", default="-")


def _header_value(scope: dict[str, Any], name: str) -> str | None:
    wanted = name.lower().encode()
    for key, value in scope.get("headers", []):
        if key.lower() == wanted:
            try:
                return cast(str, value.decode("ascii"))
            except UnicodeDecodeError:
                return None
    return None


def _request_id(scope: dict[str, Any]) -> str:
    candidate = _header_value(scope, REQUEST_ID_HEADER)
    if (
        candidate is not None
        and len(candidate) <= REQUEST_ID_MAX_LENGTH
        and re.fullmatch(REQUEST_ID_ALLOWED_PATTERN, candidate) is not None
    ):
        return candidate
    return str(uuid.uuid4())


class RequestLoggingMiddleware:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        request_id = _request_id(scope)
        scope.setdefault("state", {})["request_id"] = request_id
        token = request_id_context.set(request_id)
        started = time.perf_counter()
        status_code = 500
        response_started = False

        async def send_with_request_id(message: dict[str, Any]) -> None:
            nonlocal status_code, response_started
            if message.get("type") == "http.response.start":
                status_code = int(message["status"])
                response_started = True
                headers = list(message.get("headers", []))
                headers.append((REQUEST_ID_HEADER.lower().encode(), request_id.encode()))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            logger.exception(
                "HTTP request failed method=%s path=%s status=%s duration_ms=%.2f request_id=%s",
                scope.get("method", ""),
                scope.get("path", ""),
                status_code,
                (time.perf_counter() - started) * 1000,
                request_id,
            )
            if response_started:
                raise
            body = json.dumps(
                {
                    "detail": INTERNAL_SERVER_ERROR_MESSAGE,
                    "code": INTERNAL_SERVER_ERROR_CODE,
                    "request_id": request_id,
                }
            ).encode()
            await send_with_request_id(
                {
                    "type": "http.response.start",
                    "status": 500,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await send_with_request_id(
                {"type": "http.response.body", "body": body, "more_body": False}
            )
        finally:
            logger.info(
                "HTTP request method=%s path=%s status=%s duration_ms=%.2f request_id=%s",
                scope.get("method", ""),
                scope.get("path", ""),
                status_code if response_started else 500,
                (time.perf_counter() - started) * 1000,
                request_id,
            )
            request_id_context.reset(token)
