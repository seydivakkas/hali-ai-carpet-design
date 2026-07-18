"""Domain data schemas — Pydantic models for all data contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from carpet_designer.domain.enums import (
    CaptionConfidence,
    CollectionItemStatus,
    CompositeAdvisory,
    DatasetStatus,
    DuplicateClass,
    LoRAStatus,
    ManufacturingAdvisory,
    ModelStatus,
    Status,
)


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _gen_id(prefix: str = "") -> str:
    return f"{prefix}{uuid4().hex[:12]}"


# --- Prompt Recipe ---


class PromptRecipe(BaseModel):
    """Prompt recipe schema per spec Section 13.3."""

    schema_version: str = "1.0.0"
    recipe_id: str = Field(default_factory=lambda: _gen_id("recipe_"))
    style_family: str = ""
    motifs: list[str] = Field(default_factory=list)
    composition: str = ""
    border: str = ""
    symmetry: str = ""
    palette_id: str = ""
    free_text: str = ""
    negative_constraints: list[str] = Field(
        default_factory=lambda: [
            "text",
            "watermark",
            "logo",
            "signature",
            "frame",
            "cut-off border",
            "photographic room scene",
            "folded rug",
            "perspective distortion",
            "low detail",
            "severe blur",
            "malformed repeated motif",
        ]
    )
    render_intent: str = "flat_design"
    seed: int = 42
    width: int = 1024
    height: int = 1024
    steps: int = 30
    guidance_scale: float = 7.0
    scheduler: str = "configured"
    model_id: str = ""
    lora_ids: list[str] = Field(default_factory=list)
    lora_scales: list[float] = Field(default_factory=list)
    reference_image_path: str = ""
    reference_image_sha256: str = ""
    reference_palette: list[str] = Field(default_factory=list)
    variation_strength: float = Field(default=0.45, ge=0.05, le=0.95)
    variation_targets: list[str] = Field(default_factory=list)


# --- Generation Result ---


class TimingInfo(BaseModel):
    """Timing breakdown for a generation."""

    load_ms: float = 0.0
    generation_ms: float = 0.0
    analysis_ms: float = 0.0
    total_ms: float = 0.0


class GenerationResult(BaseModel):
    """Generation result schema per spec Section 14.6."""

    generation_id: str = Field(default_factory=lambda: _gen_id("gen_"))
    created_at: datetime = Field(default_factory=_utcnow)
    recipe_id: str = ""
    model_id: str = ""
    lora_adapters: list[str] = Field(default_factory=list)
    seed: int = 42
    scheduler: str = ""
    steps: int = 30
    guidance_scale: float = 7.0
    width: int = 1024
    height: int = 1024
    device: str = ""
    dtype: str = ""
    timing: TimingInfo = Field(default_factory=TimingInfo)
    image_sha256: str = ""
    image_path: str = ""
    status: Status = Status.NOT_RUN
    warnings: list[str] = Field(default_factory=list)


# --- Color Analysis ---


class DominantColor(BaseModel):
    """A dominant color extracted from an image."""

    hex: str = ""
    lab: list[float] = Field(default_factory=list)
    rgb: list[int] = Field(default_factory=list)
    proportion: float = 0.0


class ColorAnalysisResult(BaseModel):
    """Color analysis result per spec Section 16.5."""

    dominant_colors: list[DominantColor] = Field(default_factory=list)
    palette_id: str = ""
    mean_delta_e: float = 0.0
    coverage_ratio: float = 0.0
    out_of_palette_ratio: float = 0.0
    status: str = "DESIGN_REFERENCE_ONLY"


# --- Geometry Analysis ---


class SymmetryResult(BaseModel):
    """Symmetry analysis result per spec Section 17.1."""

    horizontal_score: float = 0.0
    vertical_score: float = 0.0
    rotational_180_score: float = 0.0
    central_alignment_score: float = 0.0


class SeamResult(BaseModel):
    """Seam/tileability analysis result per spec Section 17.2."""

    left_right_difference: float = 0.0
    top_bottom_difference: float = 0.0
    gradient_continuity: float = 0.0
    frequency_discontinuity: float = 0.0
    overall_score: float = 0.0


class RepeatabilityResult(BaseModel):
    """Repeatability analysis result per spec Section 17.3."""

    autocorrelation_peak_count: int = 0
    periodicity_score: float = 0.0
    spacing_consistency: float = 0.0
    dominant_period_px: int = 0


# --- Composite Analysis ---


class DesignAnalysis(BaseModel):
    """Complete design analysis result."""

    generation_id: str = ""
    color: ColorAnalysisResult = Field(default_factory=ColorAnalysisResult)
    symmetry: SymmetryResult = Field(default_factory=SymmetryResult)
    seam: SeamResult = Field(default_factory=SeamResult)
    repeatability: RepeatabilityResult = Field(default_factory=RepeatabilityResult)
    motif_density: float = 0.0
    advisory: CompositeAdvisory = CompositeAdvisory.DESIGN_ANALYSIS_ONLY
    manufacturing: ManufacturingAdvisory = ManufacturingAdvisory.NOT_EVALUATED


class DesignRunResult(BaseModel):
    """Complete output contract returned by the application service."""

    recipe: PromptRecipe
    positive_prompt: str = ""
    negative_prompt: str = ""
    generation: GenerationResult
    analysis: DesignAnalysis
    engine_mode: str = "demo"
    json_report_path: str = ""
    html_report_path: str = ""


# --- Retrieval ---


class RetrievalMatch(BaseModel):
    """A single retrieval match."""

    item_id: str = ""
    similarity: float = 0.0
    duplicate_class: DuplicateClass = DuplicateClass.NO_CLOSE_MATCH_FOUND
    image_path: str = ""
    signals: dict[str, float] = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    """Retrieval search result."""

    query_sha256: str = ""
    matches: list[RetrievalMatch] = Field(default_factory=list)
    index_version: str = ""
    disclaimer: str = "Retrieval results do not establish legal originality or copyright status."


# --- Dataset Manifest ---


class DatasetFileEntry(BaseModel):
    """Single file entry in a dataset manifest per spec Section 11.5."""

    relative_path: str = ""
    sha256: str = ""
    source_object_id: str = ""
    source_url: str = ""
    license: str = ""
    width: int = 0
    height: int = 0
    caption_path: str = ""
    style_labels: list[str] = Field(default_factory=list)
    palette_labels: list[str] = Field(default_factory=list)
    split: str = ""


class DatasetManifest(BaseModel):
    """Dataset manifest per spec Section 11.5."""

    schema_version: str = "1.0.0"
    dataset_id: str = ""
    source: dict[str, str] = Field(default_factory=dict)
    counts: dict[str, int] = Field(default_factory=dict)
    files: list[DatasetFileEntry] = Field(default_factory=list)
    manifest_sha256: str = ""


# --- Caption ---


class CaptionSchema(BaseModel):
    """Caption schema per spec Section 12.4."""

    subject: str = "carpet/rug pattern"
    culture_or_style: list[str] = Field(default_factory=list)
    motifs: list[str] = Field(default_factory=list)
    composition: list[str] = Field(default_factory=list)
    palette: list[str] = Field(default_factory=list)
    geometry: list[str] = Field(default_factory=list)
    texture: list[str] = Field(default_factory=list)
    period: str | None = None
    source_terms: list[str] = Field(default_factory=list)
    confidence: CaptionConfidence = CaptionConfidence.AUTO_SUGGESTED
    free_text: str = ""


# --- Model Registry ---


class BaseModelManifest(BaseModel):
    """Base model manifest per spec Section 21.1."""

    model_id: str = ""
    repository_id: str = ""
    revision: str = ""
    license: str = ""
    local_path: str = ""
    artifact_sha256: str = ""
    status: ModelStatus = ModelStatus.NOT_FOUND


class LoRAManifest(BaseModel):
    """LoRA adapter manifest per spec Section 21.2."""

    lora_id: str = Field(default_factory=lambda: _gen_id("lora_"))
    adapter_name: str = "carpet_domain_v1"
    base_model_id: str = ""
    training_run_id: str = ""
    dataset_manifest_sha256: str = ""
    license_register_sha256: str = ""
    artifact_path: str = ""
    artifact_sha256: str = ""
    rank: int = 16
    alpha: int = 16
    status: LoRAStatus = LoRAStatus.DRAFT
    metrics_path: str = ""


# --- System Doctor ---


class DoctorCheck(BaseModel):
    """A single system doctor check result."""

    name: str
    status: Status
    detail: str = ""
    value: Any = None


class DoctorReport(BaseModel):
    """Full system doctor report per spec Section 9.4."""

    timestamp: datetime = Field(default_factory=_utcnow)
    checks: list[DoctorCheck] = Field(default_factory=list)
    overall_status: Status = Status.NOT_RUN


# --- Human Review ---


class HumanReview(BaseModel):
    """Human review entry per spec Section 20.3."""

    review_id: str = Field(default_factory=lambda: _gen_id("rev_"))
    generation_id: str = ""
    reviewer: str = ""
    rubric: dict[str, int] = Field(default_factory=dict)
    overall_preference: int = 0
    comment: str = ""
    created_at: datetime = Field(default_factory=_utcnow)


# --- Collection ---


class CollectionItem(BaseModel):
    """Collection item entry."""

    collection_item_id: str = Field(default_factory=lambda: _gen_id("col_"))
    generation_id: str | None = None
    source_type: str = ""
    source_sha256: str = ""
    title: str = ""
    status: CollectionItemStatus = CollectionItemStatus.CANDIDATE
    reviewer: str = ""
    created_at: datetime = Field(default_factory=_utcnow)


# --- Dataset License Register ---


class DatasetLicenseEntry(BaseModel):
    """Dataset license register entry per spec Section 11.4."""

    dataset_id: str = ""
    source_name: str = ""
    source_url: str = ""
    retrieved_at: str = ""
    license: str = ""
    training_use: str = "unclear"
    commercial_use: str = "unclear"
    attribution_required: str = "yes"
    permission_ref: str = ""
    archive_sha256: str = ""
    manifest_sha256: str = ""
    image_count: int = 0
    caption_count: int = 0
    excluded_count: int = 0
    restrictions: str = ""
    status: DatasetStatus = DatasetStatus.PENDING


class EvaluationResult(BaseModel):
    eval_id: str
    metrics: dict[str, float | None]
    details: dict[str, Any] = Field(default_factory=dict)
    status: str
