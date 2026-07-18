"""Tests for governed multi-source training data preparation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from PIL import Image

from carpet_designer.data.training_builder import TrainingDatasetBuilder

if TYPE_CHECKING:
    from pathlib import Path


def _write_image(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (40, 60), color).save(path)


def test_builder_merges_approved_sources_and_excludes_augmented(tmp_path: Path) -> None:
    restricted_catalog = tmp_path / "restricted_catalog"
    _write_image(restricted_catalog / "images" / "m1.jpeg", (120, 40, 30))
    (restricted_catalog / "manifest.json").write_text(
        json.dumps(
            {
                "training_use": "approved",
                "permission_ref": "APPROVAL-1",
                "entries": [
                    {
                        "image_file": "m1.jpeg",
                        "source_id": "M1",
                        "source_url": "https://example.test/m1",
                        "title": "M1",
                        "collection": "Pilot",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    kaggle = tmp_path / "kaggle"
    _write_image(kaggle / "001.jpg", (20, 60, 100))
    _write_image(kaggle / "001 g.jpg", (80, 80, 80))
    met = tmp_path / "met"
    _write_image(met / "images" / "rug.jpg", (30, 90, 40))
    _write_image(met / "images" / "painting.jpg", (90, 30, 40))
    (met / "manifest.json").write_text(
        json.dumps(
            [
                {"image_file": "rug.jpg", "source_id": "R1", "title": "Historic Carpet"},
                {"image_file": "painting.jpg", "source_id": "P1", "title": "Painting"},
            ]
        ),
        encoding="utf-8",
    )

    output = tmp_path / "output"
    stale_image = output / "images" / "stale_generated.jpg"
    _write_image(stale_image, (1, 2, 3))
    manifest = TrainingDatasetBuilder(
        restricted_catalog_dir=restricted_catalog,
        kaggle_dir=kaggle,
        met_dir=met,
        canvas_size=64,
    ).build(output)

    assert manifest["counts"]["total"] == 3
    assert manifest["counts"]["restricted_catalog"] == 1
    assert manifest["counts"]["kaggle_safavid"] == 1
    assert manifest["counts"]["met"] == 1
    assert manifest["counts"]["stale_images_removed"] == 1
    assert not stale_image.exists()
    assert len(list((output / "images").glob("*.jpg"))) == 3
    assert "001 g.jpg" not in (output / "metadata.jsonl").read_text(encoding="utf-8")
    assert '"file_name": "images/' in (output / "metadata.jsonl").read_text(
        encoding="utf-8"
    )


def test_builder_rejects_restricted_catalog_without_permission(tmp_path: Path) -> None:
    restricted_catalog = tmp_path / "restricted_catalog"
    restricted_catalog.mkdir()
    (restricted_catalog / "manifest.json").write_text(
        json.dumps({"training_use": "blocked_pending_written_permission", "entries": []}),
        encoding="utf-8",
    )

    builder = TrainingDatasetBuilder(
        restricted_catalog_dir=restricted_catalog,
        kaggle_dir=tmp_path / "kaggle",
        met_dir=tmp_path / "met",
    )
    with pytest.raises(PermissionError, match="permission"):
        builder.build(tmp_path / "output")
