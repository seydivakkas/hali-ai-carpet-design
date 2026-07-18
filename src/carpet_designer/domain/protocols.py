"""Domain protocols (abstract interfaces) for dependency inversion."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path

    from PIL import Image

    from carpet_designer.domain.schemas import (
        DesignAnalysis,
        GenerationResult,
        PromptRecipe,
        RetrievalResult,
    )


@runtime_checkable
class GenerationPipeline(Protocol):
    """Protocol for generation pipeline adapters."""

    def is_loaded(self) -> bool:
        """Check if the pipeline is loaded and ready."""
        ...

    def generate(self, recipe: PromptRecipe) -> tuple[Image.Image, GenerationResult]:
        """Generate an image from a prompt recipe.

        Args:
            recipe: The prompt recipe to generate from.

        Returns:
            Tuple of (PIL Image, GenerationResult metadata).
        """
        ...

    def unload(self) -> None:
        """Unload the pipeline and free resources."""
        ...


@runtime_checkable
class DesignAnalyzer(Protocol):
    """Protocol for design analysis."""

    def analyze(self, image: Image.Image, palette_id: str = "") -> DesignAnalysis:
        """Analyze a design image.

        Args:
            image: PIL Image to analyze.
            palette_id: Optional palette ID for matching.

        Returns:
            Complete design analysis result.
        """
        ...


@runtime_checkable
class DesignRetriever(Protocol):
    """Protocol for design retrieval/similarity search."""

    def search(self, image: Image.Image, top_k: int = 5) -> RetrievalResult:
        """Search for similar designs.

        Args:
            image: Query image.
            top_k: Number of results to return.

        Returns:
            Retrieval result with matches.
        """
        ...


@runtime_checkable
class ArtifactStore(Protocol):
    """Protocol for artifact persistence."""

    def save_image(self, image: Image.Image, path: Path) -> str:
        """Save an image and return its SHA-256 hash.

        Args:
            image: PIL Image to save.
            path: Target file path.

        Returns:
            SHA-256 hex digest of the saved file.
        """
        ...

    def save_json(self, data: dict, path: Path) -> str:  # type: ignore[type-arg]
        """Save JSON data and return its SHA-256 hash.

        Args:
            data: Dictionary to serialize.
            path: Target file path.

        Returns:
            SHA-256 hex digest of the saved file.
        """
        ...
