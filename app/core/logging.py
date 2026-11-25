import logging
import logging.config
import re

from app.core.config import Settings
from app.core.middleware import request_id_context

DEVELOPMENT_FORMAT = "%(asctime)s %(levelname)s request_id=%(request_id)s %(name)s: %(message)s"
PRODUCTION_FORMAT = (
    "level=%(levelname)s request_id=%(request_id)s logger=%(name)s message=%(message)s"
)

_SENSITIVE_PATTERNS = (
    (
        re.compile(
            r"(?i)([\"']?authorization[\"']?\s*[:=]\s*(?:\w+\s+)?|[\"']?(?:password|access_token|refresh_token)[\"']?\s*[:=]\s*)(?:([\"'])(?:(?!\2).)*\2|[^\"',\s}]+)"
        ),
        r"\1\2[REDACTED]\2",
    ),
    (re.compile(r"\b[\w.+-]+@[\w.-]+\.\w+\b"), "[REDACTED_EMAIL]"),
)


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get()
        return True


class RequestContextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        try:
            message = super().format(record)
        except Exception:
            message = f"{record.levelname} {record.name}: {record.msg}"
        for pattern, replacement in _SENSITIVE_PATTERNS:
            message = pattern.sub(replacement, message)
        return message


def configure_logging(settings: Settings) -> None:
    level = settings.log_level
    formatter = "production" if settings.app_env == "production" else "development"
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {"request_context": {"()": RequestContextFilter}},
            "formatters": {
                "development": {"()": RequestContextFormatter, "format": DEVELOPMENT_FORMAT},
                "production": {"()": RequestContextFormatter, "format": PRODUCTION_FORMAT},
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": formatter,
                    "filters": ["request_context"],
                    "stream": "ext://sys.stderr",
                }
            },
            "loggers": {
                "uvicorn": {"handlers": ["console"], "level": level, "propagate": False},
                "uvicorn.error": {"handlers": ["console"], "level": level, "propagate": False},
                "uvicorn.access": {"handlers": ["console"], "level": level, "propagate": False},
            },
            "root": {"level": level, "handlers": ["console"]},
        }
    )
