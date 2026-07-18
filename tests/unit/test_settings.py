"""Unit tests for settings module."""

from __future__ import annotations

from pathlib import Path

from carpet_designer.settings import Settings


class TestSettings:
    """Tests for Settings configuration."""

    def test_default_settings(self) -> None:
        settings = Settings()
        assert settings.device == "auto"
        assert settings.log_level == "INFO"
        assert settings.telemetry is False
        assert settings.default_width == 1024
        assert settings.max_batch_size == 16

    def test_custom_settings(self, tmp_path: Path) -> None:
        settings = Settings(
            project_root=tmp_path,
            device="cpu",
            log_level="DEBUG",
        )
        assert settings.device == "cpu"
        assert settings.log_level == "DEBUG"

    def test_resolve_path(self, tmp_path: Path) -> None:
        settings = Settings(project_root=tmp_path)
        resolved = settings.resolve_path(Path("test/dir"))
        assert resolved == (tmp_path / "test" / "dir").resolve()

    def test_resolve_absolute_path(self, tmp_path: Path) -> None:
        settings = Settings(project_root=tmp_path)
        abs_path = tmp_path / "absolute"
        resolved = settings.resolve_path(abs_path)
        assert resolved == abs_path
