"""Tests for the deterministic CPU demo generation engine."""

from __future__ import annotations

from typing import TYPE_CHECKING

from carpet_designer.domain.enums import Status
from carpet_designer.domain.schemas import PromptRecipe
from carpet_designer.models.pipeline import GenerationPipeline
from carpet_designer.settings import Settings

if TYPE_CHECKING:
    from pathlib import Path


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        project_root=tmp_path,
        artifacts_dir=tmp_path / "artifacts",
        data_dir=tmp_path / "data",
        configs_dir=tmp_path / "configs",
        db_path=tmp_path / "artifacts" / "test.db",
        device="cpu",
        generation_mode="demo",
    )


def _recipe(seed: int) -> PromptRecipe:
    return PromptRecipe(
        style_family="anatolian_geometric",
        motifs=["diamond", "star", "ram_horn"],
        composition="central_medallion",
        border="multi_band",
        symmetry="quadrilateral",
        palette_id="classic_red_navy_v1",
        seed=seed,
        width=256,
        height=256,
        model_id="demo-procedural-v1",
    )


def test_demo_generation_is_deterministic(tmp_path: Path) -> None:
    pipeline = GenerationPipeline(_settings(tmp_path))

    first = pipeline.generate(_recipe(42))
    second = pipeline.generate(_recipe(42))

    assert first.status == Status.PASS
    assert second.status == Status.PASS
    assert first.image_sha256 == second.image_sha256
    assert first.model_id == "demo-procedural-v1"
    assert first.warnings and first.warnings[0].startswith("DEMO_ONLY")


def test_seed_changes_demo_output(tmp_path: Path) -> None:
    pipeline = GenerationPipeline(_settings(tmp_path))

    first = pipeline.generate(_recipe(10))
    second = pipeline.generate(_recipe(11))

    assert first.image_sha256 != second.image_sha256
