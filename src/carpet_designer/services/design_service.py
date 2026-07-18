"""Application service orchestrating design generation, analysis and persistence."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
import yaml
from PIL import Image

from carpet_designer.analysis.color import extract_dominant_colors
from carpet_designer.analysis.geometry import (
    analyze_repeatability,
    analyze_seam_continuity,
    analyze_symmetry,
)
from carpet_designer.domain.enums import CompositeAdvisory, ManufacturingAdvisory, Status
from carpet_designer.domain.errors import GenerationFailedError
from carpet_designer.domain.schemas import (
    DesignAnalysis,
    DesignRunResult,
    LoRAManifest,
    PromptRecipe,
)
from carpet_designer.models.pipeline import GenerationPipeline
from carpet_designer.persistence.database import get_connection
from carpet_designer.persistence.migrations import run_migrations
from carpet_designer.persistence.repositories import (
    AnalysisRepository,
    GenerationRepository,
    RecipeRepository,
)
from carpet_designer.prompts.recipe import PromptBuilder
from carpet_designer.reporting.reports import ReportWriter
from carpet_designer.settings import Settings, get_settings


class DesignService:
    """Backend facade used by Streamlit and CLI entry points."""

    def __init__(
        self,
        settings: Settings | None = None,
        pipeline: GenerationPipeline | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.pipeline = pipeline or GenerationPipeline(self.settings)
        self._ensure_database()

    def _ensure_database(self) -> None:
        conn = get_connection(self.settings.resolved_db_path)
        try:
            run_migrations(conn)
        finally:
            conn.close()

    def catalog(self) -> dict[str, Any]:
        """Load UI taxonomy and palette catalogs from YAML config."""
        taxonomy_path = self.settings.resolved_configs_dir / "prompt_taxonomy.yaml"
        palette_path = self.settings.resolved_configs_dir / "palettes.yaml"
        taxonomy = yaml.safe_load(taxonomy_path.read_text(encoding="utf-8")) or {}
        palettes = yaml.safe_load(palette_path.read_text(encoding="utf-8")) or {}
        return {
            "taxonomy": taxonomy.get("prompt_taxonomy", {}),
            "palettes": palettes.get("palettes", {}),
        }

    def generate_design(self, recipe: PromptRecipe) -> DesignRunResult:
        """Run generation, analysis, persistence and reporting as one transaction-like flow."""
        if not recipe.model_id:
            recipe = recipe.model_copy(update={"model_id": "demo-procedural-v1"})
        palette = recipe.reference_palette or self._palette_colors(recipe.palette_id)
        generation = self.pipeline.generate(
            recipe,
            base_model_path=self._base_model_path(recipe.model_id),
            palette=palette,
            lora_paths=self._lora_paths(recipe.lora_ids),
        )
        if generation.status != Status.PASS or not generation.image_path:
            raise GenerationFailedError(
                "Tasarım üretilemedi",
                detail="; ".join(generation.warnings),
            )

        with Image.open(generation.image_path) as opened:
            image = opened.convert("RGB")
            analysis = self._analyze(image, generation.generation_id, recipe.palette_id, palette)

        builder = PromptBuilder(recipe)
        engine_mode = "procedural_demo" if generation.model_id == "demo-procedural-v1" else "sdxl"
        report_writer = ReportWriter(self.settings.resolved_artifacts_dir / "reports")
        json_path, html_path = report_writer.paths_for(generation.generation_id)
        run = DesignRunResult(
            recipe=recipe,
            positive_prompt=builder.build_positive_prompt(),
            negative_prompt=builder.build_negative_prompt(),
            generation=generation,
            analysis=analysis,
            engine_mode=engine_mode,
            json_report_path=str(json_path),
            html_report_path=str(html_path),
        )

        conn = get_connection(self.settings.resolved_db_path)
        try:
            RecipeRepository(conn).save(recipe)
            GenerationRepository(conn).save(generation)
            report_writer.write(run)
            AnalysisRepository(conn).save(
                analysis_id=f"ana_{uuid4().hex[:12]}",
                generation_id=generation.generation_id,
                palette_id=recipe.palette_id,
                mean_delta_e=analysis.color.mean_delta_e,
                symmetry_score=analysis.symmetry.central_alignment_score,
                seam_score=analysis.seam.overall_score,
                repeatability_score=analysis.repeatability.periodicity_score,
                result_json_path=str(json_path),
            )
        finally:
            conn.close()
        return run

    def generate_batch(self, recipe: PromptRecipe, count: int) -> list[DesignRunResult]:
        """Generate deterministic variants by incrementing the seed."""
        count = max(1, min(count, self.settings.max_batch_size))
        results: list[DesignRunResult] = []
        for index in range(count):
            variant = recipe.model_copy(
                update={
                    "recipe_id": f"recipe_{uuid4().hex[:12]}",
                    "seed": recipe.seed + index,
                }
            )
            results.append(self.generate_design(variant))
        return results

    def list_recent(self, limit: int = 12) -> list[dict[str, Any]]:
        """List recent generation records."""
        conn = get_connection(self.settings.resolved_db_path)
        try:
            return GenerationRepository(conn).list_recent(limit)
        finally:
            conn.close()

    def dashboard_stats(self) -> dict[str, float | int | str]:
        """Return operational metrics for the frontend dashboard."""
        conn = get_connection(self.settings.resolved_db_path)
        try:
            row = conn.execute(
                """
                SELECT COUNT(*) AS total,
                       SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) AS passed,
                       COALESCE(AVG(total_latency_ms), 0) AS avg_latency
                FROM generations
                """
            ).fetchone()
            analysis = conn.execute(
                """
                SELECT COALESCE(AVG(symmetry_score), 0) AS symmetry,
                       COALESCE(AVG(seam_score), 0) AS seam
                FROM analyses
                """
            ).fetchone()
            return {
                "total": int(row["total"] or 0),
                "passed": int(row["passed"] or 0),
                "avg_latency_ms": float(row["avg_latency"] or 0.0),
                "avg_symmetry": float(analysis["symmetry"] or 0.0),
                "avg_seam": float(analysis["seam"] or 0.0),
            }
        finally:
            conn.close()

    def list_loras(self) -> list[dict[str, Any]]:
        """List registered LoRA adapters."""
        conn = get_connection(self.settings.resolved_db_path)
        try:
            rows = conn.execute("SELECT * FROM lora_adapters ORDER BY lora_id").fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def register_lora(self, manifest: LoRAManifest) -> None:
        """Register a trained LoRA and its SDXL base model transactionally."""
        conn = get_connection(self.settings.resolved_db_path)
        try:
            conn.execute(
                """INSERT OR REPLACE INTO models
                   (model_id, repository_id, revision, license, local_path, artifact_sha256, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    "sdxl_base_v1",
                    "stabilityai/stable-diffusion-xl-base-1.0",
                    "main",
                    "openrail++",
                    str(
                        self.settings.resolved_artifacts_dir
                        / "models"
                        / "base"
                        / "sdxl-base-1.0"
                    ),
                    "",
                    "READY_ON_DEMAND",
                ),
            )
            conn.execute(
                """INSERT OR REPLACE INTO lora_adapters
                   (lora_id, adapter_name, base_model_id, training_run_id,
                    dataset_manifest_sha256, license_register_sha256, artifact_path,
                    artifact_sha256, rank, alpha, status, metrics_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    manifest.lora_id,
                    manifest.adapter_name,
                    "sdxl_base_v1",
                    manifest.training_run_id,
                    manifest.dataset_manifest_sha256,
                    manifest.license_register_sha256,
                    manifest.artifact_path,
                    manifest.artifact_sha256,
                    manifest.rank,
                    manifest.alpha,
                    manifest.status.value,
                    manifest.metrics_path,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def set_lora_status(self, lora_id: str, status: str) -> None:
        """Update LoRA lifecycle state after evaluation."""
        conn = get_connection(self.settings.resolved_db_path)
        try:
            conn.execute("UPDATE lora_adapters SET status = ? WHERE lora_id = ?", (status, lora_id))
            conn.commit()
        finally:
            conn.close()

    def _lora_paths(self, lora_ids: list[str]) -> dict[str, Path]:
        if not lora_ids:
            return {}
        conn = get_connection(self.settings.resolved_db_path)
        try:
            placeholders = ",".join("?" for _ in lora_ids)
            rows = conn.execute(
                f"SELECT lora_id, artifact_path FROM lora_adapters WHERE lora_id IN ({placeholders})",
                tuple(lora_ids),
            ).fetchall()
            return {str(row["lora_id"]): Path(str(row["artifact_path"])) for row in rows}
        finally:
            conn.close()

    def _base_model_path(self, model_id: str) -> Path | None:
        if not model_id or model_id == "demo-procedural-v1":
            return None
        conn = get_connection(self.settings.resolved_db_path)
        try:
            row = conn.execute(
                "SELECT local_path FROM models WHERE model_id = ?", (model_id,)
            ).fetchone()
            if row and row["local_path"]:
                path = Path(str(row["local_path"]))
                if path.is_dir():
                    return path
        finally:
            conn.close()
        local_sdxl = (
            self.settings.resolved_artifacts_dir / "models" / "base" / "sdxl-base-1.0"
        )
        return local_sdxl if model_id == "sdxl_base_v1" and local_sdxl.is_dir() else None

    def search_collection(
        self, query_image: Image.Image, top_k: int = 5
    ) -> list[dict[str, Any]]:
        """Search generated designs and restricted reference-catalog images."""
        query_vector = self._histogram(query_image)
        matches: list[dict[str, Any]] = []
        for item in self.list_recent(limit=100):
            path = str(item["image_path"])
            try:
                with Image.open(path) as candidate:
                    vector = self._histogram(candidate.convert("RGB"))
                score = float(np.dot(query_vector, vector))
                matches.append(
                    {
                        "generation_id": str(item["generation_id"]),
                        "image_path": path,
                        "score": max(0.0, min(score, 1.0)),
                        "source_type": "generated_design",
                    }
                )
            except OSError:
                continue

        manifest_path = (
            self.settings.resolved_data_dir
            / "external"
            / "restricted_catalog"
            / "manifest.json"
        )
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                image_dir = manifest_path.parent / "images"
                for item in manifest.get("entries", []):
                    image_file = str(item.get("image_file", ""))
                    if not image_file:
                        continue
                    reference_path = image_dir / image_file
                    if not reference_path.is_file():
                        continue
                    with Image.open(reference_path) as candidate:
                        vector = self._histogram(candidate.convert("RGB"))
                    score = float(np.dot(query_vector, vector))
                    title = str(item.get("title") or item.get("source_id") or image_file)
                    matches.append(
                        {
                            "generation_id": title,
                            "image_path": str(reference_path),
                            "score": max(0.0, min(score, 1.0)),
                            "source_type": "restricted_catalog_reference",
                            "source_id": str(item.get("source_id", "")),
                            "collection": str(item.get("collection", "")),
                            "source_url": str(item.get("source_url", "")),
                            "usage_scope": str(item.get("usage_scope", "")),
                            "training_use": str(item.get("training_use", "")),
                            "dataset_status": str(item.get("status", "")),
                        }
                    )
            except (json.JSONDecodeError, OSError, TypeError):
                pass
        matches.sort(key=lambda item: float(item["score"]), reverse=True)
        return matches[: max(1, top_k)]

    def _analyze(
        self,
        image: Image.Image,
        generation_id: str,
        palette_id: str,
        palette: list[str],
    ) -> DesignAnalysis:
        color = extract_dominant_colors(image)
        color.palette_id = palette_id
        distances = []
        covered = 0.0
        palette_rgb = [self._hex_to_rgb(item) for item in palette]
        for dominant in color.dominant_colors:
            nearest = min(math.dist(dominant.rgb, target) for target in palette_rgb) / math.sqrt(
                3 * 255**2
            )
            distances.append(nearest * dominant.proportion)
            if nearest <= 0.12:
                covered += dominant.proportion
        color.mean_delta_e = sum(distances) * 100
        color.coverage_ratio = min(1.0, covered)
        color.out_of_palette_ratio = max(0.0, 1.0 - color.coverage_ratio)
        return DesignAnalysis(
            generation_id=generation_id,
            color=color,
            symmetry=analyze_symmetry(image),
            seam=analyze_seam_continuity(image),
            repeatability=analyze_repeatability(image),
            advisory=CompositeAdvisory.DESIGN_ANALYSIS_ONLY,
            manufacturing=ManufacturingAdvisory.DIGITAL_DESIGN_ONLY,
        )

    def _palette_colors(self, palette_id: str) -> list[str]:
        palettes = self.catalog()["palettes"]
        entry = palettes.get(palette_id) or palettes.get("classic_red_navy_v1") or {}
        return list(entry.get("colors", []))

    def _histogram(self, image: Image.Image) -> np.ndarray:
        resized = np.asarray(image.convert("RGB").resize((96, 96)), dtype=np.uint8)
        histogram, _ = np.histogramdd(
            resized.reshape(-1, 3),
            bins=(8, 8, 8),
            range=((0, 256), (0, 256), (0, 256)),
        )
        vector = histogram.astype(np.float32).reshape(-1)
        norm = np.linalg.norm(vector)
        return vector / norm if norm else vector

    def _hex_to_rgb(self, value: str) -> tuple[int, int, int]:
        normalized = value.lstrip("#")
        return (
            int(normalized[0:2], 16),
            int(normalized[2:4], 16),
            int(normalized[4:6], 16),
        )

    def export_recent_json(self, limit: int = 50) -> str:
        """Return recent generation metadata as JSON for diagnostics."""
        return json.dumps(self.list_recent(limit), indent=2, ensure_ascii=False)
