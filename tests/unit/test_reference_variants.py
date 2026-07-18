"""Reference-image variant generation tests."""

from __future__ import annotations

import hashlib
from io import BytesIO
from typing import TYPE_CHECKING

import pytest
from PIL import Image, ImageChops, ImageOps

from carpet_designer.data.reference_image import (
    build_reference_guidance,
    fit_generation_size,
    store_reference_image,
)
from carpet_designer.domain.enums import Status
from carpet_designer.domain.schemas import PromptRecipe
from carpet_designer.models.pipeline import GenerationPipeline
from carpet_designer.models.procedural import ProceduralCarpetGenerator
from carpet_designer.settings import Settings

if TYPE_CHECKING:
    from pathlib import Path


def _png_bytes(size: tuple[int, int] = (120, 80)) -> bytes:
    image = Image.new("RGB", size, (120, 30, 40))
    image.paste((20, 40, 120), (size[0] // 2, 0, size[0], size[1]))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


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


def test_reference_upload_is_content_addressed_and_palette_is_extracted(tmp_path: Path) -> None:
    payload = _png_bytes()

    stored = store_reference_image(payload, tmp_path / "references")

    assert stored.path.is_file()
    assert stored.sha256 == hashlib.sha256(payload).hexdigest()
    assert (stored.width, stored.height) == (120, 80)
    assert len(stored.palette) >= 2
    assert all(color.startswith("#") and len(color) == 7 for color in stored.palette)


def test_reference_upload_rejects_tiny_image(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="64×64"):
        store_reference_image(_png_bytes((32, 32)), tmp_path / "references")


def test_generation_size_preserves_reference_aspect_ratio() -> None:
    assert fit_generation_size(1200, 800, 768, preserve_aspect_ratio=True) == (768, 512)
    assert fit_generation_size(1200, 800, 768, preserve_aspect_ratio=False) == (768, 768)


def test_reference_guidance_names_changed_and_preserved_fields() -> None:
    guidance = build_reference_guidance(["palette", "motifs"])

    assert "change only color palette, motifs" in guidance
    assert "preserve the source style family, composition" in guidance


def test_demo_reference_variation_is_deterministic(tmp_path: Path) -> None:
    reference = tmp_path / "reference.png"
    Image.new("RGB", (256, 256), (220, 210, 190)).save(reference)
    recipe = PromptRecipe(
        motifs=["diamond", "star"],
        composition="central_medallion",
        border="multi_band",
        symmetry="quadrilateral",
        palette_id="classic_red_navy_v1",
        seed=71,
        width=256,
        height=256,
        model_id="demo-procedural-v1",
        reference_image_path=str(reference),
        variation_strength=0.4,
        variation_targets=["motifs", "border", "symmetry"],
    )
    pipeline = GenerationPipeline(_settings(tmp_path))

    first = pipeline.generate(recipe)
    second = pipeline.generate(recipe)

    assert first.status == Status.PASS
    assert first.image_sha256 == second.image_sha256
    assert any(warning.startswith("REFERENCE_VARIATION") for warning in first.warnings)
    with Image.open(first.image_path) as generated:
        assert generated.size == (256, 256)
        assert ImageChops.difference(generated.convert("RGB"), Image.open(reference)).getbbox()


def test_procedural_bilateral_symmetry_is_exact() -> None:
    recipe = PromptRecipe(
        motifs=["diamond", "hook"],
        composition="all_over_repeat",
        border="multi_band",
        symmetry="bilateral",
        seed=9,
        width=256,
        height=256,
    )

    image = ProceduralCarpetGenerator().generate(recipe)
    left = image.crop((0, 0, 128, 256))
    right = image.crop((128, 0, 256, 256))

    assert ImageChops.difference(ImageOps.mirror(left), right).getbbox() is None
