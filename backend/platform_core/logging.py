"""Structured logging with JSON-safe message serialization."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "severity": record.levelname,
            "service": "lodgeflow-api",
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = str(getattr(record, "request_id", "") or "")[:80]
        if request_id:
            payload["request_id"] = request_id
        if record.exc_info and record.exc_info[0]:
            payload["exception_type"] = record.exc_info[0].__name__
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
