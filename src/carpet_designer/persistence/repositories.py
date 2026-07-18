"""SQLite CRUD repositories for domain entities."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from carpet_designer.domain.schemas import EvaluationResult, GenerationResult, PromptRecipe
from carpet_designer.logging_config import get_logger

if TYPE_CHECKING:
    import sqlite3

logger = get_logger("persistence.repositories")


def _utcnow_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


class RecipeRepository:
    """CRUD operations for prompt recipes."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def save(self, recipe: PromptRecipe) -> str:
        """Save a prompt recipe.

        Args:
            recipe: The prompt recipe to save.

        Returns:
            The recipe_id of the saved recipe.
        """
        recipe_json = recipe.model_dump_json()
        self._conn.execute(
            """INSERT OR REPLACE INTO recipes
               (recipe_id, created_at, recipe_json, recipe_sha256)
               VALUES (?, ?, ?, ?)""",
            (recipe.recipe_id, _utcnow_iso(), recipe_json, _sha256(recipe_json)),
        )
        self._conn.commit()
        return recipe.recipe_id

    def get(self, recipe_id: str) -> PromptRecipe | None:
        """Retrieve a recipe by ID.

        Args:
            recipe_id: The recipe identifier.

        Returns:
            PromptRecipe if found, None otherwise.
        """
        row = self._conn.execute(
            "SELECT recipe_json FROM recipes WHERE recipe_id = ?", (recipe_id,)
        ).fetchone()
        if row is None:
            return None
        return PromptRecipe.model_validate_json(row["recipe_json"])

    def list_all(self) -> list[dict[str, Any]]:
        """List all recipes with metadata.

        Returns:
            List of recipe metadata dictionaries.
        """
        rows = self._conn.execute(
            "SELECT recipe_id, created_at, recipe_sha256 FROM recipes ORDER BY created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]


class GenerationRepository:
    """CRUD operations for generation results."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def save(self, result: GenerationResult) -> str:
        """Save a generation result.

        Args:
            result: The generation result to save.

        Returns:
            The generation_id of the saved result.
        """
        self._conn.execute(
            """INSERT OR REPLACE INTO generations
               (generation_id, created_at, recipe_id, model_id, lora_ids_json,
                seed, scheduler, steps, guidance_scale, width, height,
                image_sha256, image_path, total_latency_ms, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                result.generation_id,
                result.created_at.isoformat(),
                result.recipe_id,
                result.model_id,
                json.dumps(result.lora_adapters),
                result.seed,
                result.scheduler,
                result.steps,
                result.guidance_scale,
                result.width,
                result.height,
                result.image_sha256,
                result.image_path,
                result.timing.total_ms,
                result.status.value,
            ),
        )
        self._conn.commit()
        return result.generation_id

    def get(self, generation_id: str) -> dict[str, Any] | None:
        """Retrieve a generation by ID.

        Args:
            generation_id: The generation identifier.

        Returns:
            Dict of generation data if found, None otherwise.
        """
        row = self._conn.execute(
            "SELECT * FROM generations WHERE generation_id = ?", (generation_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        """List recent generations.

        Args:
            limit: Maximum number of results.

        Returns:
            List of generation metadata dictionaries.
        """
        rows = self._conn.execute(
            "SELECT * FROM generations ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]


class AnalysisRepository:
    """CRUD operations for design analyses."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def save(
        self,
        analysis_id: str,
        generation_id: str,
        palette_id: str = "",
        mean_delta_e: float = 0.0,
        symmetry_score: float = 0.0,
        seam_score: float = 0.0,
        repeatability_score: float = 0.0,
        nearest_match_id: str = "",
        nearest_similarity: float = 0.0,
        result_json_path: str = "",
    ) -> str:
        """Save an analysis result.

        Args:
            analysis_id: Unique analysis identifier.
            generation_id: Related generation ID.
            palette_id: Palette used for matching.
            mean_delta_e: Mean Delta E value.
            symmetry_score: Symmetry measurement.
            seam_score: Seam quality score.
            repeatability_score: Repeatability score.
            nearest_match_id: ID of nearest match in collection.
            nearest_similarity: Similarity to nearest match.
            result_json_path: Path to full JSON result.

        Returns:
            The analysis_id.
        """
        self._conn.execute(
            """INSERT OR REPLACE INTO analyses
               (analysis_id, generation_id, palette_id, mean_delta_e,
                symmetry_score, seam_score, repeatability_score,
                nearest_match_id, nearest_similarity, result_json_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                analysis_id,
                generation_id,
                palette_id,
                mean_delta_e,
                symmetry_score,
                seam_score,
                repeatability_score,
                nearest_match_id,
                nearest_similarity,
                result_json_path,
            ),
        )
        self._conn.commit()
        return analysis_id

    def get_by_generation(self, generation_id: str) -> dict[str, Any] | None:
        """Get analysis for a generation.

        Args:
            generation_id: The generation identifier.

        Returns:
            Dict of analysis data if found, None otherwise.
        """
        row = self._conn.execute(
            "SELECT * FROM analyses WHERE generation_id = ?", (generation_id,)
        ).fetchone()
        return dict(row) if row else None


class EvaluationRepository:
    """Persistence operations for evaluation results."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def save(self, result: EvaluationResult) -> None:
        self.conn.execute(
            """
            INSERT INTO analyses (analysis_id, generation_id, mean_delta_e, symmetry_score, seam_score, result_json_path)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(analysis_id) DO UPDATE SET result_json_path=excluded.result_json_path
            """,
            (
                result.eval_id,
                "mock_gen",
                0.0,
                result.metrics.get("symmetry_avg") or 0.0,
                result.metrics.get("seam_continuity_avg") or 0.0,
                json.dumps(result.metrics),
            ),
        )
        self.conn.commit()
