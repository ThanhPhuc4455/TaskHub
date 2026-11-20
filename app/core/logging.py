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
    (re.compile(r"(?i)(authorization\s*[:=]\s*).+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(password\s*[:=]\s*)([^\s,]+)"), r"\1[REDACTED]"),
    (re.compile(r"\b[\w.+-]+@[\w.-]+\.\w+\b"), "[REDACTED_EMAIL]"),
)


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get()
        message = record.getMessage()
        for pattern, replacement in _SENSITIVE_PATTERNS:
            message = pattern.sub(replacement, message)
        record.msg = message
        record.args = ()
        return True


def configure_logging(settings: Settings) -> None:
    level = settings.log_level
    formatter = "production" if settings.app_env == "production" else "development"
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {"request_context": {"()": RequestContextFilter}},
            "formatters": {
                "development": {"format": DEVELOPMENT_FORMAT},
                "production": {"format": PRODUCTION_FORMAT},
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": formatter,
                    "filters": ["request_context"],
                    "stream": "ext://sys.stderr",
                }
            },
            "root": {"level": level, "handlers": ["console"]},
        }
    )
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(logger_name).setLevel(level)
