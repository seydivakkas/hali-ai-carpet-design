"""Shared test fixtures and configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from carpet_designer.persistence.database import get_connection
from carpet_designer.persistence.migrations import run_migrations
from carpet_designer.settings import Settings

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory."""
    return tmp_path


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Provide test settings with temporary paths."""
    return Settings(
        project_root=tmp_path,
        artifacts_dir=tmp_path / "artifacts",
        data_dir=tmp_path / "data",
        configs_dir=tmp_path / "configs",
        db_path=tmp_path / "test.db",
        device="cpu",
        log_level="DEBUG",
    )


@pytest.fixture
def db_connection(tmp_path: Path) -> sqlite3.Connection:
    """Provide a test database connection with migrations applied."""
    db_path = tmp_path / "test.db"
    conn = get_connection(db_path)
    run_migrations(conn)
    yield conn  # type: ignore[misc]
    conn.close()
