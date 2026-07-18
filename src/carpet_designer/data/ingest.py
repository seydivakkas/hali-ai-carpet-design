"""Dataset ingestion and validation utilities per spec Section 11."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from PIL import Image

from carpet_designer.domain.enums import DatasetStatus, ErrorCode
from carpet_designer.domain.errors import CarpetDesignerError
from carpet_designer.domain.schemas import DatasetFileEntry
from carpet_designer.logging_config import get_logger

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger("data.ingest")


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of a file.

    Args:
        file_path: Path to the file.

    Returns:
        Hex string of the SHA256 hash.
    """
    sha256 = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


class IngestionPipeline:
    """Pipeline for dataset ingestion and validation."""

    def __init__(self, source_dir: Path, target_dir: Path, license_type: str = "custom") -> None:
        """Initialize the pipeline.

        Args:
            source_dir: Directory containing raw data (images and text files).
            target_dir: Directory to save ingested and validated data.
            license_type: License type for ingested files.
        """
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.license_type = license_type

        # Ensure target directory exists
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def validate_image(self, file_path: Path) -> None:
        """Validate an image file.

        Args:
            file_path: Path to image file.

        Raises:
            CarpetDesignerError: If the image is invalid or cannot be processed.
        """
        try:
            with Image.open(file_path) as img:
                img.verify()
        except Exception as e:
            raise CarpetDesignerError(
                message=f"Invalid image file {file_path.name}: {e}",
                error_code=ErrorCode.CD_DATASET_INVALID,
            ) from e

    def ingest_file(self, file_path: Path, split: str = "train") -> DatasetFileEntry:
        """Ingest a single file and its corresponding caption if available.

        Args:
            file_path: Path to the image file.
            split: Dataset split ('train', 'val', 'test').

        Returns:
            DatasetFileEntry with metadata.
        """
        self.validate_image(file_path)

        # Look for corresponding caption file (e.g. image1.jpg -> image1.txt)
        caption_path = file_path.with_suffix(".txt")
        target_caption_path = ""

        if caption_path.exists():
            target_caption = self.target_dir / caption_path.name
            target_caption.write_text(
                caption_path.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            target_caption_path = target_caption.name

        # Copy file to target directory
        target_path = self.target_dir / file_path.name
        target_path.write_bytes(file_path.read_bytes())

        file_hash = compute_sha256(target_path)

        return DatasetFileEntry(
            relative_path=target_path.name,
            sha256=file_hash,
            license=self.license_type,
            split=split,
            caption_path=target_caption_path,
        )

    def run(self) -> tuple[list[DatasetFileEntry], DatasetStatus]:
        """Run the ingestion pipeline on the source directory.

        Returns:
            Tuple of generated DatasetFileEntries and overall DatasetStatus.
        """
        if not self.source_dir.exists():
            raise CarpetDesignerError(
                message=f"Source directory not found: {self.source_dir}",
                error_code=ErrorCode.CD_DATASET_NOT_FOUND,
            )

        entries: list[DatasetFileEntry] = []
        valid_extensions = {".jpg", ".jpeg", ".png", ".webp"}

        for file_path in self.source_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in valid_extensions:
                try:
                    entry = self.ingest_file(file_path)
                    entries.append(entry)
                    logger.debug("Ingested file %s", file_path.name)
                except CarpetDesignerError as e:
                    logger.warning("Skipping file %s: %s", file_path.name, e)

        if not entries:
            return [], DatasetStatus.INVALID_OR_MISSING

        # Check licensing restriction
        if self.license_type.lower() not in {"cc0", "public_domain", "open"}:
            status = DatasetStatus.RESTRICTED
        else:
            status = DatasetStatus.VERIFIED

        return entries, status
