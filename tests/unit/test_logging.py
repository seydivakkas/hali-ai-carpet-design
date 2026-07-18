"""Unit tests for logging configuration."""

from __future__ import annotations

import json
import logging

from carpet_designer.logging_config import JSONLFormatter, configure_logging, get_logger


class TestLogging:
    """Tests for structured logging."""

    def test_get_logger(self) -> None:
        logger = get_logger("test")
        assert logger.name == "carpet_designer.test"

    def test_jsonl_formatter(self) -> None:
        formatter = JSONLFormatter()
        record = logging.LogRecord(
            name="carpet_designer.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["level"] == "INFO"
        assert data["event"] == "Test message"
        assert "timestamp" in data

    def test_jsonl_formatter_with_extra(self) -> None:
        formatter = JSONLFormatter()
        record = logging.LogRecord(
            name="carpet_designer.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Gen complete",
            args=(),
            exc_info=None,
        )
        record.generation_id = "gen_test123"  # type: ignore[attr-defined]
        record.duration_ms = 1500.0  # type: ignore[attr-defined]
        output = formatter.format(record)
        data = json.loads(output)
        assert data["generation_id"] == "gen_test123"
        assert data["duration_ms"] == 1500.0

    def test_configure_logging(self) -> None:
        configure_logging("DEBUG")
        logger = logging.getLogger("carpet_designer")
        assert logger.level == logging.DEBUG
