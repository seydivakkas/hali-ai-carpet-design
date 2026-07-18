"""Application settings loaded from environment and config files."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _project_root() -> Path:
    """Return the project root directory."""
    current = Path(__file__).resolve().parent
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return current.parent.parent


class Settings(BaseSettings):
    """Global application settings.

    Loaded from environment variables prefixed with ``CARPET_DESIGNER_``
    and a ``.env`` file at the project root.
    """

    model_config = SettingsConfigDict(
        env_prefix="CARPET_DESIGNER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Paths
    project_root: Path = Field(default_factory=_project_root)
    artifacts_dir: Path = Field(default=Path("artifacts"))
    data_dir: Path = Field(default=Path("data"))
    configs_dir: Path = Field(default=Path("configs"))

    # Device
    device: Literal["auto", "cuda", "cpu", "mps"] = "auto"

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Telemetry
    telemetry: bool = False

    # Hugging Face
    huggingface_token: str = ""
    hf_home: Path = Field(default=Path("artifacts/cache/huggingface"))

    # Company data governance
    restricted_catalog_permission_ref: str = ""

    # Generation defaults
    default_width: int = 1024
    default_height: int = 1024
    default_steps: int = 30
    default_guidance_scale: float = 7.0
    max_batch_size: int = 16
    max_image_pixels: int = 178_956_970  # PIL default limit
    generation_mode: Literal["auto", "demo", "sdxl"] = "auto"

    # Database
    db_path: Path = Field(default=Path("artifacts/carpet_designer.db"))

    def resolve_path(self, relative: Path) -> Path:
        """Resolve a relative path against the project root.

        Args:
            relative: Path relative to the project root.

        Returns:
            Absolute resolved path.
        """
        if relative.is_absolute():
            return relative
        return (self.project_root / relative).resolve()

    @property
    def resolved_artifacts_dir(self) -> Path:
        """Return the resolved artifacts directory."""
        return self.resolve_path(self.artifacts_dir)

    @property
    def resolved_data_dir(self) -> Path:
        """Return the resolved data directory."""
        return self.resolve_path(self.data_dir)

    @property
    def resolved_configs_dir(self) -> Path:
        """Return the resolved configs directory."""
        return self.resolve_path(self.configs_dir)

    @property
    def resolved_db_path(self) -> Path:
        """Return the resolved database path."""
        return self.resolve_path(self.db_path)


def get_settings() -> Settings:
    """Create and return application settings.

    Returns:
        Configured Settings instance.
    """
    return Settings()
