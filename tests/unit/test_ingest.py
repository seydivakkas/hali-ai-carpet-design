"""Unit tests for dataset ingestion."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image

from carpet_designer.data.ingest import IngestionPipeline

if TYPE_CHECKING:
    from pathlib import Path


def test_ingest_file_copies_image_and_caption(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()

    image_path = source_dir / "sample.png"
    Image.new("RGB", (8, 6), color="red").save(image_path)
    caption_path = source_dir / "sample.txt"
    caption_path.write_text("geometric red carpet\n", encoding="utf-8")

    pipeline = IngestionPipeline(source_dir, target_dir, license_type="cc0")
    entry = pipeline.ingest_file(image_path)

    assert entry.relative_path == "sample.png"
    assert entry.caption_path == "sample.txt"
    assert (target_dir / entry.relative_path).is_file()
    assert (target_dir / entry.caption_path).read_text(encoding="utf-8") == (
        "geometric red carpet\n"
    )
    assert len(entry.sha256) == 64
