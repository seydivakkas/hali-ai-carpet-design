"""Unit tests for domain schemas."""

from __future__ import annotations

from carpet_designer.domain.enums import ErrorCode, LoRAStatus, Status
from carpet_designer.domain.schemas import (
    DatasetManifest,
    DesignAnalysis,
    DoctorCheck,
    DoctorReport,
    GenerationResult,
    LoRAManifest,
    PromptRecipe,
)


class TestPromptRecipe:
    """Tests for PromptRecipe schema."""

    def test_default_recipe(self) -> None:
        recipe = PromptRecipe()
        assert recipe.schema_version == "1.0.0"
        assert recipe.recipe_id.startswith("recipe_")
        assert recipe.width == 1024
        assert recipe.height == 1024
        assert recipe.steps == 30
        assert recipe.guidance_scale == 7.0
        assert recipe.seed == 42
        assert len(recipe.negative_constraints) > 0

    def test_recipe_serialization(self) -> None:
        recipe = PromptRecipe(
            style_family="anatolian_geometric",
            motifs=["ram_horn", "diamond"],
            composition="central_medallion",
        )
        json_str = recipe.model_dump_json()
        restored = PromptRecipe.model_validate_json(json_str)
        assert restored.style_family == "anatolian_geometric"
        assert restored.motifs == ["ram_horn", "diamond"]

    def test_recipe_with_lora(self) -> None:
        recipe = PromptRecipe(
            lora_ids=["lora_test_01"],
            lora_scales=[0.8],
        )
        assert recipe.lora_ids == ["lora_test_01"]
        assert recipe.lora_scales == [0.8]


class TestGenerationResult:
    """Tests for GenerationResult schema."""

    def test_default_result(self) -> None:
        result = GenerationResult()
        assert result.generation_id.startswith("gen_")
        assert result.status == Status.NOT_RUN
        assert result.timing.total_ms == 0.0

    def test_result_serialization(self) -> None:
        result = GenerationResult(
            model_id="test_model",
            seed=123,
            status=Status.PASS,
        )
        json_str = result.model_dump_json()
        restored = GenerationResult.model_validate_json(json_str)
        assert restored.model_id == "test_model"
        assert restored.status == Status.PASS


class TestDatasetManifest:
    """Tests for DatasetManifest schema."""

    def test_empty_manifest(self) -> None:
        manifest = DatasetManifest(dataset_id="test_ds")
        assert manifest.dataset_id == "test_ds"
        assert len(manifest.files) == 0

    def test_manifest_with_files(self) -> None:
        from carpet_designer.domain.schemas import DatasetFileEntry

        entry = DatasetFileEntry(
            relative_path="images/test.jpg",
            sha256="abc123",
            license="CC0",
            split="train",
        )
        manifest = DatasetManifest(
            dataset_id="test_ds",
            files=[entry],
            counts={"total": 1, "train": 1},
        )
        assert len(manifest.files) == 1
        assert manifest.counts["total"] == 1


class TestDesignAnalysis:
    """Tests for DesignAnalysis schema."""

    def test_default_analysis(self) -> None:
        analysis = DesignAnalysis()
        assert analysis.color.mean_delta_e == 0.0
        assert analysis.symmetry.horizontal_score == 0.0
        assert analysis.seam.overall_score == 0.0


class TestDoctorReport:
    """Tests for DoctorReport schema."""

    def test_report_creation(self) -> None:
        checks = [
            DoctorCheck(name="Python", status=Status.PASS, detail="3.11"),
            DoctorCheck(name="GPU", status=Status.HARDWARE_BLOCKED, detail="None"),
        ]
        report = DoctorReport(checks=checks, overall_status=Status.PASS_WITH_RESTRICTIONS)
        assert len(report.checks) == 2
        assert report.overall_status == Status.PASS_WITH_RESTRICTIONS


class TestLoRAManifest:
    """Tests for LoRAManifest schema."""

    def test_default_lora(self) -> None:
        lora = LoRAManifest()
        assert lora.lora_id.startswith("lora_")
        assert lora.status == LoRAStatus.DRAFT
        assert lora.rank == 16
        assert lora.alpha == 16


class TestEnums:
    """Tests for domain enums."""

    def test_status_values(self) -> None:
        assert Status.PASS.value == "PASS"
        assert Status.FAIL.value == "FAIL"
        assert Status.HARDWARE_BLOCKED.value == "HARDWARE_BLOCKED"

    def test_error_codes(self) -> None:
        assert ErrorCode.CD_CONFIG_INVALID.value == "CD_CONFIG_INVALID"
        assert ErrorCode.CD_GENERATION_OOM.value == "CD_GENERATION_OOM"

    def test_lora_status(self) -> None:
        assert LoRAStatus.DRAFT.value == "DRAFT"
        assert LoRAStatus.ACTIVE_DEMO.value == "ACTIVE_DEMO"
