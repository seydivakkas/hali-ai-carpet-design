"""SQLite database connection and lifecycle management."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

from carpet_designer.logging_config import get_logger

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger("persistence.database")


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Create or open a SQLite database connection.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        A configured sqlite3.Connection instance.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
