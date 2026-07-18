"""Structured JSONL logging configuration."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


class JSONLFormatter(logging.Formatter):
    """Emit each log record as a single JSON line.

    Fields per spec Section 29: timestamp, level, event, run_id,
    generation_id, recipe_id, model_id, lora_ids, dataset_id,
    device, dtype, duration_ms, memory_mb, error_code.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a JSON line.

        Args:
            record: The log record to format.

        Returns:
            JSON-encoded string representing the log record.
        """
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
            "logger": record.name,
        }

        # Add optional structured fields from extra
        structured_fields = [
            "run_id",
            "generation_id",
            "recipe_id",
            "model_id",
            "lora_ids",
            "dataset_id",
            "device",
            "dtype",
            "duration_ms",
            "memory_mb",
            "error_code",
        ]
        for field in structured_fields:
            value = getattr(record, field, None)
            if value is not None:
                log_entry[field] = value

        if record.exc_info and record.exc_info[1]:
            log_entry["exception_type"] = type(record.exc_info[1]).__name__
            log_entry["exception_message"] = str(record.exc_info[1])

        return json.dumps(log_entry, default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """Configure application-wide structured logging.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    root_logger = logging.getLogger("carpet_designer")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    root_logger.handlers.clear()

    # JSONL handler for structured output
    jsonl_handler = logging.StreamHandler(sys.stderr)
    jsonl_handler.setFormatter(JSONLFormatter())
    root_logger.addHandler(jsonl_handler)

    # Prevent propagation to root logger
    root_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under the carpet_designer namespace.

    Args:
        name: Logger name, will be prefixed with ``carpet_designer.``.

    Returns:
        Configured Logger instance.
    """
    return logging.getLogger(f"carpet_designer.{name}")
