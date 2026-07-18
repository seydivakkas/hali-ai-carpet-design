"""Unit tests for persistence layer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from carpet_designer.domain.enums import Status
from carpet_designer.domain.schemas import GenerationResult, PromptRecipe, TimingInfo
from carpet_designer.persistence.repositories import GenerationRepository, RecipeRepository

if TYPE_CHECKING:
    import sqlite3


class TestRecipeRepository:
    """Tests for RecipeRepository."""

    def test_save_and_get(self, db_connection: sqlite3.Connection) -> None:
        repo = RecipeRepository(db_connection)
        recipe = PromptRecipe(
            style_family="anatolian_geometric",
            motifs=["ram_horn"],
        )
        saved_id = repo.save(recipe)
        assert saved_id == recipe.recipe_id

        loaded = repo.get(recipe.recipe_id)
        assert loaded is not None
        assert loaded.style_family == "anatolian_geometric"

    def test_get_nonexistent(self, db_connection: sqlite3.Connection) -> None:
        repo = RecipeRepository(db_connection)
        result = repo.get("nonexistent_id")
        assert result is None

    def test_list_all(self, db_connection: sqlite3.Connection) -> None:
        repo = RecipeRepository(db_connection)
        repo.save(PromptRecipe(style_family="test1"))
        repo.save(PromptRecipe(style_family="test2"))
        items = repo.list_all()
        assert len(items) == 2


class TestGenerationRepository:
    """Tests for GenerationRepository."""

    def test_save_and_get(self, db_connection: sqlite3.Connection) -> None:
        repo = GenerationRepository(db_connection)
        # Need recipe first
        recipe_repo = RecipeRepository(db_connection)
        recipe = PromptRecipe()
        recipe_repo.save(recipe)

        result = GenerationResult(
            recipe_id=recipe.recipe_id,
            model_id="test_model",
            seed=42,
            scheduler="euler",
            status=Status.PASS,
            image_sha256="abc123",
            image_path="/tmp/test.png",
            timing=TimingInfo(total_ms=1000.0),
        )
        saved_id = repo.save(result)
        assert saved_id == result.generation_id

        loaded = repo.get(result.generation_id)
        assert loaded is not None
        assert loaded["model_id"] == "test_model"
        assert loaded["status"] == "PASS"

    def test_list_recent(self, db_connection: sqlite3.Connection) -> None:
        repo = GenerationRepository(db_connection)
        recipe_repo = RecipeRepository(db_connection)
        recipe = PromptRecipe()
        recipe_repo.save(recipe)

        for i in range(3):
            result = GenerationResult(
                recipe_id=recipe.recipe_id,
                model_id=f"model_{i}",
                seed=i,
                scheduler="euler",
                status=Status.PASS,
                image_sha256=f"hash_{i}",
                image_path=f"/tmp/test_{i}.png",
            )
            repo.save(result)

        recent = repo.list_recent(limit=2)
        assert len(recent) == 2
