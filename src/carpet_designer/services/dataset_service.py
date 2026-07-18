"""Dataset preparation service per spec Section 12."""

from __future__ import annotations

from typing import TYPE_CHECKING

from carpet_designer.data.ingest import IngestionPipeline
from carpet_designer.data.manifest import ManifestBuilder
from carpet_designer.domain.enums import DatasetStatus, ErrorCode
from carpet_designer.domain.errors import CarpetDesignerError
from carpet_designer.logging_config import get_logger

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger("services.dataset_service")


class DatasetService:
    """Service to orchestrate dataset preparation."""

    def __init__(self, data_dir: Path, manifests_dir: Path) -> None:
        """Initialize the service.

        Args:
            data_dir: Base directory for dataset storage.
            manifests_dir: Directory to save generated manifests.
        """
        self.data_dir = data_dir
        self.manifests_dir = manifests_dir

    def prepare_dataset(
        self,
        source_dir: Path,
        dataset_id: str,
        license_type: str = "custom",
    ) -> Path:
        """Prepare a dataset from a raw source folder.

        Runs validation, hashes files, and generates manifest.

        Args:
            source_dir: Directory with raw images/captions.
            dataset_id: Identifier for the new dataset.
            license_type: Declared license for these files.

        Returns:
            Path to the generated manifest.json file.
        """
        target_dir = self.data_dir / dataset_id

        # 1. Ingest files
        pipeline = IngestionPipeline(
            source_dir=source_dir,
            target_dir=target_dir,
            license_type=license_type,
        )
        entries, status = pipeline.run()

        if status == DatasetStatus.INVALID_OR_MISSING:
            raise CarpetDesignerError(
                message=f"No valid images found in {source_dir}",
                error_code=ErrorCode.CD_DATASET_INVALID,
            )

        logger.info(
            "Ingested %d files for dataset %s (Status: %s)",
            len(entries),
            dataset_id,
            status.value,
        )

        # 2. Build and save manifest
        builder = ManifestBuilder(
            dataset_id=dataset_id,
            description=f"Generated from {source_dir.name}",
        )
        builder.add_entries(entries)
        manifest = builder.build()

        manifest_path = self.manifests_dir / f"{dataset_id}_manifest.json"
        ManifestBuilder.save(manifest, manifest_path)

        return manifest_path
