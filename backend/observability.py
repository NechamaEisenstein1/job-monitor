"""Structured (JSON-lines) event logging. Never pass secrets or full payloads."""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

_logger = logging.getLogger("job_monitor")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "level": record.levelname.lower(),
            "event": record.getMessage(),
            **getattr(record, "fields", {}),
        }
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    _logger.handlers[:] = [handler]
    _logger.setLevel(level.upper())
    _logger.propagate = False


def log_event(event: str, level: int = logging.INFO, **fields: object) -> None:
    _logger.log(level, event, extra={"fields": fields})
