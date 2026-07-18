"""Dataset manifest generation per spec Section 11."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from carpet_designer.domain.schemas import DatasetFileEntry, DatasetManifest
from carpet_designer.logging_config import get_logger

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger("data.manifest")


class ManifestBuilder:
    """Builder for DatasetManifest."""

    def __init__(self, dataset_id: str, description: str = "") -> None:
        """Initialize builder.

        Args:
            dataset_id: Unique identifier for the dataset.
            description: Optional description.
        """
        self.dataset_id = dataset_id
        self.description = description
        self.files: list[DatasetFileEntry] = []

    def add_entries(self, entries: list[DatasetFileEntry]) -> None:
        """Add multiple entries to the manifest.

        Args:
            entries: List of DatasetFileEntry instances.
        """
        self.files.extend(entries)

    def build(self) -> DatasetManifest:
        """Build the final DatasetManifest.

        Returns:
            The assembled DatasetManifest.
        """
        counts: dict[str, int] = {"total": len(self.files)}
        for entry in self.files:
            counts[entry.split] = counts.get(entry.split, 0) + 1

        return DatasetManifest(
            dataset_id=self.dataset_id,
            files=self.files,
            counts=counts,
            metadata={"description": self.description},
            updated_at=datetime.now(tz=UTC),
        )

    @staticmethod
    def save(manifest: DatasetManifest, target_path: Path) -> None:
        """Save a manifest to a JSON file.

        Args:
            manifest: The manifest to save.
            target_path: File path to save JSON to.
        """
        target_path.parent.mkdir(parents=True, exist_ok=True)
        json_str = manifest.model_dump_json(indent=2)
        target_path.write_text(json_str, encoding="utf-8")
        logger.info("Saved dataset manifest to %s", target_path)

    @staticmethod
    def load(source_path: Path) -> DatasetManifest:
        """Load a manifest from a JSON file.

        Args:
            source_path: File path to load JSON from.

        Returns:
            The loaded DatasetManifest.
        """
        json_str = source_path.read_text(encoding="utf-8")
        return DatasetManifest.model_validate_json(json_str)
