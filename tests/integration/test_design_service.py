"""End-to-end tests for the application service backend."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from PIL import Image

from carpet_designer.domain.schemas import PromptRecipe
from carpet_designer.services.design_service import DesignService
from carpet_designer.settings import Settings


def test_generate_analyze_persist_and_report(tmp_path: Path) -> None:
    project_root = Path(__file__).parents[2]
    settings = Settings(
        project_root=project_root,
        artifacts_dir=tmp_path / "artifacts",
        data_dir=tmp_path / "data",
        configs_dir=project_root / "configs",
        db_path=tmp_path / "artifacts" / "designs.db",
        device="cpu",
        generation_mode="demo",
    )
    service = DesignService(settings=settings)
    recipe = PromptRecipe(
        motifs=["diamond", "star"],
        composition="all_over_repeat",
        border="multi_band",
        palette_id="earth_v1",
        seed=7,
        width=256,
        height=256,
        model_id="demo-procedural-v1",
    )

    run = service.generate_design(recipe)

    assert Path(run.generation.image_path).is_file()
    assert Path(run.json_report_path).is_file()
    assert Path(run.html_report_path).is_file()
    assert run.analysis.color.dominant_colors
    assert 0.0 <= run.analysis.symmetry.central_alignment_score <= 1.0
    assert 0.0 <= run.analysis.seam.overall_score <= 1.0
    assert service.dashboard_stats()["total"] == 1

    with sqlite3.connect(settings.resolved_db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM recipes").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM generations").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0] == 1

    with Image.open(run.generation.image_path) as image:
        matches = service.search_collection(image, top_k=1)
    assert matches[0]["generation_id"] == run.generation.generation_id
    assert float(matches[0]["score"]) > 0.99


def test_search_includes_restricted_catalog_reference(tmp_path: Path) -> None:
    project_root = Path(__file__).parents[2]
    settings = Settings(
        project_root=project_root,
        artifacts_dir=tmp_path / "artifacts",
        data_dir=tmp_path / "data",
        configs_dir=project_root / "configs",
        db_path=tmp_path / "artifacts" / "designs.db",
        device="cpu",
        generation_mode="demo",
    )
    image_dir = settings.resolved_data_dir / "external" / "restricted_catalog" / "images"
    image_dir.mkdir(parents=True)
    reference_path = image_dir / "catalog_test.jpeg"
    Image.new("RGB", (64, 64), (120, 50, 30)).save(reference_path)
    manifest_path = image_dir.parent / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "image_file": reference_path.name,
                        "source_id": "TEST-001",
                        "title": "TEST 001",
                        "collection": "Pilot",
                        "source_url": "https://catalog.example/test-001",
                        "usage_scope": "internal_design_reference_only",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    service = DesignService(settings=settings)
    matches = service.search_collection(Image.new("RGB", (64, 64), (120, 50, 30)), top_k=1)

    assert matches[0]["source_type"] == "restricted_catalog_reference"
    assert matches[0]["source_id"] == "TEST-001"
    assert float(matches[0]["score"]) > 0.99
