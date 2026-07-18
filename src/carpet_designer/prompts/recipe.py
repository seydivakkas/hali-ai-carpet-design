"""Prompt recipe builder per spec Section 13."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from carpet_designer.domain.schemas import PromptRecipe


class PromptBuilder:
    """Builds a flat text prompt string from a structured PromptRecipe."""

    def __init__(self, recipe: PromptRecipe) -> None:
        """Initialize the builder.

        Args:
            recipe: The structured recipe to build a prompt from.
        """
        self.recipe = recipe

    def build_positive_prompt(self) -> str:
        """Assemble the positive prompt.

        Follows the strict compositional order defined in spec Section 13.

        Returns:
            The assembled positive prompt string.
        """
        parts: list[str] = []

        # 1. Base intent
        if self.recipe.render_intent == "flat_design":
            parts.append("A top-down, completely flat 2D carpet design pattern")
        elif self.recipe.render_intent == "room_mockup":
            parts.append("A realistic carpet placed in a well-lit living room")
        else:
            parts.append("A carpet design")

        # 2. Style family
        if self.recipe.style_family:
            parts.append(f"in {self.recipe.style_family.replace('_', ' ')} style")

        # 3. Composition
        if self.recipe.composition:
            parts.append(f"featuring a {self.recipe.composition.replace('_', ' ')}")

        # 4. Motifs
        if self.recipe.motifs:
            motifs_str = ", ".join(m.replace("_", " ") for m in self.recipe.motifs)
            parts.append(f"with {motifs_str} motifs")

        # 5. Border
        if self.recipe.border:
            parts.append(f"enclosed by a {self.recipe.border.replace('_', ' ')}")

        # 6. Symmetry
        if self.recipe.symmetry:
            parts.append(f"exhibiting {self.recipe.symmetry.replace('_', ' ')} symmetry")

        # 7. Palette (if described by id)
        if self.recipe.palette_id:
            parts.append(f"colored in {self.recipe.palette_id.replace('_', ' ')} palette tones")

        # 8. Free text additions
        if self.recipe.free_text:
            parts.append(self.recipe.free_text)

        return ", ".join(parts) + ", highly detailed, high quality, 8k resolution"

    def build_negative_prompt(self) -> str:
        """Assemble the negative prompt.

        Returns:
            The assembled negative prompt string.
        """
        constraints = self.recipe.negative_constraints.copy()
        if self.recipe.render_intent == "flat_design":
            constraints.extend(["perspective", "shadows", "3d depth", "folded", "wrinkled"])

        return ", ".join(constraints)
