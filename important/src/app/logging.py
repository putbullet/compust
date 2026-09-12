import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Optional

# Context variable to hold active scraping execution context
_scraping_context: ContextVar[dict[str, Any]] = ContextVar(
    "scraping_context", default={}
)


class JsonFormatter(logging.Formatter):
    """
    Outputs structured log records in JSON format, enriched with
    active scraping run context (scraping_run_id, company_id, target_id)
    and optional event markers for queryable observability.
    """

    def format(self, record: logging.LogRecord) -> str:
        ctx = _scraping_context.get({})
        
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Tag with scraping run context if present
        if "scraping_run_id" in ctx:
            payload["scraping_run_id"] = ctx["scraping_run_id"]
        if "company_id" in ctx:
            payload["company_id"] = ctx["company_id"]
        if "target_id" in ctx:
            payload["target_id"] = ctx["target_id"]

        # If an event tag was passed via extra={"event": ...}
        if hasattr(record, "event") and record.event:
            payload["event"] = record.event
        elif "event" in ctx:
            payload["event"] = ctx["event"]

        # Include any other custom extra fields passed on the record
        standard_attrs = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName",
            "processName", "process", "message", "event",
        }
        extras = {
            k: v for k, v in record.__dict__.items()
            if k not in standard_attrs and not k.startswith("_")
        }
        if extras:
            payload["extra"] = extras

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def get_logger(name: str = "compust") -> logging.Logger:
    """Returns a configured structured JSON logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


class ScrapingRunScope:
    """Context manager to tag all logs within a scraping run."""

    def __init__(
        self,
        scraping_run_id: Optional[int] = None,
        company_id: Optional[int] = None,
        target_id: Optional[int] = None,
    ):
        self.new_ctx = {}
        if scraping_run_id is not None:
            self.new_ctx["scraping_run_id"] = scraping_run_id
        if company_id is not None:
            self.new_ctx["company_id"] = company_id
        if target_id is not None:
            self.new_ctx["target_id"] = target_id
        self.token = None

    def __enter__(self):
        current = dict(_scraping_context.get({}))
        current.update(self.new_ctx)
        self.token = _scraping_context.set(current)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.token is not None:
            _scraping_context.reset(self.token)
